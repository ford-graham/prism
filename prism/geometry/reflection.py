"""The mirror-pointing solver.

Given a satellite position, a ground target and the sun position (all ECEF, km),
compute the flat-mirror orientation that reflects sunlight onto the target, plus
a full feasibility assessment.

Physics
-------
A flat mirror reflects an incoming ray about its surface normal. Let

    u_sun    = unit vector from the satellite toward the Sun
    u_target = unit vector from the satellite toward the target

The incoming sunlight propagates along ``-u_sun`` and we want the reflected ray
to propagate along ``u_target``. For a flat mirror the surface normal must
bisect the incoming-reversed and outgoing directions, i.e.

    n = normalize(u_sun + u_target)

This is exact. The half-angle between the normal and either ray is
``angle(u_sun, u_target) / 2`` -- the angle of incidence equals the angle of
reflection by construction.

Feasibility requires all of:
  * the satellite is sunlit (not in Earth's cylindrical shadow),
  * the target is above the satellite's local horizon (line of sight is clear),
  * the geometry is physically reflectable (incidence angle < 90 deg).
"""

from __future__ import annotations

import datetime as _dt
import math
from dataclasses import dataclass
from typing import Optional

from .vectors import Vec3
from .coordinates import (
    R_EARTH_KM,
    ecef_to_geodetic,
    elevation_azimuth,
)


@dataclass
class ReflectionSolution:
    """Result of :func:`solve_reflection`."""

    feasible: bool
    reason: str
    # The commanded mirror surface normal, unit vector in ECEF.
    mirror_normal_ecef: Vec3
    # Angle of incidence == angle of reflection, degrees.
    incidence_angle_deg: float
    # Elevation/azimuth/range of the target as seen from the satellite.
    target_elevation_deg: float
    target_azimuth_deg: float
    slant_range_km: float
    # Is the satellite illuminated by the Sun?
    satellite_sunlit: bool
    # Sun elevation at the target (negative => target is in darkness; that is
    # when a reflected beam is actually useful/visible).
    target_sun_elevation_deg: float

    def to_dict(self) -> dict:
        return {
            "feasible": self.feasible,
            "reason": self.reason,
            "mirror_normal_ecef": self.mirror_normal_ecef.as_list(),
            "incidence_angle_deg": self.incidence_angle_deg,
            "target_elevation_deg": self.target_elevation_deg,
            "target_azimuth_deg": self.target_azimuth_deg,
            "slant_range_km": self.slant_range_km,
            "satellite_sunlit": self.satellite_sunlit,
            "target_sun_elevation_deg": self.target_sun_elevation_deg,
        }


def is_sunlit(sat_ecef: Vec3, sun_ecef: Vec3) -> bool:
    """Cylindrical-umbra shadow test: is the satellite in sunlight?"""
    u_sun = sun_ecef.normalized()
    along = sat_ecef.dot(u_sun)
    if along >= 0.0:
        # On the day side of the terminator plane -> always lit.
        return True
    # Night side: lit only if outside the anti-solar shadow cylinder.
    perp = (sat_ecef - u_sun * along).norm()
    return perp > R_EARTH_KM


def solve_reflection(
    sat_ecef: Vec3,
    target_ecef: Vec3,
    sun_ecef: Vec3,
    *,
    target_lat: float,
    target_lon: float,
    min_target_elevation_deg: float = 0.0,
) -> ReflectionSolution:
    """Compute the mirror normal and feasibility for one instant.

    ``target_lat``/``target_lon`` are the geodetic coordinates of ``target_ecef``
    (passed in to avoid recomputing them).
    """
    u_sun = (sun_ecef - sat_ecef).normalized()
    to_target = target_ecef - sat_ecef
    slant_range = to_target.norm()
    u_target = to_target.normalized()

    # Mirror normal: bisector of sun and target directions.
    bisector = u_sun + u_target
    if bisector.norm() < 1e-12:
        # Sun and target are exactly opposite from the satellite: undefined.
        normal = u_target
        incidence = 90.0
    else:
        normal = bisector.normalized()
        incidence = math.degrees(u_sun.angle_to(normal))

    # Target as seen from the satellite (elevation of sat above target horizon
    # equals elevation of target below sat; we use the target-frame elevation of
    # the satellite as the line-of-sight test).
    sat_elev, _, _ = elevation_azimuth(target_ecef, sat_ecef, target_lat, target_lon)
    tgt_elev_from_sat, tgt_az_from_sat, _ = elevation_azimuth(
        sat_ecef, target_ecef,
        *ecef_to_geodetic(sat_ecef)[:2],
    )

    # Sun elevation at the target (day/night indicator).
    sun_elev_at_target, _, _ = elevation_azimuth(
        target_ecef, sun_ecef, target_lat, target_lon
    )

    sunlit = is_sunlit(sat_ecef, sun_ecef)

    feasible = True
    reason = "ok"
    if not sunlit:
        feasible, reason = False, "satellite is in Earth's shadow"
    elif sat_elev < min_target_elevation_deg:
        feasible, reason = (
            False,
            f"satellite below target horizon ({sat_elev:.1f} deg < "
            f"{min_target_elevation_deg:.1f} deg)",
        )
    elif incidence >= 90.0:
        feasible, reason = False, "reflection geometry impossible (incidence >= 90 deg)"

    return ReflectionSolution(
        feasible=feasible,
        reason=reason,
        mirror_normal_ecef=normal,
        incidence_angle_deg=incidence,
        target_elevation_deg=sat_elev,
        target_azimuth_deg=tgt_az_from_sat,
        slant_range_km=slant_range,
        satellite_sunlit=sunlit,
        target_sun_elevation_deg=sun_elev_at_target,
    )
