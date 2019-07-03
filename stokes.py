"""A script to find the net outer boundary or boundaries of a collection of 
abutting polygons.

The name "stokes" is taken from the Stokes Theorem 
(https://en.wikipedia.org/wiki/Stokes%27_theorem).

It is difficult to explain why that association makes sense. See the 
2014-02-24 edition of the webcomic Saturday Morning Breakfast Cereal
(https://www.smbc-comics.com/comic/2014-02-24) for an explanation of 
why it is difficult to explain."""

def _orientation(side):
    a, b = side
    if a < b:
        return 1
    elif a > b:
        return -1
    else:
        raise ValueError('side connects a vertex to itself: ' + str(side))

class SideMinder:
    """A class to keep track of directed edges (polygon sides) being added
    together."""
    
    def __init__(self):
        self.em = {}
    
    def add(self, side):
        verts = frozenset(side)
        new_net_orientation = self.em.get(verts, 0) + _orientation(side)
        if new_net_orientation == 0:
            del self.em[verts]
        elif abs(new_net_orientation) == 1:
            self.em[verts] = new_net_orientation
        else:
            raise ValueError('net orientation outside allowed range')
    
    def net_sides(self):
        nets = set()
        for fs, ori in self.em.items():
            x,y = fs
            alphab = (x,y)
            baphla = (y,x)
            if _orientation(alphab) == ori:
                nets.add(alphab)
            elif _orientation(baphla) == ori:
                nets.add(baphla)
            else:
                raise ValueError('impossible orientation situation')
        return nets

def _cross_product(de1, de2):
    """To be used with directed edges defined by their endpoints"""
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
        #dirty hack designed to work if original outer bounds curl ccw
        nexts.sort(key=(lambda x : _cross_product(side, x)))
    
    next_side = nexts[0]

    remaining_net_sides.remove(next_side)
    return next_side

def stokes(polygons):
    
    side_adder = SideMinder()
    for polygon in polygons:
        for i in range(1, len(polygon)):
            side_adder.add(polygon[i-1:i+1])
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
