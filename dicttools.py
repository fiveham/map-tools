_SORTED = sorted

class Grouper(dict):
    
    def plus(self, key, value_element):
        try:
            extant = self[key]
        except KeyError:
            self[key] = extant = []
        extant.append(value_element)
    
    def plusdate(self, key_value_pairs):
        for key, value in key_value_pairs:
            try:
                extant = self[key]
            except KeyError:
                self[key] = extant = []
            extant.append(value)

def invert_mapping(mapping, single=False):
    """Map from the values of `mapping` to their associated keys.

       :param mapping: a dict whose values are hashable or containers of hashables.
       :param single: True if values are to be keys in returned dict.
       :returns: a dict mapping from the values (or values' elements) to collection of keys.
       """
    result = {}
    for k,V in mapping.items():
        iterable_V = [V] if single else V
        for v in iterable_V:
            try:
                extant = result[v]
            except KeyError:
                result[v] = extant = set()
            extant.add(k)
    return result

def sorted(dict):
    return {key:dict[key] for key in _SORTED(dict)}
