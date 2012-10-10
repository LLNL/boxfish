import sys
import numpy as np
import matplotlib.cm as cm

from PySide.QtCore import *

from boxfish.ModuleAgent import *
from boxfish.ModuleView import *
import TorusIcons

class Torus3dAgent(ModuleAgent):
    """This is an agent for all 3D Torus based modules."""
    
    # shape, node->coords, coords->node, link->coords, coords->link
    torusUpdateSignal   = Signal(list, dict, dict, dict, dict)

    # shape, ids, values, id->coords dict, coords->id dict
    nodeUpdateSignal = Signal(list, list)
    linkUpdateSignal = Signal(list, list)

    # node and link ID lists that are now highlighted
    highlightUpdateSignal = Signal(list, list)

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
        self.highlightSceneChangeSignal.connect(self.processHighlights)

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
            shape = [hardware["dim"][coord] for coord in coords]

            node_coords_dict, coords_node_dict = \
                self.coords_table.createIdAttributeMaps(coords)


            link_coords = [hardware["source_coords"][coord]
                for coord in coords]
            link_coords.extend([hardware["destination_coords"][coord]
                for coord in coords])
            self.link_coords_table = run.getTable(hardware["link_coords_table"])
            link_coords_dict, coords_link_dict = \
                self.link_coords_table.createIdAttributeMaps(link_coords)

            self.torusUpdateSignal.emit(shape, 
                node_coords_dict, coords_node_dict,
                link_coords_dict, coords_link_dict)


    def requestUpdated(self, name):
        if name == "nodes":
            self.updateNodeValues()
        elif name == "links":
            self.updateLinkValues()

    def updateNodeValues(self):
        """When the node-related request is updated, this re-grabs the
           values associated with the node-ids and signals the change.
        """
        node_ids, values = self.requestOnDomain("nodes",
            domain_table = self.coords_table,
            row_aggregator = "mean", attribute_aggregator = "mean")
        self.nodeUpdateSignal.emit(node_ids, values)


    def updateLinkValues(self):
        """When the link-related request is updated, this re-grabs the
           values associated with the link-ids and signals the change.
        """
        link_ids, values = self.requestOnDomain("links",
            domain_table = self.link_coords_table,
            row_aggregator = "mean", attribute_aggregator = "mean")
        self.linkUpdateSignal.emit(link_ids, values)

    @Slot()
    def processHighlights(self):
        """When highlights have changed, projects them onto the domains
           we care about and signals the changed local highlights.
        """
        if self.run is not None:
            node_highlights = self.getHighlightIDs(self.coords_table, self.run)
            link_highlights = self.getHighlightIDs(self.link_coords_table,
                self.run)

            self.highlightUpdateSignal.emit(node_highlights, link_highlights)


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

        kwarg("default_node_color", (0.5, 0.5, 0.5, 1.0))
        kwarg("node_cmap", cm.get_cmap("jet"))

        kwarg("default_link_color", (0.5, 0.5, 0.5, 1.0))
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

    @Slot(list, dict, dict, dict, dict)
    def updateTorus(self, shape, node_coord, coord_node, link_coord, coord_link):
        """Updates the shape and id maps of this model to a new torus."""
        self.shape = shape
        self.node_to_coord = node_coord
        self.coord_to_node = coord_node
        self.link_to_coord = link_coord
        self.coord_to_link = coord_link

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

    def set_all_alphas(self, alpha):
        """Set all nodes and links to the same given alpha value."""
        self.node_colors[:,:,:,3] = alpha
        self.avg_link_colors[:,:,:,:,3] = alpha

    def link_coord_to_index(self, coord):
        """Given a 6 scalar link coordinate, returns the 4 scalar index
           of that link in our block arrays and the link direction.
        """
        sx, sy, sz, tx, ty, tz = coord
        start = np.array(coord[0:3])
        end = np.array(coord[3:])

        diff = end - start               # difference bt/w start and end
        axis = np.nonzero(diff)[0]       # axis where start and end differ

        if diff[axis] == 1 or diff[axis] < -1:   # positive direction link
            return sx, sy, sz, axis, 1
        elif diff[axis] == -1 or diff[axis] > 1: # negative direction link
            return tx, ty, tz, axis, -1

    @Slot(list, list)
    def updateNodeData(self, nodes, vals):
        if not vals:
            return

        cval = cmap_range(vals)
        for node_id, val in zip(nodes, vals):
            x, y, z = self.node_to_coord[node_id]
            self.node_colors[x, y, z] = self.map_node_color(cval(val))

        self._notifyListeners()

    @Slot(list, list)
    def updateLinkData(self, links, vals):
        if not vals:
            return

        # Make sure we have no more values than links
        num_values = len(vals)
        num_links = np.product(self.shape) * 6
        if num_values > num_links:
            raise ValueError("received %d values for %d links!"
                             % (num_values, num_links))

        avg_link_values = np.zeros(self._shape + [3, 1])

        cval = cmap_range(vals)
        for link_id, val in zip(links, vals):
            x, y, z, axis, direction = self.link_coord_to_index(
                self.link_to_coord[link_id])
            
            avg_link_values[x,y,z,axis] += val
            c = self.map_link_color(cval(val))
            if direction > 0:
                self.pos_link_colors[x,y,z,axis] = c
            else:
                self.neg_link_colors[x,y,z,axis] = c

        for index in np.ndindex(self.shape):
            x, y, z = index
            for axis in range(3):
                color_val = cval(avg_link_values[x, y, z, axis])
                self.avg_link_colors[x, y, z, axis] = self.map_link_color(color_val)

        self._notifyListeners()

    @Slot(list, list)
    def updateHighlights(self, node_ids, link_ids):
        """Given a list of the node and link ids to be highlighted, changes
           the alpha values accordingly and notifies listeners.

           In the future, when this becomes DataModel, will probably just
           update some property that the view will manipulate.
        """
        if node_ids or link_ids:
            self.set_all_alphas(0.2)
            for node in node_ids:
                x, y, z = self.node_to_coord[node]
                self.node_colors[x, y, z, 3] = 1.0
            for link in link_ids:
                x, y, z, axis, direction = self.link_coord_to_index(
                    self.link_to_coord[link])
                self.avg_link_colors[x,y,z,axis,3] = 1.0
        else:
            self.set_all_alphas(1.0)

        self._notifyListeners()


class Torus3dView(ModuleView):
    """This is a base class for a rendering of a 3d torus.
       Subclasses need to define this method:
           createView(self)
               Must return a subclass of GLWidget that displays the scene
               in the view.

       Subclasses should receive updates by registering for change updates
       with the color model.
    """
    def __init__(self, parent, parent_view = None, title = None):
        # Need to set this before the module initialization so that createView can use it.
        # TODO: not sure whether I like this order.  It's not very intuitive, but seems necessary.
        self.colorModel = Torus3dViewColorModel()
        super(Torus3dView, self).__init__(parent, parent_view, title)

        self.agent.torusUpdateSignal.connect(self.colorModel.updateTorus)
        self.agent.nodeUpdateSignal.connect(self.colorModel.updateNodeData)
        self.agent.linkUpdateSignal.connect(self.colorModel.updateLinkData)
        self.agent.highlightUpdateSignal.connect(self.colorModel.updateHighlights)
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

