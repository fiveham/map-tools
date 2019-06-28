"""A script to do point-in-polygon testing for GIS."""

class BoundaryException(Exception):
    """An exception to be raised if and when a point being tested is found to
       sit on the boundary of the polygon. Because that sort of information can
       define the point's inside/outside status, an exception thrown back up
       the call stack provides a shortcut and a quicker answer."""
    pass

class BBox:
    """A class to model the bounding box of a collection of points in 2D
       space."""

    def __init__(self, x, X, y, Y, illegal=False):
        """
           `x`: low x value
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
        #treat equality as inside to ensure that if the point is also on
        #the boundary of the polygon itself the user-specified edge_okay
        #value ultimately gets returned
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

class Ring(list):
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
        super(Ring, self).__init__(points)
        
        e = BBox(10**9, -10**9, 10**9, -10**9, illegal=True)
        for point in self:
            x,y = point
            e.x = min(x, e.x)
            e.X = max(x, e.X)
            e.y = min(y, e.y)
            e.Y = max(y, e.Y)
        self.bbox = e

ERR_RAD_DEG = 8.98315e-06 #in degrees. Along equator, about 1 meter

#throw exception if point and v are too close
#Return the orientation from point to v
def _orient(point, v):
    vx = v[0]
    vy = v[1]
    px = point[0]
    py = point[1]
    
    dx = vx - px
    dy = vy - py
    
    if dx * dy == 0: #along an axis
        if ERR_RAD_DEG ** 2 > dx ** 2 + dy ** 2:
            raise BoundaryException()
        if dx == 0:
            return 0 if dy > 0 else 2
        else: #dy == 0
            return 1 if dx > 0 else 3
    else:
        if dx < 0:
            return 2 if dy < 0 else 3
        else: #dx > 0
            return 1 if dy < 0 else 0

def _cross_product(a,b):
    return a[0]*b[1] - a[1]*b[0]

#throw exception if side between v1 and v2
#appears to pass too close to point
def _turning_sign(point, v1, v2):
    ray2 = (v2[0] - point[0], v2[1] - point[1])
    ray1 = (v1[0] - point[0], v1[1] - point[1])
    x = _cross_product(ray2, ray1)
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else: #x == 0
        raise BoundaryException()

#TODO ensure that 180-degree orientation changes have the correct sign
#depending on which way the boundary curls around the point
def _turning(point, v1, v2):
    o1 = _orient(point, v1)
    o2 = _orient(point, v2)
    
    #call early in case it raises a BoundaryException
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

def _point_in_ring(point, ring, ignore_bbox=False):
    return ((ignore_bbox
             or
             point in ring.bbox)
            and
            -4 == _winding(point, ring))

#Return True if point inside polygon, False if outside.
#Raise exception if point too close to boundary to be sure.
def _point_in_polygon(point, polygon):
    if not any(_point_in_ring(point, outer) for outer in polygon.outers):
        return False
    if any(_point_in_ring(point, inner) for inner in polygon.inners):
        return False
    return True

def point_in_polygon(point, polygon, edge_okay=False):
    """Return `True` if `point` is in `polygon`, `False` otherwise.

    ``point``: a tuple of numbers with at least two elements or any other
    object subscriptable with 0 and 1
    (for example, a dict {1: -43, 50: 'a', 0: 91})
    ``polygon``: a `Polygon` as defined in this script.
    ``edge_okay``: `True` if a point on the boundary of `polygon` should be
    considered to be inside the polygon, `False` otherwise."""
    try:
        return _point_in_polygon(point, polygon)
    except BoundaryException:
        return edge_okay

#Originally this class was intended to be used with polygons from KML files,
#and in the KML standard polygons wind counterclockwise.
#So all the point-in-polygon functions in this script implicitly rely on
#counterclockwise winding for outer boundaries.
class Polygon:
    """A class to represent a polygon for GIS applications, with one or more
       outer boundaries and zero or more inner boundaries."""
    
    def __init__(self, outers, inners=None, clockwise=False, info=None,
                 edge_okay=False):
        """
        ``outers``: a list of one or more outer boundaries
        ``inners``: if specified, a list of zero or more inner boundaries
        ``clockwise``: `False` or falsey if outer boundaries wind
        counter-clockwise as in the KML standard, `True` or truthy if outer
        boundaries wind clockwise, as in the Shapefile standard. Default is
        `False`.
        ``info``: Any data or metadata object the user wants."""

        assert len(outers) > 0, 'need at least one outer boundary'
        inners = inners or []

        #In case the caller sends outers=outer instead of outers=[outer]
        #where outer is the single outer ring for a polygon with only one
        #outer boundary
        for variety in [outers, inners]:
            assert isinstance(variety, list), ('`outers` and `inners` must be '
                                               'of type `list`')
            if variety: #has contents
                for boundary in variety:
                    assert isinstance(boundary, list), ('each boundary must be '
                                                        'of type `list`')
                    assert len(boundary) > 0, 'a boundary may not be empty'
                    for pt in boundary:
                        assert isinstance(pt, tuple), ('the vertices of a '
                                                       'boundary must be of '
                                                       'type `tuple`')
                        assert len(pt) >= 2, ('each vertex on a boundary must '
                                              'have at least two coordinates')
        
        orderer = reversed if clockwise else (lambda x : x)
        
        self.outers = [Ring(list(orderer(outer))) for outer in outers]        
        self.inners = [Ring(list(orderer(inner))) for inner in inners]

        self.info = info
        self.edge_okay = edge_okay
        
    def __contains__(self, point):
        return point_in_polygon(point, self, edge_okay=self.edge_okay)
    
    @property
    def rings(self):
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
        return sum((ring.bbox for ring in self.rings), BBox(0,0,0,0))
    
    @property
    def vertices(self):
        """Return a generator that iterates over all the vertices of this
           Polygon. Since the first point of a boundary is duplicated as the
           last point, all such points will occur twice."""
        for ring in self.rings:
            for vertex in ring:
                yield vertex
    
    @property
    def sides(self):
        """Return a generator that iterates over all the sides of all the
           boundaries (both inner and outer) of this Polygon."""
        for ring in self.rings:
            for i in range(1, len(ring)):
                side = (ring[i-1], ring[i])
                yield side

def from_shape(shape, info=None, edge_okay=False):
    """Convert a shapefile.py shape into a Polygon"""
    import shapefile
    bounds = list(shape.parts) + [len(shape.points)]
    lines = []
    for i in range(1,len(bounds)):
        start = bounds[i-1]
        stop  = bounds[i]
        lines.append(list(shape.points[start:stop]))
    
    #separate lines into outer/inner boundaries (using winding/signed area)
    outers = []
    inners = []
    for line in lines:
        #value >= 0 indicates a counter-clockwise oriented ring
        #Negative value -> outer boundary
        a = shapefile.signed_area(line)
        if a >= 0:
            inners.append(line)
        else:
            outers.append(line)
    
    return Polygon(outers, inners, clockwise=True, info=info,
                   edge_okay=edge_okay)
