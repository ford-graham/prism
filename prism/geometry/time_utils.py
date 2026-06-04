"""Time conversions: civil UTC -> Julian date -> Greenwich sidereal time.

These are the standard formulae used throughout astrodynamics. We treat UTC as
UT1 (the <1 s difference is far below the pointing precision this framework
targets, and is documented in the README).
"""

from __future__ import annotations

import datetime as _dt
import math


def to_utc_naive(when: _dt.datetime) -> _dt.datetime:
    """Return a naive datetime in UTC. Naive inputs are assumed to be UTC."""
    if when.tzinfo is not None:
        when = when.astimezone(_dt.timezone.utc).replace(tzinfo=None)
    return when


def julian_date(when: _dt.datetime) -> float:
    """Julian Date for a UTC ``datetime`` (Fliegel-Van Flandern style)."""
    when = to_utc_naive(when)
    year, month = when.year, when.month
    day_frac = (
        when.day
        + (when.hour + (when.minute + (when.second + when.microsecond / 1e6) / 60.0) / 60.0)
        / 24.0
    )
    if month <= 2:
        year -= 1
        month += 12
    a = year // 100
    b = 2 - a + a // 4
    jd0 = (
        math.floor(365.25 * (year + 4716))
        + math.floor(30.6001 * (month + 1))
        - 1524.5
        + b
    )
    return jd0 + day_frac


def gmst_rad(jd: float) -> float:
    """Greenwich Mean Sidereal Time in radians (IAU 1982 expression)."""
    t = (jd - 2451545.0) / 36525.0
    gmst_deg = (
        280.46061837
        + 360.98564736629 * (jd - 2451545.0)
        + 0.000387933 * t * t
        - (t ** 3) / 38710000.0
    )
    gmst_deg %= 360.0
    return math.radians(gmst_deg)
