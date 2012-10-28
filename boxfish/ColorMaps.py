import matplotlib.colors
import matplotlib.cm as cm

boxfish_maps = dict()

#HOWTO Make another colormap
#For each colormap, there is a red, green and blue list
#Each element in the list is:
#(normalized value between 0 and 1, value between 0 and 1, the same value again)
#So (0.5, 1.0, 1.0) in the red list means "At normalized value 0.5, the red
# value of the color is 1.0 (=xFF)".
# Unspecified values will be interpolated between the given values

# Goes from purple to green
bdict = {'red':   ((0.0, 0.686,    0.686),
    (1.0, 0.5, 0.5)),
    'green': ((0.0, 0.55,    0.55),
    (1.0, 0.75,    0.75)),
    'blue':  ((0.0, 0.765,    0.765),
    (1.0, 0.482,    0.483))}
BFPuGrmap = matplotlib.colors.LinearSegmentedColormap('BFPuGrmap',bdict,256)
boxfish_maps['BFPuGr'] = BFPuGrmap

# Goes from blue to red with yellow in the middle
bdict = {'red':   ((0.0, 145.0/255.0,    145.0/255.0),
    (0.5, 1.0, 1.0),
    (1.0, 252.0/255.0, 252.0/255.0)),
    'green': ((0.0, 191.0/255.0, 191.0/255.0),
    (0.5, 1.0, 1.0),
    (1.0, 141.0/255.0,  141.0/255.0)),
    'blue':  ((0.0, 219.0/255.0,  219.0/255.0),
    (0.5, 191.0/255.0, 191.0/255.0),
    (1.0, 89.0/255.0, 89.0/255.0))}
BFBlYeRdmap = matplotlib.colors.LinearSegmentedColormap('BFBlYeRdmap',bdict,256)
boxfish_maps['BFBlYeRd'] = BFBlYeRdmap

# Blue, Red with grey in the middle
bdict = {'red':   ((0.0, 0.0,    0.0),
    (0.5, 0.83, 0.83),
    (1.0, 1.0, 1.0)),
    'green': ((0.0, 0.0, 0.0),
    (0.5, 0.83, 0.83),
    (1.0, 0.0,  0.0)),
    'blue':  ((0.0, 1.0,  1.0),
    (0.5, 0.83, 0.83),
    (1.0, 0.0, 0.0))}
BFBlGyRdmap = matplotlib.colors.LinearSegmentedColormap('BFBlGyRdmap',bdict,256)
boxfish_maps['BFBlGyRd'] = BFBlGyRdmap

def hasMap(colormap):
    """Returns True if the given colormap String is found in our list
       of custom colormaps.
    """
    return colormap in boxfish_maps

def getMap(colormap):
    """Returns the matplotlib colormap object associated with the given
       name parameter. It searches both the custom colormaps and the
       matplotlib colormaps.
    """
    if hasMap(colormap):
        return boxfish_maps[colormap]
    else:
        return cm.get_cmap(colormap)

def mapNames():
    """Returns a list of colormap names including both matplotlib colormaps
       and custom ones.
    """
    map_names = []
    for mpl_map in cm.datad:
        map_names.append(mpl_map)
    map_names.extend(boxfish_maps.keys())
    return map_names
