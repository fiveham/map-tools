"""A script to do point-in-polygon testing for GIS."""

from enum import Enum

_MAX = float('inf')
_MIN = -_MAX

class BoundaryException(Exception):
    """An exception raised when a point being tested sits on the
       boundary of a polygon. That fact defines the point's inside/outside
       status. An exception thrown back up the call stack provides a shortcut
       and a quicker answer."""
    pass

class BBox:
    """A class to model the bounding box of a collection of points in 2D
       space."""

    ADD_IDENT = None

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
    
    def __str__(self):
        return 'BBox(%s, %s, %s, %s)' % tuple(self)
    
    def __repr__(self):
        return str(self)
    
    def __iter__(self):
        return iter([self.x, self.X, self.y, self.Y])
BBox.ADD_IDENT = BBox(_MAX, _MIN, _MAX, _MIN, illegal=True)

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
    
    def contains(self, point, edge_okay=False):
        try:
            return point in self
        except BoundaryException:
            return edge_okay

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
    I   = 0 # First  quadrant, for x>0, y>0
    II  = 1 # Second quadrant, for x>0, y<0
    III = 2 # Third  quadrant, for x<0, y<0
    IV  = 3 # Fourth quadrant, for x<0, y>0

_ERR_RAD_DEG = 8.98315e-07 #in degrees. Along equator, about 10 centimeters
_ERR_RAD_DEG_SQ = _ERR_RAD_DEG ** 2 #precomputed for reuse

#Return the quadrant v is in with respect to point as the origin.
def _orient(point, v):
    vx, vy = v[0], v[1]
    px, py = point[0], point[1]
    
    dx = vx - px
    dy = vy - py
    
    if _ERR_RAD_DEG_SQ > dx ** 2 + dy ** 2:
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

    :param point: a tuple of numbers with at least two elements or any other
    object subscriptable with 0 and 1 (for example, a dict
    {1: -43, 50: 'a', 0: 91})
    
    :param vertex_ring: The vertices of the polygon. The first vertex must be
    repeated as the final element.
    
    :param edge_okay: Return this value if `point` is on the boundary of the
    `vertex_ring`. False by default."""
    
    try:
        return point in _Ring(vertex_ring)
    except BoundaryException:
        return edge_okay

def _SORT_BY_AREA_VERTS(ring):
    try:
        return 1 / ring.area / len(ring)
    except ZeroDivisionError:
        return _MAX

class Polygon:
    """A polygon for GIS, with >=1 outer bounds and >=0 inner bounds."""
    
    def __init__(self, outers, inners=None, info=None, edge_okay=False):
        """Make a Polygon
           
           :param outers: a list of one or more outer boundaries

           :param inners: if specified, a list of zero or more inner boundaries

           :param info: Any data or metadata object the user wants.
           
           :param edge_okay: `point in self` will evaluate to this if `point`
            sits on a boundary. False by default."""
        
        if not len(outers):
            raise ValueError('need at least one outer boundary')
        inners = inners or []
        
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
                containers = [i
                              for i in range(len(self.outers))
                              if self.outers[i].contains(point,
                                                         edge_okay=True)]
                container = min(containers,
                                key=(lambda x : self.outers[x].area))
                
                self._out_to_in[container].append(assign_me)
            for v in self._out_to_in.values():
                v.sort(key=_SORT_BY_AREA_VERTS)
        self._bbox = None
        self.__hash = None
    
    def __contains__(self, point):
        """Determine whether `point` is in this Polygon.

           Return `self.edge_okay` if `point` is exactly on a boundary."""
        
        try:
            #which outer boundary contains `point`?
            outerbound_containing_point = next(iter(
                    i
                    for i in range(len(self.outers))
                    if point in self.outers[i]))

            #and which inner boundaries are inside that outer-bound?
            inners = self._out_to_in[outerbound_containing_point]

            #if `point` is in any inner boundary, then it's not in the Polygon
            return all(point not in inner
                       for inner in inners)
        except StopIteration: #none of the outers contain `point`
            return False
        except BoundaryException: # `point` sits on an outer or inner bound
            return self.edge_okay
    
    def __hash__(self):
        if self.__hash is None:
            self.__hash = hash((tuple(tuple(tuple(point)
                                            for point in outer)
                                      for outer in self.outers), 
                                tuple(tuple(tuple(point)
                                            for point in inner)
                                      for inner in self.inners)))
        return self.__hash
    
    def __eq__(self, other):
        return self is other
        #return self.outers == other.outers and self.inners == other.inners
    
    def to_kml(self, soup=None):
        import kml
        if soup is None:
            result = '<Placemark>%s</Placemark>'
            if len(self.outers) > 1:
                result %= '<MultiGeometry>%s</MultiGeometry>'
            for i, outer in enumerate(self.outers):
                inners = self._out_to_in[i]
                polygon = '<Polygon><outerBoundaryIs><LinearRing><coordinates>'
                polygon += kml.coords_to_text(outer)
                polygon += '</coordinates></LinearRing></outerBoundaryIs>'
                for inner in inners:
                    polygon += '<innerBoundaryIs><LinearRing><coordinates>'
                    polygon += kml.coords_to_text(inner)
                    polygon += '</coordinates></LinearRing></innerBoundaryIs>'
                polygon += '</Polygon>%s'
                
                result %= polygon
            result %= ''
            return result
        else:
            result = soup.new_tag('Placemark')
            focus = result
            if len(self.outers) > 1:
                focus = kml.add(focus, 'MultiGeometry', soup=soup)
            for i, outer in enumerate(self.outers):
                inners = self._out_to_in[i]
                polygon = kml.add(focus, 'Polygon', soup=soup)
                kml.add(polygon,
                        ['outerBoundaryIs',
                         'LinearRing',
                         'coordinates'],
                        soup=soup).string = kml.coords_to_text(outer)
                for inner in inners:
                    kml.add(polygon,
                            ['innerBoundaryIs',
                             'LinearRing',
                             'coordinates'],
                            soup=soup).string = kml.coords_to_text(inner)
            return result
    
    def spatial_index(self, scale):
        import spindex
        
        cells = set()
        for outer in self.outers:
            cells.update(spindex.get_cells_2d(outer, scale=scale))
        rims = [spindex.get_cells_1d(inner, scale=scale)
                for inner in self.inners]
        guts = [spindex.get_cells_2d(inner,
                                     scale=scale,
                                     boundary_cells=rims[i])
                for i, inner in enumerate(self.inners)]
        for gut in guts:
            cells -= gut
        for rim in rims:
            cells.update(rim)
        return cells
    
    @property
    def _rings(self):
        """Iterate over inner and outer boundaries."""
        for o in self.outers:
            yield o
        for i in self.inners:
            yield i
    
    @property
    def stokesable(self):
        """Yield copies of all boundaries, with inner bounds reversed."""
        for o in self.outers:
            yield list(o)
        for i in self.inners:
            yield list(reversed(i))
    
    @property
    def bbox(self):
        """The least and greatest x and y coordinates of the vertices."""
        if not self._bbox:
            self._bbox = sum((ring.bbox for ring in self._rings),
                             BBox(_MAX, _MIN, _MAX, _MIN, illegal=True))
        return self._bbox
    
    @property
    def vertices(self):
        """Iterates over all the vertices of this Polygon.

           Since the first point of a boundary is duplicated as the
           last point, all such points will occur twice."""
        for ring in self._rings:
            for vertex in ring:
                yield vertex
    
    @property
    def sides(self):
        """Iterate over the sides of the outer and inner boundaries."""
        for ring in self._rings:
            for i in range(1, len(ring)):
                yield ring[i-1:i+1]
    
    @staticmethod
    def from_shape(shape, info=None, edge_okay=False):
        """Convert a shapefile.Shape into a Polygon.

           Because inner and outer boundaries in the shapefile standard are
           defined as such only implicity via their curling orientation,
           distinguishing whether a given boundary is inner or outer requires
           detecting its curling orientation, which is achieved via
           `shapefile.signed_area`.

           :param shape: a shapefile.Shape object
           :param info: passed to __init__
           :param edge_okay: passed to __init__"""
        
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
    
    @staticmethod
    def from_boundaries(boundaries, info=None, edge_okay=False):
        from shapefile import signed_area
        outers, inners = [], []
        for boundary in boundaries:
            if signed_area(boundary) >= 0:
                outers.append(boundary)
            else:
                inners.append(boundary)
        return Polygon(outers, inners, info=info, edge_okay=edge_okay)
    
    @staticmethod
    def from_kml(placemark, info=None, edge_okay=False):
        """Convert a KML Placemark into a Polygon.

           :param placemark: a <Placemark> tag from a KML document
           :param info: passed to __init__
           :param edge_okay: passed to __init__"""
        
        import kml, itertools
        geo = placemark.MultiGeometry or placemark.Polygon
        if geo is None:
            print(placemark)
        outers = [kml.coords_from_tag(obi.coordinates)
                  for obi in geo('outerBoundaryIs')]
        
        #The KML spec indicates that there is only one LinearRing per
        #innerBoundaryIs, but KMLs generated by Google Earth from shapefiles
        #may put (and render) multiple LinearRings in a single innerBoundaryIs
        inners = [kml.coords_from_tag(coordinates_tag)
                  for coordinates_tag in itertools.chain.from_iterable(
                          ibi('coordinates')
                          for ibi in geo('innerBoundaryIs'))]
        
        return Polygon(outers, inners, info=info, edge_okay=edge_okay)
