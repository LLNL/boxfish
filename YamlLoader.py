"""This module contains functions for reading files into datastructures used
by Boxfish.
"""

def read_header(filename):
    import yaml
    input = open(filename,'r')

    loader = yaml.Loader(input)
    
    # List of tuples
    dtype = loader.get_data()

    input.close()
    return dtype

# For loading files with map data (among others)
# e.g. bgpcounter data
def load_yaml(filename):
    """Reads the given file and returns a numpy recarray of the data.

    If the file does not contain x,y,z field, None is returned. 

    If the file does not contain an mpirank field, one is created and 
    populated by line numbers for each record.
    """
    import numpy as np
    
    dtype = read_header(filename)

    # Reopen to actually get data
    input = open(filename,'r')
    line = input.readline()
    while input.readline().split()[0] != "...":
        continue

    # Map information is required
    if not 'x' in np.dtype(dtype).names or \
        not 'y' in np.dtype(dtype).names or \
        not 'z' in np.dtype(dtype).names:
        return None

    # If not present, mpirank is assumed
    if not 'mpirank' in np.dtype(dtype).names:
       recs = []
       dtype.append(('mpirank', 'int32'))
       for i, line in enumerate(input):
         newrec = line.split()
         newrec.append(i)
         newrec = tuple(newrec)
         recs.append(newrec)
       data = np.array(recs, dtype)
    else: 
       data = np.loadtxt(input, dtype=np.dtype(dtype))

    return data

# For loading communicator files
def load_list(filename):
    """Loads communicator information from a file in a recarray with 
    communicator names and a dict mapping communicator names to a list of 
    subcommunicator rank lists.

    If a comm_name field is not found, returns None for both data structures.
    """
    import numpy as np

    dtype = read_header(filename)

    # Reopen to actually get data
    input = open(filename,'r')
    line = input.readline()
    while input.readline().split()[0] != "...":
        continue

    # Requires names
    if not 'comm_name' in np.dtype(dtype).names:
       return (None, None)

    rec = [] # np.empty(0, dtype)
    recdict = dict()

    # Comms with same comm_name are grouped and assumed to be
    # sibling subcommunicators
    for i, line in enumerate(input):
        newrec = line.split()[:len(dtype)]
        newrec = tuple(newrec)
        rec.append(newrec)
        comm_name = str(np.array(newrec, dtype)['comm_name'])
        if comm_name in recdict:
           recdict[comm_name].append(map(int,line.split()[len(dtype):]))    
        else:
           recdict[comm_name] = [map(int,line.split()[len(dtype):])]

    recarr = np.array(rec, dtype)
    return (recarr, recdict)


if __name__ == '__main__':
    from sys import argv

    if len(argv) > 1:
        comms, commlists = load_list(argv[1])
    else:
        data = load_yaml("bgpcounter_data.yaml")
    
    
    
    
