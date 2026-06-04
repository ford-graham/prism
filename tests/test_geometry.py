import pytest

from prism.geometry.coordinates import (
    geodetic_to_ecef, ecef_to_geodetic, R_EARTH_KM, elevation_azimuth,
)


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
