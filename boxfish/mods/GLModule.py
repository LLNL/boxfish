import sys
import numpy as np
import matplotlib.cm as cm

from PySide.QtCore import *

from boxfish.ModuleAgent import *
from boxfish.ModuleView import *
from boxfish.SceneInfo import ModuleScene

class GLAgent(ModuleAgent):
    """This is an agent for all GL based modules."""

    # rotation and translation
    transformUpdateSignal = Signal(np.ndarray, np.ndarray)

    # background color
    bgColorUpdateSignal = Signal(np.ndarray)

    def __init__(self, parent, datatree):
        super(GLAgent, self).__init__(parent, datatree)

        self.receiveModuleSceneSignal.connect(self.processModuleScene)

    @Slot(ModuleScene)
    def processModuleScene(self, module_scene):
        if self.module_scene.module_name == module_scene.module_name:
            self.module_scene = module_scene.copy()
            self.transformUpdateSignal.emit(self.module_scene.rotation,
                self.module_scene.translation)
        if (self.module_scene.background_color is not None
            and module_scene.background_color is not None
            and (self.module_scene.background_color
            == module_scene.background_color).all()) \
            or self.module_scene.background_color != module_scene.background_color:
            self.module_scene.background_color \
                = module_scene.background_color
            self.bgColorUpdateSignal.emit(self.module_scene.background_color)


class GLView(ModuleView):
    """This is a base class for a rendering in OpenGL.
       Subclasses need to define this method:
           createView(self)
               Must return a subclass of GLWidget that displays the scene
               in the view.
    """
    def __init__(self, parent, parent_view = None, title = None):
        # Need to set this before the module initialization so that createView can use it.
        # TODO: not sure whether I like this order.  It's not very intuitive, but seems necessary.
        super(GLView, self).__init__(parent, parent_view, title)

        self.agent.transformUpdateSignal.connect(self.updateTransform)
        self.agent.bgColorUpdateSignal.connect(self.updateBGColor)

        self.view.transformChangeSignal.connect(self.transformChanged)

        self.color_tab_type = GLColorTab

    def transformChanged(self, rotation, translation):
        self.agent.module_scene.rotation = rotation
        self.agent.module_scene.translation = translation
        self.agent.module_scene.announceChange()

    @Slot(np.ndarray, np.ndarray)
    def updateTransform(self, rotation, translation):
        self.view.set_transform(rotation, translation)

    @Slot(np.ndarray)
    def updateBGColor(self, color):
        self.view.change_background_color(color)

    def buildTabDialog(self):
        super(GLView, self).buildTabDialog()
        self.tab_dialog.addTab(self.color_tab_type(self.tab_dialog,
            self), "Colors")


class GLModuleScene(ModuleScene):
    """Contains scene information for propagation between GL-based
       modules."""

    def __init__(self, agent_type, module_type, rotation = None,
        translation = None, background_color = None):
        super(GLModuleScene, self).__init__(agent_type, module_type)

        self.rotation = rotation
        self.translation = translation
        self.background_color = background_color

    def __equals__(self, other):
        if self.rotation == other.rotation \
            and self.translation == other.translation \
            and self.background_color == other.background_color:
            return True
        return False

    def copy(self):
        return GLModuleScene(self.agent_type, self.module_name,
            self.rotation.copy() if self.rotation is not None else None,
            self.translation.copy() if self.translation is not None
                else None,
            self.background_color.copy()
                if self.background_color is not None else None)


class GLColorTab(QWidget):
    """This is the widget for changing color related information in
       GL Views. The base takes care of GL background colors.
    """

    def __init__(self, parent, view):
        """Construct a GLColorTab with given parent (TabDialog) and
           ModuleAgent.
        """
        super(GLColorTab, self).__init__(parent)

        self.view = view

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)

        self.createContent()

        self.setLayout(self.layout)

    def createContent(self):
        self.layout.addWidget(self.buildBGColorWidget())


    def gl_to_rgb(self, color):
        if color is None:
            return [0, 0, 0, 0]

        return [int(255 * x) for x in color]

    def rgbString(self, color):
        return "rgb(" + str(color[0]) + "," + str(color[1]) + ","\
            + str(color[2]) + ")"

    def buildBGColorWidget(self):
        widget = QWidget()
        layout = QHBoxLayout()
        label = QLabel("Background Color")
        self.bgColorBox = ClickFrame(self, QFrame.Panel | QFrame.Sunken)
        self.bgColorBox.setLineWidth(0)
        self.bgColorBox.setMinimumHeight(12)
        self.bgColorBox.setMinimumWidth(36)
        self.bgColorBox.clicked.connect(self.bgColorChange)

        self.bgcolor = self.gl_to_rgb(self.view.agent.module_scene.background_color)
        self.bgColorBox.setStyleSheet("QFrame { background-color: "\
            + self.rgbString(self.bgcolor) + " }")

        layout.addWidget(label)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.bgColorBox)

        widget.setLayout(layout)
        return widget

    def bgColorChange(self):
        color = QColorDialog.getColor(QColor(*self.bgcolor), self)

        self.bgcolor = [color.red(), color.green(), color.blue(), self.bgcolor[3]]
        self.bgColorBox.setStyleSheet("QFrame { background-color: "\
            + self.rgbString(self.bgcolor) + " }")
        self.view.agent.module_scene.background_color = np.array(
            [x / 255.0 for x in self.bgcolor])
        self.view.agent.module_scene.announceChange()

        # Normally we shouldn't have to do this but when I try opening the 
        # TabDialog with show() which gives back control, unfortunate things
        # can happen, so I use .exec_() which halts processing events
        # outside the dialog, so I force this color change here
        # Sadly this appears to only solve the problem for modules created
        # after this one. Will need to fix some other time...
        self.view.updateBGColor(self.view.agent.module_scene.background_color)

        QApplication.processEvents()


