import numpy as np
import operator

from OpenGL.GL import *
from OpenGL.GLU import *

from boxfish.gl.GLWidget import GLWidget, set_perspective, setupPaintEvent
from boxfish.gl.glutils import *

from Torus3dModule import *

class T3V3ModuleScene(GLModuleScene):

    def __init__(self, agent_type, module_type, rotation = None,
        translation = None, background_color = None, draw_links = True,
        node_size = 0.2):
        super(T3V3ModuleScene, self).__init__(agent_type, module_type,
            rotation, translation, background_color)

        self.draw_links = draw_links
        self.node_size = node_size

    def __eq__(self, other):
        if self.draw_links != other.draw_links:
            return False
        if self.node_size != other.node_size:
            return False
        return super(T3V3ModuleScene, self).__eq__(other)

    def __ne__(self, other):
        return not self == other

    def copy(self):
        return T3V3ModuleScene(self.agent_type, self.module_name,
            self.rotation.copy() if self.rotation is not None else None,
            self.translation.copy() if self.translation is not None
                else None,
            self.background_color.copy()
                if self.background_color is not None else None,
            self.draw_links, self.node_size)


class Torus3dView3dAgent(Torus3dAgent):

    drawLinksUpdateSignal = Signal(bool)
    nodeSizeUpdateSignal = Signal(float)

    def __init__(self, parent, datatree):
        super(Torus3dView3dAgent, self).__init__(parent, datatree)

    @Slot(ModuleScene)
    def processModuleScene(self, module_scene):
        super(Torus3dView3dAgent, self).processModuleScene(module_scene)

        if self.module_scene.draw_links != module_scene.draw_links:
            self.module_scene.draw_links = module_scene.draw_links
            self.drawLinksUpdateSignal.emit(self.module_scene.draw_links)
        if self.module_scene.node_size != module_scene.node_size:
            self.module_scene.node_size = module_scene.node_size
            self.nodeSizeUpdateSignal.emit(self.module_scene.node_size)


@Module("3D Torus - 3D View", Torus3dView3dAgent, T3V3ModuleScene)
class Torus3dView3d(Torus3dFrame):
    """This is a 3d rendering of a 3d torus.
    """

    def __init__(self, parent, parent_frame = None, title = None):
        super(Torus3dView3d, self).__init__(parent, parent_frame, title)

        self.draw_links = True
        self.agent.drawLinksUpdateSignal.connect(self.glview.setDrawLinks)
        self.agent.nodeSizeUpdateSignal.connect(self.glview.setNodeSize)

    def createView(self):
        self.glview = GLTorus3dView(self, self.dataModel)
        return self.glview

    def buildTabDialog(self):
        super(Torus3dView3d, self).buildTabDialog()
        self.tab_dialog.addTab(Torus3dView3dRenderTab(self.tab_dialog,
            self), "Rendering")


class GLTorus3dView(Torus3dGLWidget):

    def __init__(self, parent, dataModel):
        super(GLTorus3dView, self).__init__(parent, dataModel)

        self.seam = [0, 0, 0]  # Offsets for seam of the torus
        self.link_radius = self.box_size * .1   # Radius of link cylinders
        self.draw_links = True

        # Display list and settings for the axis
        self.axisLength = 0.3
        self.axisList = DisplayList(self.drawAxis)


        self.change_background_color(\
            self.parent.agent.module_scene.background_color)



    def setDrawLinks(self, draw_links):
        self.draw_links = draw_links
        if not self.draw_links:
            if self.drawLinkColorBar in self.legendCalls:
                self.legendCalls.remove(self.drawLinkColorBar)
        else:
            if not self.drawLinkColorBar in self.legendCalls:
                self.legendCalls.append(self.drawLinkColorBar)
        #self.updateGL()
        self.paintEvent(None)

    def setNodeSize(self, node_size):
        self.box_size = node_size
        self.cubeList.update()
        #self.updateGL()
        self.paintEvent(None)

    def paintEvent(self, event):
        with setupPaintEvent(self):
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glGetError()
            self.orient_scene()
            self.cubeList()
            if self.draw_links:
                self.linkList()
            self.doAxis()
            self.doLegend()

        super(GLTorus3dView, self).paintGL()

    def initializeGL(self):
        """We use transparency simply here, so we enable GL_BLEND."""
        super(GLTorus3dView, self).initializeGL()

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def centerView(self):
        """ First we move the coordinate system by half the size of the total
            grid. This will allow us to draw boxes and links at (0,0,0),
            (1,0,0),... etc. but they will appear centered around the global
            origin.
        """
        spans = np.array(self.dataModel.shape, float)
        half_spans = (spans - 1) / -2 * self.axis_directions
        glTranslatef(*half_spans)

    def centerNode(self, node):
        """Translate view to coords where we want to render the node (x,y,z)"""
        node = (np.array(node, int) + self.seam) % self.dataModel.shape
        node *= self.axis_directions
        glTranslatef(*node)

    def drawCubes(self):
        glPushMatrix()
        self.centerView()

        for node in np.ndindex(*self.dataModel.shape):
            # draw a dataed cube with its center at (0,0,0)
            glPushMatrix()
            self.centerNode(node)
            glColor4f(*self.node_colors[node])
            notGlutSolidCube(self.box_size)
            glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()


    def drawLinks(self):
        glMaterialfv(GL_FRONT_AND_BACK,GL_DIFFUSE,[1.0, 1.0, 1.0, 1.0])
        glPushMatrix()
        self.centerView()

        # origin-relative poly cylinder points for each dimension
        poly_cylinders =[[(-1, 0, 0), (0, 0,  0), (1, 0, 0), (2, 0, 0)],
                         [(0, -2, 0), (0, -1, 0), (0, 0, 0), (0, 1, 0)],
                         [(0, 0, -2), (0, 0, -1), (0, 0, 0), (0, 0, 1)]]

        for node in np.ndindex(*self.dataModel.shape):
            glPushMatrix()
            self.centerNode(node)
            colors = self.link_colors[node]

            # Draw links for each dim as poly cylinders
            for dim in range(3):
                glColor4f(*colors[dim])
                notGlePolyCylinder(poly_cylinders[dim], None, self.link_radius)

            glPopMatrix()
        glPopMatrix()

    def drawAxis(self):
        """This function does the actual drawing of the lines in the axis."""
        glLineWidth(2.0)
        with glSection(GL_LINES):
            glColor4f(1.0, 0.0, 0.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(self.axisLength, 0, 0)

            glColor4f(0.0, 1.0, 0.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, -self.axisLength, 0)

            glColor4f(0.0, 0.0, 1.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, 0, -self.axisLength)

    def doAxis(self):
        """This function does the actual drawing of the lines in the axis."""
        glViewport(0,0,80,80)

        glPushMatrix()
        with attributes(GL_CURRENT_BIT, GL_LINE_BIT):
            glLoadIdentity()
            glTranslatef(0,0, -self.axisLength)
            glMultMatrixd(self.rotation)
            with disabled(GL_DEPTH_TEST):
                self.axisList()

        glPopMatrix()
        glViewport(0, 0, self.width(), self.height())

    def mousePressEvent(self, event):
        """We capture right clicking for picking here."""
        super(GLTorus3dView, self).mousePressEvent(event)

        if event.button() == Qt.RightButton:
            self.parent.agent.selectionChanged([["nodes", self.doPick(event)]])

    def doPick(self, event):
        """Allow the user to pick nodes."""
        # Adapted from Josh Levine's version in Boxfish 0.1
        #steps:
        #render the scene with labeled nodes
        #find the color of the pixel @self.x, self.y
        #map color back to id and return

        #disable unneded
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
        glDisable(GL_BLEND)

        #set up the selection buffer
        select_buf_size = reduce(operator.mul, self.dataModel.shape) + 10
        glSelectBuffer(select_buf_size)

        #switch to select mode
        glRenderMode(GL_SELECT)

        #initialize name stack
        glInitNames()
        glPushName(0)

        #set up the pick matrix to draw a narrow view
        viewport = glGetIntegerv(GL_VIEWPORT)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        #this sets the size and location of the pick window
        #changing the 1,1 will change sensitivity of the pick
        gluPickMatrix(event.x(),(viewport[3]-event.y()),
            1,1,viewport)
        set_perspective(self.fov, self.width()/float(self.height()),
            self.near_plane, self.far_plane)
        #switch back to modelview and draw the scene
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(*self.translation[:3])
        glMultMatrixd(self.rotation)

        #let's draw some red boxes, color is inconsequential
        box_size = self.box_size
        glColor3f(1.0, 0.0, 0.0)

        # Redo the drawing
        glPushMatrix()
        self.centerView()

        # And draw all the cubes
        # color index variable
        for node in np.ndindex(*self.dataModel.shape):
            glLoadName(self.dataModel.coord_to_node[node])
            glPushMatrix()
            self.centerNode(node)
            notGlutSolidCube(box_size)
            glPopMatrix()

        glPopMatrix()

        #pop projection matrix
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glFlush()

        #get the hit buffer
        glMatrixMode(GL_MODELVIEW)
        pick_buffer = glRenderMode(GL_RENDER)

        #this code finds the nearest hit.  
        #Otherwise, populate hitlist with hit[2] for all
        #pick_buffer has a 3-tuple of info, [near, far, name]
        nearest = 4294967295
        hitlist = []
        for hit in pick_buffer :
            if hit[0] < nearest :
              nearest = hit[0]
              hitlist = [hit[2][0]]

        #go back to normal rendering
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        print hitlist
        return hitlist

class Torus3dView3dRenderTab(QWidget):

    def __init__(self, parent, mframe):
        super(Torus3dView3dRenderTab, self).__init__(parent)

        self.mframe = mframe
        self.number_of_ticks = 10

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)

        self.createContent()

        self.setLayout(self.layout)

    def createContent(self):
        self.layout.addWidget(self.buildLinksCheckbox())
        self.layout.addItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildBoxSlider())

    def buildLinksCheckbox(self):
        widget = QWidget()
        layout = QHBoxLayout()
        self.drawLinksCheckbox = QCheckBox("Draw links", widget)
        self.drawLinksCheckbox.setChecked(
            self.mframe.agent.module_scene.draw_links)
        self.drawLinksCheckbox.stateChanged.connect(self.drawLinksChanged)
        layout.addWidget(self.drawLinksCheckbox)
        widget.setLayout(layout)
        return widget

    @Slot(int)
    def drawLinksChanged(self, state):
        self.mframe.agent.module_scene.draw_links \
            = self.drawLinksCheckbox.isChecked()
        self.mframe.agent.module_scene.announceChange()
        self.mframe.glview.setDrawLinks(self.drawLinksCheckbox.isChecked())

        QApplication.processEvents()

    def buildBoxSlider(self):
        widget = QWidget()
        layout = QHBoxLayout()
        label = QLabel("Node size: ")
        layout.addWidget(label)
        layout.addItem(QSpacerItem(5,5))

        self.boxslider = QSlider(Qt.Horizontal, widget)
        self.boxslider.setRange(0,self.number_of_ticks)
        self.boxslider.setTickInterval(1)
        self.boxslider.setSliderPosition(
            int(self.number_of_ticks * self.mframe.glview.box_size))
        self.boxslider.valueChanged.connect(self.boxSliderChanged)

        layout.addWidget(self.boxslider)
        widget.setLayout(layout)
        return widget

    @Slot(int)
    def boxSliderChanged(self, value):
        node_size = value / float(self.number_of_ticks)
        self.mframe.agent.module_scene.node_size = node_size
        self.mframe.agent.module_scene.announceChange()
        self.mframe.glview.setNodeSize(node_size)

        QApplication.processEvents()
