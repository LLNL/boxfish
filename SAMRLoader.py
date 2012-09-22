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

    patches = np.empty(shape=(mapping.shape[0],6),dtype=np.float32)
    patch_id = np.empty(shape=(mapping.shape))

    for i,m in enumerate(mapping):

        # Now we stuff a structure [id, [center_x.center_y,center_z],
        # [size_x,size_y, size_z]] into the list of patches
        # The unique id is created by the level_id << 3 + level
        patch_id[i] = (m[3] << 3) + m[2]
        c = 0.5*(location[i][2]+location[i][3])
        s = location[i][3] - location[i][2]
        patches[i] = [c[0],c[1],c[2],s[0],s[1],s[2]]


    return patch_id,patches
               
def loadSAMRAttributes(file_name):

    file = h5py.File(file_name,'r')

    # First we load the geometry data
    extents = file['extents']

    data = []
    for v in extents.values():
        name = v.name.split('/')[-1]
        if name.find('patch') != -1:
            continue

        field = np.empty(shape=v.shape)
        for i,x in enumerate(v):
            field[i] = x[-1]

        data.append([name,field])

    return data
    
if __name__ == "__main__":

    from sys import argv,exit

    ids,patches = loadSAMRPatches(argv[1])
    data = loadSAMRAttributes(argv[1])

    if len(argv) > 2:
        yaml = open(argv[2],'w')


        yaml.write("""
---
key: BGPCOUNTER_ORIGINAL
---
- [patchid, int32]
- [patch-center, 3float32]
- [patch-size, 3float32]
""")

        view = patches
        for attr in data:
            yaml.write('- [%s,float32]\n' % attr[0])
            view = np.hstack((view,attr[1].reshape(attr[1].shape[0],1)))
            
        yaml.write('...\n')

        for v,i in zip(view,ids):
            yaml.write('%d ' % i)

            yaml.write(
            for x in v:
                yaml.write(' %.3f' % x)
            yaml.write('\n')


        
        #for i,p in enumerate(patches):
        #    yaml.write('%d %.3f %.3f %.3f %.3f %.3f %.3f' % (p[0],p[1][0],p[1][1],p[1][2],p[2][0],p[2][1],p[2][2]))

         #   for d in data:
         #       yaml.write(' %f' % d[1][i])
         #   yaml.write('\n')
        
        #yaml.close()
            
                   
