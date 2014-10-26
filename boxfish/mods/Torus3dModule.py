from PySide.QtCore import *

from GLModule import *
from boxfish.gl.GLWidget import GLWidget, set_perspective, setupPaintEvent
from boxfish.gl.glutils import *

import TorusIcons
from boxfish.ColorMaps import ColorMap, ColorMapWidget, drawGLColorBar

class Torus3dAgent(GLAgent):
    """This is an agent for all 3D Torus based modules."""

    # shape, node->coords, coords->node, link->coords, coords->link, link flag
    torusUpdateSignal   = Signal(list, dict, dict, dict, dict, bool)

    # ids values
    nodeUpdateSignal = Signal(list, list)
    linkUpdateSignal = Signal(list, list)

    # node and link ID lists that are now highlighted
    highlightUpdateSignal = Signal(list, list)

    # node colormap and range, link colormap and range
    nodelinkSceneUpdateSignal = Signal(ColorMap, tuple, ColorMap, tuple)

    # Name of run for labeling
    runNameUpdateSignal = Signal(str)

    def __init__(self, parent, datatree):
        super(Torus3dAgent, self).__init__(parent, datatree)

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
        self.shape = [0, 0, 0]
        self.has_links = False
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
                    "Only runs done on 3D tori/mesh may use this module.\n"
                    + "Run meta file missing coords field.")
                return False

            coords = hardware["coords"]

            if len(coords) != 3:
                QMessageBox.warning(None, "Incorrect Shape",
                    "Only runs done on 3D tori/mesh may use this module.\n"
                    + "Run meta file coords field must be of three dimensions.")
                return False

            self.coords = coords
            self.coords_table = run.getTable(hardware["coords_table"])
            shape = [hardware["dim"][coord] for coord in coords]

            node_coords_dict, coords_node_dict = \
                self.coords_table.createIdAttributeMaps(coords)

            if "link_coords_table" in hardware:
                link_coords = [hardware["source_coords"][coord]
                    for coord in coords]
                link_coords.extend([hardware["destination_coords"][coord]
                    for coord in coords])
                self.link_coords_table = run.getTable(hardware["link_coords_table"])
                link_coords_dict, coords_link_dict = \
                    self.link_coords_table.createIdAttributeMaps(link_coords)
                self.has_links = True

                self.torusUpdateSignal.emit(shape,
                    node_coords_dict, coords_node_dict,
                    link_coords_dict, coords_link_dict, self.has_links)

            else:
                self.has_links = False
                self.torusUpdateSignal.emit(shape,
                    node_coords_dict, coords_node_dict,
                    None, None, self.has_links)

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
            node_highlights = self.getHighlightIDs(self.coords_table, self.run)
            link_highlights = self.getHighlightIDs(self.link_coords_table,
                self.run)

            self.highlightUpdateSignal.emit(node_highlights, link_highlights)


    # TODO: Change the parameters to an object rather than bunch of lists
    def selectionChanged(self, highlight_ids):
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


def cmap_range(vals):
    """Use to normalize ranges for color maps.  Given an set of values,
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

def range_tuple(vals):
    min_val = np.min(vals)
    max_val = np.max(vals)
    return (min_val, max_val)


class Torus3dFrameDataModel(object):
    """This class is designed to hold data for a view of a 3d Torus.
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
        self.agent = None
        self.listeners = set()
        self._shape = None
        self.shape = [0, 0, 0]
        self.has_links = False
        self.link_direction = 0

    def clearNodes(self):
        # The first is the actual value, the second is a flag
        # indicating the validity of the data. 
        self.node_values = np.tile(0.0, self._shape + [2])

    def clearLinks(self):
        self.pos_link_values = np.tile(0.0, self._shape + [3, 2])
        self.neg_link_values = np.tile(0.0, self._shape + [3, 2])
        self.avg_link_values = np.tile(0.0, self._shape + [3, 2])
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
            self.clearNodes()
            self.clearLinks()

    # enforce that shape always looks like a tuple externally
    shape = property(lambda self: tuple(self._shape), setShape)

    @Slot(list, dict, dict, dict, dict, bool)
    def updateTorus(self, shape, node_coord, coord_node, link_coord, coord_link,
        has_links):
        """Updates the shape and id maps of this model to a new torus."""
        self.node_to_coord = node_coord
        self.coord_to_node = coord_node
        self.link_to_coord = link_coord
        self.coord_to_link = coord_link
        self.shape = shape
        self.has_links = has_links

    def _notifyListeners(self):
        for listener in self.listeners:
            listener()

    def registerListener(self, listener):
        self.listeners.add(listener)

    def unregisterListener(self, listener):
        self.listeners.remove(listener)

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

        self.clearNodes() # when only some values are given

        print self.agent.requestScene("nodes").total_range, "is total range for nodes"
        cval = self.agent.requestScene("nodes").cmap_range()
        for node_id, val in zip(nodes, vals):
            x, y, z = self.node_to_coord[node_id]
            self.node_values[x, y, z] = [cval(val), 1]

        self._notifyListeners()

    @Slot(list, list)
    def updateLinkData(self, links, vals):
        if not vals or not self.has_links:
            return

        self.clearLinks() # when only some values are given

        # Make sure we have no more values than links
        num_values = len(vals)
        num_links = np.product(self.shape) * 6
        if num_values > num_links:
            raise ValueError("received %d values for %d links!"
                             % (num_values, num_links))

        avg_link_values = np.zeros(self._shape + [3, 1])

        cval = self.agent.requestScene("links").cmap_range()
        for link_id, val in zip(links, vals):
            x, y, z, axis, direction = self.link_coord_to_index(
                self.link_to_coord[link_id])

            avg_link_values[x,y,z,axis] += val / 2.0
            c = cval(val)
            if direction > 0:
                self.pos_link_values[x,y,z,axis] = [c, 1]
            else:
                self.neg_link_values[x,y,z,axis] = [c, 1]

        print self.agent.requestScene("links").total_range, "is total range"
        for index in np.ndindex(self.shape):
            x, y, z = index
            for axis in range(3):
                color_val = cval(avg_link_values[x, y, z, axis])
                self.avg_link_values[x, y, z, axis] = [color_val, 1]

        self.changeLinkDirection(self.link_direction)



class Torus3dFrame(GLFrame):
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
        self.dataModel = Torus3dFrameDataModel()
        super(Torus3dFrame, self).__init__(parent, parent_frame, title)

        self.dataModel.agent = self.agent
        self.droppedDataSignal.connect(self.droppedData)
        self.agent.torusUpdateSignal.connect(self.dataModel.updateTorus)
        self.agent.nodeUpdateSignal.connect(self.dataModel.updateNodeData)
        self.agent.linkUpdateSignal.connect(self.dataModel.updateLinkData)
        self.agent.highlightUpdateSignal.connect(self.glview.updateHighlights)
        self.agent.nodelinkSceneUpdateSignal.connect(self.glview.updateScene)


        self.base_title = parent.windowTitle()
        self.agent.runNameUpdateSignal.connect(self.newRun)

        self.createDragOverlay(["nodes", "links"],
            ["Color Nodes", "Color Links"],
            [QPixmap(":/nodes.png"), QPixmap(":/links.png")])

        self.color_tab_type = Torus3dColorTab

    @Slot(list, str)
    def droppedData(self, index_list, tag):
        if tag == "nodes":
            self.agent.registerNodeAttributes(index_list)
        elif tag == "links":
            self.agent.registerLinkAttributes(index_list)

    @Slot(str)
    def newRun(self, name):
        self.parent().setWindowTitle(name + "  |  " + self.base_title)

    def updateNodeDefaultColor(self, color):
        self.glview.updateNodeDefaultColor(color)

    def buildTabDialog(self):
        """Adds a tab for ranges to the Tab Dialog.

           This tab will have controls for both nodes and links attributes.
           Note if these attributes are the same, they will affect each other.

        """
        super(Torus3dFrame, self).buildTabDialog()
        self.tab_dialog.addTab(Torus3dRangeTab(self.tab_dialog, self), "Data Range")


class Torus3dGLWidget(GLWidget):

    nodeColorChangeSignal = Signal()
    linkColorChangeSignal = Signal()

    def __init__(self, parent, dataModel, rotation = True, **keywords):
        super(Torus3dGLWidget, self).__init__(parent, rotation = rotation)

        def kwarg(name, default_value):
            setattr(self, name, keywords.get(name, default_value))

        self.parent = parent
        self.dataModel = None
        self.legendCalls = []
        self.legendCalls.append(self.drawNodeColorBar)
        self.legendCalls.append(self.drawLinkColorBar)

        self.box_size = 0.2
        self.link_width = 2.

        kwarg("default_node_color", (0.2, 0.2, 0.2, 0.3))
        kwarg("node_cmap", self.parent.agent.requestScene("nodes").color_map)

        kwarg("default_link_color", (0.2, 0.2, 0.2, 0.3))
        kwarg("link_cmap", self.parent.agent.requestScene("links").color_map)


        # Color map bound changing
        self.delta = 0.05
        self.lowerBound = 0
        self.upperBound = 1

        # Display lists for nodes and links
        self.cubeList = DisplayList(self.drawCubes)
        self.linkList = DisplayList(self.drawLinks)
        self.nodeBarList = DisplayList(self.drawNodeColorBar)
        self.linkBarList = DisplayList(self.drawLinkColorBar)
        self.nodeColorChangeSignal.connect(self.cubeList.update)
        self.linkColorChangeSignal.connect(self.linkList.update)

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
        #self.update()

    def update(self):
        """Update the drawing."""
        self.updateCubeColors()
        self.updateLinkColors()
        #self.updateGL()
        self.paintEvent(None)

    def updateDrawing(self):
        """Updates and redraws when the node/link information has changed."""
        self.cubeList.update()
        self.linkList.update()
        #self.updateGL()
        self.paintEvent(None)

    def clearNodes(self):
        """Sets the nodes to the default color."""
        self.node_colors = np.tile(self.default_node_color,
            list(self.dataModel.shape) + [1])

    def clearLinks(self):
        """Sets the links to the default color."""
        self.link_colors = np.tile(self.default_link_color,
            list(self.dataModel.shape) + [3, 1])

    def keyPressEvent(self, event):
        key_map = { 
                    "1" : lambda :  self.dataModel.changeLinkDirection(0),
                    "2" : lambda :  self.dataModel.changeLinkDirection(1),
                    "3" : lambda :  self.dataModel.changeLinkDirection(-1),
                   }

        if event.text() in key_map:
            key_map[event.text()]()
        else:
            super(TorusedGLWidget, self).keyPressEvent(event)

    def updateNodeDefaultColor(self, color):
        self.default_node_color = color
        self.updateCubeColors()
        #self.updateGL()
        self.paintEvent(None)

    def updateCubeColors(self):
        """Updates the node colors from the dataModel."""
        self.clearNodes()
        for node in np.ndindex(*self.dataModel.shape):
            self.node_colors[node] = self.map_node_color(
                self.dataModel.node_values[node][0]) \
                if (self.dataModel.node_values[node][1] \
                > sys.float_info.epsilon) else self.default_node_color
        self.nodeColorChangeSignal.emit()

    def updateLinkColors(self):
        """Updates the link colors from the dataModel."""
        self.clearLinks()
        #link_range = self.dataModel.avg_link_range[1] - self.dataModel.avg_link_range[0]
        #for node in np.ndindex(*self.dataModel.shape):
        #    for dim in range(3):
        #        self.link_colors[node][dim] = self.map_link_color(
        #            self.dataModel.avg_link_values[node][dim][0], link_range) \
        #            if (self.dataModel.avg_link_values[node][dim][1] \
        #            > sys.float_info.epsilon) else self.default_link_color
        for node in np.ndindex(*self.dataModel.shape):
            for dim in range(3):
                self.link_colors[node][dim] = self.map_link_color(
                    self.dataModel.link_values[node][dim][0]) \
                    if (self.dataModel.link_values[node][dim][1] \
                    > sys.float_info.epsilon) else self.default_link_color
        self.linkColorChangeSignal.emit()

    def doLegend(self, bar_width = 20, bar_height = 160, bar_x = 20,
        bar_y = 90):
        """Draws the legend information over the main view. This includes
           the colorbars and anything done in functions that have been
           appeneded to the legendCalls member of this class.
        """
        with overlays2D(self.width(), self.height(), self.bg_color):
            for func in self.legendCalls:
                func()


    # TODO: Move these crazy defaults somewhere sane
    def drawNodeColorBar(self, x = 20, y = 90, w = 20, h = 120):
        """Draw the color bar for nodes."""
        node_bar = []
        for i in range(11):
            node_bar.append(self.map_node_color(float(i)/10.0))

        self.textdraws.append(drawGLColorBar(node_bar, x, y, w, h, "N", self.height()))

        # I want this extra stuff to take up no more than 1/10 of the
        # screen space. Therefore total width = self.width() / 10

        #bar_width = int(max(2.0 / 13.0 * self.width(), 20))
        #bar_spacing = int(3.0 / 2.0 * bar_width)
        #bar_height = int(max(self.height() / 5.0, 150))
        #drawGLColorBar(node_bar, bar_spacing, y, bar_width, bar_height)

    def drawLinkColorBar(self, x = 50, y = 90, w = 20, h = 120):
        """Draw the color bar for links."""
        link_bar = []
        for i in range(11):
            link_bar.append(self.map_link_color(float(i)/10.0))

        self.textdraws.append(drawGLColorBar(link_bar, x, y, w, h, "L", self.height()))


    def map_node_color(self, val, preempt_range = 0):
        """Turns a color value in [0,1] into a 4-tuple RGBA color.
           Used to map nodes.
        """
        return self.node_cmap.getColor(val, preempt_range)

    def map_link_color(self, val, preempt_range = 0):
        """Turns a color value in [0,1] into a 4-tuple RGBA color.
           Used to map links.
        """
        if val < self.lowerBound-1e-8 or val > self.upperBound+1e-8:
            return [1,1,1,0]
        else:
            return self.link_cmap.getColor(val, preempt_range)

    def set_all_alphas(self, alpha):
        """Set all nodes and links to the same given alpha value."""
        self.node_colors[:,:,:,3] = alpha
        self.link_colors[:,:,:,:,3] = alpha

    @Slot(list, list)
    def updateHighlights(self, node_ids, link_ids):
        """Given a list of the node and link ids to be highlighted, changes
           the alpha values accordingly and notifies listeners.

           In the future, when this becomes DataModel, will probably just
           update some property that the view will manipulate.
        """
        if node_ids or link_ids: # Alpha based on appearance in these lists
            self.set_all_alphas(0.2)
            for node in node_ids:
                x, y, z = self.dataModel.node_to_coord[node]
                self.node_colors[x, y, z, 3] = 1.0
            for link in link_ids:
                x, y, z, axis, direction = self.dataModel.link_coord_to_index(
                    self.dataModel.link_to_coord[link])
                self.link_colors[x,y,z,axis,3] = 1.0
        else: # Alpha based on data-present value in dataModel
            for node in np.ndindex(*self.dataModel.shape):
                self.node_colors[node][3] = 1.0 \
                    if self.dataModel.node_values[node][1] > 0 else 0.2
                vals = self.dataModel.link_values[node]
                for dim in range(3):
                    self.link_colors[node][dim][3] = 1.0 \
                        if (vals[dim][1] > 0) else 0.2

        self.updateDrawing()

    @Slot(ColorMap, tuple, ColorMap, tuple)
    def updateScene(self, node_cmap, node_range, link_cmap, link_range):
        """Handle AttributeScene information from agent."""
        self.node_cmap = node_cmap
        self.link_cmap = link_cmap
        self.nodeBarList.update()
        self.linkBarList.update()
        self.update()
        # TODO: deal with the ranges, will have to move them into the 
        # dataModel

    # Stuff for Timo's bound changing, move into Torus
    def lowerLowerBound(self):
        self.lowerBound = max(self.lowerBound-self.delta,0)
        self.updateLinkColors()
        #self.updateGL()
        self.paintEvent(None)
        print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)

    def raiseLowerBound(self):
        self.lowerBound = min(self.lowerBound+self.delta,1)
        self.updateLinkColors()
        #self.updateGL()
        self.paintEvent(None)
        print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)

    def lowerUpperBound(self):
        self.upperBound = max(self.upperBound-self.delta,0)
        self.updateLinkColors()
        #self.updateGL()
        self.paintEvent(None)
        print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)

    def raiseUpperBound(self):
        self.upperBound = min(self.upperBound+self.delta,1)
        self.updateLinkColors()
        #self.updateGL()
        self.paintEvent(None)
        print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)


class Torus3dColorTab(GLColorTab):
    """Color controls for Torus views."""

    def __init__(self, parent, mframe):
        """Create the Torus3dColorTab."""
        super(Torus3dColorTab, self).__init__(parent, mframe)

    def createContent(self):
        """Overriden createContent adds the node and link color controls
           to any existing ones in the superclass.
        """
        super(Torus3dColorTab, self).createContent()

        self.layout.addSpacerItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildNodeDefaultColorWidget())
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
        scene.color_map = color_map
        scene.processed = False
        scene.announceChange()

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

    # Copied mostly from GLModule
    # TODO: Factor out this color widget builder to something reusable 
    # like the ColorMapWidget
    def buildNodeDefaultColorWidget(self):
        """Creates the controls for altering the node default color
           (when there is no node data).
        """
        widget = QWidget()
        layout = QHBoxLayout()
        label = QLabel("Default (no data) Node Color")
        self.nodeDefaultBox = ClickFrame(self, QFrame.Panel | QFrame.Sunken)
        self.nodeDefaultBox.setLineWidth(0)
        self.nodeDefaultBox.setMinimumHeight(12)
        self.nodeDefaultBox.setMinimumWidth(36)
        self.nodeDefaultBox.clicked.connect(self.nodeDefaultColorChange)

        #self.default_color = ColorMaps.gl_to_rgb(
        #    self.mframe.agent.module_scene.node_default_color)
        self.default_color = ColorMaps.gl_to_rgb(
            self.mframe.glview.default_node_color)
        self.nodeDefaultBox.setStyleSheet("QFrame {\n background-color: "\
            + ColorMaps.rgbStylesheetString(self.default_color) + ";\n"
            + "border: 1px solid black;\n border-radius: 2px;\n }")

        layout.addWidget(label)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.nodeDefaultBox)

        widget.setLayout(layout)
        return widget

    def nodeDefaultColorChange(self):
        """Handles change events to the background color."""
        color = QColorDialog.getColor(QColor(*self.default_color), self,
            "Default Node Color", QColorDialog.ShowAlphaChannel)

        self.default_color = [color.red(), color.green(), color.blue(),
            color.alpha()]
        self.nodeDefaultBox.setStyleSheet("QFrame {\n background-color: "\
            + ColorMaps.rgbStylesheetString(self.default_color) + ";\n"
            + "border: 1px solid black;\n border-radius: 2px;\n }")
        #self.mframe.agent.module_scene.node_default_color = np.array(
        #    [x / 255.0 for x in self.default_color])
        #self.mframe.agent.module_scene.announceChange()
        self.mframe.glview.default_node_color = np.array(
            [x / 255.0 for x in self.default_color])
        self.mframe.updateNodeDefaultColor(self.mframe.glview.default_node_color)

        # Normally we shouldn't have to do this but when I try opening the 
        # TabDialog with show() which gives back control, unfortunate things
        # can happen, so I use .exec_() which halts processing events
        # outside the dialog, so I force this color change here
        # Sadly this appears to only solve the problem for modules created
        # after this one. Will need to fix some other time...
        #self.mframe.updateNodeDefaultColor(
        #    self.mframe.agent.module_scene.node_default_color)

        #QApplication.processEvents()


class Torus3dRangeTab(QWidget):
    """Range controls for Torus views."""

    def __init__(self, parent, mframe):
        """Create the Torus3dColorTab."""
        super(Torus3dRangeTab, self).__init__(parent)

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
