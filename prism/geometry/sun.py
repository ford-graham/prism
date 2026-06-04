"""Geocentric solar position.

Low-precision solar coordinates from the *Astronomical Almanac* (good to about
0.01 degrees over 1950-2050), which is far better than the pointing budget here.
Returns the geocentric equatorial (inertial) sun vector in kilometres, and a
helper to express it in the Earth-fixed frame.
"""

from __future__ import annotations

import datetime as _dt
import math

from .vectors import Vec3
from .time_utils import julian_date, gmst_rad
from .coordinates import eci_to_ecef

_AU_KM = 149_597_870.7


def sun_eci(when: _dt.datetime) -> Vec3:
    """Geocentric equatorial (inertial) sun position vector in km."""
    jd = julian_date(when)
    n = jd - 2451545.0
    # Mean longitude and mean anomaly (degrees)
    L = (280.460 + 0.9856474 * n) % 360.0
    g = math.radians((357.528 + 0.9856003 * n) % 360.0)
    # Ecliptic longitude
    lam = math.radians(L + 1.915 * math.sin(g) + 0.020 * math.sin(2.0 * g))
    # Obliquity of the ecliptic
    eps = math.radians(23.439 - 0.0000004 * n)
    # Distance in AU
    r_au = 1.00014 - 0.01671 * math.cos(g) - 0.00014 * math.cos(2.0 * g)
    r = r_au * _AU_KM
    x = r * math.cos(lam)
    y = r * math.cos(eps) * math.sin(lam)
    z = r * math.sin(eps) * math.sin(lam)
    return Vec3(x, y, z)


def sun_ecef(when: _dt.datetime) -> Vec3:
    """Geocentric sun position vector in the Earth-fixed (ECEF) frame, km."""
    jd = julian_date(when)
    return eci_to_ecef(sun_eci(when), gmst_rad(jd))
