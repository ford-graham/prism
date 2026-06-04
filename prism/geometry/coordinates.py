"""Coordinate transforms between geodetic, ECEF, ENU and inertial frames.

All Cartesian vectors are in kilometres. The WGS84 ellipsoid is used for
geodetic conversions. The inertial<->ECEF rotation is a GMST-only rotation
about the Z axis: this neglects precession, nutation and polar motion, which is
appropriate for the few-arc-minute pointing precision this framework targets and
keeps the ECI sun vector and the TEME satellite vector in a *consistent* Earth
frame (consistency is what matters for the reflection geometry).
"""

from __future__ import annotations

import math

from .vectors import Vec3

# WGS84
R_EARTH_KM = 6378.137
_F = 1.0 / 298.257223563
_E2 = _F * (2.0 - _F)
_B = R_EARTH_KM * (1.0 - _F)


def geodetic_to_ecef(lat_deg: float, lon_deg: float, alt_km: float = 0.0) -> Vec3:
    """Geodetic latitude/longitude/altitude (deg, deg, km) -> ECEF (km)."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    n = R_EARTH_KM / math.sqrt(1.0 - _E2 * sin_lat * sin_lat)
    x = (n + alt_km) * cos_lat * math.cos(lon)
    y = (n + alt_km) * cos_lat * math.sin(lon)
    z = (n * (1.0 - _E2) + alt_km) * sin_lat
    return Vec3(x, y, z)


def ecef_to_geodetic(p: Vec3) -> "tuple[float, float, float]":
    """ECEF (km) -> (lat_deg, lon_deg, alt_km). Bowring's iterative method."""
    x, y, z = p.x, p.y, p.z
    lon = math.atan2(y, x)
    r = math.hypot(x, y)
    # initial guess
    lat = math.atan2(z, r * (1.0 - _E2))
    for _ in range(8):
        sin_lat = math.sin(lat)
        n = R_EARTH_KM / math.sqrt(1.0 - _E2 * sin_lat * sin_lat)
        alt = r / math.cos(lat) - n
        lat = math.atan2(z, r * (1.0 - _E2 * n / (n + alt)))
    sin_lat = math.sin(lat)
    n = R_EARTH_KM / math.sqrt(1.0 - _E2 * sin_lat * sin_lat)
    alt = r / math.cos(lat) - n
    return math.degrees(lat), math.degrees(lon), alt


def eci_to_ecef(v: Vec3, gmst: float) -> Vec3:
    """Rotate an inertial vector into the Earth-fixed frame by GMST (radians)."""
    c = math.cos(gmst)
    s = math.sin(gmst)
    return Vec3(c * v.x + s * v.y, -s * v.x + c * v.y, v.z)


def ecef_to_eci(v: Vec3, gmst: float) -> Vec3:
    """Inverse of :func:`eci_to_ecef`."""
    c = math.cos(gmst)
    s = math.sin(gmst)
    return Vec3(c * v.x - s * v.y, s * v.x + c * v.y, v.z)


def ecef_to_enu(d_ecef: Vec3, lat_deg: float, lon_deg: float) -> Vec3:
    """Rotate an ECEF *displacement* into the local East/North/Up frame."""
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    sin_lat, cos_lat = math.sin(lat), math.cos(lat)
    sin_lon, cos_lon = math.sin(lon), math.cos(lon)
    east = -sin_lon * d_ecef.x + cos_lon * d_ecef.y
    north = -sin_lat * cos_lon * d_ecef.x - sin_lat * sin_lon * d_ecef.y + cos_lat * d_ecef.z
    up = cos_lat * cos_lon * d_ecef.x + cos_lat * sin_lon * d_ecef.y + sin_lat * d_ecef.z
    return Vec3(east, north, up)


def elevation_azimuth(observer_ecef: Vec3, target_ecef: Vec3,
                      observer_lat: float, observer_lon: float) -> "tuple[float, float, float]":
    """Elevation (deg), azimuth (deg, 0=N CW), and range (km) of ``target`` as
    seen from ``observer``."""
    d = target_ecef - observer_ecef
    enu = ecef_to_enu(d, observer_lat, observer_lon)
    rng = d.norm()
    horizontal = math.hypot(enu.x, enu.y)
    elevation = math.degrees(math.atan2(enu.z, horizontal))
    azimuth = math.degrees(math.atan2(enu.x, enu.y)) % 360.0
    return elevation, azimuth, rng
