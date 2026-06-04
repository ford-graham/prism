"""Command-line interface for prism.

Subcommands
-----------
  serve    Run the reference satellite endpoint (the thing you connect to).
  status   Connect to a satellite by IP and print its status.
  solve    Compute the reflection solution for a TLE + target at a time.
  windows  List reflection-access windows over a time span.
  point    Connect to a satellite and run the closed pointing loop.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from typing import List, Optional

from .orbit.propagator import TLEPropagator
from .orbit.access import find_access_windows
from .control import Target, solve_pointing, PointingController
from .client import SatelliteReflectorClient
from .server import ReferenceSatelliteServer


def _parse_when(s: Optional[str]) -> _dt.datetime:
    if s is None or s.lower() == "now":
        return _dt.datetime.utcnow()
    # Accept ISO 8601, optionally trailing 'Z'.
    return _dt.datetime.fromisoformat(s.replace("Z", ""))


def _parse_target(s: str) -> Target:
    parts = [p.strip() for p in s.split(",")]
    if len(parts) not in (2, 3):
        raise argparse.ArgumentTypeError("target must be 'lat,lon' or 'lat,lon,alt_km'")
    lat, lon = float(parts[0]), float(parts[1])
    alt = float(parts[2]) if len(parts) == 3 else 0.0
    return Target(lat, lon, alt)


def _load_propagator(args) -> TLEPropagator:
    if args.tle:
        return TLEPropagator.from_file(args.tle)
    if args.line1 and args.line2:
        return TLEPropagator(args.line1, args.line2, name=args.name or "satellite")
    raise SystemExit("error: provide --tle FILE or both --line1 and --line2")


# -- subcommands -----------------------------------------------------
def cmd_serve(args) -> int:
    server = ReferenceSatelliteServer(
        host=args.host, port=args.port,
        satellite_id=args.satellite_id, token=args.token,
    )
    host, port = server.bound_address
    print(f"[prism] reference satellite '{args.satellite_id}' listening on "
          f"{host}:{port}" + (" (auth required)" if args.token else ""))
    print("[prism] connect with:  prism status --host <ip> "
          f"--port {port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[prism] shutting down")
        server.shutdown()
    return 0


def cmd_status(args) -> int:
    with SatelliteReflectorClient(args.host, args.port, token=args.token) as sat:
        print(json.dumps(sat.get_status(), indent=2))
    return 0


def cmd_solve(args) -> int:
    prop = _load_propagator(args)
    when = _parse_when(args.time)
    sol = solve_pointing(prop, args.target, when,
                         min_target_elevation_deg=args.min_elevation)
    out = {"time_utc": when.isoformat() + "Z", **sol.to_dict()}
    print(json.dumps(out, indent=2))
    return 0 if sol.feasible else 2


def cmd_windows(args) -> int:
    prop = _load_propagator(args)
    start = _parse_when(args.start)
    end = start + _dt.timedelta(hours=args.hours)
    windows = find_access_windows(
        prop, args.target.lat, args.target.lon, start, end,
        target_alt_km=args.target.alt_km,
        step_s=args.step,
        min_target_elevation_deg=args.min_elevation,
        require_target_darkness=args.dark,
    )
    if not windows:
        print("no reflection-access windows found in the span")
        return 2
    for w in windows:
        print(f"{w.start.isoformat()}Z -> {w.end.isoformat()}Z  "
              f"({w.duration_s:6.0f}s)  peak_elev={w.peak_elevation_deg:5.1f} deg "
              f"@ {w.peak.isoformat()}Z")
    return 0


def cmd_point(args) -> int:
    prop = _load_propagator(args)
    with SatelliteReflectorClient(args.host, args.port, token=args.token) as sat:
        print(f"[prism] connected to {sat.satellite_id} at {args.host}:{args.port}")
        controller = PointingController(
            sat, prop, args.target,
            min_target_elevation_deg=args.min_elevation,
            update_interval_s=args.interval,
        )

        def report(sol):
            stamp = _dt.datetime.utcnow().isoformat()
            if sol.feasible:
                print(f"{stamp}Z  COMMAND  incidence={sol.incidence_angle_deg:5.1f} deg "
                      f"elev={sol.target_elevation_deg:5.1f} deg "
                      f"range={sol.slant_range_km:7.1f} km")
            else:
                print(f"{stamp}Z  hold     {sol.reason}")

        controller.run(args.duration, on_update=report)
    return 0


# -- parser ----------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="prism", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    def add_tle_args(sp):
        sp.add_argument("--tle", help="path to a 2/3-line TLE file")
        sp.add_argument("--line1", help="TLE line 1 (if not using --tle)")
        sp.add_argument("--line2", help="TLE line 2 (if not using --tle)")
        sp.add_argument("--name", help="satellite name (with --line1/--line2)")

    def add_net_args(sp):
        sp.add_argument("--host", required=True, help="satellite IP address / host")
        sp.add_argument("--port", type=int, default=5723, help="satellite port (default 5723)")
        sp.add_argument("--token", help="auth token, if the satellite requires one")

    sp = sub.add_parser("serve", help="run the reference satellite endpoint")
    sp.add_argument("--host", default="0.0.0.0", help="bind address (default 0.0.0.0)")
    sp.add_argument("--port", type=int, default=5723)
    sp.add_argument("--satellite-id", default="REFLECTOR-1")
    sp.add_argument("--token", help="require this auth token from clients")
    sp.set_defaults(func=cmd_serve)

    sp = sub.add_parser("status", help="connect to a satellite and print status")
    add_net_args(sp)
    sp.set_defaults(func=cmd_status)

    sp = sub.add_parser("solve", help="compute a reflection solution (no network)")
    add_tle_args(sp)
    sp.add_argument("--target", required=True, type=_parse_target,
                    help="ground target 'lat,lon' or 'lat,lon,alt_km'")
    sp.add_argument("--time", help="UTC time (ISO 8601) or 'now' (default)")
    sp.add_argument("--min-elevation", type=float, default=10.0,
                    help="minimum target elevation in degrees (default 10)")
    sp.set_defaults(func=cmd_solve)

    sp = sub.add_parser("windows", help="list reflection-access windows")
    add_tle_args(sp)
    sp.add_argument("--target", required=True, type=_parse_target)
    sp.add_argument("--start", help="UTC start (ISO 8601) or 'now' (default)")
    sp.add_argument("--hours", type=float, default=24.0, help="span in hours (default 24)")
    sp.add_argument("--step", type=float, default=10.0, help="sample step seconds (default 10)")
    sp.add_argument("--min-elevation", type=float, default=10.0)
    sp.add_argument("--dark", action="store_true",
                    help="require the target to be in darkness (useful-beam constraint)")
    sp.set_defaults(func=cmd_windows)

    sp = sub.add_parser("point", help="connect and run the closed pointing loop")
    add_tle_args(sp)
    add_net_args(sp)
    sp.add_argument("--target", required=True, type=_parse_target)
    sp.add_argument("--duration", type=float, default=60.0, help="loop seconds (default 60)")
    sp.add_argument("--interval", type=float, default=2.0, help="update seconds (default 2)")
    sp.add_argument("--min-elevation", type=float, default=10.0)
    sp.set_defaults(func=cmd_point)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ConnectionError, OSError) as exc:
        print(f"network error: {exc}", file=sys.stderr)
        return 1
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 - surface a clean message to the CLI
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
