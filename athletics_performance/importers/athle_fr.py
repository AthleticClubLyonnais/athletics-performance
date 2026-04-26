"""Importer for performances from athle.fr website."""

from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .base import PerformanceImporter


class AthleFrImporter(PerformanceImporter):
    """Import performances from athle.fr (Fédération Française d'Athlétisme).

    Scrapes performance data from the results page:
    https://www.athle.fr/bases/liste.aspx?frmbase=resultats&...
    """

    BASE_URL = "https://www.athle.fr/bases/liste.aspx"

    def __init__(self, data_dir: Optional[Path] = None, timeout: int = 30) -> None:
        """Initialize the athle.fr importer.

        Parameters
        ----------
        data_dir : Path, optional
            Directory to store imported Parquet files.
        timeout : int
            Request timeout in seconds (default: 30)
        """
        super().__init__(data_dir)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    @property
    def source_name(self) -> str:
        """Identifier for athle.fr source."""
        return "athle_fr"

    def fetch_data(
        self,
        club_id: str,
        season: int = 2026,
        mode: int = 1,
        **kwargs
    ) -> pd.DataFrame:
        """Fetch performance data from athle.fr for a specific club.

        Parameters
        ----------
        club_id : str
            Club identifier (e.g., "069106")
        season : int
            Athletics season year (default: 2026)
        mode : int
            Results display mode (1: all results, 2: records, etc.)
        **kwargs
            Additional query parameters

        Returns
        -------
        pd.DataFrame
            Raw HTML table data from the page
        """
        params = {
            "frmbase": "resultats",
            "frmmode": mode,
            "frmsaison": season,
            "frmclub": club_id,
            "frmespace": 0,
            "frmpostback": "true",
        }
        params.update(kwargs)

        try:
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch data from athle.fr: {e}")

        # Parse HTML table
        soup = BeautifulSoup(response.content, "html.parser")
        tables = soup.find_all("table")

        if not tables:
            raise ValueError("No results found for the given club and season")

        # Find the results table (usually the main data table)
        # Look for the table with performance data
        data = []
        for table in tables:
            rows = table.find_all("tr")
            if len(rows) > 1:  # At least header + one data row
                data = self._parse_table(rows)
                if data:
                    break

        if not data:
            raise ValueError("Could not parse performance data from the page")

        return pd.DataFrame(data)

    @staticmethod
    def _parse_table(rows: list) -> list[dict]:
        """Parse HTML table rows into data dictionaries.

        Parameters
        ----------
        rows : list
            List of <tr> elements from BeautifulSoup

        Returns
        -------
        list[dict]
            List of row data as dictionaries
        """
        data = []
        headers = []

        for row_idx, row in enumerate(rows):
            cells = row.find_all(["th", "td"])
            cell_texts = [cell.get_text(strip=True) for cell in cells]

            if row_idx == 0:
                # Header row
                headers = cell_texts
            elif cell_texts and any(cell_texts):  # Skip empty rows
                # Data row
                row_dict = {
                    headers[i]: cell_texts[i]
                    for i in range(min(len(headers), len(cell_texts)))
                }
                data.append(row_dict)

        return data

    def parse_performances(self, df: pd.DataFrame) -> pd.DataFrame:
        """Parse athle.fr raw data into standardized performance format.

        Expects columns from athle.fr (French names):
        - Athlète (or Nom/Prénom)
        - Épreuve (event name)
        - Lieu (location/venue)
        - Perf. (performance)
        - Date
        - Licence (athlete license)
        - Club

        Parameters
        ----------
        df : pd.DataFrame
            Raw data from fetch_data()

        Returns
        -------
        pd.DataFrame
            Standardized performance data
        """
        if df.empty:
            return df

        # Make a copy to avoid modifying the original
        result = df.copy()

        # Map French column names to English
        column_mapping = {
            "Athlète": "athlete_name",
            "Nom": "last_name",
            "Prénom": "first_name",
            "Épreuve": "event_name",
            "Lieu": "venue",
            "Perf.": "performance",
            "Perf": "performance",
            "Performance": "performance",
            "Date": "date",
            "Licence": "athlete_id",
            "Club": "club_name",
            "Sexe": "sex",
        }

        # Rename columns
        result = result.rename(columns={k: v for k, v in column_mapping.items() if k in result.columns})

        # Parse date
        if "date" in result.columns:
            result["date"] = pd.to_datetime(result["date"], format="%d/%m/%Y", errors="coerce")

        # Create performance ID if not present
        if "perf_id" not in result.columns:
            athlete_id_col = (
                result["athlete_id"].astype(str)
                if "athlete_id" in result.columns
                else pd.Series(["UNK"] * len(result), index=result.index)
            )
            date_str = (
                result["date"].dt.strftime("%Y%m%d")
                if "date" in result.columns
                else pd.Series(["00000000"] * len(result), index=result.index)
            )
            perf_str = (
                result["performance"].astype(str).str.replace(".", "_", 1)
                if "performance" in result.columns
                else pd.Series(["0"] * len(result), index=result.index)
            )
            result["perf_id"] = athlete_id_col + "_" + date_str + "_" + perf_str

        # Select and reorder standard columns
        standard_cols = [
            "perf_id",
            "athlete_id",
            "athlete_name",
            "first_name",
            "last_name",
            "event_name",
            "performance",
            "venue",
            "date",
            "club_name",
            "sex",
        ]

        available_cols = [col for col in standard_cols if col in result.columns]
        result = result[available_cols + [col for col in result.columns if col not in available_cols]]

        return result

    def close(self) -> None:
        """Close the HTTP session."""
        self.session.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
