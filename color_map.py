#Given a kml file of districts, assuming that the districts together form a
#single connected region and that the border between any two adjacent regions
#is defined using the same points in both regions, color the regions using at
#most four colors, represented by the numbers 1 through 4.

COLORS = {1,2,3,4}

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
def uncolored(neighbors, coloring, supply):
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

#Transform and return soup, add Style tag for each color, assign styleUrl to
#each Placemark to map it to its assigned color.
def color(soup):
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
        i = uncolored(neighbors, coloring, supply)
        illegal_colors = {coloring[n] for n in neighbors[i]}
        legal_colors = COLORS - illegal_colors

        #TODO dirty hack
        if not legal_colors:
            legal_colors = set(COLORS)
            print('Coloring illegally on purpose.')
        #end dirty hack
        
        ms_colors = None
        try:
            ms_colors = supply.most(legal_colors)
        except ValueError:
            print("i = %d"%i)
            print("neighbors[i] = %s"%str(neighbors[i]))
            print("illegal_colors = %s"%str(illegal_colors))
            print("legal_colors = %s"%str(legal_colors))
            print("coloring = %s"%str(coloring))
            raise
        
        color = min(ms_colors)
        coloring[i] = supply.take(color)

    #Maybe tweak the colorings to ensure color-parity as well as legality?

    #Print warnings about problems as a stand-in for now
    for edge in (thing for thing in graph if isinstance(thing,frozenset)):
        a,b = edge
        if coloring[a] == coloring[b]:
            print("Illegal color-sharing: %d %s"%(coloring[a],str(edge)))
    print("Parity status (%d): %s"%(len(neighbors),
                                    str([sum(1
                                             for color in coloring.values()
                                             if color == x)
                                         for x in COLORS])))

    return coloring #TODO actually modify the kml soup like I said I would
