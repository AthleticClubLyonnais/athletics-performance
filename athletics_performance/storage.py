"""Flexible data storage backend supporting local and S3 storage.

This module provides an abstraction layer for storing and retrieving performance
data, supporting both local filesystem and AWS S3, allowing users to choose where
their potentially large performance databases are stored independently of the
installed package.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Union

import pandas as pd


class DataStore(ABC):
    """Abstract base class for performance data storage backends."""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a file exists at the given path."""
        pass

    @abstractmethod
    def read_parquet(self, path: str) -> pd.DataFrame:
        """Read a Parquet file from storage."""
        pass

    @abstractmethod
    def write_parquet(
        self, df: pd.DataFrame, path: str, index: bool = False
    ) -> None:
        """Write a Parquet file to storage."""
        pass

    @abstractmethod
    def list_files(self, directory: str) -> list[str]:
        """List all files in a directory."""
        pass

    @abstractmethod
    def delete(self, path: str) -> None:
        """Delete a file from storage."""
        pass


class LocalDataStore(DataStore):
    """Local filesystem storage backend."""

    def __init__(self, base_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize local data store.

        Parameters
        ----------
        base_path : str or Path, optional
            Base directory for storing data. If not provided, uses
            {user_home}/.athletics_performance/data/
        """
        if base_path is None:
            base_path = Path.home() / ".athletics_performance" / "data"
        else:
            base_path = Path(base_path)

        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def exists(self, path: str) -> bool:
        """Check if file exists."""
        return (self.base_path / path).exists()

    def read_parquet(self, path: str) -> pd.DataFrame:
        """Read Parquet file from local storage."""
        file_path = self.base_path / path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        return pd.read_parquet(file_path)

    def write_parquet(
        self, df: pd.DataFrame, path: str, index: bool = False
    ) -> None:
        """Write Parquet file to local storage."""
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(file_path, index=index)

    def list_files(self, directory: str) -> list[str]:
        """List Parquet files in directory."""
        dir_path = self.base_path / directory
        if not dir_path.exists():
            return []
        return [f.name for f in dir_path.glob("*.parquet")]

    def delete(self, path: str) -> None:
        """Delete a file from local storage."""
        file_path = self.base_path / path
        if file_path.exists():
            file_path.unlink()


class S3DataStore(DataStore):
    """AWS S3 storage backend."""

    def __init__(
        self,
        bucket: str,
        prefix: str = "athletics-performance",
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
    ) -> None:
        """Initialize S3 data store.

        Parameters
        ----------
        bucket : str
            S3 bucket name
        prefix : str, default "athletics-performance"
            Prefix path in S3 bucket (subdirectory)
        aws_access_key_id : str, optional
            AWS access key. If not provided, uses AWS credentials chain
            (environment variables, IAM role, etc.)
        aws_secret_access_key : str, optional
            AWS secret access key
        region_name : str, default "us-east-1"
            AWS region
        """
        try:
            import boto3
        except ImportError:
            raise ImportError(
                "boto3 is required for S3 support. "
                "Install with: pip install boto3"
            )

        self.bucket = bucket
        self.prefix = prefix.rstrip("/")
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            region_name=region_name,
        )

    def _s3_path(self, path: str) -> str:
        """Convert local-style path to S3 key."""
        return f"{self.prefix}/{path}".lstrip("/")

    def exists(self, path: str) -> bool:
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket, Key=self._s3_path(path)
            )
            return True
        except self.s3_client.exceptions.NoSuchKey:
            return False

    def read_parquet(self, path: str) -> pd.DataFrame:
        """Read Parquet file from S3."""
        s3_path = f"s3://{self.bucket}/{self._s3_path(path)}"
        return pd.read_parquet(s3_path)

    def write_parquet(
        self, df: pd.DataFrame, path: str, index: bool = False
    ) -> None:
        """Write Parquet file to S3."""
        s3_path = f"s3://{self.bucket}/{self._s3_path(path)}"
        df.to_parquet(s3_path, index=index)

    def list_files(self, directory: str) -> list[str]:
        """List Parquet files in S3 directory."""
        prefix = self._s3_path(directory)
        if not prefix.endswith("/"):
            prefix += "/"

        response = self.s3_client.list_objects_v2(
            Bucket=self.bucket, Prefix=prefix
        )

        if "Contents" not in response:
            return []

        return [
            obj["Key"].split("/")[-1]
            for obj in response["Contents"]
            if obj["Key"].endswith(".parquet")
        ]

    def delete(self, path: str) -> None:
        """Delete a file from S3."""
        if self.exists(path):
            self.s3_client.delete_object(
                Bucket=self.bucket, Key=self._s3_path(path)
            )


def get_default_data_store(
    storage_config: Optional[dict] = None,
) -> DataStore:
    """Get a data store instance from configuration.

    Parameters
    ----------
    storage_config : dict, optional
        Configuration dictionary with keys:
        - 'type': 'local' or 's3' (default: 'local')
        - 'path': Local path (for local storage)
        - 'bucket': S3 bucket (for S3 storage)
        - 'prefix': S3 prefix (for S3 storage, default: 'athletics-performance')
        - 'region': AWS region (for S3 storage, default: 'us-east-1')

        If not provided, uses environment variables:
        - ATHLETICS_STORAGE_TYPE: 'local' or 's3'
        - ATHLETICS_STORAGE_PATH: Local path
        - ATHLETICS_S3_BUCKET: S3 bucket
        - ATHLETICS_S3_PREFIX: S3 prefix
        - ATHLETICS_AWS_REGION: AWS region

    Returns
    -------
    DataStore
        Configured data store instance

    Examples
    --------
    >>> # Local storage (default)
    >>> store = get_default_data_store({'type': 'local', 'path': '/data/athletics'})
    >>> store = get_default_data_store()  # Uses ~/.athletics_performance/data/

    >>> # S3 storage
    >>> store = get_default_data_store({
    ...     'type': 's3',
    ...     'bucket': 'my-athletics-bucket',
    ...     'prefix': 'performances'
    ... })
    """
    import os

    if storage_config is None:
        storage_config = {}

    storage_type = storage_config.get(
        "type", os.environ.get("ATHLETICS_STORAGE_TYPE", "local")
    )

    if storage_type == "s3":
        bucket = storage_config.get(
            "bucket", os.environ.get("ATHLETICS_S3_BUCKET")
        )
        if not bucket:
            raise ValueError(
                "S3 bucket must be specified via 'bucket' config or "
                "ATHLETICS_S3_BUCKET environment variable"
            )

        prefix = storage_config.get(
            "prefix",
            os.environ.get(
                "ATHLETICS_S3_PREFIX", "athletics-performance"
            ),
        )
        region = storage_config.get(
            "region", os.environ.get("ATHLETICS_AWS_REGION", "us-east-1")
        )

        return S3DataStore(bucket=bucket, prefix=prefix, region_name=region)

    else:  # local
        path = storage_config.get(
            "path", os.environ.get("ATHLETICS_STORAGE_PATH")
        )
        return LocalDataStore(base_path=path)
