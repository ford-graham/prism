"""Geometry, astronomy and reflection math for prism.

All of the code in this subpackage is self-contained, dependency-free and
unit-testable. It implements the real math that the framework relies on:

* :mod:`prism.geometry.vectors`      -- a small 3-vector type
* :mod:`prism.geometry.time_utils`   -- Julian date and GMST
* :mod:`prism.geometry.coordinates`  -- geodetic / ECEF / ENU / ECI<->ECEF
* :mod:`prism.geometry.sun`          -- geocentric solar position
* :mod:`prism.geometry.reflection`   -- the mirror-pointing solver
"""

from .vectors import Vec3
from .time_utils import julian_date, gmst_rad
from .coordinates import (
    geodetic_to_ecef,
    ecef_to_geodetic,
    eci_to_ecef,
    ecef_to_enu,
    elevation_azimuth,
    R_EARTH_KM,
)
from .sun import sun_ecef, sun_eci
from .reflection import ReflectionSolution, solve_reflection

__all__ = [
    "Vec3",
    "julian_date",
    "gmst_rad",
    "geodetic_to_ecef",
    "ecef_to_geodetic",
    "eci_to_ecef",
    "ecef_to_enu",
    "elevation_azimuth",
    "R_EARTH_KM",
    "sun_ecef",
    "sun_eci",
    "ReflectionSolution",
    "solve_reflection",
]
