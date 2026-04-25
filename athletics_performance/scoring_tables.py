"""
Scoring tables: abstract base and category-specific implementations.

This module provides a hierarchical system for different athletics scoring tables,
each applicable to specific athlete categories (age groups).

- `ScoringTable`: Abstract base class for all scoring tables.
- `WorldAthletics2025ScoringTable`: Official World Athletics 2025 tables (senior categories).
- `ScoringTableResolver`: Factory to select the appropriate table for an athlete's category.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import pandas as pd

_SECTIONS = [
    ("M", 9, 38),
    ("M", 39, 68),
    ("M", 69, 98),
    ("M", 99, 128),
    ("M", 129, 158),
    ("M", 159, 188),
    ("M", 189, 218),
    ("M", 219, 248),
    ("M", 249, 278),
    ("M", 279, 308),
    ("M", 309, 337),
    ("M", 338, 367),
    ("M", 368, 397),
    ("M", 398, 427),
    ("W", 428, 457),
    ("W", 458, 487),
    ("W", 488, 517),
    ("W", 518, 547),
    ("W", 548, 577),
    ("W", 578, 607),
    ("W", 608, 637),
    ("W", 638, 667),
    ("W", 668, 697),
    ("W", 698, 727),
    ("W", 728, 757),
    ("W", 758, 787),
    ("W", 788, 817),
    ("W", 818, 845),
]

_DISTANCE_PREFIXES = frozenset(
    [
        "HJ",
        "PV",
        "LJ",
        "TJ",
        "SP",
        "DT",
        "HT",
        "JT",
        "WT",
        "Dec",
        "Hept",
        "Pent",
        "Pentat",
    ]
)


class ScoringTable(ABC):
    """
    Abstract base class for athletics scoring tables.

    Each subclass represents a scoring system applicable to specific athlete
    categories (age groups, gender).

    Subclasses must implement:
    - score(): Return points for a performance
    - performance_for_points(): Return required performance for a points level
    - available_events(): List available events
    """

    @property
    @abstractmethod
    def applicable_categories(self) -> frozenset[str]:
        """
        Categories (age groups) this scoring table applies to.

        Returns
        -------
        frozenset[str]
            Set of category codes (e.g., {"CA", "JU", "ES", "SE", "M", "M0", "M1", ...}).
        """
        pass

    @abstractmethod
    def score(self, sex: str, event_id: str, performance: float) -> int:
        """
        Return points for a given performance.

        Parameters
        ----------
        sex : {"M", "W"}
            Athlete sex.
        event_id : str
            Event identifier (e.g., "100m", "LJ").
        performance : float
            Performance value in standard units (seconds or metres).

        Returns
        -------
        int
            Points awarded. Returns 0 if performance does not qualify.
        """
        pass

    @abstractmethod
    def performance_for_points(self, sex: str, event_id: str, points: int) -> float:
        """
        Return the minimum performance required for a given points level.

        Parameters
        ----------
        sex : {"M", "W"}
            Athlete sex.
        event_id : str
            Event identifier.
        points : int
            Points level.

        Returns
        -------
        float
            Minimum performance (seconds or metres).

        Raises
        ------
        ValueError
            If no data exists for the given points level.
        """
        pass

    @abstractmethod
    def available_events(self, sex: str | None = None) -> list[str]:
        """
        List all available events.

        Parameters
        ----------
        sex : {"M", "W"}, optional
            Filter by sex. If None, return all.

        Returns
        -------
        list[str]
            Sorted list of event identifiers.
        """
        pass

    @staticmethod
    def _is_time_event(event_id: str) -> bool:
        """Determine if an event is time-based (lower is better)."""
        for prefix in _DISTANCE_PREFIXES:
            if event_id.startswith(prefix):
                return False
        return True


class WorldAthletics2025ScoringTable(ScoringTable):
    """
    Official World Athletics 2025 scoring tables.

    Applicable to senior categories: CA (16–17), JU (18–19), ES (20–22),
    SE (23–34), and M (35+, broken down into 5-year brackets: M0, M1, ..., M9).

    Parameters
    ----------
    df : pd.DataFrame
        Loaded table with columns: sex, event, points, performance.
    """

    # Senior categories for which WA tables apply
    _APPLICABLE = frozenset(
        ["CA", "JU", "ES", "SE", "M", "M0", "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"]
    )

    DATA_PATH = (
        Path(__file__).parent / "data" / "world_athletics_scoring_tables_2025.parquet"
    )
    PDF_PATH = (
        Path(__file__).parent / "data" / "World_Athletics_Scoring_Tables_2025.pdf"
    )

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    @property
    def applicable_categories(self) -> frozenset[str]:
        """World Athletics tables apply to all senior categories."""
        return self._APPLICABLE

    @classmethod
    def build_from_pdf(cls, pdf_path: Optional[Path] = None) -> None:
        """
        Parse World Athletics PDF and save as parquet.

        Run once to generate the lookup table. Subsequent imports use load().

        Parameters
        ----------
        pdf_path : Path, optional
            Path to PDF. Defaults to PDF_PATH.
        """
        import pdfplumber

        if pdf_path is None:
            pdf_path = cls.PDF_PATH

        records = []

        with pdfplumber.open(pdf_path) as pdf:
            for sex, start_page, end_page in _SECTIONS:
                for page_num in range(start_page - 1, end_page):
                    page = pdf.pages[page_num]
                    page_records = cls._parse_page(page, sex)
                    records.extend(page_records)

        if not records:
            raise ValueError("No scoring table data extracted from PDF")

        df = pd.DataFrame(records, columns=["sex", "event", "points", "performance"])
        df.drop_duplicates(
            subset=["sex", "event", "points"], keep="first", inplace=True
        )
        df["points"] = df["points"].astype("int16")
        df["performance"] = df["performance"].astype("float32")

        cls.DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(cls.DATA_PATH, index=False)

    @classmethod
    def load(cls) -> WorldAthletics2025ScoringTable:
        """
        Load scoring tables from parquet into memory.

        Returns
        -------
        WorldAthletics2025ScoringTable
            Ready-to-use instance.

        Raises
        ------
        FileNotFoundError
            If parquet file does not exist.
        """
        if not cls.DATA_PATH.exists():
            raise FileNotFoundError(
                f"Parquet file not found at {cls.DATA_PATH}. "
                "Run WorldAthletics2025ScoringTable.build_from_pdf() first."
            )
        df = pd.read_parquet(cls.DATA_PATH)
        return cls(df)

    def score(self, sex: str, event_id: str, performance: float) -> int:
        """
        Return World Athletics points for a given performance.

        For time events, lower is better; returns highest points the performance qualifies for.
        For distance events, higher is better.

        Parameters
        ----------
        sex : {"M", "W"}
            Athlete sex.
        event_id : str
            Event identifier (e.g., "100m", "LJ", "200m_sh").
        performance : float
            Performance value in standard units (seconds for time, metres for distance).

        Returns
        -------
        int
            World Athletics points. Returns 0 if performance is below minimum.
        """
        mask = (self._df["sex"] == sex) & (self._df["event"] == event_id)
        event_df = self._df[mask]

        if event_df.empty:
            return 0

        is_time = self._is_time_event(event_id)

        if is_time:
            valid = event_df[event_df["performance"] >= performance]
        else:
            valid = event_df[event_df["performance"] <= performance]

        if valid.empty:
            return 0

        return int(valid["points"].max())

    def performance_for_points(self, sex: str, event_id: str, points: int) -> float:
        """
        Return the minimum performance required for a given points level.

        Parameters
        ----------
        sex : {"M", "W"}
            Athlete sex.
        event_id : str
            Event identifier.
        points : int
            World Athletics points level.

        Returns
        -------
        float
            Performance threshold (time in seconds or distance in metres).

        Raises
        ------
        ValueError
            If no performance data exists for the given points or higher.
        """
        event_df = self._df[(self._df["sex"] == sex) & (self._df["event"] == event_id)]
        mask = event_df["points"] == points
        row = event_df[mask]

        if row.empty:
            next_rows = event_df[event_df["points"] > points].sort_values("points")
            if next_rows.empty:
                raise ValueError(
                    f"No performance data for {sex} {event_id} at {points} points or above."
                )
            row = next_rows.iloc[[0]]

        return float(row.iloc[0]["performance"])

    def available_events(self, sex: str | None = None) -> list[str]:
        """
        List all available events.

        Parameters
        ----------
        sex : {"M", "W"}, optional
            Filter by sex. If None, returns all.

        Returns
        -------
        list[str]
            Sorted list of event identifiers.
        """
        df = self._df
        if sex is not None:
            df = df[df["sex"] == sex]
        return sorted(df["event"].unique().tolist())

    @classmethod
    def _parse_page(cls, page, sex: str) -> list[tuple]:
        """
        Parse a single PDF page and extract (sex, event, points, performance) records.

        Parameters
        ----------
        page : pdfplumber.PDF.pages[i]
            A pdfplumber page object.
        sex : {"M", "W"}
            Athlete sex.

        Returns
        -------
        list[tuple]
            List of (sex, event_id, points, performance_float) tuples.
        """
        words = page.extract_words(x_tolerance=3, y_tolerance=3)
        if not words:
            return []

        lines = cls._group_lines(words)
        if not lines:
            return []

        header_line_idx = None
        for i, line in enumerate(lines):
            if any(w["text"] == "Points" for w in line):
                header_line_idx = i
                break

        if header_line_idx is None:
            return []

        try:
            columns = cls._parse_header_columns(lines[header_line_idx])
        except Exception:
            return []

        records = []
        for line in lines[header_line_idx + 1 :]:
            try:
                row_data = cls._assign_to_columns(line, columns)
                points_str = row_data.get("Points")
                if points_str is None:
                    continue

                try:
                    points = int(points_str)
                except (ValueError, TypeError):
                    continue

                for col in columns:
                    event_id = col["name"]
                    if event_id == "Points":
                        continue

                    perf_str = row_data.get(event_id)
                    if perf_str is None or perf_str in ("-", "–", ""):
                        continue

                    try:
                        perf_float = cls._parse_performance(perf_str)
                        records.append((sex, event_id, points, perf_float))
                    except (ValueError, TypeError):
                        continue
            except Exception:
                continue

        return records

    @staticmethod
    def _group_lines(words: list[dict], y_tolerance: float = 3.0) -> list[list[dict]]:
        """
        Group words into lines by y-coordinate.

        Parameters
        ----------
        words : list[dict]
            List of word dicts from pdfplumber.
        y_tolerance : float
            Tolerance in pixels for grouping consecutive words into the same line.

        Returns
        -------
        list[list[dict]]
            List of lines, each containing words sorted left-to-right.
        """
        if not words:
            return []

        lines = []
        current_line = []
        current_y = None

        for word in sorted(words, key=lambda w: w["top"]):
            if current_y is None or abs(word["top"] - current_y) <= y_tolerance:
                current_line.append(word)
                if current_y is None:
                    current_y = word["top"]
            else:
                if current_line:
                    lines.append(sorted(current_line, key=lambda w: w["x0"]))
                current_line = [word]
                current_y = word["top"]

        if current_line:
            lines.append(sorted(current_line, key=lambda w: w["x0"]))

        return lines

    @staticmethod
    def _parse_header_columns(
        header_words: list[dict], gap_threshold: float = 5.0
    ) -> list[dict]:
        """
        Parse column headers from header line, merging compound event names.

        Compound event names like "200m sh" appear as two adjacent words with small gaps (~2px).
        Words within gap_threshold (px) horizontally are merged with '_'.

        Parameters
        ----------
        header_words : list[dict]
            Words from the header line, already sorted left-to-right.
        gap_threshold : float
            Maximum x-gap (px) between consecutive words to merge them.
            Default ~5px to merge compound names but not separate columns (gap ~25-35px).

        Returns
        -------
        list[dict]
            List of column dicts: {"name": event_id, "x_mid": float, "x0": float, "x1": float}
        """
        columns = []
        i = 0

        while i < len(header_words):
            col_name = header_words[i]["text"].rstrip(
                "."
            )  # Remove trailing dots (e.g., "Hept." → "Hept")
            col_x0 = header_words[i]["x0"]
            col_x1 = header_words[i]["x1"]

            j = i + 1
            while j < len(header_words):
                gap = header_words[j]["x0"] - col_x1
                if gap < gap_threshold:
                    word_text = header_words[j]["text"].rstrip(".")
                    col_name += "_" + word_text
                    col_x1 = header_words[j]["x1"]
                    j += 1
                else:
                    break

            col_mid = (col_x0 + col_x1) / 2.0
            # Normalize event name: replace dots with nothing, commas with nothing
            col_name = col_name.replace(
                ",", ""
            )  # Remove commas from event names like "10,000m"
            columns.append(
                {"name": col_name, "x_mid": col_mid, "x0": col_x0, "x1": col_x1}
            )
            i = j

        return columns

    @staticmethod
    def _assign_to_columns(line_words: list[dict], columns: list[dict]) -> dict:
        """
        Assign words in a data line to their column by proximity to column centers.

        Parameters
        ----------
        line_words : list[dict]
            Words from a data line, already sorted left-to-right.
        columns : list[dict]
            Column definitions with "name" and "x_mid".

        Returns
        -------
        dict
            Mapping of column name → word text (first word found for each column).
        """
        row_data = {}

        for word in line_words:
            word_mid = (word["x0"] + word["x1"]) / 2.0
            nearest_col = min(columns, key=lambda c: abs(c["x_mid"] - word_mid))
            col_name = nearest_col["name"]

            if col_name not in row_data:
                row_data[col_name] = word["text"]

        return row_data

    @staticmethod
    def _parse_performance(perf_str: str) -> float:
        """
        Convert a performance string to float seconds or metres.

        Handles:
        - Decimal: "9.58", "8.95"
        - MM:SS.cc: "1:30.25", "2:45.50"
        - H:MM:SS.cc: "1:02:45.50"

        Parameters
        ----------
        perf_str : str
            Raw performance string.

        Returns
        -------
        float
            Performance in standard units (seconds or metres).
        """
        s = perf_str.strip().replace(",", ".")

        if ":" in s:
            parts = s.split(":")
            seconds = float(parts[-1])
            minutes = int(parts[-2])
            hours = int(parts[0]) if len(parts) == 3 else 0
            return hours * 3600 + minutes * 60 + seconds

        return float(s)


class ScoringTableResolver:
    """
    Factory to resolve and select the appropriate scoring table for an athlete category.

    Currently supports:
    - World Athletics 2025 (senior categories: CA, JU, ES, SE, M, M0–M9)
    - Placeholders for youth categories (BE, MI)
    """

    _tables: dict[str, ScoringTable] = {}

    @classmethod
    def register(cls, table: ScoringTable) -> None:
        """Register a scoring table."""
        for category in table.applicable_categories:
            cls._tables[category] = table

    @classmethod
    def get(cls, category: str) -> ScoringTable | None:
        """
        Get the scoring table for a given category.

        Parameters
        ----------
        category : str
            Category code with optional sex suffix (e.g., "CA", "CAM", "JU", "SEM", "BE", "BEF", "MI", "MIM").
            Sex suffixes ("M" or "W") are stripped automatically.

        Returns
        -------
        ScoringTable or None
            The applicable scoring table, or None if not available.
        """
        # Strip sex suffix if present (last char is M or W)
        if category and category[-1] in ("M", "W"):
            base_category = category[:-1]
        else:
            base_category = category
        return cls._tables.get(base_category)

    @classmethod
    def _init_default(cls) -> None:
        """Initialize default tables (lazy-loaded on first access)."""
        if not cls._tables:
            cls.register(WorldAthletics2025ScoringTable.load())


class BEYouthScoringTable(ScoringTable):
    """
    French youth scoring tables for BE category (14–15 years old).

    Combines BEM (boys) and BEF (girls) scoring tables from
    2025-2028_pointjeunes_bem.pdf and 2025-2028_pointjeunes_bef.pdf.

    Parameters
    ----------
    df : pd.DataFrame
        Loaded table with columns: sex, event, points, performance.
    """

    _APPLICABLE = frozenset(["BE"])

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    @property
    def applicable_categories(self) -> frozenset[str]:
        """BE tables apply to 14–15 year-old athletes."""
        return self._APPLICABLE

    @classmethod
    def build_from_pdfs(
        cls,
        bem_path: Optional[Path] = None,
        bef_path: Optional[Path] = None,
    ) -> BEYouthScoringTable:
        """
        Parse BE youth PDFs and create a scoring table.

        Parameters
        ----------
        bem_path : Path, optional
            Path to BEM (boys) PDF. Defaults to data/2025-2028_pointjeunes_bem.pdf.
        bef_path : Path, optional
            Path to BEF (girls) PDF. Defaults to data/2025-2028_pointjeunes_bef.pdf.

        Returns
        -------
        BEYouthScoringTable
            Ready-to-use instance.
        """
        data_dir = Path(__file__).parent / "data"
        bem_path = bem_path or data_dir / "2025-2028_pointjeunes_bem.pdf"
        bef_path = bef_path or data_dir / "2025-2028_pointjeunes_bef.pdf"

        records = []
        records.extend(cls._parse_pdf(bem_path, "M"))
        records.extend(cls._parse_pdf(bef_path, "W"))

        df = pd.DataFrame(records, columns=["sex", "event", "points", "performance"])
        df["points"] = df["points"].astype("int16")
        df["performance"] = df["performance"].astype("float32")
        return cls(df)

    @classmethod
    def _parse_pdf(cls, pdf_path: Path, sex: str) -> list[tuple]:
        """
        Parse a BE youth PDF and extract (sex, event, points, performance) records.

        Parameters
        ----------
        pdf_path : Path
            Path to PDF file.
        sex : {"M", "W"}
            Athlete sex.

        Returns
        -------
        list[tuple]
            List of (sex, event_id, points, performance_float) tuples.
        """
        import pdfplumber

        records = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if not tables:
                    continue
                table = tables[0]

                # Skip empty tables
                if len(table) < 2:
                    continue

                # First row is header with event names
                header = table[0]
                events = [cls._normalize_event_name(h) for h in header[1:-1]]

                # Remaining rows are points with corresponding performances
                for row_idx in range(1, len(table)):
                    try:
                        points = int(table[row_idx][0])
                    except (ValueError, TypeError, IndexError):
                        continue

                    # Parse performances for each event
                    for col_idx, event in enumerate(events, start=1):
                        if col_idx >= len(table[row_idx]):
                            continue

                        perf_str = table[row_idx][col_idx]
                        if perf_str is None or perf_str in ("", "-", "–"):
                            continue

                        try:
                            perf_float = cls._parse_performance(perf_str)
                            records.append((sex, event, points, perf_float))
                        except (ValueError, TypeError):
                            continue

        return records

    @staticmethod
    def _normalize_event_name(event_str: str) -> str:
        """Normalize event name from PDF header."""
        if not event_str:
            return ""
        # Clean up newlines and extra spaces, remove parenthetical notes
        event = event_str.replace("\n", " ").strip()
        # Remove weights/distances in parens: "Poids (3 Kg)" → "Poids"
        event = event.split("(")[0].strip()
        # Replace common spacing issues
        event = " ".join(event.split())
        return event

    @staticmethod
    def _parse_performance(perf_str: str) -> float:
        """Convert performance string to float."""
        s = str(perf_str).strip().replace(",", ".")
        if ":" in s:
            parts = s.split(":")
            seconds = float(parts[-1])
            minutes = int(parts[-2])
            hours = int(parts[0]) if len(parts) == 3 else 0
            return hours * 3600 + minutes * 60 + seconds
        return float(s)

    def score(self, sex: str, event_id: str, performance: float) -> int:
        """
        Return BE youth points for a given performance.

        Parameters
        ----------
        sex : {"M", "W"}
            Athlete sex.
        event_id : str
            Event identifier.
        performance : float
            Performance value.

        Returns
        -------
        int
            Points awarded. Returns 0 if performance does not qualify.
        """
        mask = (self._df["sex"] == sex) & (self._df["event"] == event_id)
        event_df = self._df[mask]

        if event_df.empty:
            return 0

        is_time = self._is_time_event(event_id)

        if is_time:
            valid = event_df[event_df["performance"] >= performance]
        else:
            valid = event_df[event_df["performance"] <= performance]

        if valid.empty:
            return 0

        return int(valid["points"].max())

    def performance_for_points(self, sex: str, event_id: str, points: int) -> float:
        """
        Return the minimum performance required for a given points level.

        Parameters
        ----------
        sex : {"M", "W"}
            Athlete sex.
        event_id : str
            Event identifier.
        points : int
            Points level.

        Returns
        -------
        float
            Minimum performance.

        Raises
        ------
        ValueError
            If no data exists for the given points.
        """
        event_df = self._df[(self._df["sex"] == sex) & (self._df["event"] == event_id)]
        row = event_df[event_df["points"] == points]

        if row.empty:
            raise ValueError(
                f"No performance data for {sex} {event_id} at {points} points."
            )

        return float(row.iloc[0]["performance"])

    def available_events(self, sex: str | None = None) -> list[str]:
        """List all available events."""
        df = self._df
        if sex is not None:
            df = df[df["sex"] == sex]
        return sorted(df["event"].unique().tolist())


class MIYouthScoringTable(ScoringTable):
    """
    French youth scoring tables for MI category (10–11 years old).

    Combines MIM (boys) and MIF (girls) scoring tables from
    2025-2028_pointjeunes_mim.pdf and 2025-2028_pointjeunes_mif.pdf.

    Parameters
    ----------
    df : pd.DataFrame
        Loaded table with columns: sex, event, points, performance.
    """

    _APPLICABLE = frozenset(["MI"])

    def __init__(self, df: pd.DataFrame) -> None:
        self._df = df

    @property
    def applicable_categories(self) -> frozenset[str]:
        """MI tables apply to 10–11 year-old athletes."""
        return self._APPLICABLE

    @classmethod
    def build_from_pdfs(
        cls,
        mim_path: Optional[Path] = None,
        mif_path: Optional[Path] = None,
    ) -> MIYouthScoringTable:
        """
        Parse MI youth PDFs and create a scoring table.

        Parameters
        ----------
        mim_path : Path, optional
            Path to MIM (boys) PDF. Defaults to data/2025-2028_pointjeunes_mim.pdf.
        mif_path : Path, optional
            Path to MIF (girls) PDF. Defaults to data/2025-2028_pointjeunes_mif.pdf.

        Returns
        -------
        MIYouthScoringTable
            Ready-to-use instance.
        """
        data_dir = Path(__file__).parent / "data"
        mim_path = mim_path or data_dir / "2025-2028_pointjeunes_mim.pdf"
        mif_path = mif_path or data_dir / "2025-2028_pointjeunes_mif.pdf"

        records = []
        records.extend(BEYouthScoringTable._parse_pdf(mim_path, "M"))
        records.extend(BEYouthScoringTable._parse_pdf(mif_path, "W"))

        df = pd.DataFrame(records, columns=["sex", "event", "points", "performance"])
        df["points"] = df["points"].astype("int16")
        df["performance"] = df["performance"].astype("float32")
        return cls(df)

    def score(self, sex: str, event_id: str, performance: float) -> int:
        """Return MI youth points for a given performance."""
        mask = (self._df["sex"] == sex) & (self._df["event"] == event_id)
        event_df = self._df[mask]

        if event_df.empty:
            return 0

        is_time = self._is_time_event(event_id)

        if is_time:
            valid = event_df[event_df["performance"] >= performance]
        else:
            valid = event_df[event_df["performance"] <= performance]

        if valid.empty:
            return 0

        return int(valid["points"].max())

    def performance_for_points(self, sex: str, event_id: str, points: int) -> float:
        """Return the minimum performance required for a given points level."""
        event_df = self._df[(self._df["sex"] == sex) & (self._df["event"] == event_id)]
        row = event_df[event_df["points"] == points]

        if row.empty:
            raise ValueError(
                f"No performance data for {sex} {event_id} at {points} points."
            )

        return float(row.iloc[0]["performance"])

    def available_events(self, sex: str | None = None) -> list[str]:
        """List all available events."""
        df = self._df
        if sex is not None:
            df = df[df["sex"] == sex]
        return sorted(df["event"].unique().tolist())


# Lazy initialization on first import
def _init_scoring_tables():
    """Initialize all scoring tables."""
    try:
        ScoringTableResolver.register(WorldAthletics2025ScoringTable.load())
    except FileNotFoundError:
        pass  # Parquet not yet generated

    try:
        ScoringTableResolver.register(BEYouthScoringTable.build_from_pdfs())
    except Exception:
        pass  # PDFs not available or parsing failed

    try:
        ScoringTableResolver.register(MIYouthScoringTable.build_from_pdfs())
    except Exception:
        pass  # PDFs not available or parsing failed


_init_scoring_tables()


# Backward compatibility: ScoringTables alias for WorldAthletics2025ScoringTable
ScoringTables = WorldAthletics2025ScoringTable
