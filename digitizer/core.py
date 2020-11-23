from xml.dom import minidom
import numpy as np
import fitz

try:
    from . import geometry
except ImportError:
    import geometry


def _to_svg(pdf, page, figure_num=0):
    with fitz.open(pdf) as doc:
        return list(doc.pages())[page].getSVGimage(
            text_as_path=True
        )


def _compute_abs_path(path):
    txts = path.getAttribute('d').strip().split(' ')
    mode = 'M'
    paths = []
    coord = [0, 0]
    idx = 0
    for txt in txts:
        if len(txt) == 1:
            mode = txt
        else:
            if mode in 'MLml':
                if mode in 'ML':
                    coord[idx] = float(txt)
                else:
                    coord[idx] += float(txt)
                if idx == 1:
                    paths.append(np.array(coord))
                    idx = 0
                else:
                    idx = 1
            elif mode in 'zZ':
                paths.append(np.array(paths[0]))
                idx = 0
            elif mode in 'hH':
                if mode == 'H':
                    coord[0] = float(txt)
                else:
                    coord[0] += float(txt)
                paths.append(np.array(coord))
                idx = 0
            elif mode in 'vV':
                if mode == 'V':
                    coord[1] = float(txt)
                else:
                    coord[1] += float(txt)
                paths.append(np.array(coord))
                idx = 0

    return paths


class Path:
    def __init__(self, path):
        self.path = path
        self._abs_path = None

    @property
    def abs_path(self):
        if self._abs_path is None:
            # compute self._abs_path
            self._abs_path = _compute_abs_path(self.path)
        return self._abs_path

    def distance2(self, point):
        if len(self.abs_path) == 0:
            return np.nan
        elif len(self.abs_path) == 1:
            # if this path is a single point
            dx = self.abs_path[0] - point
            return dx @ dx        
        
        distances = [
            geometry.distance2(
                self.abs_path[i], self.abs_path[i+1], point) 
            for i in range(len(self.abs_path) - 1)]
        return np.min(distances)


class Paths:
    """
    A collection of paths
    """
    def __init__(self, svg_txt):
        self.svg = svg_txt
        doc = minidom.parseString(svg_txt)
        # common attribute: style, d, id
        self.paths = [Path(path) for path in doc.getElementsByTagName('path')]

    def find_nearest(self, point):
        """
        Find the nearest path with given points = (x, y)
        """
        point = np.array(point)
        distances = [path.distance2(point) for path in self.paths]
        i = np.nanargmin(distances)
        return self.paths[i]

    def appended_svd(self, path):
        svg0 = self.svg[:self.svg.find('</svg>')]
        pathstring = path.toxml()
        

    def group(self, path, mode='style'):
        """
        returns a list of paths sharing the same style
        """
        pass