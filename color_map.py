#Given a kml file of districts, assuming that the districts together form a
#single connected region and that the border between any two adjacent regions
#is defined using the same points in both regions, color the regions using at
#most four colors, represented by the numbers 1 through 4.

COLORS = {1,2,3,4}

BASE_STYLE = ('<Style id="color%d"><PolyStyle><color>7f%s</color></PolyStyle>'
            '<LineStyle><color>7f666666</color></LineStyle></Style>')

#kml does colors in aabbggrr order instead of aarrggbb
COLOR_CODES = [(1, 'a8d7b6'), (2, '065fb4'), (3, '6bb2f6'), (4, '4fa86a')]

class Supply:
    def __init__(self, size=1):
        if not isinstance(self, int) or size < 1:
            size = 1
        self.levels = {color:size for color in COLORS}

    def most(self, colors):
        cm = {color:self.levels[color] for color in colors}
        demand = max(cm.values())
        result = set(color for color,v in cm.items() if demand == v)
        return result

    def take(self, color):
        self.levels[color] = self.levels[color] - 1
        while any(x < 1 for x in self.levels.values()):
            for c in self.levels:
                self.levels[c] = 1 + self.levels[c]
        return color

    def check(self, color):
        return self.levels[color]

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
def _uncolored(neighbors, coloring, supply, kicked_back):
    if kicked_back and coloring[kicked_back[-1]] == 0:
        return kicked_back[-1]
    max_color_constraint = 0
    vertices = []
    for index,ns in neighbors.items():
        if coloring[index] != 0:
            continue
        color_constraint = len({c
                                for c in (coloring[n]
                                          for n in ns)
                                if c != 0})
        if color_constraint > max_color_constraint:
            max_color_constraint = color_constraint
            vertices = []
        if color_constraint == max_color_constraint:
            vertices.append(index)

    min_uncolored_neighbors = len(neighbors)
    new_verts = []
    for vert in vertices:
        uncolored_neighbors = sum(1
                                  for n in neighbors[vert]
                                  if coloring[n] == 0)
        if uncolored_neighbors < min_uncolored_neighbors:
            min_uncolored_neighbors = uncolored_neighbors
            new_verts = []
        if uncolored_neighbors == min_uncolored_neighbors:
            new_verts.append(vert)
    vertices = new_verts
    del new_verts

    max_max_supply = 0
    new_verts = []
    for vert in vertices:
        illegal_colors = {c
                          for c in (coloring[n]
                                    for n in ns)
                          if c != 0}
        max_supply = max(supply.check(color)
                         for color in (COLORS - illegal_colors))
        if max_supply > max_max_supply:
            max_max_supply = max_supply
            new_verts = []
        if max_supply == max_max_supply:
            new_verts.append(vert)

    return min(new_verts)

class Clog(Exception):
    pass

#Transform and return soup, add Style tag for each color, assign styleUrl to
#each Placemark to map it to its assigned color.
def _try_color(soup, kicked_back):
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
            if kicked_back is not None:
                raise Clog(str(i))
            else:
                pass

        #dirty hack
        if not legal_colors:
            legal_colors = set(COLORS)
            print('Coloring illegally on purpose. (%d)'%i)
        #end dirty hack
        
        ms_colors = supply.most(legal_colors)
        color = min(ms_colors)
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

    #Apply chosen coloring dict to the soup
    #Add the Styles to the soup.
    #Remove preexisting Styles with the same ids.
    #Change each Placemark's styleUrl to correspond to the color chosen
    #    for that Placemark
    from bs4 import BeautifulSoup
    styles = [BeautifulSoup(BASE_STYLE % (a,b), 'xml') for a,b in COLOR_CODES]
    for style in reversed(styles):
        incumbents = soup.Document(lambda tag :
                                   (tag.name == "Style" and
                                    'id' in tag.attrs and
                                    tag['id'] == style.Style['id']))
        for incumbent in incumbents:
            incumbent.decompose()
        soup.Document.find("name").insert_after(style.Style)
    for i,color in coloring.items():
        pms[i].styleUrl.string = "#color%d" % color
    
    return coloring

def color(soup):
    kickbacks = []
    while 0 == len(kickbacks) or kickbacks[-1] not in kickbacks[:-1]:
        try:
            return _try_color(soup, kickbacks)
        except Clog as e:
            kickbacks.append(int(str(e)))
            print(str(e)+" kicked back")
    return _try_color(soup, None)
