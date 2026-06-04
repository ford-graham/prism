import datetime as _dt
import socket

import pytest

from prism.protocol import codec, messages
from prism.orbit.propagator import TLEPropagator
from prism.control import Target, solve_pointing
from prism.client import SatelliteReflectorClient
from prism.server import ReferenceSatelliteServer

# A real published ISS TLE (epoch 2023). Used purely as deterministic test data.
ISS_TLE = """ISS (ZARYA)
1 25544U 98067A   23274.54791667  .00016717  00000-0  30074-3 0  9994
2 25544  51.6416 247.4627 0006703 130.5360 325.0288 15.49514637 12345"""


def test_codec_roundtrip_over_socket():
    a, b = socket.socketpair()
    try:
        msg = messages.point([0.1, 0.2, 0.9733285], target={"lat": 1.0, "lon": 2.0},
                             hold_s=4.0, ref="abc")
        codec.send_message(a, msg)
        got = codec.read_message(b)
        assert got == msg
    finally:
        a.close()
        b.close()


def test_codec_rejects_non_object():
    import struct
    a, b = socket.socketpair()
    try:
        # A valid frame whose payload is a JSON array, not an object -> rejected.
        payload = b"[1,2,3]"
        a.sendall(struct.pack(">I", len(payload)) + payload)
        with pytest.raises(codec.ProtocolError):
            codec.read_message(b)
    finally:
        a.close()
        b.close()


def test_propagator_iss_reasonable():
    prop = TLEPropagator.from_tle_text(ISS_TLE)
    state = prop.propagate(_dt.datetime(2023, 10, 1, 13, 0, 0))
    assert 300.0 < state.altitude_km < 460.0       # ISS altitude band
    assert -52.0 < state.latitude_deg < 52.0        # within inclination
    assert state.position_ecef_km.norm() == pytest.approx(
        6378.137 + state.altitude_km, rel=0.02
    )


def test_solve_pointing_returns_solution():
    prop = TLEPropagator.from_tle_text(ISS_TLE)
    sol = solve_pointing(prop, Target(51.5, -0.12), _dt.datetime(2023, 10, 1, 13, 0, 0),
                         min_target_elevation_deg=-90.0)
    n = sol.mirror_normal_ecef
    assert abs(n.norm() - 1.0) < 1e-9
    assert 0.0 <= sol.incidence_angle_deg <= 180.0


def _free_server():
    return ReferenceSatelliteServer(host="127.0.0.1", port=0, satellite_id="TEST-SAT")


def test_end_to_end_client_server():
    server = _free_server()
    server.serve_in_thread()
    host, port = server.bound_address
    try:
        with SatelliteReflectorClient(host, port) as sat:
            assert sat.satellite_id == "TEST-SAT"
            assert "point" in sat.capabilities

            status0 = sat.get_status()
            assert status0["commands_received"] == 0
            assert status0["mirror_normal_ecef"] is None

            ack = sat.point([0.0, 0.0, 1.0], target={"lat": 10.0, "lon": 20.0}, ref="r1")
            assert ack["type"] == messages.ACK and ack["ok"] and ack["ref"] == "r1"

            status1 = sat.get_status()
            assert status1["commands_received"] == 1
            assert status1["mirror_normal_ecef"] == [0.0, 0.0, 1.0]
            assert status1["mode"] == messages.MODE_TRACK

            pong = sat.ping("xyz")
            assert pong["type"] == messages.PONG and pong["nonce"] == "xyz"
    finally:
        server.shutdown()
        server.server_close()


def test_auth_required():
    server = ReferenceSatelliteServer(host="127.0.0.1", port=0, token="s3cret")
    server.serve_in_thread()
    host, port = server.bound_address
    try:
        # Wrong token -> connect() raises during handshake auth.
        with pytest.raises(Exception):
            SatelliteReflectorClient(host, port, token="wrong").connect()
        # Correct token works.
        with SatelliteReflectorClient(host, port, token="s3cret") as sat:
            assert sat.get_status()["satellite_id"] == "REFLECTOR-1"
    finally:
        server.shutdown()
        server.server_close()
