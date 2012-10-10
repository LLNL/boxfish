import sys
import numpy as np
import matplotlib.cm as cm

from PySide.QtCore import *

from boxfish.ModuleAgent import *
from boxfish.ModuleView import *
import TorusIcons

class Torus3dAgent(ModuleAgent):
    """This is an agent for all 3D Torus based modules."""

    # shape, ids, values, id->coords dict, coords->id dict
    nodeUpdateSignal = Signal(list, list, list, dict, dict)
    linkUpdateSignal = Signal(list, list, list, dict, dict)

    # rotation and translation
    transformUpdateSignal = Signal(np.ndarray, np.ndarray)

    def __init__(self, parent, datatree):
        super(Torus3dAgent, self).__init__(parent, datatree)

        self.addRequest("nodes")
        self.addRequest("links")
        self.coords_table = None
        self.node_coords_dict = dict()
        self.coords_node_dict = dict()
        self.link_coords_table = None
        self.link_coords_dict = dict()
        self.coords_link_dict = dict()
        self.run = None
        self.shape = [0, 0, 0]
        self.receiveModuleSceneSignal.connect(self.processModuleScene)

    def registerNodeAttributes(self, indices):
        self.registerRun(self.datatree.getItem(indices[0]).getRun())
        self.requestAddIndices("nodes", indices)

    def registerLinkAttributes(self, indices):
        self.registerRun(self.datatree.getItem(indices[0]).getRun())
        self.requestAddIndices("links", indices)

    def registerRun(self, run):
        """Grab the hardware information from this run, verifying it is
           the appropriate network structure for this module.

           TODO: Actually verify.
        """
        if run is not self.run:
            self.run = run
            hardware = run["hardware"]
            coords = hardware["coords"]
            self.coords_table = run.getTable(hardware["coords_table"])
            self.shape = [hardware["dim"][coord] for coord in coords]

            self.node_coords_dict, self.coords_node_dict = \
                self.coords_table.createIdAttributeMaps(coords)


            link_coords = [hardware["source_coords"][coord]
                for coord in coords]
            link_coords.extend([hardware["destination_coords"][coord]
                for coord in coords])
            self.link_coords_table = run.getTable(hardware["link_coords_table"])
            self.link_coords_dict, self.coords_link_dict = \
                self.link_coords_table.createIdAttributeMaps(link_coords)


    def requestUpdated(self, name):
        if name == "nodes":
            self.updateNodeValues()
        elif name == "links":
            self.updateLinkValues()

    def updateNodeValues(self):
        node_ids, values = self.requestOnDomain("nodes",
            domain_table = self.coords_table,
            row_aggregator = "mean", attribute_aggregator = "mean")
        self.nodeUpdateSignal.emit(self.shape, node_ids, values,
            self.node_coords_dict, self.coords_node_dict)


    def updateLinkValues(self):
        link_ids, values = self.requestOnDomain("links",
            domain_table = self.link_coords_table,
            row_aggregator = "mean", attribute_aggregator = "mean")
        self.linkUpdateSignal.emit(self.shape, link_ids, values,
            self.link_coords_dict, self.coords_link_dict)


    @Slot(ModuleScene)
    def processModuleScene(self, module_scene):
        if self.module_scene.module_name == module_scene.module_name:
            self.module_scene = module_scene.copy()
            self.transformUpdateSignal.emit(self.module_scene.rotation,
                self.module_scene.translation)



def cmap_range(vals):
    """Use to normalize ranges for color maps.  Given an set of values,
    this will return a function that will normalize those values to
    something in [0..1] based on their range.
    """
    min_val = min(vals)
    max_val = max(vals)
    range = max_val - min_val
    if range <= sys.float_info.epsilon:
        range = 1.0
    def evaluator(val):
        return (val - min_val) / range
    return evaluator


class Torus3dViewColorModel(object):
    """This class is designed to hold color data for a view of a 3d Torus.
       This is really where the raw data to be displayed lives; you might
       say that this is the torus "domain" itself.  Views of the torus
       display the colors stored in this model.

       The data is stored in numpy arrays to make rendering fast and simple.
       Compare this to the way data is projected and passed to the view,
       which is not really ready for rendering yet.

       Views can register listeners with this class to receive updates when
       things change.  This class can also allows multiple views to share the
       same color model so that the same attributes can be viewed consistently.
       Note that attribute consistency isn't implemented, but the color stuff
       is factored into this class so that it can be shared.
    """
    def __init__(self, **keywords):
        def kwarg(name, default_value):
            setattr(self, name, keywords.get(name, default_value))

        kwarg("default_node_color", (0.5, 0.5, 0.5, 0.2))
        kwarg("node_cmap", cm.get_cmap("jet"))

        kwarg("default_link_color", (0.5, 0.5, 0.5, 0.2))
        kwarg("link_cmap", cm.get_cmap("jet"))

        self._shape = None
        self.shape = [0, 0, 0]
        self.listeners = set()

    def clearNodes(self):
        self.node_colors = np.tile(self.default_node_color, self._shape + [1])

    def clearLinks(self):
        self.pos_link_colors = np.tile(self.default_link_color, self._shape + [3, 1])
        self.neg_link_colors = np.tile(self.default_link_color, self._shape + [3, 1])
        self.avg_link_colors = np.tile(self.default_link_color, self._shape + [3, 1])

    def setShape(self, shape):
        if self._shape != shape:
            self._shape = shape
            self.clearNodes()
            self.clearLinks()

    # enforce that shape always looks like a tuple externally
    shape = property(lambda self: tuple(self._shape), setShape)

    def _notifyListeners(self):
        for listener in self.listeners:
            listener()

    def registerListener(self, listener):
        self.listeners.add(listener)

    def unregisterListener(self, listener):
        self.listeners.remove(listener)

    def map_node_color(self, val):
        """Turns a color value in [0,1] into a 4-tuple RGBA color.
           Used to map nodes.
        """
        return self.node_cmap(val)

    def map_link_color(self, val):
        """Turns a color value in [0,1] into a 4-tuple RGBA color.
           Used to map links.
        """
        return self.link_cmap(val)

    @Slot(list, list, list, dict, dict)
    def updateNodeData(self, shape, nodes, vals, node_coord, coord_node):
        if not vals:
            return
        self.shape = shape

        cval = cmap_range(vals)
        for node_id, val in zip(nodes, vals):
            x, y, z = node_coord[node_id]
            self.node_colors[x, y, z] = self.map_node_color(cval(val))

        self._notifyListeners()

    @Slot(list, list, list, dict, dict)
    def updateLinkData(self, shape, links, vals, link_coord, coord_link):
        if not vals:
            return
        self.shape = shape

        # Make sure we have no more values than links
        num_values = len(vals)
        num_links = np.product(self.shape) * 6
        if num_values > num_links:
            raise ValueError("received %d values for %d links!"
                             % (num_values, num_links))

        avg_link_values = np.zeros(self._shape + [3, 1])

        cval = cmap_range(vals)
        for link_id, val in zip(links, vals):
            #sx, sy, sz, tx, ty, tz = coord
            sx, sy, sz, tx, ty, tz = link_coord[link_id]
            start = np.array(link_coord[link_id][0:3])
            end = np.array(link_coord[link_id][3:])

            diff = end - start               # difference bt/w start and end
            axis = np.nonzero(diff)[0]       # axis where start and end differ

            c = self.map_link_color(cval(val))
            if diff[axis] == 1 or diff[axis] < -1:   # positive direction link
                self.pos_link_colors[sx, sy, sz, axis] = c
                avg_link_values[sx, sy, sz, axis] += val
            elif diff[axis] == -1 or diff[axis] > 1: # negative direction link
                self.neg_link_colors[tx, ty, tz, axis] = c
                avg_link_values[tx, ty, tz, axis] += val

        for index in np.ndindex(self.shape):
            x, y, z = index
            for axis in range(3):
                color_val = cval(avg_link_values[x, y, z, axis])
                self.avg_link_colors[x, y, z, axis] = self.map_link_color(color_val)

        self._notifyListeners()


class Torus3dView(ModuleView):
    """This is a base class for a rendering of a 3d torus.
       Subclasses need to define this method:
           createView(self)
               Should return the widget that will display the scene in the view.

       Subclasses should receive updates by registering for change updates
       with the color model.
    """
    def __init__(self, parent, parent_view = None, title = None):
        # Need to set this before the module initialization so that createView can use it.
        # TODO: not sure whether I like this order.  It's not very intuitive, but seems necessary.
        self.colorModel = Torus3dViewColorModel()
        super(Torus3dView, self).__init__(parent, parent_view, title)

        if self.agent:
            self.agent.nodeUpdateSignal.connect(self.colorModel.updateNodeData)
            self.agent.linkUpdateSignal.connect(self.colorModel.updateLinkData)
            self.agent.transformUpdateSignal.connect(self.updateTransform)

            self.createDragOverlay(["nodes", "links"],
                ["Color Nodes", "Color Links"],
                [QPixmap(":/nodes.png"), QPixmap(":/links.png")])

            self.view.transformChangeSignal.connect(self.transformChanged)

    def transformChanged(self, rotation, translation):
        self.agent.module_scene.rotation = rotation
        self.agent.module_scene.translation = translation
        self.agent.module_scene.announceChange()

    def droppedData(self, index_list, tag):
        if tag == "nodes":
            self.agent.registerNodeAttributes(index_list)
        elif tag == "links":
            self.agent.registerLinkAttributes(index_list)

    @Slot(np.ndarray, np.ndarray)
    def updateTransform(self, rotation, translation):
        self.view.set_transform(rotation, translation)

