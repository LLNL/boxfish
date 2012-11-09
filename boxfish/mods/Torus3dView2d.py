import sys, math
import numpy as np

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLE import *

from Torus3dModule import *
from boxfish.gl.GLWidget import GLWidget
from boxfish.gl.glutils import *

class T3V2ModuleScene(GLModuleScene):
    def __init__(self, agent_type, module_type, rotation = None,
        translation = None, background_color = None, axis = 0):
        super(T3V2ModuleScene, self).__init__(agent_type, module_type,
            rotation, translation, background_color)

        self.axis = axis

    def __eq__(self, other):
        if self.axis != other.axis:
            return False
        return super(T3V2ModuleScene, self).__eq__(other)

    def __ne__(self, other):
        return not self == other

    def copy(self):
        return T3V2ModuleScene(self.agent_type, self.module_name,
            self.rotation.copy() if self.rotation is not None else None,
            self.translation.copy() if self.translation is not None
                else None,
            self.background_color.copy()
                if self.background_color is not None else None,
            self.axis)

class Torus3dView2dAgent(Torus3dAgent):

    axisUpdateSignal = Signal(int)

    def __init__(self, parent, datatree):
        super(Torus3dView2dAgent, self).__init__(parent, datatree)

    @Slot(ModuleScene)
    def processModuleScene(self, module_scene):
        super(Torus3dView2dAgent, self).processModuleScene(module_scene)

        if isinstance(module_scene, T3V2ModuleScene):
            self.module_scene = module_scene.copy()
            self.axisUpdateSignal.emit(self.module_scene.axis)



@Module("3D Torus - 2D View", Torus3dView2dAgent, T3V2ModuleScene)
class Torus3dView2d(Torus3dView):
    """This is a 2d rendering of a 3d torus.
       Initial concept for this view by Aaditya Landge.
    """
    def __init__(self, parent, parent_view = None, title = None):
        super(Torus3dView2d, self).__init__(parent, parent_view, title)

        self.view.axisUpdateSignal.connect(self.axisChanged)
        self.agent.axisUpdateSignal.connect(self.view.setAxis)

    def createView(self):
        return GLTorus2dView(self, self.dataModel)

    @Slot(int)
    def axisChanged(self, axis):
        self.agent.module_scene.axis = axis
        self.agent.module_scene.announceChange()


def cylinder(node, shape, axis):
    """This function is for finding the index of the squared cylinder
       containing particular points in the torus.  Cylinders are
       defined for a shape, along a particular axis.
       i.e., if the axis is going into the screen, cylinders are:

           +---------------+  Cylinder 4 (outermost)
           | +-----------+ |  Cylinder 3
           | | +-------+ | |  Cylinder 2
           | | | +---+ | | |  Cylinder 1
           | | | | + | | | |  Cylinder 0 (innermost)
           | | | +---+ | | |
           | | +-------+ | |
           | +-----------+ |
           +---------------+

       In the case of odd dimensions (as in above), the innermost
       cylinder is really not a cylinder but leftover odd links.

       A cylinder is computed for a point by by finding distance
       from nearest edge in each dimension.
    """
    dims = shape[:axis] + shape[axis+1:]
    num_cylinders = (min(dims) + 1) / 2
    nonaxis = node[:axis] + node[axis+1:]
    d_near_edge = [min(abs(d - n - 1), n) for n, d in zip(nonaxis, dims)]
    return num_cylinders - min(d_near_edge) - 1


def shift(point, axis, amount):
    """Increments the <axis> dimension in the point by <amount>"""
    p = list(point)
    p[axis] += amount
    return tuple(p)


class GLTorus2dView(Torus3dGLWidget):

    axisUpdateSignal = Signal(int)

    def __init__(self, parent, dataModel):
        super(GLTorus2dView, self).__init__(parent, dataModel, rotation=False)

        self.link_width = 2   # Width of links in the view in pixels

        self.axis = 2           # Which axis the display should look down (default Z)
        self.gap = 2            # Spacing between successive cylinders
        self.pack_factor = 3.5  # How close to pack boxes (1.5 is .5 box space)

        # selection interface
        self.right_drag = False

        self.miniMapSizes()
        self.miniMapList = DisplayList(self.miniMaps)
        self.legendCalls.append(self.miniMapList)
        self.resizeSignal.connect(self.miniMapList.update)

    # Convenience property for color model's shape
    shape = property(fget = lambda self: self.dataModel.shape)

    def initializeGL(self):
        """Turn up the ambient light for this view and enable simple
           transparency."""
        super(GLTorus2dView, self).initializeGL()
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [1.0, 1.0, 1.0, 1.0])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glLineWidth(self.link_width)

    def update(self):
        super(GLTorus2dView, self).update()

        # We really want this only to happen when the shape changes but
        # we have no way of checking this right now. May need to add
        # another signal to the data model
        self.updateAxis()

    def setAxis(self, a):
        if self.axis != a:
            self.axis = a
            self.axisUpdateSignal.emit(a)
            self.updateAxis()

    def increaseLinkWidth(self):
        self.link_width += 1
        glLineWidth(self.link_width)
        self.updateGL()

    def decreaseLinkWidth(self):
        self.link_width -= 1
        self.link_width = max(1,self.link_width)
        glLineWidth(self.link_width)
        self.updateGL()

#    def keyAction(self, key):
#        axis_map = { int(Qt.Key_X) : lambda : self.setAxis(0),
#                     int(Qt.Key_Y) : lambda : self.setAxis(1),
#                     int(Qt.Key_Z) : lambda : self.setAxis(2)
#                     int(Qt.Key_Z) : lambda : self.increaseLineWidth()
#                     }
#
#        if key in axis_map:
#            axis_map[key]()

    def keyPressEvent(self, event):
        key_map = { "x" : lambda :  self.setAxis(0),
                    "y" : lambda :  self.setAxis(1),
                    "z" : lambda :  self.setAxis(2),
                    "+" : lambda :  self.increaseLinkWidth(),
                    "-" : lambda :  self.decreaseLinkWidth(),
                    "<" : lambda :  self.lowerLowerBound(),
                    ">" : lambda :  self.raiseLowerBound(),
                    "," : lambda :  self.lowerUpperBound(),
                    "." : lambda :  self.raiseUpperBound(),
                    }
        if event.text() in key_map:
            key_map[event.text()]()
        else:
            GLWidget.keyPressEvent(self,event)

    def width_height(self):
        """Get the dimensions that span width and height of screen"""
        axis_map = { 0: (2, 1), 1: (0, 2), 2: (0, 1) }
        return axis_map[self.axis]


    def spans(self):
        """Span in OpenGL space of each dimension of the 2D view"""
        b = self.box_size * self.pack_factor
        def span(d):
            return b * (self.shape[self.axis] + self.gap) * (d+2)
        return [span(d) for d in self.shape]

    def updateAxis(self):
        # Rotate so that the camera is looking the correct direction
        # for the 2d view's axis
        glLoadIdentity()
        if self.axis == 0:
            glRotatef(90, 0, 1, 0)
        if self.axis == 1:
            glRotatef(90, 1, 0, 0)
        self.rotation = glGetDouble(GL_MODELVIEW_MATRIX)

        # Set initial position based on the size and axis of the model

        w, h = self.width_height()
        w_span, h_span = self.shape[w], self.shape[h]
        if w_span != 0 and h_span != 0:
            spans = self.spans()
            aspect = self.width() / float(self.height())

            # Check both distances instead of the one with the larger span
            # as we don't know how aspect ratio will come into play versus shape

            # Needed vertical distance
            fovy = float(self.fov) * math.pi / 360.
            disty = spans[h] / 2. / math.tan(fovy)

            # Needed horizontal distance
            fovx = float(self.fov) * aspect * math.pi / 360.
            distx = spans[w] / 2. / math.tan(fovx)

            self.translation = [0, 0, -max(distx, disty)]

        self.miniMapList.update()
        self.updateDrawing()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.orient_scene()
        self.cubeList()
        self.linkList()
        self.doLegend()

        super(GLTorus2dView, self).paintGL()

    def centerView(self):
        half_spans = np.array(self.spans(), np.float) / -2
        half_spans[self.axis] = 0
        half_spans *= self.axis_directions
        glTranslatef(*half_spans)


    def map2d(self, node):
        axis = self.axis
        b = self.box_size * self.pack_factor   # box plus spacing
        h = (self.shape[axis] * b) + self.gap  # grid spacing

        def coord(n, d):
            center = float(self.shape[d] - 1) / 2
            inset = node[axis] * b * np.sign(center - n)
            even = (self.shape[d] % 2 == 0)
            return h * (n + int(even and n > center)) + inset

        dim = range(3)
        dim.remove(axis)

        node2d = np.zeros(3)
        for d in dim:
            node2d[d] = coord(node[d], d)
        node2d *= self.axis_directions
        return node2d


    def drawCubes(self):
        glPushMatrix()
        self.centerView()

        for x, y, z in np.ndindex(*self.shape):
            glPushMatrix()

            # center around the mapped noded
            node = self.map2d((x, y, z))
            glTranslatef(*node)

            # Draw cube with node color from the model
            glColor4f(*self.node_colors[x,y,z])
            glutSolidCube(self.box_size)

            glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()


    def drawLinkCylinder(self, start, end):
        # calculate a vector in direction start -> end
        v = end - start

        # interpolate cylinder points
        cyl_points = [tuple(p) for p in [start - v, start, end, end + v]]

        # Draw link
        glePolyCylinder(cyl_points, None, self.link_width / 2.0)

    def drawLinkQuad(self, start, end):

        glBegin(GL_LINES)
        glVertex3fv(start)
        glVertex3fv(end)
        glEnd()

        return
        # unit vector in direction start -> end
        dir = end - start

        # vector in direction of axis
        ax = np.zeros(3)
        ax[self.axis] = 1.0

        # v is perpendicular to u and axis
        v = np.cross(ax, dir)
        v /= np.linalg.norm(v)
        v *= self.link_width / 2.0

        # draw corners and normal of quad.
        with glSection(GL_QUADS):
            glVertex3fv(start + v)
            glVertex3fv(end + v)
            glVertex3fv(end - v)
            glVertex3fv(start - v)
            glNormal3f(*ax)


    def drawLinks(self):
        glMaterialfv(GL_FRONT_AND_BACK,GL_DIFFUSE,[1.0, 1.0, 1.0, 1.0])
        glPushMatrix()
        self.centerView()

        shape, axis = self.shape, self.axis

        for start_node in np.ndindex(*shape):
            colors = self.avg_link_colors[start_node]

            start_cyl = cylinder(start_node, shape, axis)
            start = np.array(self.map2d(start_node))

            # iterate over dimensions.
            for dim in range(3):
                end_node = shift(start_node, dim, 1)

                # Skip torus wraparound links
                if end_node[dim] >= shape[dim]:
                    continue

                # Only render lines that connect points within the same cylinder
                end_cyl = cylinder(end_node, shape, axis)
                if start_cyl == end_cyl:
                    # Prevents occluding links on the innermost cylinder by not
                    # rendering links that would make T-junctions
                    if start_cyl == 0:
                        # find transverse dimension
                        for t in range(3):
                            if t != axis and t != dim: break
                        left_cyl = cylinder(shift(start_node, t, -1), shape, axis)
                        right_cyl = cylinder(shift(start_node, t, 1), shape, axis)
                        if end_cyl == right_cyl and end_cyl == left_cyl:
                            continue

                    end = np.array(self.map2d(end_node))
                    glColor4f(*colors[dim])
                    self.drawLinkQuad(start, end)

        glPopMatrix()


    def mousePressEvent(self, event):
        """We keep track of right-click drags for picking."""
        super(GLTorus2dView, self).mousePressEvent(event)

        if event.button() == Qt.RightButton:
            self.right_drag = True
        else:
            axis = self.isAxisChange(event.x(), self.height() - event.y())
            if axis >= 0:
                self.setAxis(axis)


    def mouseReleaseEvent(self, event):
        """We keep track of whether a drag occurred with right-click."""
        super(GLTorus2dView, self).mouseReleaseEvent(event)

        if self.right_drag:
            self.right_drag = False

    def isAxisChange(self, x, y):
        if x > self.minimap_x and x < self.minimap_x + self.minimap_size:
            if y > self.minimap_y0 and y < self.minimap_y0 + self.minimap_size:
                return 0
            if y > self.minimap_y1 and y < self.minimap_y1 + self.minimap_size:
                return 1
            if y > self.minimap_y2 and y < self.minimap_y2 + self.minimap_size:
                return 2
        return -1

    def miniMapSizes(self):
        self.minimap_x = 5
        self.minimap_y0 = self.height() - 75
        self.minimap_y1 = self.height() - 150
        self.minimap_y2 = self.height() - 225
        self.minimap_size = 70

    def miniMaps(self):
        self.miniMapSizes()
        self.drawMiniMaps(0, self.minimap_x, self.minimap_y0,
            self.minimap_size, self.minimap_size)
        self.drawMiniMaps(1, self.minimap_x, self.minimap_y1,
            self.minimap_size, self.minimap_size)
        self.drawMiniMaps(2, self.minimap_x, self.minimap_y2,
            self.minimap_size, self.minimap_size)
        #self.drawMiniMaps(0, 5, self.height() - 75, 70, 70)
        #self.drawMiniMaps(1, 5, self.height() - 150, 70, 70)
        #self.drawMiniMaps(2, 5, self.height() - 225, 70, 70)

    def drawMiniMaps(self, axis, x, y, w, h):
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        glScissor(x, y, w, h)
        glViewport(x, y, w, h)
        glOrtho(x, x+w, y, y+h, -1, 1)

        glMatrixMode(GL_MODELVIEW)

        with glMatrix():
            glLoadIdentity()
            glTranslatef(x, y, 0)
            
            glClearColor(*self.bg_color)
            glClear(GL_COLOR_BUFFER_BIT)
            glClear(GL_DEPTH_BUFFER_BIT)




            # Draw Border
            glColor3f(0.0, 0.0, 0.0)
            if axis == self.axis:
                glLineWidth(3.0)
            with glMatrix():
                with glSection(GL_LINES):
                    glVertex3f(0.01, 0.01, 0.01)
                    glVertex3f(w, 0.01, 0.01)
                    glVertex3f(w, 0.01, 0.01)
                    glVertex3f(w, h, 0.01)
                    glVertex3f(w, h, 0.01)
                    glVertex3f(0.01, h, 0.01)
                    glVertex3f(0.01, h, 0.01)
                    glVertex3f(0.01, 0.01, 0.01)
            if axis == self.axis:
                glLineWidth(self.link_width)
                    
