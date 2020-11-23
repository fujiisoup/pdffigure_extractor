import copy
from xml.dom import minidom
import numpy as np
import fitz

try:
    from . import geometry
except ImportError:
    import geometry


def n_pages(pdf):
    with fitz.open(pdf) as doc:
        return len(list(doc.pages()))
    
def _to_svg(pdf, page, figure_num=0):
    with fitz.open(pdf) as doc:
        return list(doc.pages())[page].getSVGimage(
            text_as_path=False
        )


def _compute_abs_path(path):
    d = path.getAttribute('d')
    if 'C' in d:
        # curve is not implemented
        return np.array([[np.nan, np.nan]])

    txts = d.strip().split(' ')

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
    # consider transform
    transform = path.getAttribute('transform')
    if transform is not None:
        transform = transform[transform.find('matrix(') + 7:-1].split(',')
        a, b, c, d, e, f = [float(t) for t in transform]
        scale = np.array([[a, b], [c, d]])
        offset = np.array([e, f])
        paths = [scale @ path + offset for path in paths]
    
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
        """
        Return nearest distance
        """
        if len(self.abs_path) == 0:
            return np.nan
        elif len(self.abs_path) == 1:
            # if this path is a single point
            dx = self.abs_path[0] - point
            return dx @ dx        
        
        distances = [
            geometry.distance2(
                point, self.abs_path[i], self.abs_path[i+1]) 
            for i in range(len(self.abs_path) - 1)]
        return np.min(distances)

    def closest_point(self, point):
        """
        Return the nearest point and distace
        """
        if len(self.abs_path) == 0:
            return np.nan
        idx = np.nanargmin([
            geometry.distance2(point, path)
            for path in self.abs_path
        ])
        return self.abs_path[idx]

    def is_inside(self, xmin, xmax):
        return all([
            ((xmin <= path) * (path <= xmax)).all() 
            for path in self.abs_path
        ])
    
    @property
    def size2(self):
        if len(self.abs_path) == 0:
            return 0
        dx = np.nanmax(self.abs_path, axis=0) - np.nanmin(self.abs_path)
        return dx @ dx

    @property
    def center(self):
        abs_path = np.stack(self.abs_path, axis=0)
        return 0.5 * (
            np.nanmax(abs_path, axis=0) + np.nanmin(abs_path, axis=0)
        )


class Paths:
    """
    A collection of paths
    """
    def __init__(self, svg_txt):
        self.svg = svg_txt
        doc = minidom.parseString(svg_txt)
        # common attribute: style, d, id
        self.paths = [Path(path) for path in doc.getElementsByTagName('path')]
        
        width = doc.getElementsByTagName('svg')[0].getAttribute('width')
        self.unit = width[-4:]        
        
    def _to_inch(self, val):
        if self.unit[-2:] == 'pt':
            return val / 72
        else:
            raise NotImplementedError

    def _from_inch(self, val):
        if self.unit[-2:] == 'pt':
            return val * 72
        else:
            raise NotImplementedError

    def find_nearest(self, point):
        """
        Find the nearest path with given points = (x, y) with unit inch
        
        if node is True, we find the closest node
        """
        point = self._from_inch(np.array(point))
        distances = [path.distance2(point) for path in self.paths]
        if len(distances) == 0:
            return None
        i = np.nanargmin(distances)
        return self.paths[i]

    def find_inside(self, point0, point1):
        x = self._from_inch(np.stack([point0, point1], axis=0))
        xmin, xmax = np.min(x, axis=0), np.max(x, axis=0)
        
        paths = [path for path in self.paths if path.is_inside(xmin, xmax)]
        if len(paths) > 0:
            idx = np.argmax([path.size2 for path in paths])
            return paths[idx]
        else:
            return None

    def find_nearest_point(self, path, point):
        point = self._from_inch(np.array(point))
        return path.closest_point(point)

    def appended_svd(self, given_path, point):
        svg0 = self.svg[:self.svg.find('</svg>')]
        txt = svg0
        # keep oritinal attributes
        attrs = {k: v for k, v in given_path.path.attributes.items()}

        color = '#FF0000'
        # copy
        path = copy.copy(given_path.path)
        path.setAttribute('stroke', color)
        path.setAttribute('stroke-width', '3')
        path.setAttribute('fill', 'none')

        txt = svg0 + path.toxml() + '\n'
        # draw the point
        dp = 0.1
        path2 = copy.copy(given_path.path)
        path2.setAttribute('d', 
        'M {} {} v {} h {} v -{} z'.format(
            *(point - dp), dp, dp, dp))
        path2.setAttribute('stroke-width', '3')
        path2.setAttribute('stroke-linejoin', "round")
        path2.setAttribute(
            'transform',
            "matrix(1,0,0,1,0,0)")

        txt = txt + path2.toxml() + '\n</svg>'
        # make sure the original path does not change
        for k, v in attrs.items():
            given_path.path.setAttribute(k, v)
        return txt

    def group(self, path, mode='style'):
        """
        returns a list of paths sharing the same style
        """
        pass