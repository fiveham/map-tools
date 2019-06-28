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
    _check_delim(path_name, kwargs)

    qualifier = (kwargs['qualifier'] if 'qualifier' in kwargs
                 else '')

    with open(path_name, 'w') as into:
        columns = [a for a in table[0]]
        into.write(delim.join(qualifier+a+qualifier for a in columns))
        for record in table:
            into.write(delim.join(qualifier+str(record[key])+qualifier
                                  for key in columns))
    
