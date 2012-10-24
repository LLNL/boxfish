#!/usr/bin/env python
"""This agent contains functions for reading files into datastructures used
by Boxfish.
"""

def read_header(filename):
    """Reads header information on a data table file.

       The header information can optionally have one (1) document with
       meta information. If this document exists, it must come before
       the dtype information for the table.
    """
    import yaml
    input = open(filename,'r')

    loader = yaml.SafeLoader(input) # No python-specific yaml

    # Where we're storing the meta data
    meta = loader.get_data()

    # List of tuples
    if loader.check_token(yaml.DocumentStartToken):
        dtype = loader.get_data()
    else:
        dtype = meta
        meta = None

    dtype = convert_dtype(dtype)
    return meta, dtype

def convert_dtype(dtype):
    """Takes a list of two element lists and turns it into a list of
       two element tuples so it will play nice with numpy recarrays.

       Assumes the original list has proper format/values.
    """
    new_dtype = []
    for pair in dtype:
        new_dtype.append(tuple(pair))

    return new_dtype

# Load meta data file
def load_meta(filename):
    """Reads the run file with the meta data. This files is composed
       of an arbitrary number of YAML documents. The first document
       is the global meta information. All following documents describe
       other files or objects.
    """
    import yaml
    input = open(filename, 'r')

    loader = yaml.SafeLoader(input) # No python-specific yaml
    if loader.check_data():
        meta = loader.get_data()

    filelist = []
    while loader.check_data(): # There's another document
        filelist.append(loader.get_data())

    return meta, filelist


def load_table(filename):
    """Reads the given file and returns a numpy recarray of the data.

       Assumes a YAML header with dtype information for the table. This
       header may also have one (1) document of meta information which
       will be read and passed back, but this is optional.
    """
    import numpy as np

    meta, dtype = read_header(filename)

    # Reopen to actually get data
    input = open(filename,'r')
    line = input.readline()

    while input.readline().split()[0] != "...":
        continue

    #print meta
    #if 'encoding' in meta and meta['encoding'] == 'binary':
    #    print "Trying ", dtype 
    #    data = np.loads(input.read())
    #else:
    data = np.loadtxt(input, dtype=np.dtype(dtype))

    return meta, data

if __name__ == '__main__':
    from sys import argv

    if len(argv) > 1:
        meta, data = load_table(argv[1])
        
        #meta, files = load_meta(argv[1])
        #for k, v in meta.iteritems():
        #    print "metakey: ", k, "value: ", v
        #for f in files:
        #    print f
    else:
        meta, data = load_meta("bgpc_meta.yaml")
        for k, v in meta.iteritems():
            print "key: ", k, "value: ", v



