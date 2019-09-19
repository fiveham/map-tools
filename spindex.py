"""Spatially index points, lines, and polygons with a scalable rectangular mesh.

The name is a crude portmanteau of 'spatial index'.

This script lets you map a point, line, or polygon onto the cell or cells that
if intersects of a lat-long-aligned grid covering the earth, which, at each
mesh scale, subdivides the cells of the scale lower by 1 into 4 quarters by
cutting the east-west width and the north-south height in half."""

_SCALE = 16

def set_scale(scale):
    if not isinstance(scale, int):
        raise TypeError('scale must be an int')
    
    if scale > 0:
        global _SCALE
        _SCALE = scale
    else:
        raise ValueError('scale must be > 0')

def get_cell(point, scale=None):
    scale = scale or _SCALE
    x_index, y_index = (int(latlng//widhei)
                        for latlng, widhei
                        in zip(point, _Cell.dims(scale)))
    return _Cell.get(x_index, y_index, scale)

class _BBox:
    
    def __init__(self, x, X=None, y=None, Y=None):
        if X is None:
            cell = x
            self.x, self.y = sw = _Cell.point(cell, 0)
            self.X, self.Y = ne = _Cell.point(cell, 1)
            self._dim = 2
        else:
            self.x, self.X, self.y, self.Y = x, X, y, Y
            self._dim = None
    
    _DIM = {(0,0):0, (0,1):1, (1,0):1, (1,1):2}
    
    @property
    def dim(self):
        if self._dim is None:
            dx = self.X - self.x
            dx = -1 if dx < 0 else 1 if dx > 0 else 0
            
            dy = self.Y - self.y
            dy = -1 if dy < 0 else 1 if dy > 0 else 0
            
            try:
                self._dim = _BBox._DIM[dx,dy]
            except KeyError:
                self._dim = -1
        return self._dim
    
    def __and__(self, that):
        x = max(self.x, that.x)
        X = min(self.X, that.X)
        y = max(self.y, that.y)
        Y = min(self.Y, that.Y)
        return _BBox(x,X,y,Y)
    
    def __add__(self, bbox):
        return _BBox(min(self.x, bbox.x),
                    max(self.X, bbox.X),
                    min(self.y, bbox.y),
                    max(self.Y, bbox.Y))
    
    def __bool__(self):
        return self.x != self.X or self.y != self.Y
    
    def __iter__(self):
        return iter([self.x, self.X, self.y, self.Y])
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        x,X,y,Y = self
        return f'_BBox({x}, {X}, {y}, {Y})'

def get_cells_2d(points, scale=None, boundary_cells=set()):
    """Return a set of the cells that intersect the polygon `points`.

       :param points: A list of points in the plane. The first point must be
       repeated as the last point

       :param scale: The surface of the earth (as a Mercator projection) is
       divided into `4**scale` rectangular cells

       :param boundary_cells: If specified, then these cells are used instead
       of calling `get_cells_1d` to compute the cells of the polygon's boundary.
       When spatially indexing polygons with many interior holes, use this to
       avoid recomputing the hole's boundary cells.
       """
    from point_in_polygon import _Ring

    scale = scale or _SCALE
    
    ring = _Ring(points)
    cells = boundary_cells.copy() or get_cells_1d(points, scale)
    
    #Build a solid rectangle of all the cells of the bounding box of `points`
    #not including the cells already assigned for return
    min_x, max_x, min_y, max_y = sum(
            (_BBox(x,x,y,y) for x,y in (cell.indices for cell in cells)),
            _BBox(float('inf'), float('-inf'),
                 float('inf'), float('-inf')))
    unassigned = {(x,y)
                  for x in range(min_x, max_x+1)
                  for y in range(min_y, max_y+1)
                  } - {tuple(cell.indices)
                       for cell in cells}
    
    #while there are still unassigned cells, grab one and grow a connected
    #component of cells around it, only growing it within the set of
    #unassigned cells, then remove all those cells in that component from the
    #unassigned set, then if that component is inside the ring made by
    #`points`, add those cells for return
    while unassigned:
        cell = next(iter(unassigned))
        news = {cell}
        edge = set()
        core = set()
        while news:
            edge, news = news, set()
            for x,y in edge:
                news.update([(x+1,y), (x-1,y), (x,y+1), (x,y-1)])
            core |= edge
            news -= core
            news &= unassigned
        unassigned -= core
        if _Cell.get(cell[0], cell[1], scale).center in ring:
            cells.update(_Cell.get(x,y,scale) for x,y in core)
    return cells

def _cross_sign(a, b, c):
    """Calculate the cross product of the vector from `a` to `b` times the
       vector from `a` to `c`. Return the sign of the z component."""
    x = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
    return -1 if x < 0 else 1 if x > 0 else 0

def _passthru(cell, point_a, point_b):
    signs = [_cross_sign(point_a, point_b, point_c)
             for point_c in cell.corners]
    if 1 in signs and -1 in signs:
        return True
    z = signs.count(0)
    if z > 2:
        raise ValueError("Impossible: Can't have more than 2 cell corners "
                         "perfectly sitting on a line.")
    elif z == 2:
        nw, ne, se, sw = signs
        return sw == 0 and (nw == 0 or se == 0)
    return False

def _grow_cells_line_segment(side, scale):
    """Find cells intersecting `side` (at `scale`) by linking neighbors.
       
       Begin growth from the cells containing the endpoints of `side`. Consider
       the 8 cells around each of those cells, and use cross products of
       a vector defined by `side` and a vector from one end of `side` to a
       corner of a cell under consideration.

       A cell under consideration intersects the line if the signs of the
       four cross products for its corners include both positive and negative.
       If the list of cross-product signs for the cell contains two zeroes,
       then if one of them is the southwest corner and the other is either the
       northwest corner or the southeast corner, then the line intersects the
       cell."""
    (xa,ya),(xb,yb) = a,b = side
    cell_a, cell_b = (get_cell(point, scale) for point in side)
    
    box = _BBox(*(sorted([xa, xb]) + sorted([ya, yb])))
    
    news = {cell_a, cell_b}
    edge, core = set(), set()
    while news:
        edge, news = news, set()
        for cell in edge:
            news.update(cell.neighbors)
        core |= edge
        news -= core
        news = {cell
                for cell in news
                if (_passthru(cell, a, b) and
                    box.dim == (_BBox(cell) & box).dim)}
    
    #Test the original seed cells, too
    for cell in [cell_a, cell_b]:
        if not (_passthru(cell, a, b) and
                box.dim == (_BBox(cell) & box).dim):
            core.remove(cell)
    
    return _Cell._cache_back(core)

##def _get_cells_line_segment(side, scale=_SCALE):
##    """Return a set of the cells that intersect `side` in the plane.
##
##       :param side: A collection of two points in the plane
##       """
##    cells = set()
##    cell_width, cell_height  = _Cell.dims(scale=scale)
##
##    #`side` is made of point `a` and point `b`, now explode those
##    #into a zillion particles
##    ((xa, ya), cellA, (Xa, Ya)), ((xb, yb), cellB, (Xb, Yb)) = (
##            [p, c, c.indices]
##            for p,c in ([point, get_cell(point, scale=scale)]
##                        for point in sorted(side)))
##    
##    m = float('inf') if xb == xa else (yb - ya) / (xb - xa)
##    for X in range(Xa, Xb+1): #for each column of cells the lineseg intersects
##        min_x = max(xa,  X    * cell_width)
##        max_x = min(xb, (X+1) * cell_width)
##        try:
##            min_y, max_y = sorted({m*(x_tr-xa)+ya for x_tr in {min_x, max_x}})
##        except ValueError: #not enough values to unpack (2 0s or 2 infs)
##            min_y, max_y = sorted([ya, yb])
##        else:
##            min_y = max(min_y, min(ya,yb))
##            max_y = min(max_y, max(ya,yb))
##        
##        min_Y = int(min_y // cell_height)
##        max_Y = int(max_y // cell_height)
##        
##        #if the maximum y height in the column is on a horizontal mesh line,
##        #then the max Y cell index will be too large by 1
##        if max_Y != min_Y and max_Y * cell_height == max_y:
##            max_Y -= 1
##        
##        cells.update(_Cell.get(X, Y, scale) for Y in range(min_Y, max_Y + 1))
##        #cells.update(_Cell.get(X, list(range(min_Y, max_Y + 1)), scale)
##    return cells

def get_cells_1d(points, scale=None):
    """Return a set of the cells that intersect the 1-D feature `points`.
       
       :param points: A sequence of at least two points
       """
    scale = scale or _SCALE
    cells = set()
    for side in ([points[i-1], points[i]] for i in range(1, len(points))):
        cells |= _grow_cells_line_segment(side, scale)
    return cells

get_cells_0d = get_cell

class _Cell:
    """A rectangular region on a Mercator projection of the surface of Earth.

       A cell has three parameters: x, y, and scale.  x and y do what they
       obviously should, and scale determines how small the cell is. The
       number of cells the surface of the earth divides into grows
       exponentially with increasing `scale`.

       Each cell, viewed on a Mercator projection, is twice as wide east-to-west
       as it is north-to-south, which is because `scale` divides the equator
       and the prime meridian by equal proportions so that at scale 0, one cell
       covers the whole planet (except the north pole, technically), at scale
       1, four cells cover the planet (again, except the north pole), and
       generally with an increase of scale by 1, there are four times as many
       cells in total.
       
       The prefered way to obtain instances of this class is to call `get`,
       which caches results. Since a huge number of cells may be needed for
       a given task, interning instances this way may save memory on
       short-running tasks but may be a liability on long-running tasks.
       """
    _INTERN_CACHE = {}
    
    @staticmethod
    def get(x_index, y_index, scale, cache=_INTERN_CACHE):
        key = (x_index, y_index, scale)
        try:
            cached = cache[key]
        except KeyError:
            cached = _Cell(x_index, y_index, scale)
            cache[key] = cached
        return cached

    @staticmethod
    def _cache_back(cells):
        """Cache uncached cells; replace others with canonical cached version.

           Return a new set equal to `cells` in which every cell is replaced
           by its corresponding instance from the cache or left alone if it
           had no corresponding cache instance. Uncached cells, when
           encountered, are added to the cache.

           :param cells: a set of _Cell instances"""
        result = set()
        for cell in cells:
            key = cell.key
            try:
                c = _Cell._INTERN_CACHE[key]
            except KeyError:
                _Cell._INTERN_CACHE[key] = c = cell
            result.add(c)
        return result
    
##    @staticmethod
##    def gets(x_indices, y_indices, scale):
##        """Just like `get` but it takes lists of indices instead of individual
##           indices."""
##        cells = {_Cell._INTERN_CACHE.get((x,y,scale), _Cell(x,y,scale))
##                 for x,y in zip(x_indices, y_indices)}
##        _Cell._INTERN_CACHE.update(cell.key:cell for cell in cells)
##        return cells
    
    @staticmethod
    def width(scale):
        return 360 / 2**scale
    
    @staticmethod
    def height(scale):
        return 180 / 2**scale
    
    @staticmethod
    def dims(scale):
        yield _Cell.width( scale)
        yield _Cell.height(scale)

    @staticmethod
    def point(instance, offset):
        return tuple((xy + offset) * widhei
                     for xy, widhei in zip(instance.indices,
                                           _Cell.dims(instance.scale)))
    
    @property
    def center(self):
        return _Cell.point(self, 0.5)
    
    @property
    def key(self):
        return (self.x, self.y, self.scale)
    
    @property
    def indices(self):
        yield self.x
        yield self.y
    
    @property
    def neighbors(self):
        x,y = self.indices
        signs = [-1, 0, 1]
        for dx in signs:
            for dy in signs:
                X, Y = x+dx, y+dy
                if dx or dy:
                    yield _Cell(X, Y, self.scale)
    
    @property
    def corners(self):
        x,y = _Cell.point(self, 0)
        X,Y = _Cell.point(self, 1)
        yield (x,Y)
        yield (X,Y)
        yield (X,y)
        yield (x,y)
    
    def __init__(self, x_index, y_index, scale):
        self._hash = None
        self.x = x_index
        self.y = y_index
        self.scale = scale
    
    def __hash__(self):
        if self._hash is None:
            self._hash = hash((self.x, self.y, self.scale))
        return self._hash
    
    def __eq__(self, that):
        return (self.x == that.x and
                self.y == that.y and
                self.scale == that.scale)
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return f'_Cell({self.x}, {self.y}, {self.scale})'
    
    def __contains__(self, point):
        (x,y),(X,Y) = (_Cell.point(self, off) for off in (0.0,1.0))
        a,b = point
        return X > a and Y > b and a >= x and b >= y
    
    def _to_kml(self, soup):
        pm = soup.new_tag('Placemark')
        pm.append(soup.new_tag('name'))
        pm.find('name').string = str(self)
        pm.append(soup.new_tag('Polygon'))
        pm.Polygon.append(soup.new_tag('outerBoundaryIs'))
        pm.outerBoundaryIs.append(soup.new_tag('LinearRing'))
        pm.LinearRing.append(soup.new_tag('coordinates'))
        (x,y),(X,Y) = (_Cell.point(self, off) for off in (0.0,1.0))
        pm.coordinates.string = f'{x},{y} {X},{y} {X},{Y} {x},{Y} {x},{y}'
        return pm
