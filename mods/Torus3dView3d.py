import numpy as np

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLE import *

from ModuleView import *
from GLModuleScene import *
from gl.GLWidget import GLWidget
from gl.glutils import *

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
        self.update()

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

