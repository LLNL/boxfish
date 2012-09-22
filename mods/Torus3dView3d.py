import numpy as np

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLE import *

from Module import *
from GLWidget import GLWidget
from GLUtils import *
from Torus3dModule import *

@Module("3D Torus - 3D View", Torus3dAgent, GLModuleScene)
class Torus3dView3d(Torus3dView):
    """This is a 3d rendering of a 3d torus.
    """
    def __init__(self, parent, parent_view = None, title = None):
        super(Torus3dView3d, self).__init__(parent, parent_view, title)

    def createView(self):
        return GLTorus3dView(self)

    def update(self):
        self.view.cubeList.update()
        self.view.linkList.update()

    def onNodeUpdate(self):
        self.update()

    def onLinkUpdate(self):
        self.update()

class GLTorus3dView(GLWidget):
    def __init__(self, parent):
        super(GLTorus3dView, self).__init__(parent)
        self.parent = parent

        # color for when we have no data
        self.default_color = [0.5, 0.5, 0.5, 0.5]
        self.default_link_color = [0.5, 0.5, 0.5, 1.0]

        self.shape = [0, 0, 0] # Set shape
        self.seam = [0, 0, 0]  # Offsets for seam of the torus
        self.box_size = 0.2    # Length of edge of each node cube

        # Radius of link cylinders
        self.link_radius = self.box_size * .1

        # Display lists for nodes and links
        self.cubeList = DisplayList(self.drawCubes)
        self.linkList = DisplayList(self.drawLinks)

        # Display list and settings for the axis
        self.axisLength = 0.3
        self.axisList = DisplayList(self.drawAxis)

    def getBoxSize(self):
        return self.box_size

    def setBoxSize(self, box_size):
        self.box_size = box_size
        self.updateGL()

    def getShape(self):
        return self.shape

    def setShape(self, shape):
        self.shape = self.parent.agent.shape
        self.clearNodes()
        self.clearLinks()

    def clearNodes(self):
        self.node_colors = np.tile(self.default_color, self.shape + [1])

    def clearLinks(self):
        self.link_colors = np.tile(self.default_link_color,
            self.shape + [3, 1])

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
        x_span, y_span, z_span = self.shape
        glTranslatef(-(x_span-1)/2.0,(y_span-1)/2.0,(z_span-1)/2.)

    def drawCubes(self):
        glPushMatrix()
        self.centerView()

        x_span, y_span, z_span = self.shape
        for x, y, z in np.ndindex(*self.shape):
            glPushMatrix()

            glColor4f(*self.node_colors[x,y,z])
            glTranslatef((x + self.seam[0]) % x_span,
                         -((y + self.seam[1]) % y_span),
                         -((z + self.seam[2]) % z_span))

            # glut will draw a cube with its center at (0,0,0)
            glutSolidCube(self.box_size)
            glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()


    def drawLinks(self):
        glMaterialfv(GL_FRONT_AND_BACK,GL_DIFFUSE,[1.0,1.0,1.0,1.0])

        glPushMatrix()
        self.centerView()

        x_span, y_span, z_span = self.shape
        for x, y, z in np.ndindex(*self.shape):
            glPushMatrix()

            glTranslatef((x + self.seam[0]) % x_span,
                         -((y + self.seam[1]) % y_span),
                         -((z + self.seam[2]) % z_span))

            # x+
            glColor4f(*self.link_colors[x,y,z,0])
            glePolyCylinder([(-1, 0, 0), (0, 0, 0), (1, 0, 0), (2, 0, 0)],
                            None, self.link_radius)
            # y+
            glColor4f(*self.link_colors[x,y,z,1])
            glePolyCylinder([(0, -2, 0), (0, -1, 0), (0, 0, 0), (0, 1, 0)],
                            None, self.link_radius)
            # z+
            glColor4f(*self.link_colors[x,y,z,2])
            glePolyCylinder([(0, 0, -2), (0, 0, -1), (0, 0, 0), (0, 0, 1)],
                            None, self.link_radius)
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

