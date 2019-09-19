"""A module for basic US Census Bureau data about states and their counties
and county-equivalents. It relies on two text files for the data and loads
the data from those files when it is imported."""

import tables

class TrickyDict(dict):
    """A dict that ignores case, and which can be called or attributed instead
       of subscripted."""

    @staticmethod
    def _as_upper(key):
        return key.upper() if isinstance(key, str) else key

    def __init__(self, dic=None, alias={}):
        dic = dic or {}
        super(TrickyDict, self).__init__([[TrickyDict._as_upper(k), v]
                                          for k,v in dic.items()])
        for new_name, old_name in alias.items():
            self[new_name] = self[old_name]
    
    def __getitem__(self, key):
        key = TrickyDict._as_upper(key)
        return super(TrickyDict, self).__getitem__(key)
    def __setitem__(self, key, value):
        key = TrickyDict._as_upper(key)
        super(TrickyDict, self).__setitem__(key, value)
    def __delitem__(self, key):
        key = TrickyDict._as_upper(key)
        super(TrickyDict, self).__delitem__(key)
    
    def __getattr__(self, name):
        return self[name]
    def __setattr__(self, name, value):
        self[name] = value
    def __delattr__(self, name):
        del self[name]

    def __call__(self, *args, **kwargs):
        key = args[0]
        return self[key]

    def alias(self, new_name, old_name=None):
        self[new_name] = self[old_name]

class State(TrickyDict):
    
    __alias = {'code'  :'STATEFP',
               'fips'  :'STATEFP',
               'postal':'STUSPS'}
    
    def __init__(self, dic):
        super(State, self).__init__(dic, State.__alias)
        self.counties = []
    
    def __repr__(self):
        return str(self)
    
    def __str__(self):
        return f'State[{self.postal}, {self.fips}]'

import fips.states as STATES
states = tables.Table(State(state)
                      for state in tables.parse(STATES.table, delim='\t'))

#Index the state table by state fips code so that each county can
#find its state quickly during this step
states.index_by('STATEFP', TrickyDict)

#Create a record for each county and add it to a list of county records kept
#by each state record
import fips.counties as COUNTIES
for county in tables.parse(COUNTIES.table, delim='\t'):
    county = TrickyDict(county, {'code': 'COUNTYFP', 'fips': 'COUNTYFP'})
    state = states(county.STATEFP)
    state.counties.append(county)
    county.state = state

#re-index the state table by postal code, since that's the targeted use-case
states.index_by('STUSPS', TrickyDict)

for state in states:
    #states.alias(state.fips,      state.postal) # Cannot do multiple-index
    #states.alias(int(state.fips), state.postal) # anymore
    state.counties = tables.Table(state.counties)
    state.counties.index_by('COUNTYFP', TrickyDict)

del state, county, STATES, COUNTIES #no reason to leave those accessible
