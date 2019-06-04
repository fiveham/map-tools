#Given several adjacent districts in terms of their boundaries, find the
#boundary of the union of the districts.

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
    #print("Generate vital dictionaries")
    verts_to_edges = {}
    edges_proper_orients = {}
    for polygon in polygons:
        #print("checking a polygon")
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
    #print("in stokes")
    if len(polygons) == 0:
        return []
    if len(polygons) == 1:
        return [list(polygons[0])]

    #print("not a degenerate stokes case" + str(len(polygons)))
    net_boundaries = []
    
    verts_to_edges, edges_proper_orients = _vital_dicts(polygons)
    used_edges = set()
    while True:
        #print("in main stokes loop")
        try:
            current_edge = _seed_edge(edges_proper_orients, used_edges)
            #print(current_edge)
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
            #print("seed exception")
            break

    #print("%d boundaries" % len(net_boundaries))
    net_boundaries.sort(key=len)
    return net_boundaries
