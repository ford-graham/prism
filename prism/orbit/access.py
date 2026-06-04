"""Search for reflection-access windows over a time span.

A window is a contiguous interval during which the reflection geometry is
feasible (satellite sunlit, target above horizon, reflectable incidence). We
sample on a fixed step and group feasible samples into intervals.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from typing import List

from .propagator import TLEPropagator
from ..geometry.coordinates import geodetic_to_ecef
from ..geometry.sun import sun_ecef
from ..geometry.reflection import solve_reflection, ReflectionSolution


@dataclass
class AccessWindow:
    start: _dt.datetime
    end: _dt.datetime
    peak: _dt.datetime
    peak_elevation_deg: float

    @property
    def duration_s(self) -> float:
        return (self.end - self.start).total_seconds()


def find_access_windows(
    propagator: TLEPropagator,
    target_lat: float,
    target_lon: float,
    start: _dt.datetime,
    end: _dt.datetime,
    *,
    target_alt_km: float = 0.0,
    step_s: float = 10.0,
    min_target_elevation_deg: float = 10.0,
    require_target_darkness: bool = False,
) -> List[AccessWindow]:
    """Return the feasible reflection windows in ``[start, end]``.

    ``require_target_darkness`` adds the practical constraint that the target be
    in twilight/night (sun below the horizon) for the reflected beam to be useful.
    """
    target_ecef = geodetic_to_ecef(target_lat, target_lon, target_alt_km)
    step = _dt.timedelta(seconds=step_s)

    windows: List[AccessWindow] = []
    cur_start = None
    cur_peak = None
    cur_peak_elev = -90.0

    t = start
    while t <= end:
        sol = solve_reflection(
            propagator.propagate(t).position_ecef_km,
            target_ecef,
            sun_ecef(t),
            target_lat=target_lat,
            target_lon=target_lon,
            min_target_elevation_deg=min_target_elevation_deg,
        )
        ok = sol.feasible
        if ok and require_target_darkness:
            ok = sol.target_sun_elevation_deg < 0.0

        if ok:
            if cur_start is None:
                cur_start = t
                cur_peak = t
                cur_peak_elev = sol.target_elevation_deg
            elif sol.target_elevation_deg > cur_peak_elev:
                cur_peak = t
                cur_peak_elev = sol.target_elevation_deg
        else:
            if cur_start is not None:
                windows.append(AccessWindow(cur_start, t - step, cur_peak, cur_peak_elev))
                cur_start = None
                cur_peak_elev = -90.0
        t += step

    if cur_start is not None:
        windows.append(AccessWindow(cur_start, end, cur_peak, cur_peak_elev))
    return windows
