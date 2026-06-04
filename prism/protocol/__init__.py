"""PRCP -- the Prism Reflector Control Protocol.

A small, real, framed request/response protocol. The wire format is a 4-byte
big-endian length prefix followed by a UTF-8 JSON object (see :mod:`codec`).
The message vocabulary is defined in :mod:`messages`.

The same protocol is spoken by :class:`prism.client.SatelliteReflectorClient`
and by :class:`prism.server.ReferenceSatelliteServer`. Real flight hardware
(or a ground-station gateway that bridges to it) only needs to implement the
same message contract to be controllable by this framework.
"""

from .codec import (
    PROTOCOL_VERSION,
    encode_message,
    read_message,
    send_message,
    ProtocolError,
)
from . import messages

__all__ = [
    "PROTOCOL_VERSION",
    "encode_message",
    "read_message",
    "send_message",
    "ProtocolError",
    "messages",
]
