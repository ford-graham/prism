import math

import pytest

from prism.geometry.vectors import Vec3


def test_vec3_products_and_norms():
    a = Vec3(1.0, 2.0, 3.0)
    b = Vec3(-2.0, 0.5, 4.0)
    assert a.dot(b) == pytest.approx(11.0)
    assert a.cross(b) == Vec3(6.5, -10.0, 4.5)
    assert a.norm() == pytest.approx(math.sqrt(14.0))
    assert a.normalized().norm() == pytest.approx(1.0)


def test_vec3_angles_and_zero_guards():
    assert Vec3(1, 0, 0).angle_to(Vec3(0, 1, 0)) == pytest.approx(math.pi / 2)
    with pytest.raises(ValueError):
        Vec3(0, 0, 0).normalized()
