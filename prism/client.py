"""The network client: connect to a satellite endpoint by IP address.

This is a real TCP client. You give it the satellite's host/IP and port; it
performs the PRCP handshake, optionally authenticates, and lets you query status
and command the mirror. Whatever is listening on the other end -- the bundled
reference server, a ground-station gateway, or real flight hardware that speaks
PRCP -- is controlled identically.
"""

from __future__ import annotations

import socket
from typing import Any, Dict, List, Optional

from .protocol import codec, messages
from .protocol.codec import ProtocolError


class SatelliteReflectorClient:
    """Client for a single satellite reflector endpoint.

    Usage::

        with SatelliteReflectorClient("192.0.2.10", 5723, token="secret") as sat:
            print(sat.get_status())
            sat.point([0.1, 0.2, 0.97], target={"lat": 51.5, "lon": -0.1})
    """

    def __init__(
        self,
        host: str,
        port: int = 5723,
        *,
        token: Optional[str] = None,
        timeout: float = 10.0,
        client_name: str = "prism-client",
    ) -> None:
        self.host = host
        self.port = port
        self.token = token
        self.timeout = timeout
        self.client_name = client_name
        self._sock: Optional[socket.socket] = None
        self.satellite_id: Optional[str] = None
        self.capabilities: List[str] = []

    # -- connection lifecycle ----------------------------------------
    def connect(self) -> Dict[str, Any]:
        """Open the socket and complete the PRCP handshake + auth."""
        sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        sock.settimeout(self.timeout)
        self._sock = sock

        codec.send_message(sock, messages.hello(self.client_name))
        welcome = codec.read_message(sock)
        if welcome.get("type") != messages.WELCOME:
            raise ProtocolError(f"expected welcome, got {welcome.get('type')!r}")
        if welcome.get("protocol") != codec.PROTOCOL_VERSION:
            raise ProtocolError(
                f"protocol mismatch: server speaks {welcome.get('protocol')!r}, "
                f"client speaks {codec.PROTOCOL_VERSION!r}"
            )
        self.satellite_id = welcome.get("satellite_id")
        self.capabilities = welcome.get("capabilities", [])

        if self.token is not None:
            codec.send_message(sock, messages.auth(self.token))
            result = self._read()
            if result.get("type") != messages.AUTH_RESULT or not result.get("ok"):
                raise ProtocolError(
                    f"authentication failed: {result.get('reason', 'unknown')}"
                )
        return welcome

    def close(self) -> None:
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def __enter__(self) -> "SatelliteReflectorClient":
        self.connect()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- request/response helpers ------------------------------------
    def _require_sock(self) -> socket.socket:
        if self._sock is None:
            raise RuntimeError("client is not connected; call connect() first")
        return self._sock

    def _read(self) -> Dict[str, Any]:
        return codec.read_message(self._require_sock())

    def _request(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        sock = self._require_sock()
        codec.send_message(sock, msg)
        return codec.read_message(sock)

    # -- commands ----------------------------------------------------
    def get_status(self) -> Dict[str, Any]:
        reply = self._request(messages.get_status())
        if reply.get("type") == messages.ERROR:
            raise ProtocolError(reply.get("message", "error"))
        return reply

    def point(
        self,
        normal_ecef: List[float],
        *,
        target: Optional[Dict[str, float]] = None,
        hold_s: float = 5.0,
        ref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Command the mirror surface normal (ECEF unit vector)."""
        reply = self._request(
            messages.point(normal_ecef, target=target, hold_s=hold_s, ref=ref)
        )
        if reply.get("type") == messages.ERROR:
            raise ProtocolError(reply.get("message", "error"))
        return reply

    def set_mode(self, mode: str) -> Dict[str, Any]:
        reply = self._request(messages.set_mode(mode))
        if reply.get("type") == messages.ERROR:
            raise ProtocolError(reply.get("message", "error"))
        return reply

    def ping(self, nonce: Optional[str] = None) -> Dict[str, Any]:
        return self._request(messages.ping(nonce))
