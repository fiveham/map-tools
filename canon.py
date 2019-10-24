class Canon:
    """Keeps canonical instances of hashable objects to save space when there
       will be many equal copies made for whatever reason.

       When webscraping, for example, there may be thousands of repetitions of
       the same text that you get from pages that come from thousands of
       separate requests. Space can be saved by simply filtering each likely-
       duplicated instance through a collection of canonical copies of that
       type of thing.

       This filtering process maps each thing onto its canonical equivalent
       (an object instance that is equal to it) from a cache. If and when the
       thing in question is not already present in the cache, the thing itself
       is added to the cache and then the thing is mapped onto itself."""
    
    def __init__(self, things=None):
        self.storage = {}
        if things:
            self.multi(things)
    
    def single(self, thing):
        """:returns: the canonical equivalent instance of `thing`"""
        try:
            return self.storage[thing]
        except KeyError:
            self.storage[thing] = thing
            return thing
    
    def multi(self, things):
        """:returns: a collection of canonical instances of elements of `things`"""
        return type(things)(self.single(thing) for thing in things)
