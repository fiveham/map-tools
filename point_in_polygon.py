"""A script to do point-in-polygon testing for GIS."""

from enum import Enum

class BoundaryException(Exception):
    """An exception raised when a point being tested sits on the
       boundary of a polygon. That fact defines the point's inside/outside
       status. An exception thrown back up the call stack provides a shortcut
       and a quicker answer."""
    pass

class BBox:
    """A class to model the bounding box of a collection of points in 2D
       space."""

    def __init__(self, x, X, y, Y, illegal=False):
        """`x`: low x value
           `X`: high x value
           `y`: low y value
           `Y`: high y value
           `illegal`: if True, skip tests to check that low x and y values are
                      less or equal to their high counterparts. Defaults to
                      False."""
        if not illegal:
            assert x <= X, 'x > X: %s > %s' % (x, X)
            assert y <= Y, 'y > Y: %s > %s' % (y, Y)
        self.x = x
        self.y = y
        self.X = X
        self.Y = Y
    
    def __contains__(self, item):
        x,y = item
        #treat equality as inside so that if the point is on the polygon
        #boundary then the caller's edge_okay value gets returned
        return self.x <= x and x <= self.X and self.y <= y and y <= self.Y

    def __add__(self, bbox):
        if not isinstance(bbox, BBox):
            raise TypeError
        x = min(self.x, bbox.x)
        X = max(self.X, bbox.X)
        y = min(self.y, bbox.y)
        Y = max(self.Y, bbox.Y)
        return BBox(x,X,y,Y)

    def __bool__(self):
        return True

class _Ring(list):
    """A class to represent an inner or outer boundary of a Polygon and to
       maintain a reference to that boundary's bounding box."""
    
    def __init__(self, points):
        assert all(points[0][i] == points[-1][i] for i in range(2)), (
                ('first and last point on a boundary must have the same first '
                 'two dimensions: %s,%s != %s,%s') % (points[0][0],
                                                      points[0][1],
                                                      points[-1][0],
                                                      points[-1][1]))
        p0x, p0y = points[0][:2]
        p1x, p1y = points[-1][:2]
        if p0x != p1x or p0y != p1y:
            raise ValueError(
                ('first and last point on a boundary must have the same first '
                 'two dimensions: %s,%s != %s,%s') % (p0x, p0y, p1x, p1y))
        import shapefile
        self.area = shapefile.signed_area(points)
        super(_Ring, self).__init__(points
                                    if self.area >= 0
                                    else reversed(points))
        self.area = abs(self.area)
        
        e = BBox(10**9, -10**9, 10**9, -10**9, illegal=True)
        for point in self:
            x,y = point
            e.x = min(x, e.x)
            e.X = max(x, e.X)
            e.y = min(y, e.y)
            e.Y = max(y, e.Y)
        self.bbox = e
    
    def __bool__(self):
        return True
    
    def __contains__(self, point):
        return point in self.bbox and -4 == _winding(point, self)

def _turning_sign(point, v1, v2):
    #cross-product
    x = ((v2[0] - point[0]) * (v1[1] - point[1]) -
         (v2[1] - point[1]) * (v1[0] - point[0]))
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else: #x == 0
        raise BoundaryException()

class Quad(Enum):
    I   = 0 # First quadrant, for x,y > 0,0
    II  = 1 # Second quadrant, for x>0, y<0
    III = 2 # Third quadrant, for x,y < 0,0
    IV  = 3 # Fourth quadrant, for x<0, y>0

ERR_RAD_DEG = 8.98315e-07 #in degrees. Along equator, about 10 centimeters
ERR_RAG_DEG_SQ = ERR_RAD_DEG ** 2 #precomputed for reuse

#Return the quadrant v is in with respect to point as the origin.
def _orient(point, v):
    vx, vy = v[0], v[1]
    px, py = point[0], point[1]
    
    dx = vx - px
    dy = vy - py
    
    if ERR_RAD_DEG_SQ > dx ** 2 + dy ** 2:
        raise BoundaryException()
    
    if dx * dy == 0: #along an axis
        if dx == 0:
            return Quad.I  if dy > 0 else Quad.III
        else: #dy == 0
            return Quad.II if dx > 0 else Quad.IV
    else:
        if dx < 0:
            return Quad.III if dy < 0 else Quad.IV
        else: #dx > 0
            return Quad.II  if dy < 0 else Quad.I

def _turning(point, v1, v2):
    o1 = _orient(point, v1).value
    o2 = _orient(point, v2).value
    
    #call early in case it raises BoundaryException
    sign = _turning_sign(point, v1, v2) 
    
    angle = o2 - o1
    if angle < -2:
        angle += 4
    elif angle > 2:
        angle -= 4
    elif abs(angle) == 2:
        angle = 2 * sign
    return angle

def _winding(point, ring):
    return sum(_turning(point, ring[i-1], ring[i])
               for i in range(1, len(ring)))

def point_in_polygon(point, vertex_ring, edge_okay=False):
    """Return True if the `point` is inside the `vertex_ring`, False otherwise.

    ``point``: a tuple of numbers with at least two elements or any other
               object subscriptable with 0 and 1 (for example, a dict
               {1: -43, 50: 'a', 0: 91})
    ``vertex_ring``: The vertices of the polygon. The first vertex must be
                     repeated as the final element.
    ``edge_okay``: Return this value if `point` is on the boundary of the
                   `vertex_ring`. False by default."""

    try:
        return point in _Ring(vertex_ring)
    except BoundaryException:
        return edge_okay

_SORT_BY_AREA_VERTS = lambda x : 1 / x.area / len(x)

class Polygon:
    """A class to represent a polygon for GIS applications, with one or more
       outer boundaries and zero or more inner boundaries."""
    
    def __init__(self, outers, inners=None, info=None, edge_okay=False):
        """``outers``: a list of one or more outer boundaries
           ``inners``: if specified, a list of zero or more inner boundaries
           ``info``: Any data or metadata object the user wants.
           ``edge_okay``: `point in self` will evaluate to this if `point` sits
                          on a boundary. False by default."""
        
        assert len(outers) > 0, 'need at least one outer boundary'
        inners = inners or []
        
        #In case the caller sends outers=outer instead of outers=[outer]
        #when the polygon has only one outer boundary
        for variety in [outers, inners]:
            assert isinstance(variety, list), ('`outers` and `inners` must be '
                                               'of type `list`')
            for boundary in variety:
                assert isinstance(boundary, list), ('each boundary must be of '
                                                    'type `list`')
                assert len(boundary) > 0, 'a boundary may not be empty'
                for pt in boundary:
                    assert isinstance(pt, tuple), ('the vertices of a boundary '
                                                   'must be of type `tuple`')
                    assert len(pt) >= 2, ('each vertex on a boundary must have '
                                          'at least two coordinates')
        
        self.outers = [_Ring(outer) for outer in outers]        
        self.inners = [_Ring(inner) for inner in inners]
        
        self.info = info
        self.edge_okay = edge_okay
        
        self.outers.sort(key=_SORT_BY_AREA_VERTS)
        self._out_to_in = {i:[] for i in range(len(self.outers))}
        if self.inners:
            unassigned_inners = list(self.inners)
            while unassigned_inners:
                assign_me = unassigned_inners.pop()
                point = assign_me[0]
                container = next(iter(i
                                      for i in range(len(self.outers))
                                      if point in self.outers[i]))
                self._out_to_in[container].append(assign_me)
            for v in self._out_to_in.values():
                v.sort(key=_SORT_BY_AREA_VERTS)
        self._bbox = None
    
    def __contains__(self, point):
        try:
            index_outer_around_point = next(iter(
                    i
                    for i in range(len(self.outers))
                    if point in self.outers[i]))
            inners = self._out_to_in[index_outer_around_point]
            return all(point not in inner
                       for inner in inners)
        except StopIteration:
            return False
        except BoundaryException:
            return self.edge_okay
    
    @property
    def _rings(self):
        """Return a generator that iterates over all the boundaries of this
           Polygon, both outer and inner."""
        for o in self.outers:
            yield o
        for i in self.inners:
            yield i
    
    @property
    def bbox(self):
        """Return the overall outer bounding box of this Polygon encapsulating
           the least and greatest x and y coordinates among all this Polygon's
           vertices."""
        if not self._bbox:
            self._bbox = sum((ring.bbox for ring in self._rings),
                             BBox(0,0,0,0))
        return self._bbox
    
    @property
    def vertices(self):
        """Return a generator that iterates over all the vertices of this
           Polygon. Since the first point of a boundary is duplicated as the
           last point, all such points will occur twice."""
        for ring in self._rings:
            for vertex in ring:
                yield vertex
    
    @property
    def sides(self):
        """Return a generator that iterates over all the sides of all the
           boundaries (both inner and outer) of this Polygon."""
        for ring in self._rings:
            for i in range(1, len(ring)):
                yield ring[i-1:i+1]

def from_shape(shape, info=None, edge_okay=False):
    """Convert a shapefile.Shape into a Polygon"""
    
    import shapefile
    bounds = list(shape.parts) + [len(shape.points)]
    outers = []
    inners = []
    for i in range(1, len(bounds)):
        start, stop = bounds[i-1], bounds[i]
        line = shape.points[start:stop]
        
        #value >= 0 indicates a counter-clockwise oriented ring
        #Negative value -> outer boundary
        a = shapefile.signed_area(line)
        if a >= 0:
            inners.append(line)
        else:
            outers.append(line)
    
    return Polygon(outers, inners, info=info, edge_okay=edge_okay)
