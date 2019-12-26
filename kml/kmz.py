import zipfile
from zipfile import ZipFile

from .io import parse as parsekml

def open(filename):
    """Put in a KMZ file's name, get out a KML soup."""
    with ZipFile(filename) as kmz:
        return parsekml(kmz.open(kmz.namelist()[0]))

def save(soup, filename):
    """Save a KML soup as a KMZ file."""
    with ZipFile(filename, mode='w', compression=zipfile.ZIP_DEFLATED) as kmz:
        kmz.writestr('doc.kml', str(soup))

def compress(kmlfile, replace=False):
    """Compress an existing KML file to KMZ. Optionally remove the original."""
    assert kmlfile.endswith('.kml')
    kmzfile = kmlfile[:-3] + 'kmz'
    with ZipFile(kmzfile, mode='w', compression=zipfile.ZIP_DEFLATED) as kmz:
        kmz.write(kmlfile, 'doc.kml')
