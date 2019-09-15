"""A helper to handle KML files with bs4"""

from bs4.element import CData, NavigableString, Tag
from bs4 import BeautifulSoup

_OPEN = open

REPLACE = {'<': '&lt;',
           '>': '&gt;',
           '&': '&amp;'}

def _as_html(string):
    """Return a copy of `string` where all less-thans, greater-thans, 
       and ampersands are replaced by their HTML character entity equivalents.
       
       `string` : a string"""
    
    for k,v in REPLACE.items():
        string = string.replace(k,v)
    return string

def format(soup):
    """Remove all leading and trailing whitespace on all strings in `soup`, 
       remove all empty or self-terminating tags, remove all kml: prefixes 
       from all tags, and ensure that all CDATA tags are properly wrapped in
       CData objects.
       
       This function modifies the `soup` object.
       
       `soup` : a KML document (bs4.BeautifulSoup)
       
       CDATA in KML gets parsed correctly when read from text, but when that
       CDATA text is put into string representations of the tag it's
       in, it is blindly given HTML entity substitution instead of being
       wrapped in "<![CDATA[...]]>"

       This function hunts down CDATA strings in `soup` and replaces them with
       bs4.element.CData objects so that they print in the "<![CDATA[...]]>"
       form.
       
       A KML document when converted to a string will often "kml:" prefixes on
       every tag. A KML file like that opens perfectly in Google Earth,
       but the Google Maps Javascript API's KmlLayer class insists that those
       make the file an "INVALID_DOCUMENT".

       This function checks every single tag and removes the "kml" prefix if it
       is present.
       
       There is never any reason for whitespace padding at the front or end of
       a string in a tag in a KML document. Similarly, pure-whitespace strings
       have no meaning in a kml document.

       This function checks every string in `soup`, replaces trimmable strings
       with their trimmed counterparts, and outright removes pure-whitespace
       strings.
       
       Empty or self-terminating tags do nothing in a KML document. This
       function checks every tag and removes the empty/self-terminating
       ones."""
    
    strip = []
    destroy = []
    for e in soup.descendants:
        if isinstance(e, NavigableString):
            if e.isspace():
                destroy.append(e) #remove empty strings
            elif e.strip() != e:
                strip.append(e) #trim trimmable strings
        elif isinstance(e, Tag):
            if e.prefix == "kml":
                e.prefix = None #remove kml: prefixes
            if e.string and e.string.parent is e: #.string works indirectly
                e.string = e.string.strip() #trim some trimmable strings
                if any(c in e.string for c in REPLACE):
                    cdata = CData(e.string)
                    if len(str(cdata)) <= len(_as_html(e.string)):
                        e.string = cdata #use CDATA to wrap HTML
    for d in destroy:
        d.extract()
    for s in strip:
        s.replace_with(s.strip())
    for tag in soup(lambda thing : isinstance(thing,Tag) and
                    len(list(thing.contents)) == 0):
        tag.decompose()

def formatted(soup):
    """Format `soup` and return it. Convenience function wrapping `format`.
    
       `soup` : a KML document (bs4.BeautifulSoup)"""
    
    format(soup)
    return soup

def get_data(pm, name):
    """Find a `<Data>` or `<SimpleData>` element in `pm` having the specified
       `name` attribute and return the element's value. Raise ValueError if no
       such data element is found.
       
       `pm` : a KML element (bs4.element.Tag), preferably a Placemark
       `name` : value of the "name' attribute of a data tag in `pm`"""
    if not isinstance(name, str) and hasattr(name, __iter__):
        return [get_data(pm, n) for n in name]
    val = pm.find(lambda tag : tag.name in ('Data','SimpleData') and
                  'name' in tag.attrs and
                  tag['name'] == name)
    if val is not None:
        return (val.value
                if val.name == "Data"
                else val).string.strip()
    raise ValueError("Data/SimpleData not found: name='"+str(name)+"'")

def add(tag, name, soup=None):
    """Create a new `name` tag and append it to `tag`. If `name` is a list,
       append the first name to `tag`, append the second name to the first, and
       so on, which is useful for creating Placemarks, since their geometry
       often looks like <Polygon><outerBoundaryIs><LinearRing><coordinates>...
       </coordinates></LinearRing></outerBoundaryIs></Polygon>

       Return the newly created (or most newly created) child tag."""
    
    soup = soup or (tag
                    if tag.parent is None
                    else next(iter(parent
                                   for parent in tag.parents
                                   if parent.parent is None)))
    if isinstance(name, list):
        pointer = tag
        for n in name:
            pointer = add(pointer, n, soup=soup)
        return pointer
    new = soup.new_tag(name)
    tag.append(new)
    return new

_SOUP_STOCK = ('<?xml version="1.0" encoding="UTF-8"?>'
               '<kml xmlns="http://www.opengis.net/kml/2.2"'
               ' xmlns:gx="http://www.google.com/kml/ext/2.2"'
               ' xmlns:kml="http://www.opengis.net/kml/2.2"'
               ' xmlns:atom="http://www.w3.org/2005/Atom">'
               '<Document>'
               '</Document>'
               '</kml>')

def new_soup(name=None, src=_SOUP_STOCK):
    """Create and return a new KML soup (bs4). This is a convenience method to
       avoid repetitive boilerplate.
       
       `name` : a name to be added to the `<Document>` tag of the soup as the
                text of a `<name>` tag.
       `src` : a string of valid KML text"""
    
    soup = BeautifulSoup(src, 'xml')
    if name is not None:
        add(soup.Document, 'name').string = name
    format(soup)
    return soup

def coords_from_tag(coordinates_tag, first_n_coords=2):
    """Return a list of x,y or x,y,z tuples of points from the string of the
       specified <coordinates> tag.

       `coordinates_tag` : a KML <coordinates> element"""
    return [tuple([float(dim) for dim in chunk.split(',')][:first_n_coords])
            for chunk in coordinates_tag.string.strip().split()]

def open(filepath):
    """Opens the specified file as a KML document (bs4.BeautifulSoup) and
       returns it

       `filepath` : the name of or relative path to a KML file"""
    return formatted(BeautifulSoup(_OPEN(filepath), 'xml'))

def save(soup, filepath):
    """Saves `soup` to a file at `filepath`

       `soup` : a KML document (bs4.BeautifulSoup)
       `filepath` : the name of the file to save"""
    _OPEN(filepath, 'w').write(str(soup))

def dock(soup, decimals=6, dims=2):
    """Reduce the number of digits in the decimal tail of floating point
       figures in <coordinates> tags to at most `decimals`.
       E.g. 10.123456789 -> 10.12345

       `soup` : a KML document (bs4.BeautifulSoup) or element
       `decimals` : the max number of digits allowed after the integer part of
                    a number"""
    import rounding
    for coordinates_tag in soup("coordinates"):
        coordinates_tag.string = ' '.join(
                ','.join(rounding.float(dim, decimals)
                         for dim in chunk.split(',')[:dims])
                for chunk in coordinates_tag.string.strip().split())

def color(soup,
          fuzzy=False,
          probe_factor=1000,
          colorize={1 : '7fa8d7b6',
                    2 : '7f065fb4',
                    3 : '7f4fa86a',
                    4 : '7f6bb2f6'}):
    """Color the polygons of the map with four colors.
       
       `soup` : a KML document (bs4.BeautifulSoup)
       `fuzzy` : If false, only use seamless side sharing (neighboring.seamless)
                 to determine polygons' adjacency, otherwise use fuzzy side
                 sharing (neighboring.fuzzy) as well
       `probe_factor` : Divide the minimum distance between two adjacent
                        vertices on any stokes boundary by this factor to get
                        the length of the line segment crossing the midpoint of
                        any stokes-remaining side used to empirically determine
                        adjacency of polygons from `soup`
       `colorize` : a dict from small ints (colors) to their aabbggrr color
                    codes (without a # symbol)"""

    #Only import these things inside this function so that if these resources
    #are not available, the rest of the script can still work
    from neighboring import fuzzy as _FUZZY
    from neighboring import seamless
    from point_in_polygon import Polygon
    
    #Get a list of the soup's Placemarks in Polygon form
    pms = soup("Placemark")
    
    pm_polygons = [Polygon.from_kml(pms[i], info=i) for i in range(len(pms))]
    
    #describe how the polygons connect to one another by combining the graph
    #of connections based on perfectly shared sides with the graph of
    #connections based on point-in-polygon testing of probe points placed
    #on opposite sides of sides that are not shared between polygons.
    graph = seamless(pm_polygons)

    if fuzzy:
        graph |= _FUZZY(pm_polygons, probe_factor=probe_factor)
    
    #Obtain a coloring of that graph
    coloring = color_graph.color(graph)
    
    #Apply those color assignments as <styleUrl>s and build a set of all
    #applied color styles
    ids = set()
    for i in range(len(pms)):
        pm = pms[i]
        url = f'#color{coloring[i]}'
        (pm.styleUrl or add(pm, 'styleUrl')).string = url
        ids.add(url[1:]) #strip the # symbol off
    
    #Remove all existing Styles or StyleMaps with the same id/url as the
    #styleUrls applied in the previous step
    for style in soup(['Style', 'StyleMap']):
        if 'id' in style.attrs and style['id'] in ids:
            style.decompose()
    
    #Add a Style to the soup for each style id/url used
    for i in ids:
        style = soup.new_tag('Style')
        soup.Document.insert(0, style)
        style['id'] = i
        add(style, ['PolyStyle', 'color']).string = colorize[int(i[-1])]
    
    return

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

STD_EXCEPTIONS = ['styleUrl','visibility','open']

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
