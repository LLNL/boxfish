import sys
import itertools
import matplotlib.cm as cm
import numpy as np

from Module import *

from GLWidget import GLWidget
from GLUtils import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLE import *

from Torus3dModule import Torus3dView

@Module("3D Torus - 3D View")
class Torus3dView3d(Torus3dView):
    """This is a 3d rendering of a 3d torus.
    """
    def __init__(self, parent, parent_view = None, title = None):
        super(Torus3dView3d, self).__init__(parent, parent_view, title)

    def createView(self):
        self.view = GLTorus3dView(self)
        self.view.rotationChangeSignal.connect(self.rotationChanged)
        self.view.translationChangeSignal.connect(self.translationChanged)
        return self.view

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


class GLTorus3dView(GLWidget):
    def __init__(self, parent):
        super(GLTorus3dView, self).__init__(parent)
        self.parent = parent

        # color for when we have no data
        self.default_color = [0.5, 0.5, 0.5, 0.5]
        self.default_link_color = [0.5, 0.5, 0.5, 1.0]

        # Set shape and set up color matrix
        self.shape = [0, 0, 0]
        # Offsets representing seam of the torus
        self.seam = [0, 0, 0]

        # Size of one edge of each cube representing a node
        self.box_size = 0.2

        # Radius of link cylinders
        self.link_radius = self.box_size * .1

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
        self.drawCubes()
        self.drawLinks()
        self.drawAxis()

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
        glViewport(0,0,80,80)

        glPushMatrix()
        glPushAttrib(GL_CURRENT_BIT)
        glPushAttrib(GL_LINE_BIT)
        glLineWidth(2.0)

        len = 0.3
        glLoadIdentity()
        glTranslatef(0,0, -len)
        glMultMatrixd(self.rotation)
        glDisable(GL_DEPTH_TEST)

        with glSection(GL_LINES):
            glColor4f(1.0, 0.0, 0.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(len, 0, 0)

            glColor4f(0.0, 1.0, 0.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, -len, 0)

            glColor4f(0.0, 0.0, 1.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, 0, -len)

        glEnable(GL_DEPTH_TEST)

        glPopAttrib()
        glPopAttrib()
        glPopMatrix()

        glViewport(0, 0, self.width(), self.height())


class GLModuleScene(ModuleScene):
    """TODO: Docs"""

    def __init__(self, rotation = None, translation = None):
        super(ModuleScene, self).__init__()

        self.rotation = rotation
        self.translation = translation

    def __equals__(self, other):
        if self.rotation == other.rotation \
                and self.translation == other.translation:
            return True
        return False

    def copy(self):
        if self.rotation is not None and self.translation is not None:
            return GLModuleScene(self.rotation.copy(), self.translation.copy())
        elif self.rotation is not None:
            return GLModuleScene(self.rotation.copy(), None)
        elif self.translation is not None:
            return GLModuleScene(None, self.translation.copy())
        else:
            return GLModuleScene()
