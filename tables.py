"""A script to read and write text data from/to files"""

def _read(path_name, args, kwargs):
    delim = kwargs['delim']
    translate = kwargs['translate']
    table = []
    with open(path_name, 'r') as outof:
        columns = []
        for line in outof:
            if line.endswith('\n'):
                line = line[:-1]
            splut = line.split(delim)
            if 'qualifier' in kwargs and kwargs['qualifier']:
                qualifier = kwargs['qualifier']
                while any(e.startswith(qualifier) for e in splut):
                    i = next(iter(i
                                  for i in range(len(splut))
                                  if splut[i].startswith(qualifier)))
                    j = next(iter(j
                                  for j in range(i,len(splut))
                                  if splut[j].endswith(qualifier)))
                    splut[i] = splut[i][len(qualifier):]
                    splut[j] = splut[j][:-len(qualifier)]
                    splut[i:j+1] = delim.join(splut[k] for k in range(i,j+1))
            elements = splut
            if not columns:
                columns = elements
                continue
            #record = {columns[i]:elements[i] for i in range(len(columns))}
            record = {c:(e
                         if c not in translate
                         else translate[c](e))
                      for c,e in ((columns[i],elements[i])
                                  for i in range(len(columns)))}
            table.append(record)
    return table

def _check_delim(path_name, kwargs):
    if 'delim' not in kwargs:
        if path_name.endswith('.txt'):
            kwargs['delim'] = '\t'
        elif path_name.endswith('.csv'):
            kwargs['delim'] = ','
        else:
            raise ValueError('Delimiter `delim` not specified. Could not '
                             'assume based on file extension.')
    return kwargs['delim']

def read(path_name, *args, **kwargs):
    """Read a data table from a file specified by path_name.

       `path_name` the name of (or path to followed by name of) the file
       to read
       `delim` the delimiter used between cell entries in the table. Defaults
       to tab for files ending in .txt and to comma for files ending in .csv.
       `translate` a dict mapping from column name to a callable (such as `int`
       or `float` or `eval`) which translates a value in that column into a new
       form."""
    _check_delim(path_name, kwargs)
    if 'translate' not in kwargs:
        kwargs['translate'] = {}
    return _read(path_name, args, kwargs)

def write(table, path_name, *args, **kwargs):
    delim = _check_delim(path_name, kwargs)
    
    qualifier = kwargs.get('qualifier', '')
    
    with open(path_name, 'w') as into:
        columns = [a for a in table[0]]
        into.write(delim.join(qualifier+a+qualifier for a in columns)+'\n')
        for record in table:
            into.write(delim.join(qualifier + str(record[key]) + qualifier
                                  for key in columns)+'\n')
    
class Table(list):
    
    """A glorified list of dicts
       
       Index records by the values of a certain column, then retrieve them
       by calling or attributing the table with that cell content. Use brackets
       or attributes to retrieve or set an entire column."""
    
    def __init__(self, records, **formats):
        super(Table, self).__init__(records)
        self.format(**formats)
        self.__index = {}
    
    def format(self, **formats):
        for record in self:
            for column,_format in formats.items():
                if column in record:
                    record[column] = _format(record[column])
    
    def by(self, column, one_to_one=False, out=None):
        result = {}
        for record in self:
            key = record[column]
            if key not in result:
                result[key] = []
            result[key].append(record)
            if one_to_one and len(result[key]) > 1:
                raise ValueError("Couldn't make it one-to-one")
        if out is not None:
            for subtable in result.values():
                for i in range(len(subtable)):
                    subtable[i] = subtable[i][out]
        if one_to_one:
            for key,subtable in result.items():
                result[key] = subtable[0]
        return result
    
    def index_by(self, column, wrapper=(lambda x : x)):
        """Index this table by the specified column so that the last (and
           ostensibly sole) record with a given value in that column can be
           retrieved by subscripting, attributing, and calling."""
        self.__index = wrapper({record[column]:record for record in self})
    
    def __call__(self, key):
        """Return the record indexed from `key`
           
           Example use:
           state_table = Table(states_records)
           state_table.index_by('fips_code')
           nc_record = table('037')"""
        return self.__index[key]
    
    def __getitem__(self, column):
        """Either delegate retrieval of elements/slices to the superclass
           or return a generator that iterates over the values in the specified
           column of the table."""
        
        #If it's a valid index for a list, send to superclass
        if isinstance(column, slice) or isinstance(column, int):
            return super(Table, self).__getitem__(column)
        
        #otherwise send back the named column
        return (record[column] for record in self)
    
    def __getattr__(self, name):

        #if that's an existing column name, return the column
        #(as a generator); otherwise try to return the record
        #corresponding to that name in the index, if there is one.
        if name in self[0]:
            return self[name]
        else:
            return self.__index[name]
    
    def __setitem__(self, column, value):
        
        #If it's a valid index for a list, send to superclass
        if isinstance(column, slice) or isinstance(column, int):
            super(Table, self).__setitem__(column, value)
        
        if len(value) != len(self):
            raise ValueError('length mismatch')
        for record,element in zip(self, value):
            record[column] = element
        raise ValueError('Need an index, slice, or column heading')
    
    def __setattr__(self, name, value):
        if name.endswith('__index'): #very dirty lazy hack TODO
            super(Table, self).__setattr__(name, value)
        else:
            self[name] = value #outsource to __setitem__
    
    def __delitem__(self, column):
        
        #If it's a valid index for a list, send to superclass
        if isinstance(column, slice) or isinstance(column, int):
            super(Table, self).__setitem__(column, value)
        
        for record in self:
            del record[column]
    
    def __delattr__(self, name):
        del self[name]
    
