#Given several adjacent districts in terms of their boundaries, find the
#boundary of the union of the districts.
#
#As long as all the boundaries share the same winding scheme, adding the
#directed edges together should cause the oppositely-oriented edges of adjacent
#polygons in the interior to negate one another while leaving the unopposed
#edges of the outer boundary(ies) intact.
#
#A winding scheme is either of the following: 1. that outer boundaries' vertices
#build up clockwise and inner boundaries' vertices build up counterclockwise, or
#2. that outer boundaries' vertices build up counterclockwise and inner
#boundaries' vertices build up clockwise.
#
#The script is named after Stokes's theorem, in which the net curl in a 2D
#surface region (the integral of the curl-density at each point in the region)
#can be summarily calculated by integrating a slightly different
#curl/curl-density term over the 1D border of the 2D region in question.
#Basically, curly things laid flat and pushed right up against each other
#naturally push the curliness out to the edge. So, by just tracking where the
#curliness in a region loaded with polygons is (even though this is discrete
#curliness) and isn't, we can identify the outer edge(s) and ignore the inner
#ones.
#
#Relevant SMBC: https://www.smbc-comics.com/comic/2014-02-24

def _proper(edge):
    a = edge[0]
    b = edge[1]
    if a[0] < b[0]: #proper
        return (edge, 1)
    elif a[0] > b[0]: #improper
        return ((edge[1], edge[0]), -1)
    elif a[1] < b[1]: #proper
        return (edge, 1)
    elif a[1] > b[1]: #improper
        return ((edge[1], edge[0]), -1)
    else:
        raise Exception("edge links a point with itself")

def _sides(polygon):
    assert polygon[0] == polygon[-1]
    result = []
    for i in range(1, len(polygon)):
        side = (polygon[i-1], polygon[i])
        yield side

def _vital_dicts(polygons):
    verts_to_edges = {}
    edges_proper_orients = {}
    for polygon in polygons:
        for edge in _sides(polygon):
            edge_proper, orient = _proper(edge)

            #edges that occur twice in two different polygons will end up
            #overlapping in opposite directions, resulting in a net orientation
            #of 0, whereas unique edges end up with a net orientation not
            #equal to zero.
            if edge_proper in edges_proper_orients:
                orient += edges_proper_orients[edge_proper]
            edges_proper_orients[edge_proper] = orient
            
            for point in edge:
                if point in verts_to_edges:
                    verts_to_edges[point].add(edge_proper)
                else:
                    verts_to_edges[point] = {edge_proper}
    return (verts_to_edges, edges_proper_orients)

def _vulgar(edge, orient):
    if orient == 1:
        return edge
    elif orient == -1:
        return (edge[1], edge[0])
    else:
        raise Exception("unexpected net edge orientation: " + orient)

class SeedException(Exception):
    pass

def _seed_edge(edges_proper_orients, used_edges):
    for edge, orient in edges_proper_orients.items():
        if orient != 0 and edge not in used_edges:
            return _vulgar(edge, orient)
    raise SeedException()
        
def _next_edge(edges_proper, current_edge, edges_proper_orients):
    for edge in edges_proper:
        if edge != _proper(current_edge)[0] and edges_proper_orients[edge] != 0:
            return _vulgar(edge, edges_proper_orients[edge])

#Each polygon vertex list's first vertex should equal that list's last vertex
def stokes(polygons):
    if len(polygons) == 0:
        return []
    if len(polygons) == 1:
        return [list(polygons[0])]

    net_boundaries = []
    
    verts_to_edges, edges_proper_orients = _vital_dicts(polygons)
    used_edges = set()
    while True:
        try:
            current_edge = _seed_edge(edges_proper_orients, used_edges)
            vertices = [current_edge[0], current_edge[1]]
            used_edges.add(_proper(current_edge)[0])
            while vertices[-1] != vertices[0]:
                next_edge = _next_edge(
                        verts_to_edges[vertices[-1]],
                        current_edge,
                        edges_proper_orients)
                vertices.append(next_edge[1])
                used_edges.add(_proper(next_edge)[0])
                current_edge = next_edge
            net_boundaries.append(vertices)
        except SeedException:
            break

    net_boundaries.sort(key=len)
    return net_boundaries
