"""Tests for performance importers."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from athletics_performance.importers import AthleFrImporter, PerformanceImporter


class TestPerformanceImporter:
    """Tests for the abstract PerformanceImporter base class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """PerformanceImporter is abstract and cannot be instantiated."""
        with pytest.raises(TypeError):
            PerformanceImporter()  # type: ignore

    def test_data_dir_created_if_not_exists(self) -> None:
        """Data directory is created automatically if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir) / "nonexistent" / "path"
            assert not data_dir.exists()

            # Subclass for testing
            class ConcreteImporter(PerformanceImporter):
                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    return pd.DataFrame()

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            ConcreteImporter(data_dir)
            assert data_dir.exists()

    def test_parquet_roundtrip(self) -> None:
        """Data can be imported and loaded from Parquet."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            class ConcreteImporter(PerformanceImporter):
                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    return pd.DataFrame({"col1": [1, 2, 3]})

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            importer = ConcreteImporter(data_dir)

            # Import data
            output_path = importer.import_to_parquet("test_data.parquet")
            assert output_path.exists()

            # Load it back
            loaded = importer.load_from_parquet("test_data.parquet")
            assert loaded.shape == (3, 1)
            assert list(loaded["col1"]) == [1, 2, 3]

    def test_handle_duplicates_skip(self) -> None:
        """Duplicate performances are skipped when handle_duplicates='skip'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            class ConcreteImporter(PerformanceImporter):
                def __init__(self, data_dir, call_count=0):
                    super().__init__(data_dir)
                    self.call_count = call_count

                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    # Return different data each call
                    if self.call_count == 0:
                        return pd.DataFrame({
                            "perf_id": ["P1", "P2"],
                            "value": [10, 20],
                        })
                    else:
                        return pd.DataFrame({
                            "perf_id": ["P2", "P3"],  # P2 is duplicate
                            "value": [20, 30],
                        })

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            importer = ConcreteImporter(data_dir)

            # First import
            importer.import_to_parquet(
                "test_data.parquet",
                handle_duplicates="skip"
            )

            # Second import with duplicate P2
            importer.call_count = 1
            importer.import_to_parquet(
                "test_data.parquet",
                handle_duplicates="skip"
            )

            # Check result - should have P1, P2, P3 but not duplicate P2
            loaded = importer.load_from_parquet("test_data.parquet")
            assert len(loaded) == 3
            assert set(loaded["perf_id"]) == {"P1", "P2", "P3"}

    def test_handle_duplicates_replace(self) -> None:
        """Duplicate performances are replaced when handle_duplicates='replace'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            class ConcreteImporter(PerformanceImporter):
                def __init__(self, data_dir, call_count=0):
                    super().__init__(data_dir)
                    self.call_count = call_count

                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    if self.call_count == 0:
                        return pd.DataFrame({
                            "perf_id": ["P1", "P2"],
                            "value": [10, 20],
                        })
                    else:
                        return pd.DataFrame({
                            "perf_id": ["P2"],  # Replace P2
                            "value": [999],
                        })

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            importer = ConcreteImporter(data_dir)

            # First import
            importer.import_to_parquet(
                "test_data.parquet",
                handle_duplicates="skip"
            )

            # Second import replacing P2
            importer.call_count = 1
            importer.import_to_parquet(
                "test_data.parquet",
                handle_duplicates="replace"
            )

            loaded = importer.load_from_parquet("test_data.parquet")
            p2_row = loaded[loaded["perf_id"] == "P2"]
            assert p2_row["value"].iloc[0] == 999

    def test_handle_duplicates_error(self) -> None:
        """ValueError raised when duplicates found with handle_duplicates='error'."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            class ConcreteImporter(PerformanceImporter):
                def __init__(self, data_dir, call_count=0):
                    super().__init__(data_dir)
                    self.call_count = call_count

                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    if self.call_count == 0:
                        return pd.DataFrame({
                            "perf_id": ["P1", "P2"],
                            "value": [10, 20],
                        })
                    else:
                        return pd.DataFrame({
                            "perf_id": ["P2", "P3"],
                            "value": [20, 30],
                        })

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            importer = ConcreteImporter(data_dir)

            # First import
            importer.import_to_parquet(
                "test_data.parquet",
                handle_duplicates="skip"
            )

            # Second import should error on duplicates
            importer.call_count = 1
            with pytest.raises(ValueError, match="Found .* duplicate"):
                importer.import_to_parquet(
                    "test_data.parquet",
                    handle_duplicates="error"
                )

    def test_apply_transformation(self) -> None:
        """Transformations can be applied to stored performances."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            class ConcreteImporter(PerformanceImporter):
                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    return pd.DataFrame({"value": [1, 2, 3]})

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            importer = ConcreteImporter(data_dir)
            importer.import_to_parquet("test_data.parquet")

            # Apply transformation
            def double_values(df: pd.DataFrame) -> pd.DataFrame:
                df["value"] = df["value"] * 2
                return df

            importer.apply_transformation(
                "test_data.parquet",
                double_values
            )

            loaded = importer.load_from_parquet("test_data.parquet")
            assert list(loaded["value"]) == [2, 4, 6]

    def test_apply_transformation_add_column(self) -> None:
        """Transformations can add new columns to stored data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            class ConcreteImporter(PerformanceImporter):
                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    return pd.DataFrame({
                        "perf_id": ["P1", "P2"],
                        "performance": ["10.5", "11.2"],
                    })

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            importer = ConcreteImporter(data_dir)
            importer.import_to_parquet("test_data.parquet")

            # Add computed column
            def add_scores(df: pd.DataFrame) -> pd.DataFrame:
                df["score"] = df["performance"].astype(float).apply(lambda x: int(1000 / x))
                return df

            importer.apply_transformation(
                "test_data.parquet",
                add_scores
            )

            loaded = importer.load_from_parquet("test_data.parquet")
            assert "score" in loaded.columns
            assert loaded["score"].iloc[0] > 0

    def test_get_duplicates(self) -> None:
        """Duplicate performances can be identified."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            class ConcreteImporter(PerformanceImporter):
                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    return pd.DataFrame({
                        "perf_id": ["P1", "P2", "P2", "P3"],
                        "value": [10, 20, 20, 30],
                    })

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            importer = ConcreteImporter(data_dir)
            importer.import_to_parquet("test_data.parquet", handle_duplicates="keep")

            duplicates = importer.get_duplicates("test_data.parquet")
            assert len(duplicates) == 2  # Both P2 entries
            assert all(duplicates["perf_id"] == "P2")

    def test_deduplicate(self) -> None:
        """Duplicate performances can be removed."""
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = Path(tmpdir)

            class ConcreteImporter(PerformanceImporter):
                @property
                def source_name(self) -> str:
                    return "test"

                def fetch_data(self, **kwargs) -> pd.DataFrame:
                    return pd.DataFrame({
                        "perf_id": ["P1", "P2", "P2", "P3"],
                        "value": [10, 20, 25, 30],
                    })

                def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
                    return df

            importer = ConcreteImporter(data_dir)
            importer.import_to_parquet("test_data.parquet", handle_duplicates="keep")

            # Keep first occurrence
            importer.deduplicate("test_data.parquet", keep="first")
            loaded = importer.load_from_parquet("test_data.parquet")
            assert len(loaded) == 3
            p2_row = loaded[loaded["perf_id"] == "P2"]
            assert p2_row["value"].iloc[0] == 20  # First occurrence


class TestAthleFrImporter:
    """Tests for the athle.fr performance importer."""

    def test_source_name(self) -> None:
        """Source name is correctly identified."""
        importer = AthleFrImporter()
        assert importer.source_name == "athle_fr"

    def test_context_manager(self) -> None:
        """AthleFrImporter works as a context manager."""
        with AthleFrImporter() as importer:
            assert importer is not None
            assert hasattr(importer, "session")

    @patch("athletics_performance.importers.athle_fr.requests.Session.get")
    def test_fetch_data_successful(self, mock_get: MagicMock) -> None:
        """fetch_data returns a DataFrame when HTML is valid."""
        # Create mock response
        html_content = """
        <html>
            <table>
                <tr><th>Athlète</th><th>Épreuve</th><th>Perf.</th><th>Date</th></tr>
                <tr><td>John Doe</td><td>100m</td><td>10.5</td><td>01/01/2026</td></tr>
                <tr><td>Jane Smith</td><td>200m</td><td>23.1</td><td>15/01/2026</td></tr>
            </table>
        </html>
        """
        mock_response = MagicMock()
        mock_response.content = html_content.encode()
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        importer = AthleFrImporter()
        df = importer.fetch_data(club_id="069106")

        # Check the DataFrame structure
        assert not df.empty
        assert "Athlète" in df.columns
        assert len(df) == 2

        # Verify the request was made with correct parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["params"]["frmclub"] == "069106"
        assert call_args[1]["params"]["frmbase"] == "resultats"

    @patch("athletics_performance.importers.athle_fr.requests.Session.get")
    def test_fetch_data_no_tables_raises_error(self, mock_get: MagicMock) -> None:
        """fetch_data raises ValueError when no tables are found."""
        mock_response = MagicMock()
        mock_response.content = b"<html><body>No tables here</body></html>"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        importer = AthleFrImporter()
        with pytest.raises(ValueError, match="No results found"):
            importer.fetch_data(club_id="069106")

    @patch("athletics_performance.importers.athle_fr.requests.Session.get")
    def test_fetch_data_network_error_raises_error(self, mock_get: MagicMock) -> None:
        """fetch_data raises ValueError on network errors."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Network error")

        importer = AthleFrImporter()
        with pytest.raises(ValueError, match="Failed to fetch data"):
            importer.fetch_data(club_id="069106")

    def test_parse_performances_empty_dataframe(self) -> None:
        """parse_performances handles empty DataFrames gracefully."""
        importer = AthleFrImporter()
        result = importer.parse_performances(pd.DataFrame())
        assert result.empty

    def test_parse_performances_column_mapping(self) -> None:
        """parse_performances maps French column names correctly."""
        importer = AthleFrImporter()

        df = pd.DataFrame({
            "Athlète": ["John Doe"],
            "Épreuve": ["100m"],
            "Perf.": ["10.5"],
            "Date": ["01/01/2026"],
            "Licence": ["12345"],
            "Club": ["AC Lyon"],
            "Lieu": ["Paris"],
            "Sexe": ["M"],
        })

        result = importer.parse_performances(df)

        assert "athlete_name" in result.columns
        assert "event_name" in result.columns
        assert "performance" in result.columns
        assert "date" in result.columns
        assert "athlete_id" in result.columns
        assert "club_name" in result.columns
        assert "venue" in result.columns
        assert "sex" in result.columns

    def test_parse_performances_date_parsing(self) -> None:
        """parse_performances correctly parses French date format."""
        importer = AthleFrImporter()

        df = pd.DataFrame({
            "Athlète": ["John Doe"],
            "Date": ["15/03/2026"],
        })

        result = importer.parse_performances(df)

        assert pd.notna(result["date"].iloc[0])
        assert result["date"].iloc[0].day == 15
        assert result["date"].iloc[0].month == 3
        assert result["date"].iloc[0].year == 2026

    def test_parse_performances_generates_perf_id(self) -> None:
        """parse_performances generates unique performance IDs."""
        importer = AthleFrImporter()

        df = pd.DataFrame({
            "Athlète": ["John Doe", "Jane Smith"],
            "Licence": ["12345", "67890"],
            "Date": ["01/01/2026", "02/01/2026"],
            "Perf.": ["10.5", "11.2"],
        })

        result = importer.parse_performances(df)

        assert "perf_id" in result.columns
        assert result["perf_id"].iloc[0] != result["perf_id"].iloc[1]
        assert "12345" in result["perf_id"].iloc[0]
        assert "20260101" in result["perf_id"].iloc[0]

    def test_parse_performances_handles_missing_columns(self) -> None:
        """parse_performances handles DataFrames with missing optional columns."""
        importer = AthleFrImporter()

        df = pd.DataFrame({
            "Athlète": ["John Doe"],
            "Épreuve": ["100m"],
        })

        result = importer.parse_performances(df)

        assert "athlete_name" in result.columns
        assert "event_name" in result.columns
        # Optional columns shouldn't cause errors
        assert len(result) == 1
