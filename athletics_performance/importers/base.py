"""Base class for performance importers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd


class PerformanceImporter(ABC):
    """Abstract base class for importing performances from various sources.

    Subclasses implement importers for specific websites, file formats,
    or APIs that provide athletic performance data.
    """

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        """Initialize the importer.

        Parameters
        ----------
        data_dir : Path, optional
            Directory to store imported Parquet files. Defaults to
            athletics_performance/data/imported/
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "imported"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @abstractmethod
    def fetch_data(self, **kwargs) -> pd.DataFrame:
        """Fetch performance data from the source.

        Returns
        -------
        pd.DataFrame
            Raw data from the source with columns that vary by source.
        """
        pass

    @abstractmethod
    def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse raw source data into standardized performance format.

        Parameters
        ----------
        df : pd.DataFrame
            Raw data from fetch_data()

        Returns
        -------
        pd.DataFrame
            Standardized performance data with columns:
            - perf_id: unique identifier
            - athlete_id: athlete license number
            - date: competition date
            - event_id: event code
            - result_value: numeric result
            - venue: competition location
            - club_id: athlete's club
            - and optional metadata columns
        """
        pass

    def import_to_parquet(
        self, output_file: Optional[str] = None, **kwargs
    ) -> Path:
        """Fetch, parse, and save performances to Parquet.

        Parameters
        ----------
        output_file : str, optional
            Output filename (default: {source}_performances.parquet)
        **kwargs
            Arguments passed to fetch_data()

        Returns
        -------
        Path
            Path to the saved Parquet file
        """
        # Fetch raw data
        raw_df = self.fetch_data(**kwargs)

        # Parse to standard format
        perf_df = self.parse_performances(raw_df)

        # Save to Parquet
        if output_file is None:
            output_file = f"{self.source_name}_performances.parquet"
        output_path = self.data_dir / output_file

        perf_df.to_parquet(output_path, index=False)
        return output_path

    def load_from_parquet(self, filename: str) -> pd.DataFrame:
        """Load previously imported performances from Parquet.

        Parameters
        ----------
        filename : str
            Parquet filename to load

        Returns
        -------
        pd.DataFrame
            Loaded performance data
        """
        path = self.data_dir / filename
        return pd.read_parquet(path)

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this import source."""
        pass
