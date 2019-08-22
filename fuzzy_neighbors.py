"""This script defines functions for building an adjacency graph describing
which polygon pairs in a given map are adjacent to one another. In a well-built
map, there should be no overlaps or gaps, but not all maps are. This script
iterates over the edges (between polygons' vertices) of a map,
generates a pair of points close to the edge but on opposite sides of it,
determines which polygons from the map each point is in, then adds edges from
each polygon that contains the first of those two probe points to each polygon
that contains the second of those two probe points (except for edges from a
polygon to itself).

If using this to find adjacency among many polygons where some neighbors share
identical borders and some have mismatched borders, the workload and operating
time of this process can and should be reduced by sending only the mismatched
edges and by obtaining the adjacency information for perfectly aligned neighbors
with a different technique."""

from point_in_polygon import Polygon
import math, mesh

def get_all_edges(polygons):
    result = set()
    for polygon in polygons:
        result.update(frozenset(side) for side in polygon.sides)
    return result

R = 10 ** -5 #in degrees. about the size of a standing human viewed from above

def get_offside_points(edge):
    (xa,ya),(xb,yb) = edge
    h = (xa+xb)/2
    k = (ya+yb)/2
    try:
        ortho_slope = (ya-yb)/(xb-xa)
        if ortho_slope < -1 or ortho_slope > 1:
            raise ArithmeticError()
    except ArithmeticError:
        return [tuple(reversed(p))
                for p in get_offside_points(tuple(reversed(q))
                                            for q in edge)]
    ortho_b = k - ortho_slope * h
    
    a = 1 + ortho_slope**2
    b = 2*(ortho_slope*(ortho_b - k) - h)
    c = (k - ortho_b)**2 + (h - R)*(h + R)
    
    discr = b**2 - 4 * a * c
    d = math.sqrt(discr)
    return {(x, ortho_slope*x + ortho_b)
            for x in ((-b + s*d)/(2*a)
                      for s in (1,-1))}

def get_cell_to_precincts_map(polygons):
    result = {}
    for polygon in polygons:
        cells = mesh.Cell.get_cells(polygon, 16)
        for cell in cells:
            if cell not in result:
                result[cell] = []
            result[cell].append(polygon)
    return result

def get_involved_precincts(point, cell_to_precincts):
    cell = mesh.Cell.for_point(point, 16)
    precincts = cell_to_precincts[cell]
    return [precinct.info
            for precinct in precincts
            if point in precinct]

def get_graph(placemarks, ctp=None, all_edges=None):
    polygons = [Polygon.from_kml(pm, info=i)
                for i,pm in ([i, placemarks[i]]
                             for i in range(len(placemarks)))]
    cell_to_precincts = ctp or get_cell_to_precincts_map(polygons)
    
    graph = {polygon.info for polygon in polygons}
    all_edges = all_edges or get_all_edges(polygons)
    for edge in all_edges:
        offside_a, offside_b = get_offside_points(edge)
        involved_a = get_involved_precincts(offside_a, cell_to_precincts)
        involved_b = get_involved_precincts(offside_b, cell_to_precincts)
        for pa in involved_a:
            for pb in involved_b:
                if pa != pb:
                    edge = frozenset([pa, pb])
                    graph.add(edge)
    return graph
