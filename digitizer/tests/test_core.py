import numpy as np
import pytest
import os
from .. import core


filename = '../example_pdfs/test_figure1.pdf'

def test_to_svg():
    with open('test.svg', 'w') as f:
        f.write(core._to_svg(filename, page=0))
    with open('test_svg.txt', 'w') as f:
        f.write(core._to_svg(filename, page=0))


def test_distance():
    paths = core.Paths(core._to_svg(filename, page=0))
    for path in paths.paths[3].abs_path:
        assert path.size == 2
    for path in paths.paths:
        dist = path.distance((0, 0))
        if np.isfinite(dist):
            assert dist > 0
        else:
            print(path.abs_path)