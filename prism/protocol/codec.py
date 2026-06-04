"""Wire framing for PRCP.

Frame layout::

    +-----------------------------+------------------------------+
    | 4-byte big-endian uint32 N  |  N bytes of UTF-8 JSON        |
    +-----------------------------+------------------------------+

This is a standard length-prefixed message framing that works correctly over a
TCP stream (it does not rely on newline delimiting and tolerates partial reads).
"""

from __future__ import annotations

import json
import socket
import struct
from typing import Any, Dict

PROTOCOL_VERSION = "prism/1"

_HEADER = struct.Struct(">I")
MAX_MESSAGE_BYTES = 1 << 20  # 1 MiB safety cap


class ProtocolError(Exception):
    """Raised on malformed frames or protocol violations."""


def encode_message(obj: Dict[str, Any]) -> bytes:
    payload = json.dumps(obj, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_MESSAGE_BYTES:
        raise ProtocolError(f"message too large: {len(payload)} bytes")
    return _HEADER.pack(len(payload)) + payload


def _recv_exactly(sock: socket.socket, n: int) -> bytes:
    chunks = []
    remaining = n
    while remaining > 0:
        chunk = sock.recv(remaining)
        if not chunk:
            raise ConnectionError("connection closed while reading frame")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def read_message(sock: socket.socket) -> Dict[str, Any]:
    """Block until one full message is read from ``sock`` and return it."""
    header = _recv_exactly(sock, _HEADER.size)
    (length,) = _HEADER.unpack(header)
    if length > MAX_MESSAGE_BYTES:
        raise ProtocolError(f"declared frame too large: {length} bytes")
    payload = _recv_exactly(sock, length)
    try:
        obj = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProtocolError(f"invalid JSON payload: {exc}") from exc
    if not isinstance(obj, dict) or "type" not in obj:
        raise ProtocolError("message must be a JSON object with a 'type' field")
    return obj


def send_message(sock: socket.socket, obj: Dict[str, Any]) -> None:
    sock.sendall(encode_message(obj))
