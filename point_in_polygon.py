#For when a point is too close to a boundary to tell for sure which
#side it's on due to floating point rounding errors.
#In practice, the size of iffiness around a boundary will be far larger than
#the region called into question due to propagation of floating-point errors.
class BoundaryException(Exception):
    pass

class BBox:
    def __init__(self, x, X, y, Y, illegal=False):
        if not illegal:
            assert x <= X
            assert y <= Y
        self.x = x
        self.y = y
        self.X = X
        self.Y = Y
    def __contains__(self, item):
        x,y = item
        return self.x <= x and x <= self.X and self.y <= y and y <= self.Y
    def __bool__(self):
        return True

class Ring(list):
    def __init__(self, points):
        assert points[0] == points[-1]
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
    sign = _turning_sign(point, v1, v2) #call early in case BoundaryException
    
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
    try:
        return _point_in_polygon(point, polygon)
    except BoundaryException:
        return edge_okay

#Originally this class was intended to be used with polygons from KML files,
#and in the KML standard polygons wind counterclockwise.
#So all the point-in-polygon functions in this script implicitly rely on
#counterclockwise winding.
class Polygon:
    def __init__(self, outers, inners=None, clockwise=False):

        assert len(outers) > 0
        inners = inners or []

        #In case the caller sends outers=outer instead of outers=[outer]
        #where outer is the single outer ring for a polygon with only one
        #outer boundary
        for variety in [outers, inners]:
            assert isinstance(variety, list)
            if variety: #has contents
                for boundary in variety:
                    assert isinstance(boundary, list)
                    assert len(boundary) > 0
                    for pt in boundary:
                        assert isinstance(pt, tuple)
                        assert len(pt) >= 2
        
        orderer = reversed if clockwise else (lambda x : x)
        
        self.outers = [Ring(list(orderer(outer))) for outer in outers]        
        self.inners = [Ring(list(orderer(inner))) for inner in inners]
        
        assert all(any(_point_in_ring(inner[0], outer)
                       for outer in self.outers)
                   for inner in self.inners)
    
    def __contains__(self, point):
        return point_in_polygon(point, self)
