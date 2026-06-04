"""Reference satellite endpoint.

This is a real TCP server that speaks PRCP. It models a single reflector
satellite: it holds an attitude/mirror-normal state, accepts POINT commands,
reports status and streams nothing it cannot justify. It exists so the whole
framework is end-to-end runnable and testable *today*, and so flight-software
authors have an executable reference for the protocol.

It is the endpoint a client reaches "by IP address": run it on a host (a
ground-station gateway, a HIL bench, a cubesat's onboard computer) and point a
:class:`prism.client.SatelliteReflectorClient` at that host.
"""

from __future__ import annotations

import datetime as _dt
import socketserver
import threading
from typing import List, Optional

from .protocol import codec, messages
from .protocol.codec import ProtocolError
from .geometry.vectors import Vec3

CAPABILITIES = ["status", "point", "set_mode", "ping"]


class SatelliteState:
    """Thread-safe mutable state of the reference satellite."""

    def __init__(self, satellite_id: str) -> None:
        self.satellite_id = satellite_id
        self.lock = threading.Lock()
        self.mode = messages.MODE_IDLE
        self.mirror_normal_ecef: Optional[List[float]] = None
        self.last_target: Optional[dict] = None
        self.last_command_utc: Optional[str] = None
        self.commands_received = 0

    def snapshot(self) -> dict:
        with self.lock:
            return {
                "satellite_id": self.satellite_id,
                "mode": self.mode,
                "mirror_normal_ecef": self.mirror_normal_ecef,
                "last_target": self.last_target,
                "last_command_utc": self.last_command_utc,
                "commands_received": self.commands_received,
                "time_utc": _dt.datetime.utcnow().isoformat() + "Z",
            }

    def apply_point(self, normal_ecef: List[float], target: Optional[dict]) -> None:
        with self.lock:
            self.mirror_normal_ecef = list(normal_ecef)
            self.last_target = target
            self.last_command_utc = _dt.datetime.utcnow().isoformat() + "Z"
            self.commands_received += 1
            if self.mode == messages.MODE_IDLE:
                self.mode = messages.MODE_TRACK

    def set_mode(self, mode: str) -> None:
        with self.lock:
            self.mode = mode


class _Handler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        sock = self.request
        server: "ReferenceSatelliteServer" = self.server  # type: ignore[assignment]
        state = server.state
        authenticated = server.token is None

        try:
            hello = codec.read_message(sock)
            if hello.get("type") != messages.HELLO:
                codec.send_message(sock, messages.error("expected hello"))
                return
            if hello.get("protocol") != codec.PROTOCOL_VERSION:
                codec.send_message(sock, messages.error("protocol version mismatch"))
                return
            codec.send_message(
                sock, messages.welcome(state.satellite_id, CAPABILITIES)
            )

            while True:
                try:
                    msg = codec.read_message(sock)
                except (ConnectionError, ProtocolError):
                    return

                mtype = msg.get("type")

                if mtype == messages.AUTH:
                    ok = msg.get("token") == server.token
                    authenticated = authenticated or ok
                    codec.send_message(
                        sock,
                        messages.auth_result(ok, "" if ok else "invalid token"),
                    )
                    continue

                if not authenticated:
                    codec.send_message(sock, messages.error("authentication required"))
                    continue

                if mtype == messages.PING:
                    codec.send_message(sock, messages.pong(msg.get("nonce")))
                elif mtype == messages.GET_STATUS:
                    codec.send_message(sock, messages.status(**state.snapshot()))
                elif mtype == messages.POINT:
                    normal = msg.get("normal_ecef")
                    if not _is_vec3(normal):
                        codec.send_message(
                            sock, messages.error("point requires normal_ecef [x,y,z]")
                        )
                        continue
                    state.apply_point(normal, msg.get("target"))
                    codec.send_message(
                        sock,
                        messages.ack(True, "mirror normal updated", ref=msg.get("ref")),
                    )
                elif mtype == messages.SET_MODE:
                    mode = msg.get("mode")
                    if mode not in messages.VALID_MODES:
                        codec.send_message(sock, messages.error(f"invalid mode {mode!r}"))
                        continue
                    state.set_mode(mode)
                    codec.send_message(sock, messages.ack(True, f"mode={mode}"))
                else:
                    codec.send_message(sock, messages.error(f"unknown type {mtype!r}"))
        except (ConnectionError, ProtocolError):
            return


def _is_vec3(v) -> bool:
    return (
        isinstance(v, (list, tuple))
        and len(v) == 3
        and all(isinstance(c, (int, float)) for c in v)
    )


class ReferenceSatelliteServer(socketserver.ThreadingTCPServer):
    """Threaded PRCP server. Bind it to an interface and serve."""

    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 5723,
        *,
        satellite_id: str = "REFLECTOR-1",
        token: Optional[str] = None,
    ) -> None:
        self.state = SatelliteState(satellite_id)
        self.token = token
        super().__init__((host, port), _Handler)

    @property
    def bound_address(self):
        return self.server_address

    def serve_in_thread(self) -> threading.Thread:
        """Start serving on a background daemon thread and return it."""
        thread = threading.Thread(target=self.serve_forever, daemon=True)
        thread.start()
        return thread
