from bs4.element import CData, NavigableString, Tag
from bs4 import BeautifulSoup

_OPEN = open

def open(filepath, encoding=None):
    """Read `filepath` and parse it as a KML document (bs4.BeautifulSoup).
       
       :param filepath: the name of or relative path to a KML file
       :param encoding: optional character encoding (rarely needed)
       :returns: a formatted KML document
       """
    return formatted(BeautifulSoup(_OPEN(filepath, encoding=encoding),
                                   'xml'))

def parse(filetext):
    """Parse `filetext` as a KML document.

       :param filetext: Either valid XML or a file-like object"""
    return formatted(BeautifulSoup(filetext, 'xml'))

def save(soup, filepath):
    """Save `soup` to a file at `filepath`.

       :param soup: a KML document (bs4.BeautifulSoup)
       :param filepath: the name of the file to save
       :returns: None
       """
    _OPEN(filepath, 'w').write(str(soup))

def format(soup, no_empty=False):
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
       ones.

       :param soup: a KML document (bs4.BeautifulSoup)

       :param no_empty: if True, remove empty tags. Default False.

       :returns: None
       """
    
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
    if no_empty:
        for tag in soup(lambda thing : isinstance(thing,Tag) and
                        len(list(thing.contents)) == 0):
            tag.decompose()

def formatted(soup, **kwargs):
    """Format `soup` and return it. Convenience function wrapping `format`.
    
       :param soup: a KML document (bs4.BeautifulSoup)
       :param no_empty: (optional, default False) remove empty tags if True
       :returns: `soup`
       """
    
    format(soup, **kwargs)
    return soup

REPLACE = {'<': '&lt;',
           '>': '&gt;',
           '&': '&amp;'}

def _as_html(string):
    """Return a copy of `string` where all less-thans, greater-thans, 
       and ampersands are replaced by their HTML character entity equivalents.
       
       :param string: a string
       :returns: a string where certain chars are replaced by html entity codes
       """
    
    for k,v in REPLACE.items():
        string = string.replace(k,v)
    return string
