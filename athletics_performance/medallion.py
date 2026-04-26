"""Medallion architecture for performance data engineering.

Implements the bronze/silver/gold data lakehouse pattern:
- Bronze: Raw imported data, minimally processed
- Silver: Cleaned, validated, deduplicated, with computed features
- Gold: Aggregated, denormalized data ready for analytics and visualization

This enables data lineage, auditability, and supports iterative refinement
of data processing pipelines.
"""

from typing import Callable

import pandas as pd

from .storage import DataStore


class PerformanceMedallion:
    """Manages performance data across medallion architecture layers."""

    def __init__(self, data_store: DataStore) -> None:
        """Initialize medallion layer manager.

        Parameters
        ----------
        data_store : DataStore
            Storage backend (local or S3) for managing all layers
        """
        self.store = data_store

    def save_bronze(
        self, df: pd.DataFrame, name: str, overwrite: bool = False
    ) -> str:
        """Save raw performance data to bronze layer.

        Bronze layer contains raw, minimally processed data from importers.
        Preserves all original columns and data as received.

        Parameters
        ----------
        df : pd.DataFrame
            Raw performance data
        name : str
            Dataset name (e.g., 'ac_lyon_2026', 'athle_fr_april_2026')
        overwrite : bool, default False
            If False, raises error if file exists. If True, overwrites.

        Returns
        -------
        str
            Path to saved bronze layer file

        Examples
        --------
        >>> medallion.save_bronze(raw_df, 'ac_lyon_2026')
        'bronze/ac_lyon_2026.parquet'
        """
        path = f"bronze/{name}.parquet"

        if self.store.exists(path) and not overwrite:
            raise FileExistsError(
                f"Bronze dataset '{name}' already exists. "
                "Use overwrite=True to replace."
            )

        self.store.write_parquet(df, path)
        return path

    def load_bronze(self, name: str) -> pd.DataFrame:
        """Load raw performance data from bronze layer.

        Parameters
        ----------
        name : str
            Dataset name

        Returns
        -------
        pd.DataFrame
            Raw performance data
        """
        path = f"bronze/{name}.parquet"
        return self.store.read_parquet(path)

    def save_silver(
        self, df: pd.DataFrame, name: str, overwrite: bool = False
    ) -> str:
        """Save processed performance data to silver layer.

        Silver layer contains cleaned, validated, deduplicated data with
        computed features (scores, derived fields, etc.) but still organized
        by the original data structure.

        Parameters
        ----------
        df : pd.DataFrame
            Processed performance data
        name : str
            Dataset name (e.g., 'ac_lyon_2026_processed')
        overwrite : bool, default False
            If False, raises error if file exists. If True, overwrites.

        Returns
        -------
        str
            Path to saved silver layer file

        Examples
        --------
        >>> # Add computed scores and save to silver
        >>> df['wa_points'] = df.apply(lambda r: compute_score(r), axis=1)
        >>> medallion.save_silver(df, 'ac_lyon_2026_scored')
        'silver/ac_lyon_2026_scored.parquet'
        """
        path = f"silver/{name}.parquet"

        if self.store.exists(path) and not overwrite:
            raise FileExistsError(
                f"Silver dataset '{name}' already exists. "
                "Use overwrite=True to replace."
            )

        self.store.write_parquet(df, path)
        return path

    def load_silver(self, name: str) -> pd.DataFrame:
        """Load processed performance data from silver layer.

        Parameters
        ----------
        name : str
            Dataset name

        Returns
        -------
        pd.DataFrame
            Processed performance data
        """
        path = f"silver/{name}.parquet"
        return self.store.read_parquet(path)

    def save_gold(
        self, df: pd.DataFrame, name: str, overwrite: bool = False
    ) -> str:
        """Save analytics-ready performance data to gold layer.

        Gold layer contains aggregated, denormalized data optimized for
        visualization and data science analysis. Examples: club records by
        event, athlete rankings, performance trends over time.

        Parameters
        ----------
        df : pd.DataFrame
            Aggregated/denormalized analytics data
        name : str
            Dataset name (e.g., 'club_records_2026', 'athlete_rankings')
        overwrite : bool, default False
            If False, raises error if file exists. If True, overwrites.

        Returns
        -------
        str
            Path to saved gold layer file

        Examples
        --------
        >>> # Save club records
        >>> records = compute_club_records(medallion.load_silver('data'))
        >>> medallion.save_gold(records, 'club_records_2026')
        'gold/club_records_2026.parquet'
        """
        path = f"gold/{name}.parquet"

        if self.store.exists(path) and not overwrite:
            raise FileExistsError(
                f"Gold dataset '{name}' already exists. "
                "Use overwrite=True to replace."
            )

        self.store.write_parquet(df, path)
        return path

    def load_gold(self, name: str) -> pd.DataFrame:
        """Load analytics-ready performance data from gold layer.

        Parameters
        ----------
        name : str
            Dataset name

        Returns
        -------
        pd.DataFrame
            Analytics-ready data
        """
        path = f"gold/{name}.parquet"
        return self.store.read_parquet(path)

    def list_bronze(self) -> list[str]:
        """List all raw datasets in bronze layer."""
        return self.store.list_files("bronze")

    def list_silver(self) -> list[str]:
        """List all processed datasets in silver layer."""
        return self.store.list_files("silver")

    def list_gold(self) -> list[str]:
        """List all analytics datasets in gold layer."""
        return self.store.list_files("gold")

    def process_pipeline(
        self,
        bronze_name: str,
        silver_name: str,
        transformations: list[Callable[[pd.DataFrame], pd.DataFrame]],
        overwrite: bool = False,
    ) -> pd.DataFrame:
        """Process raw data through bronze → silver pipeline.

        Applies a sequence of transformations to bronze data and saves
        result to silver layer, maintaining full lineage.

        Parameters
        ----------
        bronze_name : str
            Source dataset name in bronze layer
        silver_name : str
            Target dataset name in silver layer
        transformations : list of callable
            Functions to apply in sequence. Each function takes a DataFrame
            and returns a DataFrame.
        overwrite : bool, default False
            If True, overwrites existing silver dataset

        Returns
        -------
        pd.DataFrame
            Processed data (also saved to silver layer)

        Examples
        --------
        >>> medallion.process_pipeline(
        ...     'ac_lyon_2026',
        ...     'ac_lyon_2026_processed',
        ...     [
        ...         lambda df: df.drop_duplicates(subset=['perf_id']),
        ...         lambda df: df.assign(score=df['perf'].apply(compute_score)),
        ...         lambda df: df[df['score'].notna()],  # filter invalid
        ...     ]
        ... )
        """
        # Load raw data
        df = self.load_bronze(bronze_name)

        # Apply transformations
        for transform in transformations:
            df = transform(df)

        # Save to silver
        self.save_silver(df, silver_name, overwrite=overwrite)

        return df

    def analytics_pipeline(
        self,
        silver_name: str,
        gold_name: str,
        aggregation_func: Callable[[pd.DataFrame], pd.DataFrame],
        overwrite: bool = False,
    ) -> pd.DataFrame:
        """Generate analytics-ready data from silver → gold pipeline.

        Takes processed data from silver layer, applies aggregation/
        denormalization, and saves to gold layer for visualization.

        Parameters
        ----------
        silver_name : str
            Source dataset name in silver layer
        gold_name : str
            Target dataset name in gold layer
        aggregation_func : callable
            Function that takes silver DataFrame and returns aggregated/
            denormalized gold DataFrame
        overwrite : bool, default False
            If True, overwrites existing gold dataset

        Returns
        -------
        pd.DataFrame
            Analytics-ready data (also saved to gold layer)

        Examples
        --------
        >>> def club_records(df):
        ...     return df.loc[df.groupby('event_name')['result_value'].idxmin()]
        >>> medallion.analytics_pipeline(
        ...     'ac_lyon_2026_processed',
        ...     'club_records_2026',
        ...     club_records
        ... )
        """
        # Load processed data
        df = self.load_silver(silver_name)

        # Apply aggregation
        analytics_df = aggregation_func(df)

        # Save to gold
        self.save_gold(analytics_df, gold_name, overwrite=overwrite)

        return analytics_df
