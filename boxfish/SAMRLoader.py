import h5py
import numpy as np

def loadSAMRPatches(file_name):
    """Given a summary.samrai file this function will return a list of
    patches ordered by levels
    """

    file = h5py.File(file_name,'r')

    # First we load the geometry data
    extents = file['extents']

    # This is the list of coordinates
    location = extents['patch_extents']

    # This is the list of patches
    mapping = extents['patch_map']

    #patches = np.empty(shape=(mapping.shape[0],6),dtype=np.float32)
    #patch_id = np.empty(shape=(mapping.shape),dtype=np.int64)

    patches = np.empty(shape=(mapping.shape[0]),dtype=[('patch-id','i8'),
                                                       ('patch-center','3f4'),
                                                       ('patch-size','3f4')])
    
    for i,m in enumerate(mapping):

        # Now we stuff a structure [id, [center_x.center_y,center_z],
        # [size_x,size_y, size_z]] into the list of patches
        # The unique id is created by the level_id << 3 + level
        patches[i][0] = (m[3] << 3) + m[2]
        c = 0.5*(location[i][2]+location[i][3])
        s = location[i][3] - location[i][2]

        patches[i][1] = c
        patches[i][2] = s

    return patches
               
def loadSAMRAttributes(file_name):

    file = h5py.File(file_name,'r')

    # First we load the geometry data
    extents = file['extents']

    dt = []
    for v in extents.values():
        name = v.name.split('/')[-1]
        if name.find('patch') != -1:
            continue
        else: 
            dt.append((str(name),v.dtype[-1].str))

    #return dt
    data = np.empty(shape=(extents.values()[0].shape[0]),dtype=dt)

    i = 0
    for v in extents.values():
        name = v.name.split('/')[-1]
        if name.find('patch') != -1:
            continue

        for j,x in enumerate(v):
            data[j][i] = x[-1]

  
    return data

def loadSAMR(file_name):

    file = h5py.File(file_name,'r')

    # First we load the geometry data
    extents = file['extents']

    # This is the list of coordinates
    location = extents['patch_extents']

    # This is the list of patches
    mapping = extents['patch_map']

    dt = [('patch-id','i8'),('patch-center','3f4'),('patch-size','3f4')]
    
    for v in extents.values():
        name = v.name.split('/')[-1]
        if name.find('patch') != -1:
            continue
        else: 
            dt.append((str(name),v.dtype[-1].str))
 
    data = np.empty(shape=(mapping.shape[0]),dtype=dt)

    # This is the list of coordinates
    location = extents['patch_extents']

    # This is the list of patches
    mapping = extents['patch_map']

    for i,m in enumerate(mapping):

        # Now we stuff a structure [id, [center_x.center_y,center_z],
        # [size_x,size_y, size_z]] into the list of patches
        # The unique id is created by the level_id << 3 + level
        data[i][0] = (m[3] << 3) + m[2]
        c = 0.5*(location[i][2]+location[i][3])
        s = location[i][3] - location[i][2]

        data[i][1] = c
        data[i][2] = s

        #return extents.values()

    for v in extents.values():
        name = v.name.split('/')[-1]
        if name.find('patch') != -1:
            continue
        print name,v.value['max']
        data[name] = v.value['max']

    return data
    
if __name__ == "__main__":

    from sys import argv,exit

    data = loadSAMR(argv[1])

    if len(argv) > 2:
        yaml = open(argv[2],'w')


        yaml.write("""
---
key: BGPCOUNTER_ORIGINAL
encoding: binary
---
""")

        for i,n in enumerate(data.dtype.names):
            yaml.write("- [%s, %s]\n" % (n,data.dtype[i].str))
        
        yaml.write('...\n')

        yaml.write(data.dumps())
        
        yaml.close()


