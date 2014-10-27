'''This module describes a 5D Torus.  Every Boxfish module consists of a frame,
scene, agent, view, and color tab.  First, the window frame is instantiated when 
the module name in the module list is dragged and dropped onto the module tree.
The frame also has a data model, called Torus5dFrameDataModel, to store the
data from tables, such as hardware and communication attributes. Heirarchy is:
    QMainWindow -> ModuleFrame -> GLFrame -> Torus5dFrame

Second, the scene handles highlighting and selection of attributes within the
view.  To pass these highlighted and selected attributes, the information is
passed onto the agent.  The heirarchy is: 
    QObject -> Scene -> ModuleScene -> GLModuleScene -> Torus5dScene

Third, the agent passes this scene information between parent & children views.
    QObject -> ModuleAgent -> GLAgent -> Torus5dAgent

Fourth, the view draws the scene using OpenGL 2.x display lists.  When the view
changes, the agent passes this information to the parent. Heirarchy is:
    QGLWidget -> GLWidget -> Torus5dGLWidget

Lastly, the color tab is a widget that pops up allowing the user to change the
colors of the nodes and links.  Heirarchy is:
    QWidget -> GLColorTab -> Torus5dColorTab
'''

import math
from PySide.QtCore import *

from GLModule import *
from boxfish.gl.GLWidget import GLWidget, set_perspective, \
    boxfish_glut_initialized, TextDraw, setupPaintEvent
from boxfish.gl.glutils import *
from OpenGL.GLUT import glutInit


import TorusIcons
from boxfish.ColorMaps import ColorMap, ColorMapWidget, drawGLColorBar

class Torus5dFrameDataModel(object):
    """This class is designed to hold data for a view of a 5d Torus.
       This is really where the raw data to be displayed lives; you might
       say that this is the torus "domain" itself.  Views of the torus
       display based on the data stored in this model.

       The data is stored in numpy arrays to make rendering fast and simple.
       Compare this to the way data is projected and passed to the view,
       which is not really ready for rendering yet.

       Views can register listeners with this class to receive updates when
       things change.  This class can also allows multiple views to share the
       same data model so that the same attributes can be viewed consistently.
    """
    # Now color information is completely handled by the GLWidget. Maybe
    # it would have been better to have created a separate color model
    # to go with the data model.

    def __init__(self, **keywords):
        self.listeners = set()
        self._shape = None
        self.shape = [0, 0, 0, 0, 0]
        self.agent = None
        self.link_direction = 0

    def clearNodes(self):
        # The first is the actual value, the second is a flag
        # indicating the validity of the data. 
        self.node_values = np.tile(0.0, self._shape + [2])

    def clearLinks(self):
        self.pos_link_values = np.tile(0.0, self._shape + [5, 2])
        self.neg_link_values = np.tile(0.0, self._shape + [5, 2])
        self.avg_link_values = np.tile(0.0, self._shape + [5, 2])
        self.link_values = np.tile(0.0, self._shape + [5, 2])

    def changeLinkDirection(self, direction):
        self.link_direction = direction
        if direction == 0:
            self.link_values = self.avg_link_values
        elif direction > 0:
            self.link_values = self.pos_link_values
        else:
            self.link_values = self.neg_link_values

        self._notifyListeners()

    def setShape(self, shape):
        if self._shape != shape:
            self._shape = shape
            self.view_planes = [set([(j, 0) for j in range(self.shape[i])]) for i in range(len(self.shape))]
            self.current_planes = [ 0 for i in range(len(self.shape))]
            self.clearNodes()
            self.clearLinks()

    # enforce that shape always looks like a tuple externally
    shape = property(lambda self: tuple(self._shape), setShape)

    @Slot(list, dict, dict, dict, dict)
    def updateTorus(self, shape, node_coord, coord_node, link_coord, coord_link):
        """Updates the shape and id maps of this model to a new torus."""
        self.node_to_coord = node_coord
        self.coord_to_node = coord_node
        self.link_to_coord = link_coord
        self.coord_to_link = coord_link
        self.shape = shape

    def _notifyListeners(self):
        #print 'NOTIFYING LISTENERS'
        for listener in self.listeners:
            listener()

    def registerListener(self, listener):
        self.listeners.add(listener)

    def unregisterListener(self, listener):
        self.listeners.remove(listener)

    def link_coord_to_index(self, coord):
        """Given a 10 scalar link coordinate, returns the 7 scalar index
           of that link in our block arrays and the link direction.
        """
        sa, sb, sc, sd, se, ta, tb, tc, td, te = coord
        start = np.array(coord[0:5])
        end = np.array(coord[5:])

        diff = end - start               # difference bt/w start and end
        axis = np.nonzero(diff)[0]       # axis where start and end differ

        if diff[axis] == 1 or diff[axis] < -1:   # positive direction link
            return sa, sb, sc, sd, se, axis, 1
        elif diff[axis] == -1 or diff[axis] > 1: # negative direction link
            #return sa, sb, sc, sd, se, axis, -1
            return ta, tb, tc, td, te, axis, -1

    def cmap_range(self, vals):
        """Use to normalize ranges for color maps.  Given a set of values,
        this will return a function that will normalize those values to
        something in [0..1] based on their range.
        """
        min_val = np.min(vals)
        max_val = np.max(vals)
        range = max_val - min_val
        if range <= sys.float_info.epsilon:
            range = 1.0
        def evaluator(val):
            return (val - min_val) / range
        return evaluator

    def range_tuple(self, vals):
        min_val = np.min(vals)
        max_val = np.max(vals)
        return (min_val, max_val)

    @Slot(list, list)
    def updateNodeData(self, nodes, vals):
        if not vals:
            return

        self.clearNodes() # when only some values are given

        cval = self.agent.requestScene("nodes").cmap_range()
        cval = self.cmap_range(vals)
        for node_id, val in zip(nodes, vals):
            a, b, c, d, e = self.node_to_coord[node_id]
            self.node_values[a, b, c, d, e] = [cval(val), 1]

        self._notifyListeners()

    @Slot(list, list)
    def updateLinkData(self, links, vals):
        if not vals:
            return

        self.clearLinks() # when only some values are given

        # Make sure we have no more values than links
        num_values = len(vals)
        num_links = np.product(self.shape) * 10
        if num_values > num_links:
            raise ValueError("received %d values for %d links!"
                             % (num_values, num_links))

        avg_link_values = np.zeros(self._shape + [5, 1])

        cval = self.agent.requestScene("links").cmap_range()

        for link_id, val in zip(links, vals):
            a, b, c, d, e, axis, direction = self.link_coord_to_index(
                self.link_to_coord[link_id])

            avg_link_values[a,b,c,d,e,axis] += val / 2.0
            clamped_val = cval(val)
            if direction > 0:
                self.pos_link_values[a,b,c,d,e,axis] = [clamped_val, 1]
            else:
                self.neg_link_values[a,b,c,d,e,axis] = [clamped_val, 1]

        # 42 billion for 4096, 42 billion for 2048, 12 billion for 1024 MILC
        for index in np.ndindex(self.shape):
            a, b, c, d, e = index
            for axis in range(5):
                #if avg_link_values[a,b,c,d,e,axis] > 30000000000:
                #    print avg_link_values[a,b,c,d,e,axis], a, b, c, d, e, axis
                #if avg_link_values[a,b,c,d,e,axis] > 0:
                    #   color_val = cval(math.log(avg_link_values[a,b,c,d,e,axis]))
                #else:
                    #   color_val = 0
                color_val = cval(avg_link_values[a, b, c, d, e, axis])
                self.avg_link_values[a, b, c, d, e, axis] = [color_val, 1]

        self.changeLinkDirection(self.link_direction)

        #self._notifyListeners()


class Torus5dFrame(GLFrame):
    """This is a base class for a rendering of a 3d torus.
       Subclasses need to define this method:
           createView(self)
               Must return a subclass of GLWidget that displays the scene
               in the view.

       Subclasses should receive updates by registering for change updates
       with the color model.
    """
    def __init__(self, parent, parent_frame = None, title = None):
        # Need to set this before the module initialization so that createView can use it.
        # TODO: not sure whether I like this order.  It's not very intuitive, but seems necessary.
        self.dataModel = Torus5dFrameDataModel()
        super(Torus5dFrame, self).__init__(parent, parent_frame, title)
        self.dataModel.agent = self.agent

        self.droppedDataSignal.connect(self.droppedData)
        self.agent.torusUpdateSignal.connect(self.dataModel.updateTorus)
        self.agent.nodeUpdateSignal.connect(self.dataModel.updateNodeData)
        self.agent.linkUpdateSignal.connect(self.dataModel.updateLinkData)

        self.agent.highlightUpdateSignal.connect(self.glview.slice4d.updateHighlights)
        self.agent.highlightUpdateSignal.connect(self.glview.slice3d.updateHighlights)
        self.agent.highlightUpdateSignal.connect(self.glview.minimaps.updateHighlights)
        self.agent.highlightUpdateSignal.connect(self.glview.overview.updateHighlights)

        self.agent.nodelinkSceneUpdateSignal.connect(self.glview.slice4d.updateScene)
        self.agent.nodelinkSceneUpdateSignal.connect(self.glview.slice3d.updateScene)
        self.agent.nodelinkSceneUpdateSignal.connect(self.glview.minimaps.updateScene)
        self.agent.nodelinkSceneUpdateSignal.connect(self.glview.overview.updateScene)
        #self.agent.nodelinkSceneUpdateSignal.connect(self.glview.egocentric.updateScene)

        self.base_title = parent.windowTitle()
        self.agent.runNameUpdateSignal.connect(self.newRun)

        self.createDragOverlay(["nodes", "links"],
            ["Color Nodes", "Color Links"],
            [QPixmap(":/nodes.png"), QPixmap(":/links.png")])

        self.color_tab_type = Torus5dColorTab

    @Slot(list, str)
    def droppedData(self, index_list, tag):
        if tag == "nodes":
            self.agent.registerNodeAttributes(index_list)
        elif tag == "links":
            self.agent.registerLinkAttributes(index_list)

    @Slot(str)
    def newRun(self, name):
        self.parent().setWindowTitle(name + "  |  " + self.base_title)

    def buildTabDialog(self):
        """Adds a tab for ranges to the Tab Dialog.

           This tab will have controls for both nodes and links attributes.
           Note if these attributes are the same, they will affect each other.

        """
        super(Torus5dFrame, self).buildTabDialog()
        self.tab_dialog.addTab(Torus5dRangeTab(self.tab_dialog, self), "Data Range")

class Torus5dScene(GLModuleScene):
    """Module Scene for 5D Torus - 2D View. This adds the axis parameters
       (which axis the user is looking down, and axis index, which
        dictates the horizontal and vertical axis) to the GLModuleScene.
    """
    def __init__(self, agent_type, module_type, rotation = None,
        translation = None, background_color = None, axis = 0, axis_index = 0, view_planes = []):
        super(Torus5dScene, self).__init__(agent_type, module_type,
            rotation, translation, background_color)

        if view_planes == None:
            pass
            # TODO:  Figure out a way to allow view_planes to be set here without knowing the shape yet
            #view_planes = [ set([j for j in range(self.shape[i])]) for i in range(len(self.shape))]
        self.axis = axis
        self.axis_index = axis_index
        self.view_planes = view_planes

    def __eq__(self, other):
        if self.axis != other.axis or self.axis_index != other.axis_index:
            return False
        else:
            for i in range(len(self.view_planes)):
                if self.view_planes[i] != other.view_planes[i]:
                    return False
        return super(Torus5dScene, self).__eq__(other)

    def __ne__(self, other):
        return not self == other

    def copy(self):
        return Torus5dScene(self.agent_type, self.module_name,
            self.rotation.copy() if self.rotation is not None else None,
            self.translation.copy() if self.translation is not None
                else None,
            self.background_color.copy()
                if self.background_color is not None else None,
            self.axis, self.axis_index, self.view_planes)


class Torus5dAgent(GLAgent):
    """This is an agent for all 5D Torus based modules.  Modified from Torus5dAgent."""

    # shape, node->coords, coords->node, link->coords, coords->link
    torusUpdateSignal   = Signal(list, dict, dict, dict, dict)

    # shape, ids, values, id->coords dict, coords->id dict
    nodeUpdateSignal = Signal(list, list)
    linkUpdateSignal = Signal(list, list)

    # node and link ID lists that are now highlighted
    highlightUpdateSignal = Signal(list, list)

    # node colormap and range, link colormap and range
    nodelinkSceneUpdateSignal = Signal(ColorMap, tuple, ColorMap, tuple)

    # Name of run for labeling
    runNameUpdateSignal = Signal(str)

    def __init__(self, parent, datatree):
        super(Torus5dAgent, self).__init__(parent, datatree)

        self.addRequest("nodes")
        self.addRequest("links")
        self.coords = None
        self.coords_table = None
        self.node_coords_dict = dict()
        self.coords_node_dict = dict()
        self.link_coords_table = None
        self.link_coords_dict = dict()
        self.coords_link_dict = dict()
        self.run = None
        self.shape = [0, 0, 0, 0, 0]
        self.requestUpdatedSignal.connect(self.requestUpdated)
        self.highlightSceneChangeSignal.connect(self.processHighlights)
        self.attributeSceneUpdateSignal.connect(self.processAttributeScenes)

        self.linkids = list()
        self.nodeids = list()
        self.linkvals = list()
        self.nodevals = list()
        self.linkrange = (0.0,1.0)
        self.noderange = (0.0,1.0)

    def registerNodeAttributes(self, indices):
        if self.registerRun(self.datatree.getItem(indices[0]).getRun()):
            self.requestAddIndices("nodes", indices)

    def registerLinkAttributes(self, indices):
        if self.registerRun(self.datatree.getItem(indices[0]).getRun()):
            self.requestAddIndices("links", indices)

    def registerRun(self, run):
        """Grab the hardware information from this run, verifying it is
           the appropriate network structure for this module.

           TODO: Actually verify.
        """
        if run is not self.run:
            self.run = run
            hardware = run["hardware"]

            if "coords" not in hardware:
                QMessageBox.warning(None, "Missing Information",
                    "Only runs done on 5D tori/mesh may use this module.\n"
                    + "Run meta file missing coords field.")
                return False

            coords = hardware["coords"]

            if len(coords) != 5:
                QMessageBox.warning(None, "Incorrect Shape",
                    "Only runs done on 5D tori/mesh may use this module.\n"
                    + "Run meta file coords field must be of five dimensions.")
                return False


            self.coords = coords
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
                self.link_coords_table.createIdAttributeMaps(link_coords, 'N.A.')

            self.torusUpdateSignal.emit(shape,
                node_coords_dict, coords_node_dict,
                link_coords_dict, coords_link_dict)

            self.runNameUpdateSignal.emit(self.run.name)
        return True

    @Slot(str)
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

        # Handle if color range has changed
        scene = self.requestScene("nodes")
        if values:
            scene.local_max_range = (min(values), max(values))
            if scene.use_max_range \
                and (scene.local_max_range[0] < scene.total_range[0] \
                     or scene.local_max_range[1] > scene.total_range[0]):
                scene.announceChange()

        self.noderange = scene.total_range
        self.nodeids = node_ids
        self.nodevals = values

        self.nodeUpdateSignal.emit(node_ids, values)


    def updateLinkValues(self):
        """When the link-related request is updated, this re-grabs the
           values associated with the link-ids and signals the change.
        """
        link_ids, values = self.requestOnDomain("links",
            domain_table = self.link_coords_table,
            row_aggregator = "mean", attribute_aggregator = "mean")

        scene = self.requestScene("links")
        if values:
            scene.local_max_range = (min(values), max(values))
            if scene.use_max_range \
                and (scene.local_max_range[0] < scene.total_range[0] \
                     or scene.local_max_range[1] > scene.total_range[0]):
                scene.announceChange()

        self.linkrange = scene.total_range
        self.linkids = link_ids
        self.linkvals = values

        self.linkUpdateSignal.emit(link_ids, values)

    @Slot()
    def processHighlights(self):
        """When highlights have changed, projects them onto the domains
           we care about and signals the changed local highlights.
        """
        if self.run is not None:
            #print 'PROCESS HIGHLIGHTS: coords_table = ' + str(self.coords_table) + ', link_coords_table = ' + str(self.link_coords_table)
            node_highlights = self.getHighlightIDs(self.coords_table, self.run)
            link_highlights = self.getHighlightIDs(self.link_coords_table,
                self.run)

            self.highlightUpdateSignal.emit(node_highlights, link_highlights)


    # TODO: Change the parameters to an object rather than bunch of lists
    def selectionChanged(self, highlight_ids):
        #print 'SELECTED:  highlight_ids = ' + str(highlight_ids)
        tables = list()
        runs = list()
        id_lists = list()
        for id_set in highlight_ids:
            runs.append(self.run)
            id_lists.append(id_set[1])
            if id_set[0] == "nodes":
                tables.append(self.coords_table)
            elif id_set[0] == "links":
                tables.append(self.link_coords_table)

        self.setHighlights(tables, runs, id_lists)

    @Slot()
    def processAttributeScenes(self):
        nodeScene = self.requestScene("nodes")
        linkScene = self.requestScene("links")

        if (nodeScene.total_range != self.noderange):
            self.noderange = nodeScene.total_range
            self.nodeUpdateSignal.emit(self.nodeids, self.nodevals)
        if (linkScene.total_range != self.linkrange):
            self.linkrange = linkScene.total_range
            self.linkUpdateSignal.emit(self.linkids, self.linkvals)

        self.nodelinkSceneUpdateSignal.emit(
            nodeScene.color_map, nodeScene.total_range,
            linkScene.color_map, linkScene.total_range)


class Torus5dGLWidget(GLWidget):
    # ------------------------------------------------------------------------
    # -------------------------      Initialize      -------------------------
    # ------------------------------------------------------------------------
    
    #TODO handle these signals
    #nodeColorChangeSignal = Signal() #to signal the frame to update
    #linkColorChangeSignal = Signal() #connect these via the frame
    def __init__(self, parent, dataModel, rotation = True, **keywords):
        super(Torus5dGLWidget, self).__init__(parent, rotation = rotation)

        if not boxfish_glut_initialized:
            boxfish_glut_initialzed = True
            glutInit()

        def kwarg(name, default_value):
            setattr(self, name, keywords.get(name, default_value))

        self.parent = parent
        self.dataModel = None

        # Note:  axis refers to which axis we're looking down in the 3d torus
        #   view.  The axis we're looking down in the overview (the 4th dimension)
        #   is the last value in the tuple (w, h, d) for each axis in [0, 1, 2, 3] below
        self.axis = 0   # Which axis the display should look down (default A)
        self.axis_index = 0 # Which horizontal and veritcal axis (default B, C)
        self.axis_map = { 0: [(1,2,3), (1,3,2), (2,3,1)], 1: [(0,2,3), (0,3,2), (2,3,0)], \
            2: [(0,1,3), (0,3,1), (1,3,0)], 3: [(0,1,2), (0,2,1), (1,2,0)]}

        # Constants for MiniMaps - user cannot modify
        self.node_size = 0.2
        self.node_pack_factor = 3.5  # How close to each link is (1.5 is .5 box space)
        self.gap = 2
        
        # Constants for Main View, user modifies link_width, e-link length (figure out)      
        self.link_width = 4. # 24
        self.link_pack_factor = 1 # 8.4
        # self.gap above
        self.elink_offset_center_x = 0.5 # 0.7
        self.elink_offset_center_y = 0.45 # 0.7
        self.elink_offset_diagonal_x = 0.4 # 2.2
        self.elink_offset_diagonal_y = 1.5 # 5.55

        self.outOfRangeOpacity = 0.07


        #self.gap = 10 * self.node_size * self.node_pack_factor # Spacing between successive cylinders
        

        kwarg("default_node_color", (0.2, 0.2, 0.2, 0.3))
        kwarg("node_cmap", self.parent.agent.requestScene("nodes").color_map)

        kwarg("default_link_color", (0.2, 0.2, 0.2, 0.3))
        kwarg("link_cmap", self.parent.agent.requestScene("links").color_map)



        # Color map bound changing
        self.delta = 0.05
        self.lowerBoundLinks = 0.
        self.upperBoundLinks = 1.
        self.lowerBoundNodes = 0.
        self.upperBoundNodes = 1.

        # Directions in which coords are laid out on the axes
        self.axis_directions = np.array([1, -1, -1])


        self.setDataModel(dataModel)
        self.clearNodes()
        self.clearLinks()

    def setDataModel(self, dataModel):
        # unregister with any old model
        if self.dataModel:
            self.dataModel.unregisterListener(self.update)
        # register with the new model
        self.dataModel = dataModel
        self.dataModel.registerListener(self.update)

    def clearNodes(self):
        """Sets the nodes to the default color."""
        self.node_colors = np.tile(self.default_node_color,
            list(self.dataModel.shape) + [1])

    def clearLinks(self):
        """Sets the links to the default color."""
        self.link_colors = np.tile(self.default_link_color,
            list(self.dataModel.shape) + [5, 1])

    # ------------------------------------------------------------------------
    # ---------------------------      Update      ---------------------------
    # ------------------------------------------------------------------------

    def update(self, nodes = True, links = True):
        '''Update the drawing, which includes lists and colors at this level.'''
        #print 'CALLING UPDATE_COLORS'
        self.updateColors(nodes, links)
        self.updateDrawing()

    def updateColors(self, nodes = True, links = True):
        """Update the drawing."""
        if nodes: self.updateCubeColors()
        if links: self.updateLinkColors()

    def updateCubeColors(self):
        """Updates the node colors from the dataModel."""
        self.clearNodes()
        for node in np.ndindex(*self.dataModel.shape):
            self.node_colors[node] = self.map_node_color(
                self.dataModel.node_values[node][0]) \
                if (self.dataModel.node_values[node][1] \
                > sys.float_info.epsilon) else self.default_node_color
        #print 'UPDATING CUBE COLORS:  self.node_colors.shape = ' + str(self.node_colors.shape)
        #self.updateView(nodes = True, links = False)
        #TODO #self.nodeColorChangeSignal.emit()

    def updateLinkColors(self):
        """Updates the link colors from the dataModel."""
        self.clearLinks()
        for node in np.ndindex(*self.dataModel.shape):
            for dim in range(5):
                #print 'avg_link_values = ' + str(self.dataModel.avg_link_values[node][dim][0]) + ', link_range = ' + str(link_range)
                self.link_colors[node][dim] = self.map_link_color(
                    self.dataModel.link_values[node][dim][0]) \
                    if (self.dataModel.link_values[node][dim][1] \
                    > sys.float_info.epsilon) else self.default_link_color
        #self.updateView(nodes = False, links = True)
        #TODO #self.linkColorChangeSignal.emit()

    def keyReleaseEvent(self, event):
        Qt.ShiftModifier = False # to fix the weird vertical translation bug
        super(Torus5dGLWidget, self).keyReleaseEvent(event)

    @Slot(list, list)
    def updateHighlights(self, node_ids, link_ids):
        """Given a list of the node and link ids to be highlighted, changes
           the alpha values accordingly and notifies listeners.

           In the future, when this becomes DataModel, will probably just
           update some property that the view will manipulate.
        """
        if node_ids or link_ids: # Alpha based on appearance in these lists
            #print 'UPDATE HIGHLIGHTS: node_ids = ' + str(node_ids) + ', link_ids = ' + str(link_ids)
            self.set_all_alphas(0.2)
            for node in node_ids:
                a, b, c, d, e = self.dataModel.node_to_coord[node]
                #print 'node:  a, b, c, d, e =',a,b,c,d,e
                self.node_colors[a, b, c, d, e, 3] = 1.0
            for link in link_ids:
                a, b, c, d, e, axis, direction = self.dataModel.link_coord_to_index(
                    self.dataModel.link_to_coord[link])
                #print 'link:  a, b, c, d, e, axis =',a,b,c,d,e,axis
                self.link_colors[a,b,c,d,e,axis,3] = 1.0
        else: # Alpha based on data-present value in dataModel
            for node in np.ndindex(*self.dataModel.shape):
                self.node_colors[node][3] = 1.0 \
                    if self.dataModel.node_values[node][1] > 0 else 0.2
                vals = self.dataModel.link_values[node]
                for dim in range(5):
                    self.link_colors[node][dim][3] = 1.0 \
                        if (vals[dim][1] > 0) else 0.2

        self.updateDrawing()
        #self.updateView()

    @Slot(ColorMap, tuple, ColorMap, tuple)
    def updateScene(self, node_cmap, node_range, link_cmap, link_range):
        """Handle AttributeScene information from agent."""
        self.node_cmap = node_cmap
        self.link_cmap = link_cmap
        self.update()

    def map_node_color(self, val, preempt_range = 0):
        """Turns a color value in [0,1] into a 4-tuple RGBA color.
           Used to map nodes.
        """
        if val < self.lowerBoundNodes-1e-8 or val > self.upperBoundNodes+1e-8:
            color = self.node_cmap.getColor(val, preempt_range)
            return [color[0], color[1], color[2], self.outOfRangeOpacity]
        else:
            return self.node_cmap.getColor(val, preempt_range)

    def map_link_color(self, val, preempt_range = 0):
        """Turns a color value in [0,1] into a 4-tuple RGBA color.
           Used to map links.
        """
        if val < self.lowerBoundLinks-1e-8 or val > self.upperBoundLinks+1e-8:
            color = self.link_cmap.getColor(val, preempt_range)
            return [color[0], color[1], color[2], self.outOfRangeOpacity]
        else:
            return self.link_cmap.getColor(val, preempt_range)

    def set_all_alphas(self, alpha):
        """Set all nodes and links to the same given alpha value."""
        self.node_colors[:,:,:,:,:,3] = alpha
        self.link_colors[:,:,:,:,:,:,3] = alpha


    def keyPressEvent(self, event):

        key_map = { 
                    "1" : lambda :  self.dataModel.changeLinkDirection(0),
                    "2" : lambda :  self.dataModel.changeLinkDirection(1),
                    "3" : lambda :  self.dataModel.changeLinkDirection(-1),
                   }

        if event.text() in key_map:
            key_map[event.text()]()
        else:
            super(Torus5dGLWidget, self).keyPressEvent(event)
    
class Torus5dColorTab(GLColorTab):
    """Color controls for Torus views."""

    def __init__(self, parent, mframe):
        """Create the Torus5dColorTab."""
        super(Torus5dColorTab, self).__init__(parent, mframe)

    def createContent(self):
        """Overriden createContent adds the node and link color controls
           to any existing ones in hte superclass.
        """
        super(Torus5dColorTab, self).createContent()

        self.layout.addSpacerItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildColorMapWidget("Node Colors",
            self.colorMapChanged, "nodes"))
        self.layout.addSpacerItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildColorMapWidget("Link Colors",
            self.colorMapChanged, "links"))

    @Slot(ColorMap, str)
    def colorMapChanged(self, color_map, tag):
        """Handles change events from the node and link color controls."""
        scene = self.mframe.agent.requestScene(tag)
        #print 'ColorTab.colorMapChanged: mframe =', self.mframe,', mframe.agent =', self.mframe.agent,', scene =',scene,', tag =',tag,', prev_color_map =',scene.color_map,', prev_color_map_name =',scene.color_map.color_map_name,', ',
        scene.color_map = color_map
        #print 'new_color_map =',scene.color_map,', new_color_map_name =',scene.color_map.color_map_name,', calling scene.announceChange'
        scene.processed = False
        scene.announceChange()
        # to handle color map changes within the module need an extra signal, 
        #   because ModuleAgent.receieveSceneFromParent() will think changes
        #   is false, because the scene has already been processed
        # TODO:  figure out exactly why this happens, talk to Kate?
        self.mframe.agent.colorMapUpdateSignal.emit() 

    def buildColorMapWidget(self, title, fxn, tag):
        """Integrates ColorMapWidgets into this Tab."""
        color_map = self.mframe.agent.requestScene(tag).color_map

        groupBox = QGroupBox(title, self)
        layout = QVBoxLayout()
        color_widget = ColorMapWidget(self, color_map, tag)
        color_widget.changeSignal.connect(fxn)

        layout.addWidget(color_widget)
        groupBox.setLayout(layout)
        return groupBox


class Torus5dRangeTab(QWidget):
    """Range controls for Torus views."""

    def __init__(self, parent, mframe):
        """Create the Torus5dColorTab."""
        super(Torus5dRangeTab, self).__init__(parent)

        self.mframe = mframe
        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)

        self.createContent()

        self.setLayout(self.layout)

    def createContent(self):
        """Overriden createContent adds the node and link range controls.
        """

        self.layout.addItem(QSpacerItem(5,5))

        self.layout.addWidget(self.buildRangeWidget("Node Range",
            self.rangeChanged, "nodes"))
        self.layout.addItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildRangeWidget("Link Range",
            self.rangeChanged, "links"))


    @Slot(bool, float, float, str)
    def rangeChanged(self, use_max, use_range_min, use_range_max, tag):
        """Handles change events from the node and link range controls."""
        print "Changing range to", use_range_min, use_range_max, use_max
        scene = self.mframe.agent.requestScene(tag)
        scene.total_range = (use_range_min, use_range_max)
        scene.use_max_range = use_max
        self.mframe.agent.processAttributeScenes()
        scene.announceChange()


    def buildRangeWidget(self, title, fxn, tag):
        """Integrates Range Widgets into this Tab."""
        current_range = self.mframe.agent.requestScene(tag).total_range
        max_range = self.mframe.agent.requestScene(tag).local_max_range
        use_max = self.mframe.agent.requestScene(tag).use_max_range

        groupBox = QGroupBox(title, self)
        layout = QVBoxLayout()
        range_widget = RangeWidget(self, use_max, current_range,
                max_range, tag)
        range_widget.changeSignal.connect(fxn)
        layout.addWidget(range_widget)
        groupBox.setLayout(layout)
        return groupBox
