"""A module to determine the connectedness (adjacency) of polygons in a plane.
   This is intended for GIS purposes."""

#The function poops out the offside probe points
#for the given `side` and probe radius
def get_probe_points(side, probe_radius):
    
    #unpack the side and then unpack its two points
    (x1, y1), (x2, y2) = side
    
    xm, ym = (x1+x2)/2, (y1+y2)/2 #midpoint of `side`
    
    if x1 == x2: #side is north-south
        return (xm - probe_radius, ym), (xm + probe_radius, ym)
    elif y1 == y2: #side is east-west
        return (xm, ym - probe_radius), (xm, ym + probe_radius)
    else:
        m = (x1 - x2) / (y2 - y1) #slope of line ortho to `side`
        x = ((1 + m**2) ** -0.5) * probe_radius
        return (xm + x, ym + m*x), (xm - x, ym - m*x)

def fuzzy(shapes, probe_factor=1000, scale=16):
    
    #Isolate the non-seamless boundaries
    from stokes import stokes
    boundaries = []
    for shape in shapes:
        boundaries.extend(list(o) for o in shape.outers)
        boundaries.extend(list(reversed(list(i))) for i in shape.inners)
    stoked = stokes(boundaries)
    
    #Determine the distance off to either side of each stokes-surviving
    #boundary to place the probe points for point-in-polygon testing
    #This distance is the shortest length of all the stokes-surviving
    #sides, divided by 2, divided by the `probe_factor`
    import geometry
    probe_radius = (min(min(geometry.dist2(boundary[i-1], boundary[i])
                            for i in range(1, len(boundary)))
                        for boundary in stoked) ** 0.5) / 2 / probe_factor
    
    #Create a mapping from latlong mesh cell on the surface of the earth to
    #the shapes from `shapes` that intersect that cell
    #The values in the dict are dicts so that they can act as sets without
    #needing the `shapes` to be hashable.
    import spindex
    cell_to_shapes = {}
    for i, shape in enumerate(shapes):

        #gather cells
        cells = set()
        for outer in shape.outers:
            cells.update(spindex.get_cells_2d(outer, scale=scale))
        for inner in shape.inners:
            d1 = spindex.get_cells_1d(inner, scale=scale)
            d2 = spindex.get_cells_2d(inner, scale=scale, boundary_cells=d1)
            cells -= (d2 - d1)

        #add mapping from each cell to the current shape
        for cell in cells:
            if cell not in cell_to_shapes:
                cell_to_shapes[cell] = {}
            cell_to_shapes[cell][i] = shape
    else:
        cell_to_shapes = {cell:list(shape_dict.values())
                          for cell, shape_dict in cell_to_shapes.items()}
    
    #start building the graph with the vertices (as ints)
    graph = set(range(len(shapes)))
    
    #for each boundary that survived the stokes process, get the side's
    #probe points, map each of those onto a latlong mesh cell, and from there
    #map each probe point onto the shapes that intersect the cell.
    #Then for each shape that only occurs in the first set of shapes and for
    #each shape that only occurs in the second such set, add an edge to the
    #graph linking those shapes to each other.
    for boundary in stoked:
        for i in range(1, len(boundary)):
            side = boundary[i-1:i+1]
            shapes1, shapes2 = ({j
                                 for j,s
                                 in enumerate(cell_to_shapes[
                                         spindex.get_cell(point)])
                                 if point in s}
                                for point in get_probe_points(side,
                                                              probe_radius))
            
            both = shapes1 & shapes2
            shapes1 -= both
            shapes2 -= both
            
            for s1 in shapes1:
                for s2 in shapes2:
                    graph.add(frozenset([s1, s2]))
    return graph

def seamless(shapes):
    #get the graph started with the vertices
    graph = set(range(len(shapes)))
    
    #build a mapping from each polygon-side to a set of the polygons that
    #have that side (as int indices)
    side_to_shapes = {}
    for i, shape in enumerate(shapes):
        for side in shape.sides:
            key = frozenset(side)
            try:
                extant = side_to_shapes[key]
            except KeyError:
                side_to_shapes[key] = {i}
            else:
                extant.add(i)
    
    #Use that mapping to identify all pairs of neighboring polygons
    #Add each such pair to the graph as a frozenset of int indices
    for side, pair in side_to_shapes.items():
        if len(pair) == 1:
            continue
        elif len(pair) > 2:
            raise Exception(
                    f"one side maps to more than two shapes: {side} -> {pair}")
        graph.add(frozenset(pair))
    
    return graph
