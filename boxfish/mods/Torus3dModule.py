from PySide.QtCore import *

from GLModule import *
from boxfish.gl.GLWidget import GLWidget, set_perspective
from boxfish.gl.glutils import *
from OpenGL.GLUT import glutStrokeCharacter, GLUT_STROKE_ROMAN

import TorusIcons
from boxfish.ColorMaps import ColorMap, ColorMapWidget

class Torus3dAgent(GLAgent):
    """This is an agent for all 3D Torus based modules."""

    # shape, node->coords, coords->node, link->coords, coords->link
    torusUpdateSignal   = Signal(list, dict, dict, dict, dict)

    # shape, ids, values, id->coords dict, coords->id dict
    nodeUpdateSignal = Signal(list, list)
    linkUpdateSignal = Signal(list, list)

    # node and link ID lists that are now highlighted
    highlightUpdateSignal = Signal(list, list)

    # node colormap and range, link colormap and range
    nodelinkSceneUpdateSignal = Signal(ColorMap, tuple, ColorMap, tuple)

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
        self.highlightSceneChangeSignal.connect(self.processHighlights)
        self.attributeSceneUpdateSignal.connect(self.processAttributeScenes)

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


class Torus3dViewDataModel(object):
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
        self.listeners = set()
        self._shape = None
        self.shape = [0, 0, 0]
        self.node_range = (0,0)
        self.pos_link_range = (0,0)
        self.neg_link_range = (0,0)
        self.avg_link_range = (0,0)

    def clearNodes(self):
        # The first is the actual value, the second is a flag
        # indicating the validity of the data. 
        self.node_values = np.tile(0.0, self._shape + [2])

    def clearLinks(self):
        self.pos_link_values = np.tile(0.0, self._shape + [3, 2])
        self.neg_link_values = np.tile(0.0, self._shape + [3, 2])
        self.avg_link_values = np.tile(0.0, self._shape + [3, 2])

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
        self.node_to_coord = node_coord
        self.coord_to_node = coord_node
        self.link_to_coord = link_coord
        self.coord_to_link = coord_link
        self.shape = shape

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

        self.node_range = range_tuple(vals)
        cval = cmap_range(vals)
        for node_id, val in zip(nodes, vals):
            x, y, z = self.node_to_coord[node_id]
            self.node_values[x, y, z] = [cval(val), 1]

        self._notifyListeners()

    @Slot(list, list)
    def updateLinkData(self, links, vals):
        if not vals:
            return

        self.clearLinks() # when only some values are given

        # Make sure we have no more values than links
        num_values = len(vals)
        num_links = np.product(self.shape) * 6
        if num_values > num_links:
            raise ValueError("received %d values for %d links!"
                             % (num_values, num_links))

        avg_link_values = np.zeros(self._shape + [3, 1])

        self.pos_link_range = range_tuple(vals)
        self.neg_link_range = self.pos_link_range
        cval = cmap_range(vals)
        for link_id, val in zip(links, vals):
            x, y, z, axis, direction = self.link_coord_to_index(
                self.link_to_coord[link_id])

            avg_link_values[x,y,z,axis] += val
            c = cval(val)
            if direction > 0:
                self.pos_link_values[x,y,z,axis] = [c, 1]
            else:
                self.neg_link_values[x,y,z,axis] = [c, 1]

        self.avg_link_range = range_tuple(avg_link_values)
        cval = cmap_range(avg_link_values)
        for index in np.ndindex(self.shape):
            x, y, z = index
            for axis in range(3):
                color_val = cval(avg_link_values[x, y, z, axis])
                self.avg_link_values[x, y, z, axis] = [color_val, 1]

        self._notifyListeners()



class Torus3dView(GLView):
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
        self.dataModel = Torus3dViewDataModel()
        super(Torus3dView, self).__init__(parent, parent_view, title)

        self.agent.torusUpdateSignal.connect(self.dataModel.updateTorus)
        self.agent.nodeUpdateSignal.connect(self.dataModel.updateNodeData)
        self.agent.linkUpdateSignal.connect(self.dataModel.updateLinkData)
        self.agent.highlightUpdateSignal.connect(self.view.updateHighlights)
        self.agent.nodelinkSceneUpdateSignal.connect(self.view.updateScene)

        self.createDragOverlay(["nodes", "links"],
            ["Color Nodes", "Color Links"],
            [QPixmap(":/nodes.png"), QPixmap(":/links.png")])

        self.color_tab_type = Torus3dColorTab

    def droppedData(self, index_list, tag):
        if tag == "nodes":
            self.agent.registerNodeAttributes(index_list)
        elif tag == "links":
            self.agent.registerLinkAttributes(index_list)



class Torus3dGLWidget(GLWidget):

    nodeColorChangeSignal = Signal()
    linkColorChangeSignal = Signal()

    def __init__(self, parent, dataModel, rotation = True, **keywords):
        super(Torus3dGLWidget, self).__init__(parent, rotation = rotation)

        def kwarg(name, default_value):
            setattr(self, name, keywords.get(name, default_value))

        self.parent = parent
        self.dataModel = None

        self.box_size = 0.2

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
        self.updateCubeColors()
        self.updateLinkColors()
        self.updateGL()

    def updateDrawing(self):
        self.cubeList.update()
        self.linkList.update()
        self.updateGL()

    def clearNodes(self):
        self.node_colors = np.tile(self.default_node_color,
            list(self.dataModel.shape) + [1])

    def clearLinks(self):
        self.avg_link_colors = np.tile(self.default_link_color,
            list(self.dataModel.shape) + [3, 1])

    def updateCubeColors(self):
        self.clearNodes()
        node_range = self.dataModel.node_range[1] - self.dataModel.node_range[0]
        for node in np.ndindex(*self.dataModel.shape):
            self.node_colors[node] = self.map_node_color(
                self.dataModel.node_values[node][0], node_range) \
                if (self.dataModel.node_values[node][1] \
                > sys.float_info.epsilon) else self.default_node_color
        self.nodeColorChangeSignal.emit()

    def updateLinkColors(self):
        self.clearLinks()
        link_range = self.dataModel.avg_link_range[1] - self.dataModel.avg_link_range[0]
        for node in np.ndindex(*self.dataModel.shape):
            for dim in range(3):
                self.avg_link_colors[node][dim] = self.map_link_color(
                    self.dataModel.avg_link_values[node][dim][0], link_range) \
                    if (self.dataModel.avg_link_values[node][dim][1] \
                    > sys.float_info.epsilon) else self.default_link_color
        self.linkColorChangeSignal.emit()
    
    def doLegend(self, bar_width = 20, bar_height = 160, bar_x = 20,
        bar_y = 90):
        # Prepare to change modes
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
        glDisable(GL_BLEND)
        glEnable(GL_SCISSOR_TEST)

        with glModeMatrix(GL_PROJECTION):
            self.nodeBarList()
            
            
        with glModeMatrix(GL_PROJECTION):
            self.linkBarList()
            

        # Change mode back
        glViewport(0, 0, self.width(), self.height())
        #glLoadIdentity()
        #print "Perspective!"
        #set_perspective(self.fov, float(self.width())/self.height(),
        #    self.near_plane, self.far_plane)
        glDisable(GL_SCISSOR_TEST)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_BLEND)
        glClearColor(*self.bg_color)

    # TODO: Move these crazy defaults somewhere sane
    def drawNodeColorBar(self, x = 20, y = 90, w = 20, h = 120):
        node_bar = []
        for i in range(11):
            node_bar.append(self.map_node_color(float(i)/10.0))
        
        # I want this extra stuff to take up no more than 1/10 of the
        # screen space. Therefore total width = self.width() / 10

        self.drawColorBar(node_bar, x, y, w, h, "N")
        bar_width = int(max(2.0 / 13.0 * self.width(), 20))
        bar_spacing = int(3.0 / 2.0 * bar_width)
        bar_height = int(max(self.height() / 5.0, 150))
        #self.drawColorBar(node_bar, bar_spacing, y, bar_width, bar_height)

    def drawLinkColorBar(self, x = 50, y = 90, w = 20, h = 120):
        link_bar = []
        for i in range(11):
            link_bar.append(self.map_link_color(float(i)/10.0))
        
        self.drawColorBar(link_bar, x, y, w, h, "L")
        bar_width = int(max(2.0 / 13.0 * self.width(), 20))
        bar_spacing = int(3.0 / 2.0 * bar_width)
        bar_height = int(max(self.height() / 5.0, 150))
        #self.drawColorBar(link_bar, 2 * bar_spacing + bar_width, y, 
        #    bar_width, bar_height)

    def drawColorBar(self, colors, bar_x, bar_y, bar_width, bar_height,
        label = ""):
        glLoadIdentity()
        glScissor(bar_x, bar_y, bar_width, bar_height + 12)
        glViewport(bar_x, bar_y, bar_width, bar_height + 12)
        glOrtho(bar_x, bar_x + bar_width, bar_y, bar_y + bar_height + 12, -1, 1)
        glMatrixMode(GL_MODELVIEW)

        with glMatrix():
            glLoadIdentity()
            glTranslatef(bar_x, bar_y, 0)

            #glClearColor(1, 1, 1, 1)
            #glClear(GL_COLOR_BUFFER_BIT)
            #glClear(GL_DEPTH_BUFFER_BIT)

            segment_size = int(float(bar_height) / 10.0)

            for i in range(10):

                with glMatrix():
                    glTranslatef(0, i*segment_size, 0)
                    with glSection(GL_QUADS):
                        glColor3f(colors[i][0], colors[i][1], colors[i][2])
                        glVertex3f(0, 0, 0)
                        glVertex3f(bar_width, 0, 0)
                        glColor3f(colors[i+1][0], colors[i+1][1], 
                            colors[i+1][2])
                        glVertex3f(bar_width, segment_size, 0)
                        glVertex3f(0, segment_size, 0)

    
            # black box around gradient
            glColor3f(0.0, 0.0, 0.0)
            with glMatrix():
                with glSection(GL_LINES):
                    glVertex3f(0.01, 0.01, 0.01)
                    glVertex3f(bar_width, 0, 0.01)
                    glVertex3f(bar_width, 0, 0.01)
                    glVertex3f(bar_width, bar_height, 0.01)
                    glVertex3f(bar_width, bar_height, 0.01)
                    glVertex3f(0.01, bar_height, 0.01)
                    glVertex3f(0.01, bar_height, 0.01)
                    glVertex3f(0.01, 0.01, 0.01)

            default_text_height = 152.38
            scale_factor = 1.0 / default_text_height * segment_size
            scale_factor = 0.08
            if len(label) > 0:
                with glMatrix():
                    glTranslatef(7, bar_height + 3, 0.2)
                    glScalef(scale_factor, scale_factor, scale_factor)
                    for c in label:
                        print c
                        glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(c))


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
        self.avg_link_colors[:,:,:,:,3] = alpha

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
                self.avg_link_colors[x,y,z,axis,3] = 1.0
        else: # Alpha based on data-present value in dataModel
            for node in np.ndindex(*self.dataModel.shape):
                self.node_colors[node][3] = 1.0 \
                    if self.dataModel.node_values[node][1] > 0 else 0.2
                vals = self.dataModel.avg_link_values[node]
                for dim in range(3):
                    self.avg_link_colors[node][dim][3] = 1.0 \
                        if (vals[dim][1] > 0) else 0.2

        self.updateDrawing()

    @Slot(ColorMap, tuple, ColorMap, tuple)
    def updateScene(self, node_cmap, node_range, link_cmap, link_range):
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
        self.updateGL()
        print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)

    def raiseLowerBound(self):
        self.lowerBound = min(self.lowerBound+self.delta,1)
        self.updateLinkColors()
        self.updateGL()
        print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)

    def lowerUpperBound(self):
        self.upperBound = max(self.upperBound-self.delta,0)
        self.updateLinkColors()
        self.updateGL()
        print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)

    def raiseUpperBound(self):
        self.upperBound = min(self.upperBound+self.delta,1)
        self.updateLinkColors()
        self.updateGL()
        print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)


class Torus3dColorTab(GLColorTab):

    def __init__(self, parent, view):
        super(Torus3dColorTab, self).__init__(parent, view)

    def createContent(self):
        super(Torus3dColorTab, self).createContent()

        self.layout.addSpacerItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildColorMapWidget("Node Colors",
            self.colorMapChanged, "nodes"))
        self.layout.addSpacerItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildColorMapWidget("Link Colors",
            self.colorMapChanged, "links"))

    @Slot(ColorMap, str)
    def colorMapChanged(self, color_map, tag):
        scene = self.view.agent.requestScene(tag)
        scene.color_map = color_map
        scene.processed = False
        scene.announceChange()

    def buildColorMapWidget(self, title, fxn, tag):
        color_map = self.view.agent.requestScene(tag).color_map

        groupBox = QGroupBox(title, self)
        layout = QVBoxLayout()
        color_widget = ColorMapWidget(self, color_map, tag)
        color_widget.changeSignal.connect(fxn)

        layout.addWidget(color_widget)
        groupBox.setLayout(layout)
        return groupBox
