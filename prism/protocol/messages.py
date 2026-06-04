"""PRCP message constructors and type constants.

Every message is a JSON object with a ``"type"`` field. Builders below keep the
client and server honest about the schema. Keeping these as plain dict factories
(rather than classes) keeps the wire contract obvious and language-agnostic --
a non-Python flight computer can implement the same strings.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .codec import PROTOCOL_VERSION

# Client -> server
HELLO = "hello"
AUTH = "auth"
GET_STATUS = "get_status"
POINT = "point"
SET_MODE = "set_mode"
PING = "ping"

# Server -> client
WELCOME = "welcome"
AUTH_RESULT = "auth_result"
STATUS = "status"
ACK = "ack"
PONG = "pong"
ERROR = "error"

# Satellite operating modes
MODE_IDLE = "idle"
MODE_TRACK = "track"
MODE_SAFE = "safe"
VALID_MODES = {MODE_IDLE, MODE_TRACK, MODE_SAFE}


def hello(client_name: str = "prism-client") -> Dict[str, Any]:
    return {"type": HELLO, "protocol": PROTOCOL_VERSION, "client": client_name}


def welcome(satellite_id: str, capabilities: List[str]) -> Dict[str, Any]:
    return {
        "type": WELCOME,
        "protocol": PROTOCOL_VERSION,
        "satellite_id": satellite_id,
        "capabilities": capabilities,
    }


def auth(token: str) -> Dict[str, Any]:
    return {"type": AUTH, "token": token}


def auth_result(ok: bool, reason: str = "") -> Dict[str, Any]:
    return {"type": AUTH_RESULT, "ok": ok, "reason": reason}


def get_status() -> Dict[str, Any]:
    return {"type": GET_STATUS}


def status(**fields: Any) -> Dict[str, Any]:
    msg = {"type": STATUS}
    msg.update(fields)
    return msg


def point(
    normal_ecef: List[float],
    *,
    target: Optional[Dict[str, float]] = None,
    hold_s: float = 5.0,
    ref: Optional[str] = None,
) -> Dict[str, Any]:
    """Command the mirror to a surface-normal orientation (ECEF unit vector)."""
    msg: Dict[str, Any] = {
        "type": POINT,
        "normal_ecef": list(normal_ecef),
        "hold_s": hold_s,
    }
    if target is not None:
        msg["target"] = target
    if ref is not None:
        msg["ref"] = ref
    return msg


def set_mode(mode: str) -> Dict[str, Any]:
    return {"type": SET_MODE, "mode": mode}


def ping(nonce: Optional[str] = None) -> Dict[str, Any]:
    msg = {"type": PING}
    if nonce is not None:
        msg["nonce"] = nonce
    return msg


def pong(nonce: Optional[str] = None) -> Dict[str, Any]:
    msg = {"type": PONG}
    if nonce is not None:
        msg["nonce"] = nonce
    return msg


def ack(ok: bool, message: str = "", ref: Optional[str] = None) -> Dict[str, Any]:
    msg = {"type": ACK, "ok": ok, "message": message}
    if ref is not None:
        msg["ref"] = ref
    return msg


def error(message: str) -> Dict[str, Any]:
    return {"type": ERROR, "message": message}
