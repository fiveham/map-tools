"""Tools for preparing kml documents for use as KmlLayer objects in the
   Google Maps Javascript API.

   The script is named 'layers' so that if you just import kml, then this
   script would be called kml.layers, which closely resembles the name of the
   KmlLayer class."""

def filter_kmllayer(soup, exceptions=STD_EXCEPTIONS):
    """Transform a KML soup (bs4) to ensure compatability with the KmlLayer
       class in the Google Maps Javascript API and to eliminate some
       unnecessary elements that simply waste space, bandwidth, and time in
       that context. Elements are removed or retained based on the value the
       element's name maps to in `KMLLAYER_TAG_SUPPORT` and inverted if that
       name is present in `exceptions`.
       
       `soup` : the KML soup (bs4) to be processed for use with the KmlLayer
                class in the Google Maps Javascript API
       `exceptions` : a list of KML tag names whose removal/retention status
                      should be the opposite of what `KMLLAYER_TAG_SUPPORT`
                      indicates.  Defaults to `STD_EXCEPTIONS`
                      ('styleUrl', 'visibility', 'open')
       
       Iterate over every tag in `soup`. Remove it and all its descendants if
       it is not supported (or if it is supported but is listed in
       `exceptions`)."""
    
    actions = {
         1: (lambda x : None),
        -1: (lambda x : x.decompose())}
    keep = 1
    decomp = -1
    for tag in soup(lambda thing : isinstance(thing,Tag)):
        action = (decomp
                  if (tag.name not in KMLLAYER_TAG_SUPPORT or
                      KMLLAYER_TAG_SUPPORT[tag.name].lower().startswith('n'))
                  else keep)
        if tag.name in exceptions:
            action *= -1
        actions[action](tag)

STD_EXCEPTIONS = ['styleUrl','visibility','open']

#From https://developers.google.com/maps/documentation/javascript/kmllayer
KMLLAYER_TAG_SUPPORT = {
        'address'           : 'no',
        'AddressDetails'    : 'no',
        'Alias'             : 'N/A',
        'altitude'          : 'no',
        'altitudeMode'      : 'no',
        'atom:author'       : 'yes',
        'atom:link'         : 'yes',
        'atom:name'         : 'yes',
        'BalloonStyle'      : 'partially',
        'begin'             : 'N/A',
        'bgColor'           : 'no',
        'bottomFov'         : 'N/A',
        'Camera'            : 'no',
        'Change'            : 'partially',
        'color'             : 'partially',
        'colorMode'         : 'no',
        'cookie'            : 'no',
        'coordinates'       : 'yes',
        'Create'            : 'no',
        'Data'              : 'yes',
        'Delete'            : 'no',
        'description'       : 'yes',
        'displayMode'       : 'no',
        'displayName'       : 'no',
        'Document'          : 'partially',
        'drawOrder'         : 'no',
        'east'              : 'yes',
        'end'               : 'N/A',
        'expires'           : 'yes',
        'ExtendedData'      : 'partially',
        'extrude'           : 'no',
        'fill'              : 'yes',
        'flyToView'         : 'no',
        'Folder'            : 'yes',
        'geomColor'         : 'no',
        'GeometryCollection': 'no',
        'geomScale'         : 'no',
        'gridOrigin'        : 'N/A',
        'GroundOverlay'     : 'yes',
        'h'                 : 'yes',
        'heading'           : 'yes',
        'in'                : 'yes',
        'hotSpot'           : 'yes',
        'href'              : 'yes',
        'httpQuery'         : 'no',
        'Icon'              : 'yes',
        'IconStyle'         : 'yes',
        'ImagePyramid'      : 'N/A',
        'innerBoundaryIs'   : 'yes',
        'ItemIcon'          : 'N/A',
        'key'               : 'N/A',
        'kml'               : 'yes',
        'labelColor'        : 'no',
        'LabelStyle'        : 'no',
        'latitude'          : 'yes',
        'LatLonAltBox'      : 'yes',
        'LatLonBox'         : 'yes',
        'leftFov'           : 'N/A',
        'LinearRing'        : 'yes',
        'LineString'        : 'yes',
        'LineStyle'         : 'yes',
        'Link'              : 'yes',
        'linkDescription'   : 'no',
        'linkName'          : 'no',
        'linkSnippet'       : 'no',
        'listItemType'      : 'N/A',
        'ListStyle'         : 'no',
        'Location'          : 'N/A',
        'Lod'               : 'yes',
        'longitude'         : 'yes',
        'LookAt'            : 'no',
        'maxAltitude'       : 'yes',
        'maxFadeExtent'     : 'yes',
        'maxHeight'         : 'N/A',
        'maxLodPixels'      : 'yes',
        'maxSessionLength'  : 'no',
        'maxWidth'          : 'N/A',
        'message'           : 'no',
        'Metadata'          : 'no',
        'minAltitude'       : 'yes',
        'minFadeExtent'     : 'yes',
        'minLodPixels'      : 'yes',
        'minRefreshPeriod'  : 'no',
        'Model'             : 'no',
        'MultiGeometry'     : 'partially',
        'name'              : 'yes',
        'near'              : 'N/A',
        'NetworkLink'       : 'yes',
        'NetworkLinkControl': 'partially',
        'north'             : 'yes',
        'open'              : 'yes',
        'Orientation'       : 'N/A',
        'outerBoundaryIs'   : 'yes',
        'outline'           : 'yes',
        'overlayXY'         : 'no',
        'Pair'              : 'N/A',
        'phoneNumber'       : 'no',
        'PhotoOverlay'      : 'no',
        'Placemark'         : 'yes',
        'Point'             : 'yes',
        'Polygon'           : 'yes',
        'PolyStyle'         : 'yes',
        'range'             : 'yes',
        'refreshInterval'   : 'partially',
        'refreshMode'       : 'yes',
        'refreshVisibility' : 'no',
        'Region'            : 'yes',
        'ResourceMap'       : 'N/A',
        'rightFov'          : 'N/A',
        'roll'              : 'N/A',
        'rotation'          : 'no',
        'rotationXY'        : 'no',
        'Scale'             : 'N/A',
        'scale'             : 'no',
        'Schema'            : 'no',
        'SchemaData'        : 'no',
        'ScreenOverlay'     : 'yes',
        'screenXY'          : 'no',
        'shape'             : 'N/A',
        'SimpleData'        : 'N/A',
        'SimpleField'       : 'N/A',
        'size'              : 'yes',
        'Snippet'           : 'yes',
        'south'             : 'yes',
        'state'             : 'N/A',
        'Style'             : 'yes',
        'StyleMap'          : 'no',
        'styleUrl'          : 'N/A', #supported in Placemark
        'targetHref'        : 'partially',
        'tessellate'        : 'no',
        'text'              : 'yes',
        'textColor'         : 'no',
        'tileSize'          : 'N/A',
        'tilt'              : 'no',
        'TimeSpan'          : 'no',
        'TimeStamp'         : 'no',
        'topFov'            : 'N/A',
        'Update'            : 'partially',
        'Url'               : 'yes',
        'value'             : 'yes',
        'viewBoundScale'    : 'no',
        'viewFormat'        : 'no',
        'viewRefreshMode'   : 'partially',
        'viewRefreshTime'   : 'yes',
        'ViewVolume'        : 'N/A',
        'visibility'        : 'partially',
        'w'                 : 'yes',
        'west'              : 'yes',
        'when'              : 'N/A',
        'width'             : 'yes',
        'x'                 : 'yes',
        'y'                 : 'yes'}

# =========================================================================== #
# ==== Splitting the map into regions to duck below the file size limits ==== #
# =========================================================================== #

#When a district map is too large to fit the filesize limits for KmlLayers,
#the map may have to be split into two or more parts.  Even then, those parts
#may need to be compressed and fetched as KMZ.

#This script is for those occasions.

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
            neib = tuple(pt[i] + (offset if i==dim else 0)
                         for i in range(len(pt)))
            if not _is_legal(neib,seq):
                continue
            qns.append((_quality(neib,seq),neib))
    return max(qns, key=(lambda a:a[0])) #only compare quality, not neib dims

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
