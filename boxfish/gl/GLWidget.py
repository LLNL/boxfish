"""\
Basic support for interactive OpenGL widgets in Qt.  See GLWindow class docs
for details.

Authors:
    Todd Gamblin, tgamblin@llnl.gov

Original rotation code was borrowed liberally from boxfish by Kate Isaacs
and Josh Levine.
"""

import math
import numpy as np
from exceptions import *

from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtOpenGL import *
from OpenGL.GL import *

from glutils import *

boxfish_glut_initialized = False

@contextmanager
def setupPaintEvent(self):
    painter = QPainter()
    painter.begin(self)
    painter.setRenderHint(QPainter.Antialiasing)

    glPushAttrib(GL_ALL_ATTRIB_BITS)
    self.initializeGL()

    yield

    glPopAttrib()

    for text in self.textdraws:
        painter.drawText(text.x, text.y, text.text)

    painter.end()


class GLWidget(QGLWidget):
    """ This class implements basic support for interactive OpenGL application
        This includes support for rotation and translation using the mouse.
        Other than handling mouse events for basic interactive features, this
        is just a regular QGLWidget, so the user still needs to implement
        resizeGL(), initializeGL(), and paintGL() to get their scene drawn.
    """

    transformChangeSignal = Signal(np.ndarray, np.ndarray)
    resizeSignal = Signal()

    def __init__(self, parent=None, **keywords):
        """Sets up initial values for dragging variables, translation, and
        rotation matrices.
        """
        super(GLWidget, self).__init__(parent)

        # Initialize last position and dragging flag to support mouse
        # interaction
        self.last_pos = [0,0,0]
        self.dragging = False

        # Initialize key tracking
        self.pressed_keys = set()
        self.setFocusPolicy(Qt.StrongFocus)

        # enabled/disabled features
        def kwarg(name, default, attr_name=None):
            if not attr_name: attr_name = name
            setattr(self, attr_name, keywords.get(name, default))

        # enable rotation and translation
        kwarg("rotation", True, "enable_rotation")
        kwarg("translation", True, "enable_translation")

        # perspective (vs. orthographic)
        kwarg("perspective", True, "enable_perspective")

        kwarg("fov", 45.0) # Vertical field of view in degrees
        kwarg("far_plane", 1000.0)  # Far clipping plane
        kwarg("near_plane", 0.1)    # Near clipping plane

        # contentious background color
        #kwarg("bg_color", [.94, .94, .94, 1.0])
        kwarg("bg_color", [1.0, 1.0, 1.0, 1.0])

        self.translation = np.zeros(3)
        self.rotation = np.identity(4)

        self.init = False

        self.textdraws = []

    def set_translation(self, t):
        """Ensure that translation is always a numpy array."""
        if type(t) == np.ndarray and t.dtype == float:
            self._translation = t
        else:
            self._translation = np.array(t, dtype=float)

        if self._translation.shape != (3,):
            raise ValueError("Illegal translation vector: " + str(t))

    def get_translation(self):
        return self._translation

    translation = property(get_translation, set_translation)

    def set_rotation(self, r):
        """Ensure that rotation is always a valid 4x4 numpy array."""
        if type(r) == np.ndarray and r.dtype == float:
            self._rotation = r
        else:
            self._rotation = np.array(r, dtype=float)

        if self._rotation.shape != (4,4):
            raise ValueError("Illegal rotation matrix: " + str(t))

    def get_rotation(self):
        return self._rotation

    rotation = property(get_rotation, set_rotation)


    def map_to_sphere(self, x, y):
        """This takes local x and y window coordinates and maps them to an
           arcball sphere based on the width and height of the window. This
           is used for quaternion rotation later in mouseMoveEvent().
        """
        width, height = self.width(), self.height()
        v = [0,0,0]

        v[0] = (2.0 * x - width) / width
        v[1] = (height - 2.0 * y) / height

        d = math.sqrt(v[0]*v[0] + v[1]*v[1])
        if d >= 1.0: d = 1.0

        v[2] = math.cos((math.pi/2.0) * d)

        a = v[0]*v[0]
        a += v[1]*v[1]
        a += v[2]*v[2]
        a = 1 / math.sqrt(a)

        v[0] *= a
        v[1] *= a
        v[2] *= a

        return v

    def initializeGL(self):
        glShadeModel(GL_SMOOTH)
        glClearColor(*self.bg_color)

        glClearDepth(1.0)
        glDepthFunc(GL_LESS)

        glLightfv(GL_LIGHT0, GL_AMBIENT,  [0.5, 0.5, 0.5, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE,  [1.0, 1.0, 1.0, 1.0])
        glLightfv(GL_LIGHT0, GL_POSITION, [-1.0, -1.0, 2.0, 1.0])

        glColorMaterial(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE)
        glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glLightModeli(GL_LIGHT_MODEL_TWO_SIDE, GL_TRUE)
        glShadeModel(GL_SMOOTH)

        glHint(GL_PERSPECTIVE_CORRECTION_HINT, GL_NICEST)
        glHint(GL_POLYGON_SMOOTH_HINT,         GL_NICEST)
        glHint(GL_LINE_SMOOTH_HINT,            GL_NICEST)
        glHint(GL_POINT_SMOOTH_HINT,           GL_NICEST)

        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glEnable(GL_LINE_SMOOTH)
        #glEnable(GL_POLYGON_SMOOTH) # Looks terrible on Quadro cards

        self.init = True

    def resizeGL(self, width, height):
        if (height == 0):
            height = 1
        glViewport(0, 0, width, height)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        aspect = float(width)/height
        if self.enable_perspective:
            set_perspective(self.fov,
                            aspect,
                            self.near_plane,
                            self.far_plane)
        else:
            maxdim = max(self.paths.shape)
            set_ortho(maxdim, aspect)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        self.resizeSignal.emit()

    #def paintGL(self):
    #    glFlush()


    def paintEvent(self, event):
        glFlush()


    def mouseDoubleClickEvent(self, event):
        self.parent.mouseDoubleClickEvent(event)

    def mousePressEvent(self, event):
        """Maps the click location to the sphere and records this in lastPos.  Also records that
           dragging has begun.
        """
        x, y = event.x(), event.y()
        self.last_pos = self.map_to_sphere(x, y)
        self.dragging = True

    def mouseReleaseEvent(self, event):
        """Ends dragging so that mouseMoveEvent() will know not to adjust
           things.
        """
        self.dragging = False

    def mouseMoveEvent(self, event):
        """This method rotates the scene around as the mouse moves, and it
           calls updateGL() to notify the UI that the system needs updating.
           Rotation is quaternion (axis/angle) based.
        """
        if not self.dragging:
            return

        if self.enable_rotation:
            x, y = event.x(), event.y()
            cur_pos = self.map_to_sphere(x, y)

            dx = cur_pos[0] - self.last_pos[0]
            dy = cur_pos[1] - self.last_pos[1]
            dz = cur_pos[2] - self.last_pos[2]

            tb_angle = 0
            tb_axis = [0,0,0]

            if dx != 0 or dy != 0 or dz != 0 :
                # compute theta and cross product
                tb_angle = 90.0 * math.sqrt(dx*dx + dy*dy + dz*dz)
                tb_axis[0] = self.last_pos[1]*cur_pos[2]\
                    - self.last_pos[2]*cur_pos[1]
                tb_axis[1] = self.last_pos[2]*cur_pos[0]\
                    - self.last_pos[0]*cur_pos[2]
                tb_axis[2] = self.last_pos[0]*cur_pos[1]\
                    - self.last_pos[1]*cur_pos[0]

                # update position
                self.last_pos = cur_pos

            # Once rotation has been computed, use OpenGL to add our rotation
            # to the current modelview matrix.  Then fetch the result and keep
            # it around.
            glLoadIdentity()
            glRotatef(0.5*tb_angle, tb_axis[0] , tb_axis[1], tb_axis[2])
            glMultMatrixd(self.rotation)
            self.rotation = glGetDouble(GL_MODELVIEW_MATRIX)
            #self.doLegend()


            #self.updateGL()
            self.paintEvent(event)
            self.transformChangeSignal.emit(self.rotation, self.translation)

    def wheelEvent(self, event):
        """Does translation in response to wheel events.  Within paintGL(),
           you will need to either call self.orient_scene() or do your own
           glTranslate() and glRotate() based on self.translation and
           self.rotation.
        """
        if self.enable_translation:
            if event.orientation() == Qt.Orientation.Vertical:
                if int(Qt.Key_Shift) in self.pressed_keys:
                    self.translation[1] += .01 * event.delta()
                else:
                    self.translation[2] += .01 * event.delta()

            elif event.orientation() == Qt.Orientation.Horizontal:
                self.translation[0] -= .01 * event.delta()

            self.transformChangeSignal.emit(self.rotation, self.translation)

            #self.updateGL()
            self.paintEvent(event)

    def keyPressEvent(self, event):
        self.pressed_keys.add(event.key())

    def keyReleaseEvent(self, event):
        key = event.key()
        if key in self.pressed_keys:
            self.pressed_keys.remove(key)
        self.keyAction(key)

    def keyAction(self, key):
        """To be implemented by subclasses"""
        pass

    def orient_scene(self):
        """You should call this from paintGL() to orient the scene before
           rendering. This will do translation and rotation so that rendering
           happens at the right location and orientation.
        """
        glLoadIdentity()
        glTranslatef(*self.translation)
        glMultMatrixd(self.rotation)


    def set_transform(self, rotation, translation):
        """Allows forcing the rotation and translation to the given values.
        """
        need_update = False

        if self.enable_translation and translation != None:
            self.translation = translation
            need_update = True
        if self.enable_rotation and rotation != None:
            self.rotation = rotation
            need_update = True

        if need_update:
            #self.updateGL()
            self.paintEvent(None)

    def change_background_color(self, color):
        """Changes the background color to the given."""
        if color is not None:
            self.bg_color = color
            glClearColor(*color)
            #self.updateGL()
            self.paintEvent(None)

def set_perspective(fovY, aspect, zNear, zFar):
    """NeHe replacement for gluPerspective"""
    fH = math.tan(fovY / 360.0 * math.pi) * zNear
    fW = fH * aspect
    glFrustum(-fW, fW, -fH, fH, zNear, zFar)

def set_ortho(maxdim, aspect):
    halfheight = maxdim
    halfwidth = aspect * halfheight
    glOrtho(-halfwidth, halfwidth, -halfheight, halfheight, -10, 100)

class TextDraw(object):
    """Holder of text and x and y position for qt painting."""

    def __init__(self, text, x, y):
        self.text = text
        self.x = x
        self.y = y
