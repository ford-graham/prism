"""A minimal, dependency-free 3-vector.

We deliberately avoid numpy so the framework installs cleanly anywhere and the
math stays auditable. Units are caller-defined (kilometres throughout the rest
of the package).
"""

from __future__ import annotations

import math
from typing import Iterable, Tuple


class Vec3:
    __slots__ = ("x", "y", "z")

    def __init__(self, x: float, y: float, z: float) -> None:
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    # -- construction -------------------------------------------------
    @classmethod
    def from_iterable(cls, it: Iterable[float]) -> "Vec3":
        x, y, z = it
        return cls(x, y, z)

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def as_list(self):
        return [self.x, self.y, self.z]

    # -- arithmetic ---------------------------------------------------
    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, s: float) -> "Vec3":
        return Vec3(self.x * s, self.y * s, self.z * s)

    __rmul__ = __mul__

    def __truediv__(self, s: float) -> "Vec3":
        return Vec3(self.x / s, self.y / s, self.z / s)

    def __neg__(self) -> "Vec3":
        return Vec3(-self.x, -self.y, -self.z)

    # -- products -----------------------------------------------------
    def dot(self, other: "Vec3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    # -- norms --------------------------------------------------------
    def norm(self) -> float:
        return math.sqrt(self.dot(self))

    def normalized(self) -> "Vec3":
        n = self.norm()
        if n == 0.0:
            raise ValueError("cannot normalize a zero-length vector")
        return self / n

    def angle_to(self, other: "Vec3") -> float:
        """Angle (radians) between this vector and ``other``."""
        denom = self.norm() * other.norm()
        if denom == 0.0:
            raise ValueError("cannot take an angle with a zero-length vector")
        c = max(-1.0, min(1.0, self.dot(other) / denom))
        return math.acos(c)

    # -- dunder -------------------------------------------------------
    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z

    def __repr__(self) -> str:
        return f"Vec3({self.x:.6g}, {self.y:.6g}, {self.z:.6g})"

    def __eq__(self, other) -> bool:
        return (
            isinstance(other, Vec3)
            and self.x == other.x
            and self.y == other.y
            and self.z == other.z
        )
