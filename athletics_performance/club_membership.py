"""
ClubMembership model – tracks an athlete's club history.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class ClubMembership:
    """
    Records one membership period of an athlete in a club.

    Parameters
    ----------
    athlete_id : str
        Licence number of the athlete.
    club_id : str
        6-digit club identifier.
    start_date : date
        First day of membership.
    end_date : Optional[date]
        Last day of membership, or ``None`` if still active.

    Examples
    --------
    >>> from datetime import date
    >>> ClubMembership(athlete_id="2275784", club_id="069001", start_date=date(2022, 1, 1))
    ClubMembership(athlete_id='2275784', club_id='069001', start_date=datetime.date(2022, 1, 1), end_date=None)
    """

    athlete_id: str
    club_id: str
    start_date: date
    end_date: Optional[date] = None

    def is_active(self, on: Optional[date] = None) -> bool:
        """
        Return ``True`` if the membership is active on *on* (defaults to today).

        Parameters
        ----------
        on : date, optional
            Reference date. Defaults to ``date.today()``.
        """
        check = on if on is not None else date.today()
        if check < self.start_date:
            return False
        if self.end_date is not None and check > self.end_date:
            return False
        return True
