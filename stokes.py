"""A script to find the net outer boundary or boundaries of a collection of 
abutting polygons.

The name "stokes" is taken from the Stokes Theorem 
(https://en.wikipedia.org/wiki/Stokes%27_theorem).

It is difficult to explain why that association makes sense. See the 
2014-02-24 edition of the webcomic Saturday Morning Breakfast Cereal
(https://www.smbc-comics.com/comic/2014-02-24) for an explanation of 
why it is difficult to explain."""

def _orientation(side):
    """Return -1 or 1 based on the orientation from the first to last point.
    """
    a, b = side
    if a < b:
        return 1
    elif a > b:
        return -1
    else:
        raise ValueError('side connects a vertex to itself: ' + str(side))

class _SideMinder(dict):
    """A class to keep track of the sums of many directed edges (polygon sides).

       When a given side's net orientation is 0, remove that side as a key
       to save space in memory."""
    
    def __missing__(self, key):
        return 0

    def __setitem__(self, key, value):
        if value == 0:
            try:
                self.__delitem__(key)
            except KeyError:
                pass
        elif abs(value) == 1:
            super(_SideMinder, self).__setitem__(key, value)
        else:
            raise ValueError(f'net orientation ({value}) of edge ({side}) '
                              'outside allowed range. This may mean that inner '
                              'and outer boundaries curl in the same direction.')
    
    def add(self, side):
        """Add `side` to the pile of directed sides already present.

           If another side with the same points and opposite direction is
           already counted, then the count for the corresponding undirected side
           becomes zero and the corresponding key is removed from the underlying
           dict altogether to save space."""
        
        verts = frozenset(side)
        self[verts] += _orientation(side)
    
    def net_sides(self):
        nets = set()
        for frznst, orinttn in self.items():
            x,y = frznst
            points_alphabetical = (x,y)
            points_alphabetical_reverse = (y,x)
            if _orientation(points_alphabetical) == orinttn:
                nets.add(points_alphabetical)
            elif _orientation(points_alphabetical_reverse) == orinttn:
                nets.add(points_alphabetical_reverse)
            else:
                raise ValueError('impossible orientation situation')
        return nets

def _cross_product(de1, de2):
    """Return the cross product of the vectors defined by the directed edges."""
    va1,vb1 = de1
    va2,vb2 = de2
    
    v1 = vb1[0] - va1[0], vb1[1] - va1[1]
    v2 = vb2[0] - va2[0], vb2[1] - va2[1]
    
    return v1[0]*v2[1] - v1[1]*v2[0]

def _next_side(side, vertex_to_sides, remaining_net_sides):
    nexts = [a
             for a in vertex_to_sides[side[1]]['next']
             if a in remaining_net_sides]
    if len(nexts) != 1:
        #dirty hack to deal with some long-forgotten edge-case with bad data
        nexts.sort(key=(lambda x : _cross_product(side, x)))
    
    next_side = nexts[0]
    
    remaining_net_sides.remove(next_side)
    return next_side

def _sides(boundary):
    """Generate pairs of adjacent elements from `boundary`."""
    old, new = None, None
    for vertex in boundary:
        old, new = new, vertex
        if old is not None:
            yield old, new

def stokes(polygons):
    """Add oriented sides so only a net boundary (usually exterior) survives.

       Return a list of the net boundaries that are the sum of the directed
       boundaries supplied by `polygons`. The curl scheme of the original
       polygons is inherited by the return value.
       
       :param polygons: an iterable of outer and inner boundaries"""
    
    side_adder = _SideMinder()
    for polygon in polygons:
        for side in _sides(polygon):
            side_adder.add(side)
    del polygons
    
    net_sides = side_adder.net_sides()
    del side_adder
    
    vertex_to_sides = {}
    for side in net_sides:
        a, b = side
        for c in side:
            if c not in vertex_to_sides:
                vertex_to_sides[c] = {'next':[], 'prev':[]}
        vertex_to_sides[a]['next'].append(side)
        vertex_to_sides[b]['prev'].append(side)
    for v,d in vertex_to_sides.items():
        assert d['next'], [v,d]
        assert d['prev'], [v,d]
    
    net_boundaries = []
    while True:
        try:
            seed = next(iter(net_sides))
        except StopIteration:
            break #out of while-loop
        else:
            polygon = list(seed)
            next_side = _next_side(seed, vertex_to_sides, net_sides)
            while next_side != seed:
                polygon.append(next_side[1])
                next_side = _next_side(next_side, vertex_to_sides, net_sides)
            net_boundaries.append(polygon)
    
    return net_boundaries
