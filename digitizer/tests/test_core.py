import numpy as np
import pytest
import os
import fitz
from .. import core


filename = '../example_pdfs/test_figure1.pdf'
# filename2 = '../example_pdfs/1908.10464.pdf'
filename2 = '../example_pdfs/example2.pdf'

def test_to_svg():
    with open('test.svg', 'w') as f:
        f.write(core._to_svg(filename, page=0))
    with open('test_svg.txt', 'w') as f:
        f.write(core._to_svg(filename, page=0))
    
    pix_doc = fitz.open("test.svg")
    pix = pix_doc.getPagePixmap(0)
    pix.writePNG("test.png")


def test_to_svg2():
    with open('test2.svg', 'w') as f:
        f.write(core._to_svg(filename2, page=2))


def test_distance():
    paths = core.Paths(core._to_svg(filename, page=0))
    for path in paths.paths[3].abs_path:
        assert path.size == 2
    for path in paths.paths:
        dist = path.distance2((0, 0))
        if np.isfinite(dist):
            assert dist > 0
        else:
            print(path.abs_path)

def test_selected():
    paths = core.Paths(core._to_svg(filename, page=0))
    path = paths.find_nearest([200, 130])
    with open('test_append.svg', 'w') as f:
        f.write(paths.appended_svd(path))

def test_group():
    paths = core.Paths(core._to_svg(filename, page=0))
    path = paths.find_nearest([200, 130])
    paths.group(path)
    with open('test_append2.svg', 'w') as f:
        f.write(paths.appended_svd(path))

