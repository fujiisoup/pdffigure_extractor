import pytest
import numpy as np
from .. import geometry


@pytest.mark.parametrize(('x0', 'x1', 'x', 'distance_squared'), [
    ([1, 0], [0, 1], [0, 0], 1 / 2),
    ([3, 2], [2, 3], [2, 2], 1 / 2),
])
def test_distance2(x0, x1, x, distance_squared):
    x0 = np.array(x0)
    x1 = np.array(x1)
    x = np.array(x)
    assert np.allclose(geometry.distance2(x, x0, x1), distance_squared)

