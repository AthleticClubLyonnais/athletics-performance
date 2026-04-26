"""Base class for performance importers."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd

from ..storage import DataStore, LocalDataStore


class PerformanceImporter(ABC):
    """Abstract base class for importing performances from various sources.

    Subclasses implement importers for specific websites, file formats,
    or APIs that provide athletic performance data.
    """

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        data_store: Optional[DataStore] = None,
    ) -> None:
        """Initialize the importer.

        Parameters
        ----------
        data_dir : Path, optional
            (Deprecated) Directory to store imported Parquet files.
            Use data_store parameter instead for more flexibility.
            Defaults to athletics_performance/data/imported/
        data_store : DataStore, optional
            Storage backend for performances (local or S3).
            If not provided and data_dir is None, uses LocalDataStore
            with default location.

        Examples
        --------
        >>> # Local storage with custom path
        >>> importer = AthleFrImporter(
        ...     data_store=LocalDataStore('/data/athletics')
        ... )

        >>> # S3 storage
        >>> from athletics_performance.storage import S3DataStore
        >>> importer = AthleFrImporter(
        ...     data_store=S3DataStore('my-bucket', 'performances')
        ... )
        """
        if data_store is not None:
            self.data_store = data_store
            # Keep data_dir for backward compatibility
            self.data_dir = None
        else:
            # Backward compatibility: use data_dir parameter
            if data_dir is None:
                data_dir = Path(__file__).parent.parent / "data" / "imported"
            self.data_dir = Path(data_dir)
            self.data_dir.mkdir(parents=True, exist_ok=True)
            self.data_store = LocalDataStore(base_path=self.data_dir)

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
        self,
        output_file: Optional[str] = None,
        handle_duplicates: str = "skip",
        **kwargs,
    ) -> Path:
        """Fetch, parse, and save performances to Parquet.

        Parameters
        ----------
        output_file : str, optional
            Output filename (default: {source}_performances.parquet)
        handle_duplicates : str, default "skip"
            How to handle duplicate performances:
            - "skip": Keep only new performances, skip existing ones
            - "replace": Replace existing performances with new data
            - "keep": Keep all performances (allow duplicates)
            - "error": Raise ValueError if duplicates found
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

        # Determine output path
        if output_file is None:
            output_file = f"{self.source_name}_performances.parquet"

        # Handle duplicates if file already exists
        if self.data_store.exists(output_file) and handle_duplicates != "keep":
            existing_df = self.data_store.read_parquet(output_file)
            perf_df = self._merge_performances(existing_df, perf_df, handle_duplicates)

        self.data_store.write_parquet(perf_df, output_file)
        return output_file

    @staticmethod
    def _merge_performances(
        existing: pd.DataFrame, new: pd.DataFrame, handle_duplicates: str
    ) -> pd.DataFrame:
        """Merge new performances with existing ones, handling duplicates.

        Parameters
        ----------
        existing : pd.DataFrame
            Previously imported performances
        new : pd.DataFrame
            Newly imported performances
        handle_duplicates : str
            How to handle duplicates ("skip", "replace", "error")

        Returns
        -------
        pd.DataFrame
            Merged performances
        """
        if "perf_id" not in existing.columns or "perf_id" not in new.columns:
            raise ValueError("DataFrames must have 'perf_id' column")

        if handle_duplicates == "skip":
            # Keep existing, skip new duplicates
            new_perf_ids = set(new["perf_id"])
            existing_perf_ids = set(existing["perf_id"])
            duplicates = new_perf_ids & existing_perf_ids
            if duplicates:
                new = new[~new["perf_id"].isin(duplicates)]
            return pd.concat([existing, new], ignore_index=True)

        elif handle_duplicates == "replace":
            # Replace existing with new
            new_perf_ids = set(new["perf_id"])
            existing = existing[~existing["perf_id"].isin(new_perf_ids)]
            return pd.concat([existing, new], ignore_index=True)

        elif handle_duplicates == "error":
            # Raise error if duplicates found
            duplicates = set(new["perf_id"]) & set(existing["perf_id"])
            if duplicates:
                raise ValueError(
                    f"Found {len(duplicates)} duplicate performance IDs: "
                    f"{list(duplicates)[:5]}{'...' if len(duplicates) > 5 else ''}"
                )
            return pd.concat([existing, new], ignore_index=True)

        else:
            raise ValueError(
                f"Invalid handle_duplicates mode: {handle_duplicates}. "
                "Use 'skip', 'replace', 'error', or 'keep'."
            )

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
        return self.data_store.read_parquet(filename)

    def apply_transformation(
        self,
        filename: str,
        transformation_func,
        output_file: Optional[str] = None,
    ) -> str:
        """Apply a transformation function to stored performances and save.

        The transformation function receives a DataFrame and should return
        a modified DataFrame. Can be used to add computed columns, filter,
        or transform existing data.

        Parameters
        ----------
        filename : str
            Source Parquet filename to load
        transformation_func : callable
            Function that takes a DataFrame and returns a modified DataFrame.
            Example: lambda df: df.assign(score=compute_score(df))
        output_file : str, optional
            Output filename (default: overwrites input file)

        Returns
        -------
        str
            Path to the saved Parquet file

        Examples
        --------
        >>> def add_scores(df):
        ...     df['score'] = df['performance'].apply(compute_score)
        ...     return df
        >>> importer.apply_transformation(
        ...     'data.parquet',
        ...     add_scores,
        ...     'data_scored.parquet'
        ... )
        """
        # Load data
        df = self.load_from_parquet(filename)

        # Apply transformation
        transformed_df = transformation_func(df)

        # Validate result
        if not isinstance(transformed_df, pd.DataFrame):
            raise TypeError(
                f"transformation_func must return a DataFrame, "
                f"got {type(transformed_df)}"
            )

        # Determine output path
        if output_file is None:
            output_file = filename

        # Save result
        self.data_store.write_parquet(transformed_df, output_file)
        return output_file

    def get_duplicates(self, filename: str) -> pd.DataFrame:
        """Find duplicate performances in stored Parquet file.

        Returns all rows that have duplicate perf_id values.

        Parameters
        ----------
        filename : str
            Parquet filename to check

        Returns
        -------
        pd.DataFrame
            DataFrame containing only duplicate performances,
            sorted by perf_id
        """
        df = self.load_from_parquet(filename)

        if "perf_id" not in df.columns:
            raise ValueError("DataFrame must have 'perf_id' column")

        # Find duplicate perf_ids
        duplicate_mask = df.duplicated(subset=["perf_id"], keep=False)
        duplicates = df[duplicate_mask].sort_values("perf_id")

        return duplicates

    def deduplicate(
        self,
        filename: str,
        keep: str = "first",
        output_file: Optional[str] = None,
    ) -> str:
        """Remove duplicate performances from stored Parquet file.

        Parameters
        ----------
        filename : str
            Source Parquet filename
        keep : str, default "first"
            Which duplicates to keep:
            - "first": Keep first occurrence of each perf_id
            - "last": Keep last occurrence of each perf_id
        output_file : str, optional
            Output filename (default: overwrites input file)

        Returns
        -------
        str
            Path to the deduplicated Parquet file
        """
        df = self.load_from_parquet(filename)

        if "perf_id" not in df.columns:
            raise ValueError("DataFrame must have 'perf_id' column")

        df_dedup = df.drop_duplicates(subset=["perf_id"], keep=keep)

        if output_file is None:
            output_file = filename

        self.data_store.write_parquet(df_dedup, output_file)

        return output_file

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this import source."""
        pass
