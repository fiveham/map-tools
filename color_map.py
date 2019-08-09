"""Given a KML map (bs4.BeautifulSoup) of adjacent districts, assign a color to
   each one and modify the map object to reflect those assignments by adding
   Style and styleUrl elements to the map and its Placemarks to define and assign
   the styles corresponding to each color.

   Internally within this script, the colors are the numbers 1 through 4.
   Visually they are shades of green and orange of unique brightnesses."""

from collections import Counter
from bs4 import BeautifulSoup

import kml

class Graph(set):
    """A convenience wrapper for a set of vertices and edges, providing
       properties to easily iterate over just the vertices or just the edges"""
    
    def __init__(self, graph):
        """`graph` : a set of vertices and of unordered pairs (frozensets) of
                     vertices"""
        super(Graph, self).__init__(graph)
        
        self.neighbors = {v:set() for v in self.vertices}
        for a,b in self.edges:
            neighbors[a].add(b)
            neighbors[b].add(a)
    
    @property
    def vertices(self):
        """Return a generator that yields only the vertices from the underlying
           set"""
        for thing in self:
            if not isinstance(thing, frozenset):
                yield thing
    
    @property
    def edges(self):
        """Return a generator that yields only the edges from the underlying
           set"""
        for thing in self:
            if isinstance(thing, frozenset):
                yield thing

COLORS = {1,2,3,4}

BASE_STYLE = ('<Style id="color%d"><PolyStyle><color>7f%s</color></PolyStyle>'
            '<LineStyle><color>7f666666</color></LineStyle></Style>')

THICK_WHITE_BORDER = ('<Style id="color%d"><PolyStyle><color>7f%s</color>'
                      '</PolyStyle><LineStyle><color>99ffffff</color>'
                      '<width>3</width></LineStyle></Style>')

#kml does colors in aabbggrr order instead of aarrggbb
COLOR_CODES = [(1, 'a8d7b6'),
               (2, '065fb4'),
               (3, '6bb2f6'),
               (4, '4fa86a')]
               #(5, 'cde5fc')

class Supply(Counter):
    """A collection of multiple instances of each color, used to determine
       which one of multiple legal colors for an uncolored vertex should be
       chosen to best maintain color parity"""
    
    def __init__(self, size=1):
        """`size` : The number of instances of each color to initially put into
                    the set"""
        if not isinstance(size, int) or size < 1:
            size = 1
        super(Supply, self).__init__()
        for color in COLORS:
            self[color] = size
    
    def most(self, colors):
        """Return a subset of `colors` whose elements are the most populous
           colors in this Supply

           `colors` : a collection of colors (int 1 to 4)"""
        as_dict = {c:self[c] for c in colors}
        target = max(as_dict.values())
        return {color for color,count in as_dict.items() if count == target}
    
    def take(self, color):
        """Remove one instance of `color` from this Supply, return that color,
           and restock one instance of all colors if the initial removal reduced
           the stock of that color to zero

           `color` the color to be pulled out of this Supply"""
        self[color] -= 1
        while any(v < 1 for v in self.values()):
            for c in self:
                self[c] += 1
        return color

def get_graph(pms):
    """Return a set of vertices (indices into `pms`) and edges (unordered pairs
       (frozensets) of adjacent vertices) on the premise that two Placemarks in
       `pms` are adjacent if and only if they share a boundary edge in common.

       `pms` : A list of KML Placemarks"""
    #Map from each boundary segment (edge) to the placemarks (ids) that have
    #that edge on their boundary
    edge_to_pms = {}
    for i,pm in (j,pms[j] for j in range(len(pms))):
        for c in pm('coordinates'):
            pts = [(float(t[0]),float(t[1]))
                   for t in (triple.split(",")
                             for triple in c.string.strip().split())]
            edges = [frozenset((pts[j-1],pts[j])) for j in range(1,len(pts))]
            for edge in edges:
                if edge not in edge_to_pms:
                    edge_to_pms[edge] = []
                edge_to_pms[edge].append(i)

    #Create graph (set of vertices and edges) of the districts
    graph = set(range(len(pms)))
    for pm_id_list in edge_to_pms.values():
        a = len(pm_id_list)
        if a == 1:
            continue
        elif a == 2:
            graph.add(frozenset(pm_id_list))
        else:
            raise Exception(str(a))
    return graph

def _legal_colors(vertex, coloring, neighbors):
    """Return a set of the colors that are viable for `vertex` by eliminating
       the colors of its neighbors from the set of all colors.

       `vertex` : The vertex (index into a list of Placemarks) whose colors
                  options are returned
       `coloring` : A dict from vertex to the vertex's color
       `neighbors` : A dict from vertex to a set of its neighbors"""
    return COLORS - {coloring[n] for n in neighbors[vertex]}

class Clog(Exception):
    """An exception indicating that an uncolored vertex with no color options
       available (because it has at least one neighbor of each color) was found"""
    pass

##class BuggyMax(Exception):
##    pass

def _buggy_max(vertex, iterable):
    """Return the maximum element of `iterable`. Raise Clog if `iterable` is
       empty.

       `vertex` : the vertex at which a clog occurs if a clog occurs
       `iterable` : an iterable whose maximum should be returned"""
    try:
        return max(iterable)
    except ValueError:
        raise Clog(str(vertex))

#Identify and return the best possible vertex of the graph for coloring
#It must be uncolored as yet, must be maximally color-constrained,
#must have the least possible count of uncolored neighbors, and
#must have the highest extant supply level among its legal colors
#
# A. Start with a list of all the uncolored vertices.
# B. Sort that list to move vertices with fewer options for their color closer
#    to the zero end of the list.
# C. Sub-sort that list to move those with greater numbers of uncolored
#    neighbors closer to the zero end of the list.
# D. Sub-sort that list to move vertices able to be colored with colors that
#    we have more of in supply closer to the zero end of the list.
# E. Return whichever vertex from that list came earliest in the original file.
def _color_me_next(neighbors, vert_to_cosugre, coloring, supply, kicked_back):
    """Choose the next vertex to be given a color and return that vertex.

       `neighbors` : A dict from vertex to a set of its neighbors
       `vert_to_cosugre` : A dict from vertex to a list of four-element complete
                           subgraphs of which it is a part
       `coloring` : A dict from vertex to the vertex's color
       `supply` : A color_map.Supply describing how many instances of each
                  color are currently available
       `kicked_back` : """
    if kicked_back and coloring[kicked_back[-1]] == 0:
        return kicked_back[-1], _legal_colors(kicked_back[-1],
                                              coloring,
                                              neighbors)
    
    vertices = list(neighbors)
    uncolored_verts = [x for x in vertices if coloring[x] == 0]
    try:
        #Fewer legal colors ranks ahead of more legal colors
        #Being a member of more complete 4-vert subgraphs ranks ahead of fewer
        #Having fewer uncolored neighbors ranks ahead of having more
        #A vertex coming earlier in the original file ranks ahead of later ones
        #Since the vertices are absolutely unique, lcs as a set will never be
        #checked for comparison. It's only here to be smuggled out later.
        #Similarly, the max-supply-of-color thing is present purely to provide
        #the opportunity for verts whose legal color options have been reduced
        #to none at all to raise a Clog.
        sortables = [(len(lcs),
                      -vert_to_cosugre[vert],
                      sum(1 for n in neighbors[vert] if coloring[n] == 0),
                      vert,
                      frozenset(lcs),
                      _buggy_max(vert, (supply[color] for color in lcs)))
                     for lcs,vert
                     in ([_legal_colors(uv, coloring, neighbors), uv]
                         for uv in uncolored_verts)]
    except Clog as e:
        if kicked_back is None:
            vertex = int(str(e))
            print('Coloring illegally on purpose. (%d)' % vertex)
            return vertex, COLORS
        else:
            raise
    sortables.sort()
    vertex = sortables[0][-3]
    lcs = sortables[0][-2]
    return vertex, lcs

def _post_check(graph, coloring):
    """Check for illegal color-sharing, print a warning if color-sharing across
       an edge is found, and print a description of the balance among the
       colors used
       
       `graph` : A color_map.Graph of vertices and unordered pairs (frozensets)
                 of adjacent vertices (edges)
       `coloring` : A dict from vertex to the vertex's color"""
    illegals = False
    for edge in graph.edges:
        a,b = edge
        if coloring[a] == coloring[b]:
            print("Illegal color-sharing: %d %s" % (coloring[a], str(edge)))
            illegals = True
    if not illegals:
        print("No illegal color-sharing.")
    print("Parity status (%d): %s"%(len(graph.neighbors),
                                    str([sum(1
                                             for color in coloring.values()
                                             if color == x)
                                         for x in COLORS])))

def _modify_soup(soup, base_style, pms, coloring):
    """Apply the specified vertex-to-color mapping to the Placemarks of `soup`,
       modifying `soup` in doing so.
       
       `soup` : A bs4.BeautifulSoup parsed from KML
       `base_style` : Valid KML text with two %s substitution sites: one for the
                      color-number and one for an rgb code
       `pms` : A list of the Placemarks in `soup`
       `coloring` : A dict from indices into `pms` (vertices) to colors (int, 1
                    to 4) chosen for those vertices"""
    #Apply chosen coloring dict to the Placemarks in the soup.
    #Add the Styles to the soup.
    #But first, remove preexisting Styles with the same ids.
    #Change each Placemark's styleUrl to correspond to the color chosen for that
    #Placemark.
    styles = [BeautifulSoup(base_style % (a,b), 'xml') for a,b in COLOR_CODES]
    for style in reversed(styles):
        incumbents = soup.Document(lambda tag :
                                   (tag.name == "Style" and
                                    'id' in tag.attrs and
                                    tag['id'] == style.Style['id']))
        for incumbent in incumbents:
            incumbent.decompose()
        
        name_tag = soup.Document.find('name', recursive=False)
        if name_tag:
            name_tag.insert_after(style.Style)
        else:
            soup.Document.insert(0, style.Style)
    
    for i,color in coloring.items():
        u = pms[i].styleUrl or kml.add(pms[i], 'styleUrl')
        u.string = "#color%d" % color

_counter = Counter()

#Transform and return soup, add Style tag for each color, assign styleUrl to
#each Placemark to map it to its assigned color.
def _try_color(soup, pms, graph, vert_to_cosugres,
               kicked_back, base_style):
    """Try to color the map in `soup`. Raise a Clog if coloring becomes
       impossible on an uncolored vertex that has neighbors of all colors.
       
       `soup` : A bs4.BeautifulSoup parsed from KML
       `pms` : A list of the Placemarks in `soup`
       `graph` : A color_map.Graph containing indices into `pms` (vertices) and
                 unordered pairs (frozensets) of those indices (edges)
       `vert_to_cosugres` : A dict from indices into `pms` (vertices) to a
                            collection of frozensets of the vertices of complete
                            four-element subgraphs of `graph`
       `kicked_back` : A list of indices into `pms` (vertices) at which a prior
                       coloring attempt failed with zero colors available for
                       that vertex
       `base_style` : Valid KML text with two %s substitution sites: one for the
                      color-number and one for an rgb code"""
    
    coloring = {i:0 for i in range(len(pms))}
    supply = Supply(len(pms)//len(COLORS))
    i = None
    for pm in pms:
        i, legal_colors = _color_me_next(graph.neighbors,
                                         vert_to_cosugres,
                                         coloring,
                                         supply,
                                         kicked_back)
        _counter[i] += 1
        most_supplied_legal_colors = supply.most(legal_colors)
        color = min(most_supplied_legal_colors)
        coloring[i] = supply.take(color)
    
    _post_check(graph, coloring)
    _modify_soup(soup, base_style, pms, coloring)
    return coloring

def _triplets(seq):
    """Yield all three-element subsets of `seq`
       
       `seq` : a list of unique elements"""
    for i in range(0, len(seq)-2):
        for j in range(i+1, len(seq)-1):
            for k in range(j+1, len(seq)):
                yield [seq[x] for x in (i,j,k)]

def _get_map_to_complete_subgraphs(graph):
    """Return a dict from vertices (int) to a list of the complete subgraphs
       of four vertices (K4) of which that vertex is a part.

       `graph` : A color_map.Graph of vertices and unordered pairs (frozensets)
                 of adjacent vertices (edges)"""
    result = {v:[] for v in graph.neighbors}
    for v,n in graph.neighbors.items():
        if len(n) < 3:
            continue
        for a,b,c in _triplets(list(n)):
            if (frozenset((a,b)) in graph and
                frozenset((b,c)) in graph and
                frozenset((a,c))in graph):
                cosugre = frozenset((v,a,b,c))
                for x in cosugre:
                    result[x].append(cosugre)
    return {k:len(v) for k,v in result.items()}

def color(soup, base_style=BASE_STYLE, get_graph=get_graph, pre_kick=None):
    """Colors the map made of the Placemarks in `soup` and modifies `soup` to
       reflect that by adding Styles and applying them to the Placemarks as
       StyleUrls
       
       `soup` : A bs4.BeautifulSoup parsed from KML
       `base_style` : Valid KML text with two %s substitution sites: one for the
                      color-number and one for an rgb code
       `get_graph` : A callable which is sent the list of Placemarks from `soup`
                     and returns a set of indices into that Placemark list and
                     frozensets of those indices 
       `pre_kick` : An index into the list of Placemarks in `soup`. Act as if
                    that vertex of the graph had been kicked back as a
                    color-clog"""
    kicked_back = [] if pre_kick is None else [pre_kick]
    pms = soup('Placemark')
    graph = Graph(get_graph(pms))
    vert_to_cosugres = _get_map_to_complete_subgraphs(graph)
    while 0 == len(kicked_back) or kicked_back[-1] not in kicked_back[:-1]:
        try:
            return _try_color(
                    soup, pms, graph, vert_to_cosugres,
                    kicked_back, base_style)
        except Clog as e:
            kicked_back.append(int(str(e)))
            print(str(e)+" kicked back")
    print("Coloring with no safeties")
    return _try_color(
            soup, pms, graph, 
            vert_to_cosugres, None, base_style)
