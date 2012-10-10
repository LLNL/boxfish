import numpy as np
import operator

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.GLE import *

from boxfish.ModuleView import *
from boxfish.gl.GLWidget import GLWidget, set_perspective
from boxfish.gl.glutils import *

from GLModuleScene import *
from Torus3dModule import *

@Module("3D Torus - 3D View", Torus3dAgent, GLModuleScene)
class Torus3dView3d(Torus3dView):
    """This is a 3d rendering of a 3d torus.
    """
    def __init__(self, parent, parent_view = None, title = None):
        super(Torus3dView3d, self).__init__(parent, parent_view, title)

    def createView(self):
        return GLTorus3dView(self, self.colorModel)


class GLTorus3dView(GLWidget):
    def __init__(self, parent, colorModel):
        super(GLTorus3dView, self).__init__(parent)
        self.parent = parent
        self.colorModel = None

        self.seam = [0, 0, 0]  # Offsets for seam of the torus
        self.box_size = 0.2    # Length of edge of each node cube
        self.link_radius = self.box_size * .1   # Radius of link cylinders

        # Display lists for nodes and links
        self.cubeList = DisplayList(self.drawCubes)
        self.linkList = DisplayList(self.drawLinks)

        # Display list and settings for the axis
        self.axisLength = 0.3
        self.axisList = DisplayList(self.drawAxis)

        # Directions in which coords are laid out on the axes
        self.axis_directions = np.array([1, -1, -1])

        # Now go ahead and update things.
        self.setColorModel(colorModel)

    def setColorModel(self, colorModel):
        # unregister with any old model
        if self.colorModel:
            self.colorMode.unregisterListener(self.update)

        # register with the new model
        self.colorModel = colorModel
        self.colorModel.registerListener(self.update)
        #self.update()

    def update(self):
        self.cubeList.update()
        self.linkList.update()
        self.updateGL()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.orient_scene()
        self.cubeList()
        self.linkList()
        self.doAxis()

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
        spans = np.array(self.colorModel.shape, float)
        half_spans = (spans - 1) / -2 * self.axis_directions
        glTranslatef(*half_spans)

    def centerNode(self, node):
        """Translate view to coords where we want to render the node (x,y,z)"""
        node = (np.array(node, int) + self.seam) % self.colorModel.shape
        node *= self.axis_directions
        glTranslatef(*node)

    def drawCubes(self):
        glPushMatrix()
        self.centerView()

        for node in np.ndindex(*self.colorModel.shape):
            # draw a colored cube with its center at (0,0,0)
            glPushMatrix()
            self.centerNode(node)
            glColor4f(*self.colorModel.node_colors[node])
            glutSolidCube(self.box_size)
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

        for node in np.ndindex(*self.colorModel.shape):
            glPushMatrix()
            self.centerNode(node)
            colors = self.colorModel.avg_link_colors[node]

            # Draw links for each dim as poly cylinders
            for dim in range(3):
                glColor4f(*colors[dim])
                glePolyCylinder(poly_cylinders[dim], None, self.link_radius)

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
        select_buf_size = reduce(operator.mul, self.colorModel.shape) + 10
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
        for node in np.ndindex(*self.colorModel.shape):
            glLoadName(self.colorModel.coord_to_node[node])
            glPushMatrix()
            self.centerNode(node)
            glutSolidCube(box_size)
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

        return hitlist

