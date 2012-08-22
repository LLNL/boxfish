from PySide.QtCore import *
from PySide.QtGui import *
from PySide.QtOpenGL import *
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from SubDomain import *
from BFModule import *
from DataModel import *
import BFIcons

class FakeGLView(BFModuleWindow):

    display_name = "Dummy GL View"
    in_use = True

    def __init__(self, parent, parent_view = None, title = None):
        super(FakeGLView, self).__init__(parent, parent_view, title)

    def createModule(self):
        return BFModule(self.parent_view.module, self.parent_view.module.model)
        self.parent_view.module.registerChild(self.module)

    def createView(self):
        view = QWidget()

        layout = QGridLayout()
        layout.addWidget(BasicGLView(self), 0, 0, 1, 1)
        layout.setRowStretch(0, 10)
        layout.setContentsMargins(0, 0, 0, 0)
        view.setLayout(layout)
        return view


class BasicGLView(QGLWidget):

    def __init__(self, parent):
        super(BasicGLView, self).__init__(parent)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glClearColor(1.0, 1.0, 1.0, 1.0)
        glLightModelfv(GL_LIGHT_MODEL_AMBIENT, [1.0, 1.0, 1.0, 0.0])
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        gluLookAt(0, 0, -10, \
                0, 0, 0, \
                0, 1, 0)

    def resizeGL(self, w, h):

        glViewport(0, 0, w, h)


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


