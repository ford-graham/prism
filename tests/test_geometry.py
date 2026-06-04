import math

import pytest

from prism.geometry.vectors import Vec3
from prism.geometry.coordinates import (
    geodetic_to_ecef, ecef_to_geodetic, R_EARTH_KM, elevation_azimuth,
)
from prism.geometry.reflection import solve_reflection, is_sunlit


def test_geodetic_ecef_roundtrip():
    for lat, lon, alt in [(0, 0, 0), (51.5, -0.12, 0.05), (-33.9, 151.2, 0.0),
                          (89.0, 179.0, 10.0)]:
        ecef = geodetic_to_ecef(lat, lon, alt)
        rlat, rlon, ralt = ecef_to_geodetic(ecef)
        assert rlat == pytest.approx(lat, abs=1e-6)
        assert rlon == pytest.approx(lon, abs=1e-6)
        assert ralt == pytest.approx(alt, abs=1e-6)


def test_equator_radius():
    ecef = geodetic_to_ecef(0.0, 0.0, 0.0)
    assert ecef.norm() == pytest.approx(R_EARTH_KM, abs=1e-6)


def test_elevation_straight_up():
    obs = geodetic_to_ecef(0.0, 0.0, 0.0)
    overhead = geodetic_to_ecef(0.0, 0.0, 500.0)
    elev, _, rng = elevation_azimuth(obs, overhead, 0.0, 0.0)
    assert elev == pytest.approx(90.0, abs=1e-3)
    assert rng == pytest.approx(500.0, abs=1e-6)


def test_reflection_law_known_geometry():
    # Satellite 7000 km up the +Z axis. Sun far along +X. Target on the ground
    # straight below the satellite. The bisector of +X and -Z is (1,0,-1)/sqrt2.
    sat = Vec3(0.0, 0.0, 7000.0)
    sun = Vec3(1.0e8, 0.0, 7000.0)
    target = Vec3(0.0, 0.0, R_EARTH_KM)
    sol = solve_reflection(sat, target, sun, target_lat=0.0, target_lon=0.0,
                           min_target_elevation_deg=0.0)
    n = sol.mirror_normal_ecef
    assert n.x == pytest.approx(math.sqrt(0.5), abs=1e-6)
    assert n.y == pytest.approx(0.0, abs=1e-9)
    assert n.z == pytest.approx(-math.sqrt(0.5), abs=1e-6)
    assert sol.incidence_angle_deg == pytest.approx(45.0, abs=1e-6)
    assert sol.feasible


def test_reflection_law_equal_angles():
    # The defining property: angle(sun, normal) == angle(target, normal).
    sat = Vec3(1000.0, 2000.0, 6800.0)
    sun = Vec3(-4.0e7, 9.0e7, 1.0e7)
    target = geodetic_to_ecef(40.0, 10.0, 0.0)
    sol = solve_reflection(sat, target, sun, target_lat=40.0, target_lon=10.0,
                           min_target_elevation_deg=-90.0)
    u_sun = (sun - sat).normalized()
    u_tgt = (target - sat).normalized()
    a_in = u_sun.angle_to(sol.mirror_normal_ecef)
    a_out = u_tgt.angle_to(sol.mirror_normal_ecef)
    assert a_in == pytest.approx(a_out, abs=1e-9)


def test_shadow_detection():
    sun = Vec3(1.0e8, 0.0, 0.0)            # sun along +X
    lit = Vec3(7000.0, 0.0, 0.0)           # day side
    dark = Vec3(-7000.0, 0.0, 0.0)         # behind Earth, inside shadow cylinder
    high = Vec3(-7000.0, 9000.0, 0.0)      # behind terminator but outside cylinder
    assert is_sunlit(lit, sun)
    assert not is_sunlit(dark, sun)
    assert is_sunlit(high, sun)
