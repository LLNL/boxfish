import numpy as np

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLE import *

from ModuleView import *
from GLWidget import GLWidget
from GLModuleScene import GLModuleScene
from GLUtils import *
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
        x_span, y_span, z_span = self.colorModel.shape
        glTranslatef(-(x_span-1)/2.0,(y_span-1)/2.0,(z_span-1)/2.)

    def drawCubes(self):
        glPushMatrix()
        self.centerView()

        x_span, y_span, z_span = self.colorModel.shape
        for x, y, z in np.ndindex(*self.colorModel.shape):
            glPushMatrix()

            glColor4f(*self.colorModel.node_colors[x,y,z])
            glTranslatef((x + self.seam[0]) % x_span,
                         -((y + self.seam[1]) % y_span),
                         -((z + self.seam[2]) % z_span))

            # glut will draw a cube with its center at (0,0,0)
            glutSolidCube(self.box_size)
            glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()


    def drawLinks(self):
        glMaterialfv(GL_FRONT_AND_BACK,GL_DIFFUSE,[1.0, 1.0, 1.0, 1.0])

        glPushMatrix()
        self.centerView()

        x_span, y_span, z_span = self.colorModel.shape
        for x, y, z in np.ndindex(*self.colorModel.shape):
            glPushMatrix()

            glTranslatef((x + self.seam[0]) % x_span,
                         -((y + self.seam[1]) % y_span),
                         -((z + self.seam[2]) % z_span))

            # average positive and negative color values
            # TODO: should color model just store the normalized values?
            # TODO: Averaging colors doesn't really make sense if the color map isn't linear.
            pos = self.colorModel.pos_link_colors[x, y, z]
            neg = self.colorModel.neg_link_colors[x, y, z]
            colors = (pos + neg) / 2

            # x+
            glColor4f(*colors[0])
            glePolyCylinder([(-1, 0, 0), (0, 0, 0), (1, 0, 0), (2, 0, 0)],
                            None, self.link_radius)
            # y+
            glColor4f(*colors[1])
            glePolyCylinder([(0, -2, 0), (0, -1, 0), (0, 0, 0), (0, 1, 0)],
                            None, self.link_radius)
            # z+
            glColor4f(*colors[2])
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

