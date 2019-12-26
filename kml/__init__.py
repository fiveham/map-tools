"""A helper to handle KML files as bs4.BeautifulSoup XML documents."""

import itertools

from shapefile import signed_area

import color_graph
import rounding
import spindex as sx
import stokes as _STOKES

from neighboring import fuzzy, seamless
from point_in_polygon import Polygon
from stokes import _sides

from . import kmz
from . import layers

from .io import _OPEN, open, parse, save, format, formatted

def get_data(pm, name=None):
    """Find a `<Data>` or `<SimpleData>` element in `pm` having the specified
       `name` attribute and return the element's value. Raise ValueError if no
       such data element is found.
       
       :param pm: a KML element (bs4.element.Tag), preferably a Placemark
       :param name: value of the "name' attribute of a data tag in `pm`, or
       None to return all data as a dict
       :returns: the Placemark's data with the specified `name` or a dict of
       all the Placemark's data"""
    if name is None:
        names = [d['name']
                 for d in pm(lambda tag :
                             tag.name in ('Data', 'SimpleData') and
                             'name' in tag.attrs)]
        values = get_data(pm, names)
        pairs = list(zip(names, values))
        dic = {x:y for x,y in pairs}
        return dic if len(dic) == len(pairs) else pairs
    elif not isinstance(name, str) and hasattr(name, '__iter__'):
        return [get_data(pm, n) for n in name]
    val = pm.find(lambda tag : tag.name in ('Data','SimpleData') and
                  'name' in tag.attrs and
                  tag['name'] == name)
    if val is not None:
        string = (val.value if val.name == 'Data' else val).string
        return '' if string is None else string.strip()
    raise ValueError("Data/SimpleData not found: name='"+str(name)+"'")

def add(tag, name, soup=None):
    """Append a new `name` tag to `tag` and return the new tag.

       If `name` is a list, call this function to add the first name to `tag,
       then call this function to add the second name onto the tag returned
       from the prior call to this function, and so on like that. Ultimately,
       the last tag added/created will be returned.

       Sending a list as `name` is useful, for example, for Polygon elements:
       <Polygon><outerBoundaryIs><LinearRing><coordinates> ...
       </coordinates></LinearRing></outerBoundaryIs></Polygon>

       add(pm, ['Polygon','outerBoundaryIs','LinearRing','coordinates'])
       is much nicer than
       add(add(add(add(pm,'Polygon'),'outerBoundaryIs'),'LinearRing'),'coordinates')

       :param tag: a bs4.element.Tag or a bs4.BeautifulSoup
       :param name: a string name for a Tag or a list of strings
       :param soup: (optional) a BeautifulSoup used to create new Tags
       :returns: the added Tag or the final added Tag
       """

    if soup is None:
        if tag.name == '[document]':
            soup = tag
        else:
            try:
                soup = next(iter(parent for parent in tag.parents
                                 if parent.name == '[document]'))
            except StopIteration:
                raise TypeError(
                        'soup cannot be None if tag is not part of a soup')
    
    if isinstance(name, (list, tuple)):
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
    """Create and return a new KML document (bs4.BeautifulSoup).
       
       :param name: a name for the kml document, added in a `<name>` tag
       :param src: a string of valid KML text
       :returns: a newly created and formatted bs4.BeautifulSoup
       """
    
    soup = BeautifulSoup(src, 'xml')
    if name is not None:
        add(soup.Document, 'name').string = name
    format(soup)
    return soup

def coords_from_tag(coordinates_tag, first_n_coords=2):
    """Return a list of points from `coordinates_tag.string`.

       :param coordinates_tag: a KML <coordinates> element (bs4.element.Tag)
       :param first_n_coords: only convert this many dimensions per point
       :returns: a list of tuples of floats
       """
    
    return [tuple([float(dim)
                   for dim in chunk.split(',')][:first_n_coords])
            for chunk in coordinates_tag.string.strip().split()]

def coords_to_text(boundary):
    """Return a text representation of the boundary or single point.
       
       :param boundary: a list of points or a single point
       :returns: text like '2.8675309,-90.4000001 1.984,3.14'
       
       This is a convenience method for constructing kml elements as text to
       be written directly to a file.
       """
    
    try:
        return ' '.join(','.join(str(dim)
                                 for dim in point)
                        for point in boundary)
    except TypeError: #boundary is a point, not a list of points
        return ','.join(str(dim) for dim in point)

def _new_tuples(dims, decimals, coordinates_tag):
    """Yield individual docked coordinate tuples but not immediate duplicates.

       Convert the coordinate string from `coordinates_tag` into a list of
       coordinate tuples, truncate each dimension of each of those tuples, and
       yield that truncated tuple only if the previous yielded value (if there
       is one) is different.

       By checking for duplicate adjacent values, a small amount of extra space
       can be saved on top of the space-savings associated with decimal
       truncation.

       :param dims: number of dimensions to retain per tuple
       :param decimals: number of digits after the decimal point to keep
       :coordinates_tag: a <coordinates> KML tag (bs4.element.Tag)
       :returns: a generator
       """
    
    prev_yield = None
    for chunk in coordinates_tag.string.strip().split():
        new_chunk = ','.join(rounding.float(dim, decimals)
                             for dim in chunk.split(',')[:dims])
        if new_chunk != prev_yield:
            prev_yield = new_chunk
            yield new_chunk

def dock(soup, decimals=6, dims=2):
    """Limit the decimal part of floats in `<coordinates>` tags.

       The function mainly exists to help limit the size of files to be used
       with KmlLayers in the Google Maps JS API.

       Unite adjacent duplicate points.
       
       :param soup: a KML document (bs4.BeautifulSoup) or element
       (bs4.element.Tag)
       :param decimals: the max number of digits allowed after the integer
       part of a number
       :returns: None
       """
    for coordinates_tag in soup("coordinates"):
        coordinates_tag.string = ' '.join(_new_tuples(dims,
                                                      decimals,
                                                      coordinates_tag))

def stokes(layer):
    """Convenience method to check for open seams before coloring.

       :param layer: a KML document or Folder (bs4.BeautifulSoup) describing a
       single layer of polygons on the Earth's surface.
       :returns: a list of the net boundaries of the polygons of `layer`
       """

    if isinstance(layer, list):
        obis = itertools.chain.from_iterable(pm('outerBoundaryIs')
                                             for pm in layer)
        ibis = itertools.chain.from_iterable(pm('innerBoundaryIs')
                                             for pm in layer)
    else:
        obis = layer('outerBoundaryIs')
        ibis = layer('innerBoundaryIs')
                        
    
    outers = [coords_from_tag(coord_tag)
              for coord_tag in itertools.chain.from_iterable(
                      obi('coordinates') for obi in obis)]
    outers = [x if signed_area(x) >= 0 else list(reversed(x)) for x in outers]
    inners = [coords_from_tag(coord_tag)
              for coord_tag in itertools.chain.from_iterable(
                      ibi('coordinates') for ibi in ibis)]
    inners = [x if signed_area(x) < 0 else list(reversed(x)) for x in inners]
    return _STOKES.stokes(itertools.chain(outers, inners))

def stokes_visualize(stoked_bounds):
    """Visualize complex stokes output as a kml document (bs4.BeautifulSoup).

       :param stoked_bounds: boundaries from stokesing a set of boundaries
       :returns: a kml document (bs4.BeautifulSoup) of the boundaries.

       Use this function to visualize complex stokes output when there are
       a lot of open or overlapping seams, polygons that share no sides with
       the polygons around them that they obviously should share sides with,
       or any other reason to need a human-style intuitive view of the bounds
       that resulted from stokes.stokes or kml.stokes.
       """
    soup = new_soup()
    for bound in stoked_bounds:
        pm = add(soup.Document, 'Placemark')
        add(pm, 'name').string = str(len(bound))
        add(pm,
            ['LinearRing', 'coordinates']
            ).string = coords_to_text(bound)
    return soup

def stokes_audit(layer, bounds):
    """Map from each bound to the Placemarks that could have contributed to it.

       Return a list of lists of Placemark elements in the same order as the
       bounds in `bounds`.

       :param layer: a kml document (bs4.BeautifulSoup) or Folder
       :param bounds: a list of lists of points (tuple/list of 2 or 3 floats)
       """
    
    pms = layer('Placemark')
    pm_sides = [set(itertools.chain.from_iterable(
            _sides(coords_from_tag(coord_tag))
            for coord_tag in pm('coordinates')))
                for pm in pms]
    
    bound_sides = [set(_sides(bound)) for bound in bounds]
    
    return [[pm
             for j, pm in enumerate(pms)
             if pm_sides[j] & bound_sides[i]]
            for i in range(len(bounds))]

def adjacency(layer, sorter=None, scale=None, probe_factor=1000):
    """Return an adajcency graph for the Placemarks of the layer.

       :param layer: a KML document or Folder
       :param sorter: function accepting a Placemark element, returning an int
       :param scale: (optional) exponential scale of spatial index mesh size.
       If None (default), fuzzy adjacency is not assessed
       :param probe_factor: divide the length of a side by twice this to get
       the distance from the side's midpoint to either probe point for that
       side
       :returns: a set of ints (vertices) and frozensets of two ints (edges)
       """
    
    pms = layer("Placemark")
    if sorter is not None:
        pms.sort(key=sorter)
    pm_polygons = [Polygon.from_kml(pms[i], info=i) for i in range(len(pms))]
    graph = seamless(pm_polygons)
    if scale is not None:
        graph |= fuzzy(pm_polygons, probe_factor=probe_factor, scale=scale)
    return graph

_GREEN_ORANGE = {1 : '7fa8d7b6',
                 2 : '7f065fb4',
                 3 : '7f4fa86a',
                 4 : '7f6bb2f6'}

_BLURPGRELLOW = {
        1 : 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png',
        2 : 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png',
        3 : 'http://maps.google.com/mapfiles/kml/paddle/grn-circle.png',
        4 : 'http://maps.google.com/mapfiles/kml/paddle/purple-circle.png'}

def color(layer,
          scale=None,
          probe_factor=1000,
          colorize=_GREEN_ORANGE,
          icons=_BLURPGRELLOW):
    """Color the polygons of the map with four colors.
       
       :param layer: a KML document or Folder (bs4.BeautifulSoup)
       
       :param scale: If specified, the scale of the lat-long mesh used to index
       the space around the placemarks in `layer` when determining fuzzy
       neighbors. If not specified, fuzzy neighbor relationship are not
       assessed and only seamless neighbors are used to determine the coloring
       graph. The scale if specified is the exponent of two in the denominator
       by which the 360 degrees of width and 180 degrees of height of the
       earth's surface are divided to determine the boundaries of the cells
       of the indexing mesh.
       
       :param probe_factor: Divide the minimum distance between two adjacent
       vertices on any stokes boundary by this factor to get the length of the
       line segment crossing the midpoint of any stokes-remaining side used to
       empirically determine adjacency of polygons from `layer`. Used only for
       fuzzy neighbor assessment.
       
       :param colorize: a dict from small ints (colors) to their aabbggrr
       color codes (without a # symbol)

       :param icons: a dict from colors to the urls of icons
       :returns: None
       """
    
    graph = adjacency(layer, scale=scale, probe_factor=probe_factor)
    coloring = color_graph.color(graph)
    apply_color(layer, coloring, colorize=colorize, icons=icons)
    return

def apply_color(layer, coloring, colorize=_GREEN_ORANGE, icons=_BLURPGRELLOW):
    """Apply the coloring to the Placemarks in `layer` in order.

       Each Placemark element in `layer` is given a styleUrl based on its
       position in sequence in `layer` (its index in the list returned by
       `layer('Placemark')`) and the color to which that position maps in
       `coloring`. The string of the styleUrl is '#color' followed by the
       number (1 through 4) to which the Placemark's position maps.

       :param layer: a KML document or Folder (bs4.BeautifulSoup)
       :param coloring: a dict from ints starting at 0 to colors (int 1 to 4)
       :param colorize: a dict from color (int 1 to 4) to aabbggrr color
       :param icons: dict from color (int 1 to 4) to icon url
       :returns: None
       """
    
    pms = layer("Placemark")
    
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
    soup = next(iter(parent
                     for parent in layer.parents
                     if (parent is not None) and (parent.parent is None)),
                layer)
    for style in soup(['Style', 'StyleMap']):
        if style.has_attr('id') and style['id'] in ids:
            style.decompose()
    
    #Add a Style to the soup for each style id/url used
    for i in sorted(ids):
        style = soup.new_tag('Style')
        soup.Document.insert(0, style)
        style['id'] = i
        add(style, ['PolyStyle', 'color']).string = colorize[int(i[-1])]
        add(style, ['LineStyle', 'color']).string = '00cccccc'
        add(style, ['IconStyle', 'Icon', 'href']).string = icons[int(i[-1])]
    
    return

##def anneal_styles(soup):
##    """Remove unused styles. Force Styles over StyleMaps. Share styles."""
##    used_style_urls = set()
##    for pm in soup('Placemark'):
##        s = pm.styleUrl
##        if s is None:
##            continue
##        u = s.string.strip()
##        if u:
##            used_style_urls.append(u[1:]) #trim # at start
##    styles = soup(['Style', 'StyleMap'])
##    used_styles = [style for style in styles if style['id'] in used_style_urls]
##    for stylemap in [style for style in used_styles if style.name == 'StyleMap']:
##        map_urls = {su.string.strip()[1:] for su in stylemap('styleUrl')}
##        used_styles.extend(style
##                           for style in styles
##                           if (style['id'] in map_urls and
##                               style not in used_styles))
    
    

def spatial_index(soup, scale=16):
    """Return a dict from rectangles on Earth to Placemarks that intersect them.
       
       If you have a large number of points and a large number of polygons and
       you need to figure out which points are in which polygons, it can take
       an extremely long time to do all the point-in-polygon tests required.
       But by organizing the polygons according to the regions of space they
       sit in the list of potential containing polygons for a given point can
       be drastically reduced.

       So this function cooks up a mesh laid over the earth, determines which
       cells in that mesh intersect the area of each Placemark in `soup`, and
       then uses a dict from cell to those intersecting Placemarks to quickly
       narrow down the possible containing polygons.

       :param soup: a KML document (bs4.BeautifulSoup)
       
       :param scale: the width/height of Earth in degrees (as in a Mercator
       projection) is divided by two raised to `scale` to determine the width/
       height of the cells by which this function indexes space
       """
    
    pms = soup('Placemark')
    index = {}
    for i in range(len(pms)):
        pm = pms[i]
        
        #Find out what cells are needed to cover the Placemark
        cells = _spatial_index(pm, scale)
        
        #add mappings from each of those cells to the current Placemark
        #into the index
        for cell in cells:
            try:
                pool = index[cell]
            except KeyError:
                index[cell] = pool = set()
            pool.add(i)
    return index

def spatial_index_stats(index):
    """Compute and return statistics about the quality of a spatial index.

       For each cell defined in the spatial index, that cell intersects and
       maps to a certain number of Placemarks. This function gathers statistics
       about those Placemarks-per-cell relationships.

       Return the average, min, max, median, range, and standard deviation
       (population-type, not sample) of the number of Placemarks intersected
       per cell.

       :param index: a dict from mesh cell to a set of ints >= 0 (index into
       list of Placemarks), such as the return value of `spatial_index`

       :returns: a dict of stats about `index` and the underlying data
       """
    stats = [len(v) for v in index.values()]
    avg = sum(stats) / len(stats)
    m,M = min(stats), max(stats)

    max_index = len(stats) - 1
    if max_index % 2 == 0:
        med_index = max_index // 2
        median = sorted(stats)[med_index]
    else:
        med_index_lo = max_index // 2
        med_index_hi = med_index_lo + 1
        median = set(sorted(stats)[med_index_lo:(med_index_hi + 1)])
        if len(median) == 1:
            median = median.pop()
        else:
            median = sorted(median)

    _range = M - m

    stdev = (sum((stat - avg)**2 for stat in stats) / len(stats)) ** 0.5

    return {'avg':avg, 'stdev':stdev, 'median':median, 'min':m, 'max':M,
            'range':_range, 'data':stats}

def _spatial_index(pm, scale):
    """Choose the appropriate implementing function to index the Placemark.

       Defers to _spdx_mg, _spdx_pg, _spdx_ls, and _spdx_pt depending on
       whether there's a MultiGeometry, Polygon, LineString, or Point in the
       Placemark.

       Raise ValueError if no such element is present.

       :param pm: a `<Placemark>` element of a KML document
       
       :param scale: the exponent of the denominator of the width and height of
       the indexing cells (in degrees)

       :returns: the Placemark's geometry (MultiGeometry, Polygon, LineString,
       or Point)
       """
    try:
        return next(iter(
                f(tag, scale)
                for tag, f in ([pm.find(name), func]
                               for name, func in _TAG_TO_FUNCTION.items())
                if tag))
    except StopIteration:
        raise ValueError('Placemark has no Point, LineString, Polygon, or '
                         'MultiGeometry')

def _spdx_pg(pg, scale):
    """Spatially index a Polygon."""
    outer = coords_from_tag(pg.outerBoundaryIs.coordinates)
    cells = _cells(outer, 2, scale)
    for ibi in pg('innerBoundaryIs'):
        inner = coords_from_tag(ibi.coordinates)
        hole_rim  = _cells(inner, 1, scale)
        hole_fill = _cells(inner, 2, scale, boundary_cells=hole_rim)
        cells -= (hole_fill - hole_rim)
    return cells

def _spdx_ls(ls, scale):
    """Spatially index a LineString."""
    return _cells(coords_from_tag(ls.coordinates), 1, scale)

def _spdx_pt(pt, scale):
    """Spatially index a Point."""
    return _cells(coords_from_tag(pt.coordinates)[0], 0, scale)

def _spdx_mg(mg, scale):
    """Spatially index a MultiGeometry."""
    cells = set()
    for geom in mg(list(_TAG_TO_FUNCTION)):
        cells.update(_TAG_TO_FUNCTION[geom.name](geom, scale))
    return cells

def _cells(points, dim, scale, dim2func={0:sx.get_cell,
                                         1:sx.get_cells_1d,
                                         2:sx.get_cells_2d},
           **named):
    """Return the spatial index cells intersecting `points`.

       :param points: a KML geometry element (Polygon, LineString, Point)
       :param dim: number of dimensions `points` internally has
       :param scale: exponential scale of spatial index mesh size
       :param dim2func: map from `dim` to the function that get cells for
       a geometry of that dimension
       :param named: named parameters to send to a function from dim2func
       """
    
    try:
        func = dim2func[dim]
    except KeyError:
        raise ValueError('dim must be 0, 1, or 2')
    return func(points, scale=scale, **named)

_TAG_TO_FUNCTION = {'MultiGeometry': _spdx_mg,
                    'Polygon'      : _spdx_pg,
                    'LineString'   : _spdx_ls,
                    'Point'        : _spdx_pt}

from .styles import stylize

def time_graph(files, sorter):
    assert all(x.endswith('.kml' ) for x in files)
    soups = [open(file) for file in files]
    polygonsies = []
    for soup in soups:
        polygons = [Polygon.from_kml(polygon, info=polygon)
                    for polygon in soup('Placemark')]
        polygons.sort(key=(lambda poly : sorter(poly.info)))
        polygonsies.append(polygons)
    return set(itertools.chain.from_iterable(
            seamless(polygons)
            for polygons in polygonsies))

def color_soups_through_time(files, sorter):
    """Turn a list of kml file names into a list of soups all colored the same.

       Use the same district-number-to-color dict to color each Placemark in
       each soup.
       
       :param files: a list of string file/paths to different kml versions of
       the same district layer
       :param sorter: callable: kml Placemark element (bs4.Tag) -> int (distr.)
       """
    
    all_graph = time_graph(files, sorter)

    soups = [open(file) for file in files]
    color_graph.COLORS = {1,2,3,4,5}
    try:
        coloring = color_graph.color(all_graph)
        for soup in soups:
            stylize(soup, {k+1:v for k,v in coloring.items()}, sorter,
                    d2=styles._COLORS_5, d0=None)
    finally:
        color_graph.COLORS = {1,2,3,4}

    return soups
