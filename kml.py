"""This is meant to help with using BeautifulSoup (bs4) to parse KML files.

CDATA in KML files gets parsed correctly when read from files, but the fact
that it was marked off as CDATA is forgotten. As such, when that literal text
is incorporated into string representations of the tag it's in, it is blindly
subected to HTML entity substitution instead of being wrapped in a CDATA

When saving a KML document, often the file gets saved with "kml:" prefixes on
every tag. Google Earth parses these perfectly, but the maps JS API KmlLayer
class won't parse that correctly, quietly labeling it as 'INVALID_DOCUMENT' 
within the KmlLayer object.

There is never any reason for whitespace padding at the front or end of a
string in a tag in a KML document to be respected. It should always be 
trimmed.

Pure space strings have no meaning in a kml document; so they should all be
removed.

Empty or self-terminating tags likewise do nothing in a KML document and 
should be removed."""

from bs4.element import CData, NavigableString, Tag
from bs4 import BeautifulSoup

_OPEN = open

REPLACE = {'<': '&lt;',
           '>': '&gt;',
           '&': '&amp;'}

def _as_html(string):
    """Return a copy of `string` where all less-thans, greater-thans, 
    and ampersands are replaced by their HTML character entity equivalents.
    
    `string` a string"""
    
    for k,v in REPLACE.items():
        string = string.replace(k,v)
    return string

def format(soup):
    """Remove all leading and trailing whitespace on all strings in `soup`, 
    remove all empty or self-terminating tags, remove all kml: prefixes 
    from all tags, and ensure that all CDATA tags are properly wrapped in
    CData objects.
    
    This function modifies the soup object.
    
    `soup` a KML soup (bs4)"""
    
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
    
    `soup` a KML soup (bs4)"""
    
    format(soup)
    return soup

def get_data(pm, name):
    """Find a `<Data>` or `<SimpleData>` tag in the specified `<Placemark>` tag 
    having the specified `name` attribute and return its value. Raise ValueError 
    if no such data element is found.
    
    `pm` a Tag (bs4), preferably a Placemark
    `name` value of the name attribute of a data tag in `pm`"""
    
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

_SOUP_STOCK = (
"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"
xmlns:gx="http://www.google.com/kml/ext/2.2"
xmlns:kml="http://www.opengis.net/kml/2.2"
xmlns:atom="http://www.w3.org/2005/Atom">
<Document>
</Document>
</kml>""")

def new_soup(name=None, src=_SOUP_STOCK):
    """Create and return a new KML soup (bs4). This is a convenience method to
       avoid repetitive boilerplate.
       
       `name` a name to be added to the `<Document>` tag of the soup as the
       text of a `<name>` tag.
       `src` kml source text"""
    
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(src, 'xml')
    if name is not None:
        add(soup.Document, 'name').string = name
    format(soup)
    return soup

def coords_from_tag(coordinates_tag, first_n_coords=2):
    """Return a list of x,y or x,y,z tuples of points from the string of the
       specified <coordinates> tag."""
    return [tuple([float(dim) for dim in chunk.split(',')][:first_n_coords])
            for chunk in coordinates_tag.string.strip().split()]

def open(filepath):
    """Opens the specified file as a KML document (bs4.BeautifulSoup) and
       returns it."""
    return formatted(BeautifulSoup(_OPEN(filepath), 'xml'))

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
       class in the Google Maps Javascript API and to eliminate  some
       unnecessary elements that simply waste space, bandwidth, and time in
       that context. Elements are removed or retained based on the value the
       element's name maps to in `KMLLAYER_TAG_SUPPORT` and inverted based on
       that name's presence in `exceptions`.
       
       `soup` the KML soup (bs4) to be processed for use with the KmlLayer
       class in the Google Maps Javascript API
       `exceptions` a list of KML tag names whose removal/retention status
       should be the opposite of what `KMLLAYER_TAG_SUPPORT` indicates.
       Defaults to `STD_EXCEPTIONS` ('styleUrl','visibility','open')
       
       Iterate over every tag in `soup`, remove it and all its descendants if
       it is not supported (or if it is supported but is listed in
       `exceptions`), and move on the next tag if it is supported (or if it is
       not but is listed in `exceptions`)."""
    
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
