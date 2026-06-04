"""prism -- orbital sunlight-reflector pointing & control framework.

Public API::

    from prism import (
        TLEPropagator, Target, solve_pointing, PointingController,
        SatelliteReflectorClient, ReferenceSatelliteServer,
    )

See the README for the honest scope of what this controls and what it does not.
"""

from .geometry import (
    Vec3,
    geodetic_to_ecef,
    ecef_to_geodetic,
    sun_ecef,
    solve_reflection,
    ReflectionSolution,
)
from .orbit import TLEPropagator, SatelliteState, find_access_windows, AccessWindow
from .client import SatelliteReflectorClient
from .server import ReferenceSatelliteServer
from .control import Target, solve_pointing, PointingController

__version__ = "0.1.0"

__all__ = [
    "Vec3",
    "geodetic_to_ecef",
    "ecef_to_geodetic",
    "sun_ecef",
    "solve_reflection",
    "ReflectionSolution",
    "TLEPropagator",
    "SatelliteState",
    "find_access_windows",
    "AccessWindow",
    "SatelliteReflectorClient",
    "ReferenceSatelliteServer",
    "Target",
    "solve_pointing",
    "PointingController",
    "__version__",
]
