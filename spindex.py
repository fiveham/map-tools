def get_cell(point, scale=16):
    lng, lat = point
    LNG, LAT = lng + 180, lat + 90
    lng_cell_width  = 360 / 2 ** scale
    lat_cell_height = 180 / 2 ** scale
    x_index = LNG // lng_cell_width
    y_index = LAT // lat_cell_height
    return _Cell.get(x_index, y_index, scale)

class BBox:
    def __init__(x,X=None,y=None,Y=None):
        if X is None:
            scale = x.scale
            width = 360 / 2**scale
            height = 180 / 2**scale
            lng = width * x.x - 180
            lat = height * x.y - 90
            self.x, self.X = lng, lng + width
            self.y, self.Y = lat, lat + height
        else:
            self.x, self.X, self.y, self.Y = x,X,y,Y
    
    def __sub__(self, bbox):
        return BBox(max(self.x, bbox.x),
                    min(self.X, bbox.X),
                    max(self.y, bbox.y),
                    min(self.Y, bbox.Y))

    def __bool__(self):
        return self.x != self.X or self.y != self.Y

def get_cells_1d(points, scale=16):
    cells = {get_cell(point, scale) for point in points}
    for i in range(1, len(points)):
        a,b = points[i-1:i+1]
        cella = get_cell(a, scale)
        cellb = get_cell(b, scale)
        if cella.x == cellb.x:
            y, Y = sorted([cella.y, cellb.y])
            for i in range(y+1, Y):
                cells.add(_Cell.get(cella.x, i, scale))
        elif cella.y == cellb.y:
            x, X = sorted([cella.x, cellb.x])
            for i in range(x+1, X):
                cells.add(_Cell.get(i, cella.y, scale))
        else:
            x, X = sorted([cella.x, cellb.x])
            y, Y = sorted([cella.y, cellb.y])
            bbox = BBox(x,X,y,Y) - BBox(cella) - BBox(cellb)
            while bbox:
                ...

class _Cell:

    @staticmethod
    def get(x_index, y_index, scale, cache={}):
        key = (x_index, y_index, scale)
        try:
            cached = cache[key]
        except KeyError:
            cached = _Cell(x_index, y_index, scale)
            cache[key] = cached
        return cached
    
    def __init__(x_index, y_index, scale):
        self._hash = None
        self.x = x_index,
        self.y = y_index
        self.scale = scale
    
    def __hash__(self):
        if self._hash is None:
            self._hash = hash((self.x, self.y, self.scale))
        return self._hash
