# Prism

**Prism is a framework for computing and commanding orbital sunlight-reflector
("space mirror") satellites.** It does the real astrodynamics — where the
satellite is, where the Sun is, and the exact mirror orientation needed to
bounce sunlight onto a point on the ground — and it ships a real network
protocol and client so you can drive a reflector satellite over a socket, given
its address.

```
   Sun
     \
      \   incoming sunlight
       \
        \        ____
         \      /    \   satellite + flat mirror
          \    | n ^  |
           \   |   |  |   mirror normal n bisects the
            \  |   |  |   sun and target directions
             \ |   |  |
              \|___|__|
               \   |
                \  |  reflected beam
                 \ |
                  \|
        ___________X__________  target (lat, lon)
        Earth
```

---

## Install

```bash
pip install prism            # or, from a checkout:
pip install -e .
```

Python ≥ 3.8. The only runtime dependency is `sgp4`.

---

## Quick start (end-to-end, no hardware)

**1. Run a satellite endpoint** in one terminal:

```bash
prism serve --port 5723 --satellite-id REFLECTOR-1
# [prism] reference satellite 'REFLECTOR-1' listening on 0.0.0.0:5723
```

**2. Connect to it by address** from another terminal:

```bash
prism status --host 127.0.0.1 --port 5723
```

**3. Compute a pointing solution** for a real satellite + ground target. Save a
TLE (e.g. from celestrak.org) to `sat.tle`, then:

```bash
prism solve --tle sat.tle --target 51.5074,-0.1278 --time now
```

```json
{
  "time_utc": "2025-...Z",
  "feasible": true,
  "mirror_normal_ecef": [0.1837, -0.4021, 0.8971],
  "incidence_angle_deg": 22.4,
  "target_elevation_deg": 41.8,
  "slant_range_km": 712.3,
  "satellite_sunlit": true,
  "target_sun_elevation_deg": -8.1
}
```

**4. Find the windows** when a target can actually be illuminated over the next
day (and require the target to be in darkness for the beam to be visible):

```bash
prism windows --tle sat.tle --target 51.5074,-0.1278 --hours 24 --dark
```

**5. Close the loop** — connect to the satellite and continuously command the
mirror normal as the geometry evolves:

```bash
prism point --tle sat.tle --target 51.5074,-0.1278 \
            --host 192.0.2.10 --port 5723 --duration 120
```

---

## Library API

```python
import datetime as dt
from prism import (
    TLEPropagator, Target, solve_pointing,
    SatelliteReflectorClient, find_access_windows,
)

prop = TLEPropagator.from_file("sat.tle")
target = Target(lat=51.5074, lon=-0.1278)

# Pure computation (no network):
sol = solve_pointing(prop, target, dt.datetime.utcnow())
print(sol.feasible, sol.mirror_normal_ecef, sol.incidence_angle_deg)

# Drive a real satellite endpoint by IP:
with SatelliteReflectorClient("192.0.2.10", 5723, token="optional") as sat:
    print(sat.get_status())
    sat.point(sol.mirror_normal_ecef.as_list(),
              target={"lat": target.lat, "lon": target.lon})
```

---

## How the pointing math works

Given the satellite position **S**, the target **T** and the Sun position
(all in Earth-fixed ECEF coordinates), Prism forms two unit vectors from the
satellite: **u_sun** toward the Sun and **u_target** toward the target. A flat
mirror reflects the incoming ray about its surface normal, so the normal that
sends sunlight to the target is their normalized sum:

```
n = normalize(u_sun + u_target)
```

By construction the angle of incidence equals the angle of reflection. Prism
then checks feasibility:

| Check                | Meaning                                                        |
|----------------------|----------------------------------------------------------------|
| satellite sunlit     | cylindrical-umbra shadow test against the Earth                |
| target above horizon | line of sight from satellite to target is clear               |
| incidence < 90°      | the geometry is physically reflectable                        |
| target in darkness*  | optional: Sun below the target horizon, so the beam is visible |

Frames: SGP4 returns TEME; Prism rotates it into ECEF by GMST (neglecting
precession/nutation/polar motion), and places the Sun in the *same* ECEF frame,
so the reflection geometry is internally consistent. This is accurate to a few
arc-minutes — appropriate for access planning and slew commanding, not for
sub-pixel beam placement.

---

## The PRCP protocol

A frame is a 4-byte big-endian length prefix followed by a UTF-8 JSON object
with a `"type"` field. Message vocabulary:

| Direction        | Types                                            |
|------------------|--------------------------------------------------|
| client → sat     | `hello` `auth` `get_status` `point` `set_mode` `ping` |
| sat → client     | `welcome` `auth_result` `status` `ack` `pong` `error` |

`point` carries `normal_ecef: [x, y, z]` (the commanded mirror surface normal as
an ECEF unit vector), an optional `target`, and a `hold_s` duration. To make
real hardware controllable by Prism, implement this contract on the spacecraft
(or in a gateway that relays it over your RF/operator link).

---

## Layout

```
prism/
  geometry/      vectors, time (JD/GMST), coordinates, sun ephemeris, reflection solver
  orbit/         SGP4 propagator, access-window search
  protocol/      PRCP codec (framing) and message vocabulary
  client.py      SatelliteReflectorClient — connect by IP
  server.py      ReferenceSatelliteServer — runnable PRCP endpoint
  control.py     solve_pointing() and the closed-loop PointingController
  cli.py         the `prism` command
tests/           geometry, protocol and end-to-end client/server tests
```

Run the tests with `pytest`.

---

## License

MIT.
