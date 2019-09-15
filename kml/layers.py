#When a district map is too large to fit the filesize limits for KmlLayers,
#the map may have to be split into two or more parts.  Even then, those parts
#may need to be compressed and fetched as KMZ.

#This script is for just those occasions.

def _extrem_dir(pm, get_dim, comp):
    val = None
    for coord_tag in pm("coordinates"):
        for point in [tuple(float(t)
                            for t in triple.split(','))
                      for triple in coord_tag.string.strip().split()]:
            d = get_dim(point)
            val = d if val is None else comp(d,val)
    return val

def _north(pt):
    return pt[1]

def _east(pt):
    return pt[0]

def max_north(pm):
    return _extrem_dir(pm, _north, max)

def min_north(pm):
    return _extrem_dir(pm, _north, min)

def mid_north(pm):
    lo = min_north(pm)
    hi = max_north(pm)
    return (lo + hi) / 2

def max_east(pm):
    return extrem_dir(pm, _east, max)

def min_east(pm):
    return extrem_dir(pm, _east, min)

def mid_east(pm):
    lo = min_north(pm)
    hi = max_north(pm)
    return (lo + hi) / 2

def count(pms):
    return len(pms)

def characters(pms):
    return sum(len(str(pm)) for pm in pms)

def _coord_string(pms):
    return sum(sum(len(c.string) for c in pm("coordinates")) for pm in pms)

def _is_legal(pt, seq):
    return (0 < pt[0] and
            pt[-1] < len(seq) and
            all(pt[i-1] < pt[i] for i in range(1,len(pt))))

def _weight(partition):
    return sum(e[2] for e in partition)

def _quality(pt,seq):
    markers = [0]+list(pt)+[len(seq)]
    partitioned = [seq[markers[i-1]:markers[i]]
                   for i in range(1,len(markers))]
    weights = [_weight(s) for s in partitioned]
    q = 1
    for w in weights:
        q *= w
    return q

def _best_neighbor(pt,seq):
    qns = []
    for dim in range(len(pt)):
        for offset in (-1,1):
            #neib = list(pt)
            #neib[dim] = pt[dim] + offset
            #neib = tuple(neib)
            neib = tuple(pt[i] + (offset if i==dim else 0)
                         for i in range(len(pt)))
            if not _is_legal(neib,seq):
                continue
            qns.append((_quality(neib,seq),neib))
    q,n = qns[0]
    for i in range(len(qns)):
        w,m = qns[i]
        if w > q:
            q = w
            n = m
    return n

#Split the map defined in a particular KML file into a certain number of pieces
#sequencing the Placemarks by mapping each one onto a number using key.
#measure determines the weight of a given sequence of Placemarks
#preprocess accepts and returns a soup
def split(kml_file_name, piece_count,
          preprocess=None, key=mid_east, measure=count):
    
    from bs4 import BeautifulSoup
    
    if preprocess is None:
        preprocess = lambda x : x
    source = preprocess(BeautifulSoup(open(kml_file_name,'r'),'xml'))
    pms = source("Placemark")
    if piece_count > len(pms):
        raise Exception(
            "Cannot split %d item list into %d pieces" %
            (len(pms),piece_count))
    seq = [(i,key(pms[i]),measure(pms[i])) for i in range(len(pms))]
    seq.sort(key=(lambda t : t[1]))

    #starting point has partitions approx equally spaced. should be near max
    point = tuple(round((len(seq)/piece_count)*i)
                  for i in range(1,piece_count))
    assert _is_legal(point, seq)
    other = _best_neighbor(point, seq)
    while _quality(other,seq) > _quality(point,seq):
        point = other
        other = _best_neighbor(point, seq)
    assert _quality(other,seq) != _quality(point,seq)

    markers = [0]+list(point)+[len(seq)]
    partitioned = [seq[markers[i-1]:markers[i]]
                   for i in range(1,len(markers))]
    part_pms = [[pms[b[0]] for b in a]
                for a in partitioned]
    
    soups = []
    for i in range(len(part_pms)):
        pm_part = part_pms[i]
        soup = preprocess(BeautifulSoup(open(kml_file_name,'r'),'xml'))
        for pm in soup("Placemark"):
            pm.decompose()
        for pm in pm_part:
            soup.Document.append(pm)
        if soup.Document.name is None:
            soup.Document.insert(0, soup.new_tag('name'))
        soup.Document.find('name').string = (kml_file_name[:-4] +
                                             ("_split_%d" % i))
        soups.append(soup)
    return soups
