#This is meant to help with using BeautifulSoup (bs4) to parse KML files.

#CDATA in KML files gets parsed correctly when read from files, but the fact
#that it was marked off as CDATA is forgotten. As such, when that literal text
#is incorporated into string representations of the tag it's in, it is blindly
#subected to HTML entity substitution instead of being wrapped in a CDATA

#When saving a KML document, often the file gets saved with "kml:" prefixes on
#every tag. Google Earth parses these perfectly, but the maps JS API KmlLayer
#class just gives up and renders nothing if you give it the URL of a KML file
#that's all prefixed like that.

#There is never any reason for whitespace padding at the front or end of a
#literal string in a tag in a KML document to be respected. It should always
#be trimmed.

#Pure space strings have no meaning in a kml document; so they should all be
#removed

from bs4.element import CData, NavigableString, Tag

REPLACE = {'<': '&lt;',
           '>': '&gt;',
           '&': '&amp;'}

def _as_html(string):
    for k,v in REPLACE.items():
        string = string.replace(k,v)
    return string

#Remove all pure-whitespace strings from soup
#Trim all remaining strings in soup
#Remove all 'kml' prefixes
#Remove all empty elements e.g. <ExtendedData/>
#Wrap all remaining strings containing HTML-replaceable chars with CDATA
def format(soup):
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
        

#format the parsed file, then return it
def formatted(soup):
    format(soup)
    return soup

#Find a data element by name and return its value
def get_data(pm, name):
    val = pm.find(lambda tag : tag.name in ('Data','SimpleData') and
                  'name' in tag.attrs and
                  tag['name'] == name)
    if val is not None:
        return (val.value
                if val.name == "Data"
                else val).string.strip()
    raise ValueError("Data/SimpleData not found: name='"+str(name)+"'")

def add(tag, name, soup=None):
    soup = soup or (tag
                    if tag.parent is None
                    else soup = next(iter(parent
                                          for parent in tag.parents
                                          if parent.parent is None)))
    if isinstance(name, list):
        pointer = tag
        for n in name:
            pointer = add(tag, n, soup=soup)
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
</kml>"""

def new_soup(src=_SOUP_STOCK, name=None):
    soup = BeautifulSoup(src, 'xml')
    if name is not None:
        add(soup.Document, 'name').string = name
    format(soup)
    return soup

#From https://developers.google.com/maps/documentation/javascript/kmllayer
KMLLAYER_TAG_SUPPORT = {'address': 'no',
                        'AddressDetails': 'no',
                        'Alias': 'N/A',
                        'altitude': 'no',
                        'altitudeMode': 'no',
                        'atom:author': 'yes',
                        'atom:link': 'yes',
                        'atom:name': 'yes',
                        'BalloonStyle': 'partially',
                        'begin': 'N/A',
                        'bgColor': 'no',
                        'bottomFov': 'N/A',
                        'Camera': 'no',
                        'Change': 'partially',
                        'color': 'partially',
                        'colorMode': 'no',
                        'cookie': 'no',
                        'coordinates': 'yes',
                        'Create': 'no',
                        'Data': 'yes',
                        'Delete': 'no',
                        'description': 'yes',
                        'displayMode': 'no',
                        'displayName': 'no',
                        'Document': 'partially',
                        'drawOrder': 'no',
                        'east': 'yes',
                        'end': 'N/A',
                        'expires': 'yes',
                        'ExtendedData': 'partially',
                        'extrude': 'no',
                        'fill': 'yes',
                        'flyToView': 'no',
                        'Folder': 'yes',
                        'geomColor': 'no',
                        'GeometryCollection': 'no',
                        'geomScale': 'no',
                        'gridOrigin': 'N/A',
                        'GroundOverlay': 'yes',
                        'h': 'yes',
                        'heading': 'yes',
                        'in': 'yes',
                        'hotSpot': 'yes',
                        'href': 'yes',
                        'httpQuery': 'no',
                        'Icon': 'yes',
                        'IconStyle': 'yes',
                        'ImagePyramid': 'N/A',
                        'innerBoundaryIs': 'yes',
                        'ItemIcon': 'N/A',
                        'key': 'N/A',
                        'kml': 'yes',
                        'labelColor': 'no',
                        'LabelStyle': 'no',
                        'latitude': 'yes',
                        'LatLonAltBox': 'yes',
                        'LatLonBox': 'yes',
                        'leftFov': 'N/A',
                        'LinearRing': 'yes',
                        'LineString': 'yes',
                        'LineStyle': 'yes',
                        'Link': 'yes',
                        'linkDescription': 'no',
                        'linkName': 'no',
                        'linkSnippet': 'no',
                        'listItemType': 'N/A',
                        'ListStyle': 'no',
                        'Location': 'N/A',
                        'Lod': 'yes',
                        'longitude': 'yes',
                        'LookAt': 'no',
                        'maxAltitude': 'yes',
                        'maxFadeExtent': 'yes',
                        'maxHeight': 'N/A',
                        'maxLodPixels': 'yes',
                        'maxSessionLength': 'no',
                        'maxWidth': 'N/A',
                        'message': 'no',
                        'Metadata': 'no',
                        'minAltitude': 'yes',
                        'minFadeExtent': 'yes',
                        'minLodPixels': 'yes',
                        'minRefreshPeriod': 'no',
                        'Model': 'no',
                        'MultiGeometry': 'partially',
                        'name': 'yes',
                        'near': 'N/A',
                        'NetworkLink': 'yes',
                        'NetworkLinkControl': 'partially',
                        'north': 'yes',
                        'open': 'yes',
                        'Orientation': 'N/A',
                        'outerBoundaryIs': 'yes',
                        'outline': 'yes',
                        'overlayXY': 'no',
                        'Pair': 'N/A',
                        'phoneNumber': 'no',
                        'PhotoOverlay': 'no',
                        'Placemark': 'yes',
                        'Point': 'yes',
                        'Polygon': 'yes',
                        'PolyStyle': 'yes',
                        'range': 'yes',
                        'refreshInterval': 'partially',
                        'refreshMode': 'yes',
                        'refreshVisibility': 'no',
                        'Region': 'yes',
                        'ResourceMap': 'N/A',
                        'rightFov': 'N/A',
                        'roll': 'N/A',
                        'rotation': 'no',
                        'rotationXY': 'no',
                        'Scale': 'N/A',
                        'scale': 'no',
                        'Schema': 'no',
                        'SchemaData': 'no',
                        'ScreenOverlay': 'yes',
                        'screenXY': 'no',
                        'shape': 'N/A',
                        'SimpleData': 'N/A',
                        'SimpleField': 'N/A',
                        'size': 'yes',
                        'Snippet': 'yes',
                        'south': 'yes',
                        'state': 'N/A',
                        'Style': 'yes',
                        'StyleMap': 'no',
                        'styleUrl': 'N/A', #supported in Placemark
                        'targetHref': 'partially',
                        'tessellate': 'no',
                        'text': 'yes',
                        'textColor': 'no',
                        'tileSize': 'N/A',
                        'tilt': 'no',
                        'TimeSpan': 'no',
                        'TimeStamp': 'no',
                        'topFov': 'N/A',
                        'Update': 'partially',
                        'Url': 'yes',
                        'value': 'yes',
                        'viewBoundScale': 'no',
                        'viewFormat': 'no',
                        'viewRefreshMode': 'partially',
                        'viewRefreshTime': 'yes',
                        'ViewVolume': 'N/A',
                        'visibility': 'partially',
                        'w': 'yes',
                        'west': 'yes',
                        'when': 'N/A',
                        'width': 'yes',
                        'x': 'yes',
                        'y': 'yes'}

STD_EXCEPTIONS = ['styleUrl','visibility','open']

def filter_kmllayer(soup, exceptions=STD_EXCEPTIONS):
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
