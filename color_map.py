#Given a kml file of districts, assuming that the districts together form a
#single connected region and that the border between any two adjacent regions
#is defined using the same points in both regions, color the regions using at
#most four colors, represented by the numbers 1 through 4.

from collections import Counter

COLORS = {1,2,3,4}

BASE_STYLE = ('<Style id="color%d"><PolyStyle><color>7f%s</color></PolyStyle>'
            '<LineStyle><color>7f666666</color></LineStyle></Style>')

THICK_WHITE_BORDER = ('<Style id="color%d"><PolyStyle><color>7f%s</color>'
                      '</PolyStyle><LineStyle><color>99ffffff</color>'
                      '<width>3</width></LineStyle></Style>')

#kml does colors in aabbggrr order instead of aarrggbb
COLOR_CODES = [(1, 'a8d7b6'), (2, '065fb4'), (3, '6bb2f6'), (4, '4fa86a')]

class Supply(Counter):
    def __init__(self, size=1):
        if not isinstance(size, int) or size < 1:
            size = 1
        super(Supply, self).__init__()
        for color in COLORS:
            self[color] = size
    
    def most(self, colors):
        as_dict = {c:self[c] for c in colors}
        target = max(as_dict.values())
        return {color for color,count in as_dict.items() if count == target}
    
    def take(self, color):
        self[color] -= 1
        while any(v < 1 for v in self.values()):
            for c in self:
                self[c] += 1
        return color

def get_graph(pms):
    #Map from each boundary segment (edge) to the placemarks (ids) that have
    #that edge on their boundary
    edge_to_pms = {}
    for i in range(len(pms)):
        pm = pms[i]
        for c in pm("coordinates"):
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

#Identify and return the best possible vertex of the graph for coloring
#It must be uncolored as yet, must be maximally color-constrained,
#must have the least possible count of uncolored neighbors, and
#must have the highest extant supply level among its legal colors
#
# A. Start with a list of all the vertices.
# B. Narrow that list down to the vertices that have the fewest options for
#    what color they can become.
# C. Narrow that list down further to those that also have the fewest uncolored
#    neighbors--those that will have the least impact on the rest of the graph
#    when colored.
# D. Narrow that list down even further to those vertices whose most-in-supply
#    possible color is the most in-supply color in the aggregate among the
#    vertices in the list.
# E. Return whichever vertex from that list came earliest in the original file.
#
#NOTE: Due to changes made while debugging, this function currenty only does
#      steps A, B, and E from the list above.
def _uncolored(neighbors, coloring, supply, kicked_back):
    for avail_color_count in range(1,5):
        verts = set()
        for v in neighbors:
            my_color = coloring[v]
            if my_color == 0:
                my_neighbors = neighbors[v]
                neighboring_colors = {coloring[my_neighbor]
                                      for my_neighbor in my_neighbors}
                available_colors = COLORS - neighboring_colors
                if avail_color_count == len(available_colors):
                    return v
    raise Exception("It shouldn't be possible to reach this point.")

class Clog(Exception):
    pass

#Transform and return soup, add Style tag for each color, assign styleUrl to
#each Placemark to map it to its assigned color.
def _try_color(soup, kicked_back, base_style, get_graph):
    #use index as id for each placemark
    pms = soup("Placemark")
    graph = get_graph(pms)
    
    #Figure out who shares a border with who so we can get that info in O(1)
    #time when needed instead of O(len(graph)) time each time
    neighbors = {i:set() for i in range(len(pms))}
    for edge in (thing for thing in graph if isinstance(thing,frozenset)):
        a,b = edge
        neighbors[a].add(b)
        neighbors[b].add(a)

    #Assign initial colors
    coloring = {i:0 for i in range(len(pms))}
    supply = Supply(len(pms)//4)
    for pm in pms:
        i = _uncolored(neighbors, coloring, supply, kicked_back)
        illegal_colors = {coloring[n] for n in neighbors[i]} 
        legal_colors = COLORS - illegal_colors

        try:
            assert legal_colors
        except AssertionError:
            if kicked_back is not None: #part of the dirty hack below
                raise Clog(str(i))
            else:
                pass #part of the dirty hack below

        #dirty hack
        if not legal_colors:
            legal_colors = set(COLORS)
            print('Coloring illegally on purpose. (%d)'%i)
        #end dirty hack
        
        most_supplied_legal_colors = supply.most(legal_colors)
        color = min(most_supplied_legal_colors)
        coloring[i] = supply.take(color)

    #Print warnings about problems as a stand-in for now
    illegals = False
    for edge in (thing for thing in graph if isinstance(thing,frozenset)):
        a,b = edge
        if coloring[a] == coloring[b]:
            print("Illegal color-sharing: %d %s"%(coloring[a],str(edge)))
            illegals = True
    else:
        if not illegals:
            print("No illegal color-sharing.")
    print("Parity status (%d): %s"%(len(neighbors),
                                    str([sum(1
                                             for color in coloring.values()
                                             if color == x)
                                         for x in COLORS])))

    #Apply chosen coloring dict to the Placemarks in the soup.
    #Add the Styles to the soup.
    #But first, remove preexisting Styles with the same ids.
    #Change each Placemark's styleUrl to correspond to the color chosen for that
    #Placemark.
    from bs4 import BeautifulSoup
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
        u = pms[i].styleUrl
        if not u:
            import kml
            u = kml.add(pms[i], 'styleUrl')
        u.string = "#color%d" % color
    
    return coloring

def color(soup, base_style=BASE_STYLE, get_graph=get_graph):
    kickbacks = []
    while 0 == len(kickbacks) or kickbacks[-1] not in kickbacks[:-1]:
        try:
            return _try_color(soup, kickbacks, base_style, get_graph)
        except Clog as e:
            kickbacks.append(int(str(e)))
            print(str(e)+" kicked back")
    print("trying with no safeties")
    return _try_color(soup, None, base_style, get_graph)
