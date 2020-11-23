import numpy as np


def distance2(x, x0, x1=None):
    """
    Obtain the distance between a path x0-x1 and x.
    """
    x0 = x0 - x
    if x1 is None:
        return x0 @ x0
    x1 = x1 - x
    dx = x1 - x0
    if dx @ x0 < 0.0 and dx @ x1 > 0.0:
        # x is inside x0 and x1
        x_sum = x0 + x1
        return 0.25 * (x_sum @ x_sum - (x0 @ x0 - x1 @ x1)**2 / (dx @ dx))

    # x is outside x0 and x1
    return np.minimum(x0 @ x0, x1 @ x1)


