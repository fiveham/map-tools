from collections import Counter

COLORS = {1,2,3,4}

def _find_constraint_and_filter(items, key, side):
    """Iterate over `items` to determine a constraint value and return a list
       of elements from `items` that map to that constraint via `key`.

       `items` : an iterable
       `key` : a callable accepting single elements from `items` and returning
               something
       `side` : a callable accepting an iterable of elements and returning one
                of those elements, such as `min()` or `max()`"""
    scores = {x : key(x) for x in items}
    constraint = side(v for v in scores.values())
    return [x for x in items if scores[x] == constraint]

def _legal_colors(vertex, neighboring, coloring):
    """Return a set of the colors that are not assigned to any of the neighbors
       of `vertex`.

       `vertex` : a vertex (int) of the graph represented by `neighboring`
       `neighboring` : a dict from vertex (int) to a set of the vertices that
                       share an edge with that key
       `coloring` : a dict from vertex (int) to color (int 1-4)"""
    return COLORS - {coloring.get(neighbor,0)
                     for neighbor in neighboring[vertex]}

def vertices_edges_neighboring(graph):
    """Return the vertices, edges, and vertex-to-neighbors dict based on
       `graph`.

       `graph` : a set of vertices (int) and edges (frozenset of two ints)

       This function encapsulates some boilerplate to keep `color()` clean and
       to provide easy access to the neighbor dict when coloring interactively
       in a shell."""
    vertices, edges, neighboring = [], [], {}
    for thing in graph:
        if isinstance(thing, int):
            vertices.append(thing)
        else:
            edges.append(thing)
            for order in [thing, reversed(list(thing))]:
                a,b = order
                if a not in neighboring:
                    neighboring[a] = set()
                neighboring[a].add(b)
    return vertices, edges, neighboring

def hypothetical_coloring(coloring, what_if):
    """Return a modified version of `coloring` in which the mappings from
       `what_if` supplant the pre-exisiting color assignments.

       `coloring` : a dict mapping from vertex (int) to color (int 1-4)
       `what_if` : a frozenset of (vertex,color) tuples; this could be read as
                   "What if this vertex were this color and that vertex were
                   that color and ...?" """
    recolor = dict(coloring)
    for v,c in what_if:
        recolor[v] = c
    return recolor

def chetwork(vertex, color1, color2, neighboring, coloring):
    """Identify and return a single-connected-component subgraph (set of
       vertices) of the graph defined by `neighboring` containing only
       vertices whose color is `color1` or `color2`.

       `vertex` : a vertex with an uncolored and uncolorable neighbor and which
                  will be the seed from which a two-color subgraph is grown
       `color1` : a color (int 1-4)
       `color2` : another color (int 1-4), different from `color1`
       `neighboring` : a dict from vertex (int) to a set of the vertices that
                       share an edge with that key
       `coloring` : a dict from vertex (int) to color (int 1-4)

       This sort of two-color subgraph is meant to be recolored in one move so
       as to enable an uncolorable vertex adjacent to the subgraph to have a
       legal color."""
    colors = {color1, color2}
    
    core, edge, news = set(), set(), {vertex}
    while news:
        edge, news = news, set()
        for v in edge:
            news.update(neighbor
                        for neighbor in neighboring[v]
                        if (neighbor not in core and
                            neighbor not in edge and 
                            coloring.get(neighbor,0) in colors))
        core.update(edge)
    return frozenset(core)

def _get_colored_neighbors(vertex, neighboring, coloring):
    """Return a subset of the neighbors of `vertex` where every member of the
       set has been assigned a color

       `vertex` : a vertex with at least one neighbor of each color
       `neighboring` : a dict from vertex (int) to a set of the vertices that
                       share an edge with that key
       `init_coloring` : the established coloring assignments for the graph,
                         of which a modified version should be returned"""
    return {neighbor
            for neighbor in neighboring[vertex]
            if coloring.get(neighbor,0) != 0}

def _chain_shift(vertex, neighboring, init_coloring):
    """Check the neighbors of `vertex` to see if there's a way to open up a
       legal color for `vertex` by simultaneously recoloring all the vertices
       of a two-color subgraph. If there is, return a modified version of
       `init_coloring` in which the two colors of that subgraph are swapped.
       
       `vertex` : a vertex with at least one neighbor of each color
       `neighboring` : a dict from vertex (int) to a set of the vertices that
                       share an edge with that key
       `init_coloring` : the established coloring assignments for the graph,
                         of which a modified version should be returned"""
    colored_neighbors = _get_colored_neighbors(vertex,
                                               neighboring,
                                               init_coloring)
    options = set()
    for neighbor in colored_neighbors:
        color = init_coloring[neighbor]
        other_colors = COLORS - {color}
        for other in other_colors:
            subgraph = chetwork(
                    neighbor, color, other, neighboring, init_coloring)
            if len(subgraph & neighboring[vertex]) == 1:
                options.add((subgraph, frozenset([color, other])))
    
    what_ifs = [frozenset((vertex, (color1
                                    if (init_coloring.get(vertex,0) == color2)
                                    else color2))
                          for vertex in subgraph)
                for subgraph, (color1, color2) in options]
    what_ifs.sort(key=len)
    
    try:
        return next(iter(
                hypotheticolor
                for hypotheticolor
                in (hypothetical_coloring(init_coloring, what_if)
                    for what_if in what_ifs)
                if _legal_colors(vertex, neighboring, hypotheticolor)))
    except StopIteration:
        raise CannotColor()

def _local_shift(vertex, neighboring, init_coloring):
    """Check the neighbors of `vertex` to see if any of them can make room for
       `vertex` to have a legal color option by changing to another color that
       they have available. If there is such a thing, return a modified
       color assignment based on `init_coloring` which has one of the neighbors
       of `vertex` recolored in that way.

       `vertex` : a vertex with at least one neighbor of each color
       `neighboring` : a dict from vertex (int) to a set of the vertices that
                       share an edge with that key
       `init_coloring` : the established coloring assignments for the graph,
                         of which a modified version should be returned"""
    colored_neighbors = _get_colored_neighbors(vertex,
                                               neighboring,
                                               init_coloring)
    neighbors_with_options = [
            neighbor
            for neighbor in colored_neighbors
            if 1 < len(_legal_colors(neighbor, neighboring, init_coloring))]
    what_ifs = set()
    for neighbor in neighbors_with_options:
        options = _legal_colors(neighbor, neighboring, init_coloring)
        options.remove(init_coloring[neighbor])
        for option in options:
            what_if = frozenset([(neighbor, option)])
            what_ifs.add(what_if)
    try:
        return next(iter(
                    hypotheticolor
                    for hypotheticolor
                    in (hypothetical_coloring(init_coloring, what_if)
                        for what_if in sorted(what_ifs))
                    if _legal_colors(vertex,
                                     neighboring,
                                     hypotheticolor)))
    except StopIteration:
        raise CannotColor()

def sidetrack(vertex, neighboring, init_coloring):
    """Try to find a way to make it possible to legally color `vertex` by
       checking for legal tweaks to the estabished coloring of the vertices
       near `vertex` that would make room for `vertex` to have at least one
       legal color.

       `vertex` : a vertex with at least one neighbor of each color
       `neighboring` : a dict from vertex (int) to a set of the vertices that
                       share an edge with that key
       `init_coloring` : the established coloring assignments for the graph,
                         of which a modified version should be returned

       This function is named in contrast to the backtracking technique for
       coloring a graph, which take eons to color a graph with thousands of
       vertices based on the electoral precincts of an entire state."""
    for technique in [_local_shift, _chain_shift]:
        try:
            return technique(vertex, neighboring, init_coloring)
        except CannotColor:
            continue
    else:
        raise CannotColor()

class CannotColor(Exception):
    pass

def color(graph, init_coloring=None):
    """`graph` : a set of vertices (int) and edges (frozenset) which each
                 contain two vertices that are connected.
       `init_coloring` : (optional) a dict mapping from vertex (int) to color
                         (int 1-4), describing a partial coloring of the
                         graph."""
    #boilerplate
    vertices, edges, neighboring = vertices_edges_neighboring(graph)
    
    #meat
    coloring = dict(init_coloring) if init_coloring is not None else {}
    while any(coloring.get(v,0) == 0 for v in vertices):
        uncolored_vertices = [v for v in vertices if coloring.get(v,0) == 0]
        most_constrained_vertices = _find_constraint_and_filter(
                uncolored_vertices,
                (lambda v : len(_legal_colors(v, neighboring, coloring))),
                min)
        
        vertex = next(iter(most_constrained_vertices))
        
        try:
            color = min(_legal_colors(vertex, neighboring, coloring))
        except ValueError: #no legal colors
            try:
                coloring = sidetrack(vertex, neighboring, coloring)
            except CannotColor:
                break #out of while loop
        else:
            coloring[vertex] = color
    else: #Exiting normally rather than due to a problem
        for vertex in neighboring:
            legals = _legal_colors(vertex, neighboring, coloring)
            counts = Counter(coloring.values())
            coloring[vertex] = min(legals, key=(lambda c : counts[c]))
    
    print(sum(1 for v in coloring.values() if v != 0),
          Counter(coloring.values()))
    return coloring
