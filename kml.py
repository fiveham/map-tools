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

from bs4.element import (CData, NavigableString, Tag)

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

