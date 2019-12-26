from kml import add

_COLORS_5 = {1 : '7f000000',
             2 : '7f007800',
             3 : '7fff0000',
             4 : '7f7f7fff',
             5 : '7fffffff'}

_GREEN_ORANGE = {1 : '7fa8d7b6',
                 2 : '7f065fb4',
                 3 : '7f4fa86a',
                 4 : '7f6bb2f6'}
_COLORS_4 = _GREEN_ORANGE

_BLURPGRELLOW = {
        1 : 'http://maps.google.com/mapfiles/kml/paddle/blu-circle.png',
        2 : 'http://maps.google.com/mapfiles/kml/paddle/ylw-circle.png',
        3 : 'http://maps.google.com/mapfiles/kml/paddle/grn-circle.png',
        4 : 'http://maps.google.com/mapfiles/kml/paddle/purple-circle.png'}

def stylize(soup, coloring, pm2int,
            d2=_GREEN_ORANGE, d1=None, d0=_BLURPGRELLOW):
    keys = set()
    for pm in soup('Placemark'):
        key = pm2int(pm)
        color = coloring[key]
        (pm.styleUrl or add(pm, 'styleUrl')).string = '#color' + str(color)

    for key in keys:
        style_tag = soup.new_tag('Style', id='color'+str(key))
        poly_color = d2 and d2[key]
        line_color = (d1 and d1[key]) or (d2 and '0'*8)
        point_href = d0 and d0[key]
        
        if poly_color:
            add(style_tag, ['PolyStyle', 'color']).string = poly_color
        if line_color:
            add(style_tag, ['LineStyle', 'color']).string = line_color
        if point_href:
            add(style_tag,
                ['IconStyle', 'Icon', 'href']).string = point_href
    return

def _get_string(tag):
    return tag.string

class BalloonStyle:
    def __init__(self, tag):
        assert tag.name == 'BalloonStyle'
        for term in 'bgColor textColor text displayMode'.split():
            thing = tag.find(term, recursive=False)
            setattr(self, term, thing and thing.string)

class Icon:
    def __init__(self, tag):
        assert tag.name == 'Icon'
        href = tag.href
        self.href = href and href.string

class hotSpot:
    def __init__(self, tag):
        assert tag.name == 'hotSpot'
        for key in 'x y xunits yunits'.split():
            setattr(self, key, tag[key])

class IconStyle:
    def __init__(self, tag):
        assert tag.name == 'IconStyle'
        wrapper = {'Icon': Icon, 'hotSpot': HotSpot}
        for term in 'color colorMode scale heading Icon hotSpot'.split():
            thing = tag.find(term, recursive=False)
            setattr(self,
                    term,
                    thing and wrapper.get(thing, _get_string)(thing))

class LabelStyle:
    def __init__(self, tag):
        assert tag.name == 'LabelStyle'
        for term in 'color colorMode scale'.split():
            thing = tag.find(term, recursive=False)
            setattr(self, term, thing and thing.string)

class LineStyle:
    def __init__(self, tag):
        assert tag.name == 'LineStyle'
        for term in 'color colorMode width'.split():
            thing = tag.find(term, recursive=False)
            setattr(self, term, thing and thing.string)
        
        gxs = 'outerColor outerWidth physicalWidth labelVisibility'
        for term in gxs.split():
            thing = tag.find((lambda t : t.name == term and t.prefix == 'gx'),
                             recursive=False)
            setattr(self, 'gx_'+term, thing and thing.string)

class ItemIcon:
    def __init__(self, tag):
        assert tag.name == 'ItemIcon'
        for term in 'state href'.split():
            thing = tag.find(term, recursive=False)
            setattr(self, term, thing and thing.string)

class ListStyle:
    def __init__(self, tag):
        assert tag.name == 'ListStyle'
        wrapper = {'ItemIcon': ItemIcon}
        for term in 'listItemType bgColor ItemIcon'.split():
            thing = tag.find(term, recursive=False)
            setattr(self,
                    term,
                    thing and wrapper.get(thing, _get_string)(thing))

class PolyStyle:
    def __init__(self, tag):
        assert tag.name == 'PolyStyle'
        for term in 'color colorMode fill outline'.split():
            thing = tag.find(term, recursive=False)
            setattr(self, term, thing and thing.string)

class Style:
    
    def __init__(self, style):
        assert style.name == 'Style'
        wrapper = {'BalloonStyle': BalloonStyle,
                   'ListStyle'   : ListStyle,
                   'LineStyle'   : LineStyle,
                   'PolyStyle'   : PolyStyle,
                   'IconStyle'   : IconStyle,
                   'LabelStyle'  : LabelStyle}
        for label, value in wrapper.items():
            v = style.find(label)
            setattr(self, label, v and value(v))
