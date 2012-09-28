from PySide.QtCore import *
from ModuleAgent import *
from ModuleView import *

import TorusIcons
import sys
import numpy as np
import matplotlib.cm as cm

class Torus3dAgent(ModuleAgent):
    nodeUpdateSignal = Signal(list, list, list) # shape, coords, vals
    linkUpdateSignal = Signal(list, list, list) # shape, coords, vals
    transformUpdateSignal = Signal(np.ndarray, np.ndarray)

    def __init__(self, parent, datatree):
        super(Torus3dAgent, self).__init__(parent, datatree)

        self.addRequest("nodes")
        self.addRequest("links")
        self.coords = None
        self.coords_table = None
        self.source_coords = None
        self.destination_coords = None
        self.link_coords_table = None
        self.shape = [0, 0, 0]
        self.receiveModuleSceneSignal.connect(self.processModuleScene)

    def registerNodeAttributes(self, indices):
        # Determine Torus info from first index
        self.registerRun(self.datatree.getItem(indices[0]).getRun())
        self.requestAddIndices("nodes", indices)
        self.updateNodeValues()

    def registerLinkAttributes(self, indices):
        # Determine Torus info from first index
        self.registerRun(self.datatree.getItem(indices[0]).getRun())
        self.requestAddIndices("links", indices)
        self.updateLinkValues()

    def registerRun(self, run):
        hardware = run["hardware"]
        self.coords = hardware["coords"]
        self.coords_table = run.getTable(hardware["coords_table"])
        self.shape = [hardware["dim"][coord] for coord in self.coords]

        self.source_coords = [hardware["source_coords"][coord]
            for coord in self.coords]
        self.destination_coords = [hardware["destination_coords"][coord]
            for coord in self.coords]
        self.link_coords_table = run.getTable(hardware["link_coords_table"])


    def requestUpdated(self, name):
        if name == "nodes":
            self.updateNodeValues()
        elif name == "links":
            self.updateLinkValues()

    def updateNodeValues(self):
        if self.coords is None:
            return
        coordinates, attribute_values = self.requestGroupBy("nodes",
            self.coords, self.coords_table, "mean", "mean")
        if attribute_values is not None:
            self.nodeUpdateSignal.emit(self.shape, coordinates, attribute_values[0])


    def updateLinkValues(self):
        if self.source_coords is None or self.destination_coords is None:
            return
        coords = self.source_coords[:]
        coords.extend(self.destination_coords)
        coordinates, attribute_values = self.requestGroupBy("links",
            coords, self.link_coords_table, "mean", "mean")
        if attribute_values is not None:
            self.linkUpdateSignal.emit(self.shape, coordinates, attribute_values[0])

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

        kwarg("default_node_color", (0.5, 0.5, 0.5, 0.5))
        kwarg("node_cmap", cm.get_cmap("jet"))

        kwarg("default_link_color", (0.5, 0.5, 0.5, 0.5))
        kwarg("link_cmap", cm.get_cmap("jet"))

        self.shape = [0, 0, 0]
        self.setShape([0, 0, 0])
        self.listeners = set()

    def clearNodes(self):
        self.node_colors = np.tile(self.default_node_color, self.shape + [1])

    def clearLinks(self):
        self.pos_link_colors = np.tile(self.default_link_color, self.shape + [3, 1])
        self.neg_link_colors = np.tile(self.default_link_color, self.shape + [3, 1])

    def setShape(self, shape):
        if shape != self.shape:
            self.shape = shape
            self.clearNodes()
            self.clearLinks()

    def _notifyListeners(self):
        for listener in self.listeners:
            listener()

    def registerListener(self, listener):
        self.listeners.add(listener)

    def unregisterListener(self, listener):
        self.listeners.remove(listener)

    @Slot(list, list)
    def updateNodeData(self, shape, coords, vals):
        if not vals:
            return

        self.setShape(shape)

        cval = cmap_range(vals)
        for coord, val in zip(coords, vals):
            x, y, z = coord
            self.node_colors[x, y, z] = self.node_cmap(cval(val))

        self._notifyListeners()

    @Slot(list, list)
    def updateLinkData(self, shape, coords, vals):
        if not vals:
            return

        self.setShape(shape)

        # Make sure we have no more values than links
        assert len(vals) <= (np.product(self.shape) * 6)

        cval = cmap_range(vals)
        for coord, val in zip(coords, vals):
            sx, sy, sz, tx, ty, tz = coord
            start = np.array(coord[0:3])
            end = np.array(coord[3:])

            diff = end - start               # difference bt/w start and end
            axis = np.nonzero(diff)[0]       # axis where start and end differ

            c = self.node_cmap(cval(val))
            if diff[axis] == 1:    # positive direction link
                self.pos_link_colors[sx, sy, sz, axis] = c
            elif diff[axis] == -1: # negative direction link
                self.neg_link_colors[tx, ty, tz, axis] = c
            elif diff[axis] < 0:   # positive torus wraparound link
                self.pos_link_colors[sx, sy, sz, axis] = c
            elif diff[axis] > 0:   # negative torus wraparound link
                self.neg_link_colors[tx, ty, tz, axis] = c

        self._notifyListeners()


class Torus3dView(ModuleView):
    """This is a base class for a rendering of a 3d torus.
       Subclasses need to define this method:
           createView(self)
               Should return an instance of some subclass of GLWidget
               that will render the scene.

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

