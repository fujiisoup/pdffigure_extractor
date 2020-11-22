import numpy as np


def distance2(x0, x1, x):
    """
    Obtain the distance between a path x0-x1 and x.
    """
    x0 = x0 - x
    x1 = x1 - x
    dx = x1 - x0
    if dx @ x0 < 0.0 and dx @ x1 > 0.0:
        # x is inside x0 and x1
        x_sum = x0 + x0
        return 0.25 * (x_sum @ x_sum - (x0 @ x0 - x1 @ x1)**2 / (dx @ dx))
    elif dx @ x0 < 0.0:
        # nearest point is x1
        return x1 @ x1
    else: 
        # nearest point is x0
        return x0 @ x0


