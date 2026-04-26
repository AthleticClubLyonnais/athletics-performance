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
