"""High-level pointing control: orbit + sun + reflection + network in one loop.

``solve_pointing`` is a pure function (no network) that returns the reflection
solution for a TLE/target/time. ``PointingController`` closes the loop against a
connected client: it repeatedly recomputes the mirror normal and sends POINT
commands while the geometry is feasible.
"""

from __future__ import annotations

import datetime as _dt
import time
from dataclasses import dataclass
from typing import Callable, Optional

from .orbit.propagator import TLEPropagator
from .geometry.coordinates import geodetic_to_ecef
from .geometry.sun import sun_ecef
from .geometry.reflection import solve_reflection, ReflectionSolution
from .client import SatelliteReflectorClient


@dataclass
class Target:
    lat: float
    lon: float
    alt_km: float = 0.0


def solve_pointing(
    propagator: TLEPropagator,
    target: Target,
    when: _dt.datetime,
    *,
    min_target_elevation_deg: float = 10.0,
) -> ReflectionSolution:
    """Compute the reflection solution for one instant (no network)."""
    state = propagator.propagate(when)
    target_ecef = geodetic_to_ecef(target.lat, target.lon, target.alt_km)
    return solve_reflection(
        state.position_ecef_km,
        target_ecef,
        sun_ecef(when),
        target_lat=target.lat,
        target_lon=target.lon,
        min_target_elevation_deg=min_target_elevation_deg,
    )


class PointingController:
    """Closed-loop controller driving a connected satellite client."""

    def __init__(
        self,
        client: SatelliteReflectorClient,
        propagator: TLEPropagator,
        target: Target,
        *,
        min_target_elevation_deg: float = 10.0,
        update_interval_s: float = 2.0,
        now_fn: Callable[[], _dt.datetime] = _dt.datetime.utcnow,
    ) -> None:
        self.client = client
        self.propagator = propagator
        self.target = target
        self.min_target_elevation_deg = min_target_elevation_deg
        self.update_interval_s = update_interval_s
        self._now = now_fn

    def step(self) -> ReflectionSolution:
        """Compute one solution and, if feasible, command the satellite once."""
        sol = solve_pointing(
            self.propagator,
            self.target,
            self._now(),
            min_target_elevation_deg=self.min_target_elevation_deg,
        )
        if sol.feasible:
            self.client.point(
                sol.mirror_normal_ecef.as_list(),
                target={"lat": self.target.lat, "lon": self.target.lon},
                hold_s=self.update_interval_s * 2.0,
            )
        return sol

    def run(
        self,
        duration_s: float,
        *,
        on_update: Optional[Callable[[ReflectionSolution], None]] = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        """Run the closed loop for ``duration_s`` seconds of wall time."""
        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            sol = self.step()
            if on_update is not None:
                on_update(sol)
            sleep_fn(self.update_interval_s)
