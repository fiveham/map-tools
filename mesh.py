"""A script to translate a lat/long pair and a mesh cell scale into the
southwest corner point of the cell in which that point is located at that
scale."""

from enum import Enum

def eq_err(a,b):
    """Return True if floats a and b are adjacent values, False otherwise."""
    return a == b or abs(a-b) / 2 + min(a,b) in (a,b)

class PerimeterElement(Enum):
    TOP          = ( 0,  1)
    TOP_RIGHT    = ( 1,  1)
    RIGHT        = ( 1,  0)
    BOTTOM_RIGHT = ( 1, -1)
    BOTTOM       = ( 0, -1)
    BOTTOM_LEFT  = (-1, -1)
    LEFT         = (-1,  0)
    TOP_LEFT     = (-1,  1)
    
    def __neg__(self):
        x, y = self.value[0], self.value[1]
        return PerimeterElement((-x, -y))
    
    @staticmethod
    def corner(point, cell, cache={'':''}):
        if cell not in cache:
            del cache[next(iter(cache))]
            x,y = cell.corner
            s = cell.scale + 1
            cache[cell] = (x + 360 / 2**s, y + 180 / 2**2)
        return cache[cell]
        
        x, y = PerimeterElement._ensure_cache(cell, cache)
        a, b = point

        if a > x:
            if b > y:
                return PerimeterElement.TOP_RIGHT
            return PerimeterElement.BOTTOM_RIGHT
        elif b > y:
            return PerimeterElement.TOP_EFTT
        return PerimeterElement.BOTTOM_LEFT

def _intersected_perimeter_elements(x1, y1, x2, y2, cell, used_el):
    """Return a set of the pieces of the perimeter of `cell` that the line segment
between points (x1,y1) and (x2,y2) intersects."""
    
    #avoid dividing by zero by quickly detecting cases where the endpoints share
    #a column or a row in the mesh.
    c1 = Cell._get_cell_indices(x1, y1, cell.scale)
    c2 = Cell._get_cell_indices(x2, y2, cell.scale)
    if c1[0] == c2[0]: #shared column
        return {PerimeterElement.TOP, PerimeterElement.BOTTOM}
    elif c1[1] == c2[1]: #shared row
        return {PerimeterElement.LEFT, PerimeterElement.RIGHT}
    del c1, c2
    
    #Generate the line that contains the line segment (determine the constants
    #of the y=mx+b form of the line) and the boundary lines.
    xc, yc = cell.corner
    Xc, Yc = Cell.get_cell(cell.x + 1, cell.y + 1, cell.scale).corner
    
    m = (y2 - y1) / (x2 - x1)
    b = y1 - m * x1
    
    #Find intersection points between the line and each of the boundaries.
    yli_x, yli_X, xli_y, xli_Y = (m * xc + b,
                                  m * Xc + b,
                                  (yc - b) / m,
                                  (Yc - b) / m)
    
    ip_tp, ip_rt, ip_bm, ip_lt = ((xli_Y, Yc),
                                  (Xc,    yli_X),
                                  (xli_y, yc),
                                  (xc,    yli_x))
    
    raw_intxn_pts = [ip_tp, ip_rt, ip_bm, ip_lt]
    
    #Discard intersection points outside the cell.
    #It's more efficient to rebuild the set from the ground up.
    #Plus we'll need the raw intersection points again later.
    bound_intxn_pts = set()
    if xc <= ip_tp[0] and ip_tp[0] <= Xc:
        bound_intxn_pts.add(ip_tp)
    if xc <= ip_bm[0] and ip_bm[0] <= Xc:
        bound_intxn_pts.add(ip_bm)
    if yc <= ip_lt[1] and ip_lt[1] <= Yc:
        bound_intxn_pts.add(ip_lt)
    if yc <= ip_rt[1] and ip_rt[1] <= Yc:
        bound_intxn_pts.add(ip_rt)
    assert len(bound_intxn_pts) == 2
    
    #Translate these points into PerimeterElements and return them
    count = {point:0 for point in raw_intxn_pts}
    for point in raw_intxn_pts:
        count[point] = count[point] + 1
    corner_intxn_pts = {point for point in raw_intxn_pts if count[point] > 1}
    del count
    side_intxn_pts = bound_intxn_pts - corner_intxn_pts

    periels = set()
    if ip_tp in side_intxn_pts:
        periels.add(PerimeterElement.TOP)
    if ip_bm in side_intxn_pts:
        periels.add(PerimeterElement.BOTTOM)
    if ip_rt in side_intxn_pts:
        periels.add(PerimeterElement.RIGHT)
    if ip_lt in side_intxn_pts:
        periels.add(PerimeterElement.LEFT)

    return (periels | {PerimeterElement.corner(cip, cell)
                       for cip in corner_intxn_pts})

def _get_punch(periels, used_el):
    complement = -used_el
    return next(iter(p for p in periels if p != complement))

def _identify_exit(x1, y1, x2, y2, cell1):
    """Return the perimeter element of `cell1` through with the line segment from
(x1,y1) to (x2,y2) exits the cell."""
    assert (x1,y1) in cell1
    xc, yc = cell1.corner
    Xc, Yc = Cell.get_cell(cell1.x + 1, cell1.y + 1, cell1.scale).corner
    
    dyt = Yc - y1 # >= 0
    dyb = yc - y1 # <= 0
    dxr = Xc - x1 # >= 0
    dxl = xc - x1 # <= 0
    dxp = x2 - x1 # <=> 0
    dyp = y2 - y1 # <=> 0
    
    if dxp > 0:       # cell2 is to the east+ of cell1
        if dyp > 0:   # cell2 is to the northeast of cell1
            mp = dyp / dxp
            mc = dyt / dxr
            if eq_err(mp, mc): #TODO: check more carefully
                return PerimeterElement.TOP_RIGHT
            elif mp > mc:
                return PerimeterElement.TOP
            else:
                return PerimeterElement.RIGHT
        elif dyp < 0: # cell2 is to the southeast of cell1
            mp = dyp / dxp
            mc = dyb / dxr
            if eq_err(mp, mc): #TODO: check more carefully
                return PerimeterElement.BOTTOM_RIGHT
            elif mp > mc:
                return PerimeterElement.RIGHT
            else:
                return PerimeterElement.BOTTOM
        else:         # cell2 is exactly east of cell1
            return PerimeterElement.RIGHT
    elif dxp < 0:     # cell2 is to the west+ of cell1
        if dyp > 0:   # cell2 is to the northwest of cell1
            mp = dyp / dxp
            mc = dyt / dxl
            if eq_err(mp, mc): #TODO: check more carefully
                return PerimeterElement.TOP_LEFT
            elif mp > mc:
                return PerimeterElement.LEFT
            else:
                return PerimeterElement.TOP
        elif dyp < 0: # cell2 is to the southwest of cell1
            mp = dyp / dxp
            mc = dyb / dxl
            if eq_err(mp, mc): #TODO: check more carefully
                return PerimeterElement.BOTTOM_LEFT
            elif mp > mc:
                return PerimeterElement.BOTTOM
            else:
                return PerimeterElement.LEFT
        else:         # cell2 is exactly west of cell1
            return PerimeterElement.LEFT
    elif dyp > 0:     # cell2 is exactly north of cell1
        return PerimeterElement.TOP
    elif dyp < 0:     # cell2 is exactly south of cell1
        return PerimeterElement.BOTTOM
    else:
        raise ValueError("endpoints cannot be equal")

class Cell:
    """A class to represent a rectangular region on a Mercator projection of
Earth bound by lines of latitude and longitude at power-of-two fractions of
the size of the globe along those dimensions.

At scale = 0, the whole Earth except the north pole is covered by one cell.

At scale = 1, the equator, the prime meridian and the 180th meridian split the
Earth into four quadrants.

At each higher scale N, the cells of the scale N-1 are split into four cels 
each by slicing along new meridians and latitudes halfway between adjacent pairs
of those used for slicing at scale N-1."""

    @staticmethod
    def for_point(point, scale):
        """Return the mesh cell that contains `point`."""
        lng, lat = point
        x, y = Cell._get_cell_indices(lng, lat, scale)
        return Cell.get_cell(x, y, scale)

    NSEW = [[0,1],[1,0],[0,-1],[-1,0]]
    
    @staticmethod
    def _connected_component(seed, x, X, y, Y, illegal):
        core = set()
        edge = {seed}
        while edge:
            news = {c
                    for c in ((a+i, b+j)
                              for a,b in edge
                              for i,j in Cell.NSEW
                              if (x <= a+i and a+i <= X and
                                  y <= b+j and b+j <= Y))
                    if (c not in core and
                        c not in edge and
                        c not in illegal)}
            core.update(edge)
            edge = news
        return core
    
    @staticmethod
    def _get_cells_side(side, scale):
        cells = set() #the cells that the side intersects
        v1, v2 = side #endpoints of the side
        
        lng1, lat1 = v1
        x1,y1 = Cell._get_cell_indices(lng1, lat1, scale)
        cell1 = Cell.get_cell(x1, y1, scale)
        cells.add(cell1)
        
        lng2, lat2 = v2
        x2,y2 = Cell._get_cell_indices(lng2, lat2, scale)
        cell2 = Cell.get_cell(x2, y2, scale)
        cells.add(cell2)
        
        #adjacent cells don't need filling,
        #nor does the same cell twice
        if (abs(x1 - x2) == 1 and y1 == y2 or
            abs(y1 - y2) == 1 and x1 == x2 or
            cell1 == cell2):
            return cells
        
        #Start from one end, figure out which side or corner the line punches
        #through, get the cell on the opposite side of that perimeter element,
        #add it to the set, then run the same analysis to find where the line
        #punches through but this time ignore the side that corresponds to the
        #perimeter element through which you entered the current cell as you
        #followed the line.
        
        used_el = _identify_exit(lng1, lat1, lng2, lat2, cell1)
        
        cell_pointer = Cell.get_cell(cell1.x + used_el.value[0],
                                      cell1.y + used_el.value[1],
                                      scale)
        cells.add(cell_pointer)
        while cell_pointer != cell2:
            periels = _intersected_perimeter_elements(
                    lng1, lat1, lng2, lat2, cell_pointer, used_el)
            #punch = None
            #try:
            punch = _get_punch(periels, used_el)
            #except StopIteration:
            #    print(side, scale)
            #    print(used_el, periels)
            #    print(cell_pointer.indices)
            #    raise
            cell_index_x = cell_pointer.x
            cell_index_y = cell_pointer.y
            next_cell_index_x = cell_index_x + punch.value[0]
            next_cell_index_y = cell_index_y + punch.value[1]
            #next_cell = None
            #try:
            next_cell = Cell.get_cell(next_cell_index_x,
                                       next_cell_index_y,
                                       scale)
            #except ValueError:
            #    print(side, scale)
            #    print(next_cell_index_x, next_cell_index_y, periels)
            #    raise
            cells.add(next_cell)
            used_el = punch
            cell_pointer = next_cell
        return cells

    @staticmethod
    def get_cells_linear(line, scale):
        """Return a set of the cells that intersect the ``line`` at the
specified ``scale``."""
        cells = set()
        for i in range(1, len(line)):
            side = line[i-1:i+1]
            cells.update(Cell._get_cells_side(side, scale))
        return cells
    
    @staticmethod
    def get_cells(polygon, scale, wire_frame=None, wire_cell_cache=None):
        """Return a set of the cells that intersect the ``polygon`` at the
specified ``scale``."""
        
        cells = set()
        
        #Get boundary cells on vertices and between vertices on sides
        if wire_frame and wire_cell_cache is not None:
            for w,wire in wire_frame:
                if w in wire_cell_cache:
                    c = wire_cell_cache[w]
                else:
                    c = Cell.get_cells_linear(wire, scale)
                    wire_cell_cache[w] = c
                cells.update(c)
        else:
            for side in polygon.sides:
                cells.update(Cell._get_cells_side(side, scale))
        print("Got %s boundary cells" % len(cells), end='')
        
        #Focus on a rectangle of cells cropped to the cells of the boundaries.
        #Determine for each cell in focus whether the cell is inside the
        #polygon or outside it.
        #Do this by selecting any cell whose in/out/boundary status is unknown,
        #then grow a connected component of cells outward from there.
        #Check whether this cell is inside or outside the polygon.
        #During this growth cells should be considered adjacent if they share
        #a side but not if they only share a corner.
        #Cells that intersect the boundary of the polygon are not added to the
        #growing connected component.
        #Once the connected component cannot grow any further, either add all
        #the cells in the component to `cells` if the starting cell is inside
        #the polygon or remove all the cells in the component from the set of
        #undesignated cells, since they are all outside the polygon.
        x,X,y,Y = 2**scale, -1, 2**scale, -1
        for cell in cells:
            xx, yy = cell.indices
            
            x = min(x, xx)
            X = max(X, xx)
            y = min(y, yy)
            Y = max(Y, yy)
        
        illegal = {cell.indices for cell in cells}
        undesignated_cells = {c
                              for c in ((a,b)
                                        for a in range(x,X+1)
                                        for b in range(y,Y+1))
                              if c not in illegal}
        
        border_cells = set()
        for i in range(x,X+1):
            for j in (y,Y):
                c = Cell.get_cell(i,j,scale)
                if c not in illegal:
                    border_cells.add(c)
        for j in range(y+1, Y):
            for i in (x,X):
                c = Cell.get_cell(i,j,scale)
                if c not in illegal:
                    border_cells.add(c)
        
        #For each cell on the border of the region in focus that's not also
        #in `illegal` and that's not already been removed from
        #undesignated_cells grow a connected component from that cell and
        #then remove all the cells in the component from undesginated_cells
        for seed in (s
                     for s in border_cells
                     if s in undesignated_cells):
            undesignated_cells -= Cell._connected_component(
                    seed,x,X,y,Y,illegal)
        
        #Classify each remaining cluster (connected component) of cells as
        #inside or outside and then either add all its cells to `cells` or
        #remove all its cells from `undesignated_cells` respectively.
        while undesignated_cells:
            seed = undesignated_cells.pop()
            
            core = Cell._connected_component(seed,x,X,y,Y,illegal)
            status_inside = (Cell.get_cell(
                    seed[0], seed[1], scale).corner in polygon)
            if status_inside:
                cells.update(Cell.get_cell(xx, yy, scale)
                             for xx,yy in core)
            undesignated_cells -= core
        
        print(", %s cells overall" % len(cells))
        
        return cells
    
    _cell_cache = {}
    
    @staticmethod
    def get_cell(x, y, scale):
        if (x, y, scale) not in Cell._cell_cache:
            Cell._cell_cache[x, y, scale] = Cell(x, y, scale)
        return Cell._cell_cache[x, y, scale]
    
    @staticmethod
    def _check_lng_lat_scale(lng, lat, scale):
        try:
            assert isinstance(lng, float) and isinstance(lat, float)
        except AssertionError:
            raise TypeError("lat and lng must be floats")
        try:
            assert isinstance(scale, int)
        except AssertionError:
            raise TypeError('scale must be an int')
        if scale < 0:
            raise ValueError('scale must be int >= 0')
        if lng < -180 or 180 <= lng:
            raise ValueError('lng (%s) must be in range [-180,180)'%lng)
        if lat < -90 or 90 < lat:
            raise ValueError('lat (%s) must be in range [-90,90]'%lat)
        return
    
    @staticmethod
    def _get_cell_indices(lng, lat, scale):
        mesh_size_lng = 360 / 2**scale
        mesh_size_lat = 180 / 2**scale
        
        mesh_x_index = int(lng / mesh_size_lng)
        mesh_y_index = int(lat / mesh_size_lat)
        
        guess_cell = Cell.get_cell(mesh_x_index, mesh_y_index, scale)
        if (lng,lat) in guess_cell:
            return mesh_x_index, mesh_y_index
        xc, yc = guess_cell.corner
        
        ne = Cell.get_cell(mesh_x_index + 1, mesh_y_index + 1, scale)
        Xc, Yc = ne.corner

        northing = 1 if lat >= Yc else -1 if lat < yc else 0
        easting  = 1 if lng >= Xc else -1 if lng < xc else 0
        
        return mesh_x_index + easting, mesh_y_index + northing
    
    @staticmethod
    def get_corner(lng, lat, scale):
        """Return the southwest corner of the abstract lat/long cell in which
the point at ``lat``, ``lng`` is located given the ``scale`` of the mesh
involved.  Mesh scale: At a scale of 0, the whole area of Earth's surface is
covered by a single cell. At a scale of 1, each cell covers a quarter of Earth,
based on slicing the globe along the equator, prime meridian, and prime
antimeridian. At scale 2, additional slicing lines are added at plus and minus
90 degrees of longitude and at plus and minus 45 degrees of latitude, spliting
the globe into 16 pieces. Generally, each additional rank of scale splits each
cell from the previous rank into four pieces by splitting it evenly according
to lines of latitude and longitude. No effort is made to balance the areas or
other geometric aspects of the split regions; only lat/long is used."""
        Cell._check_lng_lat_scale(lng, lat, scale)
##        mesh_size_lng = 360 / 2**scale
##        mesh_size_lat = 180 / 2**scale
##        
##        mesh_lng_index = int(lng / mesh_size_lng)
##        mesh_lat_index = int(lat / mesh_size_lat)
        
        mesh_lng_index, mesh_lat_index = Cell._get_cell_indices(lng,lat,scale)
        return Cell.get_cell(mesh_lng_index, mesh_lat_index, scale).corner
    
    @staticmethod
    def _get_corner(lng, lat, scale):
        Cell._check_lng_lat_scale(lng, lat, scale)
        if scale == 0:
            return -180, -90
        lng_lower, lat_lower = Cell._get_corner(lng, lat, scale - 1)
        
        lng_higher = lng_lower + 360 / 2**scale
        lat_higher = lat_lower + 180 / 2**scale
        
        result_lng = lng_lower if lng_higher > lng else lng_higher
        result_lat = lat_lower if lat_higher > lat else lat_higher
        
        return result_lng, result_lat
    
    def __init__(self, x, y, scale):
        """Initialize a Cell instance at the specified `scale` having the
           specified `x` and `y` indices on the mesh at that scale."""
        
        if not isinstance(x, int) or not isinstance(y, int):
            raise TypeError
        
        self.x = x
        self.y = y
        self.scale = scale
        
        mesh_scale_lng = 360 / 2**scale
        mesh_scale_lat = 180 / 2**scale
        
        corner_guess_lng = x * mesh_scale_lng
        corner_guess_lat = y * mesh_scale_lat
        
        cell_center_guess_lng = corner_guess_lng + mesh_scale_lng / 2
        cell_center_guess_lat = corner_guess_lat + mesh_scale_lat / 2

        self.corner = Cell._get_corner(cell_center_guess_lng,
                                       cell_center_guess_lat,
                                       scale)
    
    def __hash__(self):
        return hash((self.scale, self.x, self.y))

    def __str__(self):
        return 'Cell(%s, %s, %s)' % (self.x, self.y, self.scale)

    def __repr__(self):
        return str(self)
    
    def __eq__(self, other):
        return self.corner == other.corner and self.scale == other.scale

    def __neq__(self, other):
        return not self == other

    def __contains__(self, point):
        a,b = point
        x,y = self.corner
        i,j = self.indices
        X,Y = Cell.get_cell(i+1, j+1, self.scale).corner
        return x <= a and a < X and y <= b and b < Y
    
    @property
    def indices(self):
        """Return the x and y indices of this cell on the mesh at this cell's scale."""
        
        return (self.x, self.y)
    
    @property
    def center_guess(self):
        finer_scale = self.scale + 1
        dx_guess = 360 / 2**finer_scale
        dy_guess = 180 / 2**finer_scale
        x,y = self.corner
        return (x + dx_guess, y + dy_guess)
