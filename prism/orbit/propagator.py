"""TLE-based orbit propagation built on the industry-standard SGP4 model.

We use the `sgp4` package (the reference C/Python implementation) to propagate a
Two-Line Element set to any epoch, then rotate the TEME result into the
Earth-fixed (ECEF) frame so it is directly comparable with ground targets and
the sun vector.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from sgp4.api import Satrec, jday

from ..geometry.vectors import Vec3
from ..geometry.time_utils import julian_date, gmst_rad, to_utc_naive
from ..geometry.coordinates import eci_to_ecef, ecef_to_geodetic


@dataclass
class SatelliteState:
    """Propagated state of the satellite at a given instant."""

    epoch: _dt.datetime
    position_ecef_km: Vec3
    velocity_ecef_kms: Vec3
    latitude_deg: float
    longitude_deg: float
    altitude_km: float


class TLEPropagator:
    """Propagate a satellite from its TLE.

    Example::

        prop = TLEPropagator(line1, line2, name="ISS")
        state = prop.propagate(datetime.utcnow())
    """

    def __init__(self, line1: str, line2: str, name: str = "satellite") -> None:
        self.name = name
        self.line1 = line1.rstrip("\n")
        self.line2 = line2.rstrip("\n")
        self._sat = Satrec.twoline2rv(self.line1, self.line2)

    @classmethod
    def from_tle_text(cls, text: str) -> "TLEPropagator":
        """Parse a 2- or 3-line TLE block."""
        lines = [ln.rstrip() for ln in text.strip().splitlines() if ln.strip()]
        if len(lines) == 3:
            name, l1, l2 = lines
            return cls(l1, l2, name=name.strip())
        if len(lines) == 2:
            return cls(lines[0], lines[1])
        raise ValueError("TLE text must contain 2 or 3 non-empty lines")

    @classmethod
    def from_file(cls, path: str) -> "TLEPropagator":
        with open(path, "r", encoding="utf-8") as fh:
            return cls.from_tle_text(fh.read())

    def propagate(self, when: _dt.datetime) -> SatelliteState:
        when = to_utc_naive(when)
        jd_whole, jd_frac = jday(
            when.year, when.month, when.day,
            when.hour, when.minute,
            when.second + when.microsecond / 1e6,
        )
        err, r_teme, v_teme = self._sat.sgp4(jd_whole, jd_frac)
        if err != 0:
            raise RuntimeError(f"SGP4 propagation error code {err} for {self.name}")

        jd = jd_whole + jd_frac
        gmst = gmst_rad(jd)
        r_ecef = eci_to_ecef(Vec3(*r_teme), gmst)
        v_ecef = eci_to_ecef(Vec3(*v_teme), gmst)
        lat, lon, alt = ecef_to_geodetic(r_ecef)
        return SatelliteState(
            epoch=when,
            position_ecef_km=r_ecef,
            velocity_ecef_kms=v_ecef,
            latitude_deg=lat,
            longitude_deg=lon,
            altitude_km=alt,
        )
