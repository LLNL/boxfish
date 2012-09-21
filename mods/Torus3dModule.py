from PySide.QtCore import *
from Module import *

import TorusIcons
import sys
import numpy as np
import matplotlib.cm as cm

class Torus3dAgent(ModuleAgent):
    nodeUpdateSignal = Signal(list, list)
    linkUpdateSignal = Signal(list, list)
    transformUpdateSignal = Signal(np.ndarray, np.ndarray)

    def __init__(self, parent, datatree):
        super(Torus3dAgent, self).__init__(parent, datatree)

        self.addRequirement("nodes")
        self.addRequirement("links")
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
            self.nodeUpdateSignal.emit(coordinates, attribute_values[0])


    def updateLinkValues(self):
        if self.source_coords is None or self.destination_coords is None:
            return
        coords = self.source_coords[:]
        coords.extend(self.destination_coords)
        coordinates, attribute_values = self.requestGroupBy("links",
            coords, self.link_coords_table, "mean", "mean")
        if attribute_values is not None:
            self.linkUpdateSignal.emit(coordinates, attribute_values[0])


    @Slot(ModuleScene)
    def processModuleScene(self, module_scene):
        if self.module_scene.module_name == module_scene.module_name:
            self.module_scene = module_scene.copy()
            self.transformUpdateSignal.emit(self.module_scene.rotation,
                self.module_scene.translation)


class Torus3dView(ModuleView):
    """This is a base class for a rendering of a 3d torus.
       Subclasses need to define this method:
           createView(self)
               Should return an instance of some subclass of GLWidget
               that will render the scene.
    """

    def __init__(self, parent, parent_view = None, title = None):
        super(Torus3dView, self).__init__(parent, parent_view, title)
        self.shape = [0, 0, 0]
        if self.agent:
            self.agent.nodeUpdateSignal.connect(self.updateNodeData)
            self.agent.linkUpdateSignal.connect(self.updateLinkData)
            self.agent.transformUpdateSignal.connect(self.updateTransform)

            self.createDragOverlay(["nodes", "links"],
                ["Color Nodes", "Color Links"],
                [QPixmap(":/nodes.png"), QPixmap(":/links.png")])

            self.view.transformChangeSignal.connect(self.transformChanged)

    @Slot(list, list)
    def updateNodeData(self, coords, vals):
        if vals is None:
            return
        min_val = min(vals)
        max_val = max(vals)
        range = max_val - min_val
        if range <= sys.float_info.epsilon:
            range = 1.0

        cmap = cm.get_cmap("jet")

        if self.agent.shape != self.shape:
            self.view.setShape(self.agent.shape)
            self.shape = self.agent.shape
        else:
            self.view.clearNodes()

        for coord, val in zip(coords, vals):
            x, y, z = coord
            self.view.node_colors[x, y, z] = cmap((val - min_val) / range)
        self.view.updateGL()

    @Slot(list, list)
    def updateLinkData(self, coords, vals):
        if vals is None:
            return

        cmap = cm.get_cmap("jet")

        if self.agent.shape != self.shape:
            self.view.setShape(self.agent.shape)
            self.shape = self.agent.shape
        else:
            self.view.clearLinks()

        # We don't draw both directions yet so we need to coalesce
        # the link values.
        link_values = np.empty(self.shape + [3], np.float)
        for coord, val in zip (coords, vals):
            sx, sy, sz, tx, ty, tz = coord
            coord_difference = [s - t for s,t
                in zip((sx, sy, sz), (tx, ty, tz))]

            # plus direction link
            if sum(coord_difference) == -1: # plus direction link
                link_dir = coord_difference.index(-1)
                link_values[sx, sy, sz, link_dir] += val
            elif sum(coord_difference) == 1: # minus direction link
                link_dir = coord_difference.index(1)
                link_values[tx, ty, tz, link_dir] += val
            elif sum(coord_difference) > 0: # plus torus seam link
                link_dir = list(np.sign(coord_difference)).index(1)
                link_values[sx, sy, sz, link_dir] += val
            elif sum(coord_difference) < 0: # minus torus seam link
                link_dir = list(np.sign(coord_difference)).index(-1)
                link_values[tx, ty, tz, link_dir] += val

        min_val = np.min(link_values)
        max_val = np.max(link_values)
        val_range = max_val - min_val
        if val_range <= sys.float_info.epsilon:
            val_range = 1.0

        for x, y, z, i in itertools.product(range(self.shape[0]),
            range(self.shape[1]), range(self.shape[2]), range(3)):
            self.view.link_colors[x, y, z, i] \
                = cmap((link_values[x, y, z, i] - min_val) / val_range)

        self.view.updateGL()

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


class GLModuleScene(ModuleScene):
    """TODO: Docs"""

    def __init__(self, agent_type, module_type, rotation = None,
        translation = None):
        super(GLModuleScene, self).__init__(agent_type, module_type)

        self.rotation = rotation
        self.translation = translation

    def __equals__(self, other):
        if self.rotation == other.rotation \
                and self.translation == other.translation:
            return True
        return False

    def copy(self):
        if self.rotation is not None and self.translation is not None:
            return GLModuleScene(self.agent_type, self.module_name,
                self.rotation.copy(), self.translation.copy())
        elif self.rotation is not None:
            return GLModuleScene(self.agent_type, self.module_name,
                self.rotation.copy(), None)
        elif self.translation is not None:
            return GLModuleScene(self.agent_type, self.module_name,
                None, self.translation.copy())
        else:
            return GLModuleScene(self.agent_type, self.module_name)
