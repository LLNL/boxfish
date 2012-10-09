from PySide.QtCore import *
from BFModule import *
from GLWidget import GLWidget
from OpenGL.GL import *
from OpenGL.GLUT import *

class Torus3dView3d(BFModuleWindow):
    """This is a 3d rendering of a 3d torus.
    """
    display_name = "3D Torus View"
    in_use = True

    def __init__(self, parent, parent_view = None, title = None):
        super(Torus3dView3d, self).__init__(parent, parent_view, title)

    def createModule(self):
        return BFModule(self.parent_view.module, self.parent_view.module.model)

    def createView(self):
        return GLBoxDisplay(self)


class GLBoxDisplay(GLWidget):
    def __init__(self, parent):
        super(GLBoxDisplay, self).__init__(parent)


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.orient_scene()

        glTranslatef(0.0, 0.0, -5.0)
        glColor4f(0.0, 1.0, 0.0, 1.0)
        glutSolidCube(5.0)

        glFlush()
