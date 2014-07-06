import sys
import numpy as np
import matplotlib.cm as cm

from PySide.QtCore import *

from boxfish.ModuleAgent import *
from boxfish.ModuleFrame import *
from boxfish.SceneInfo import ModuleScene
import boxfish.ColorMaps as ColorMaps

class GLAgent(ModuleAgent):
    """This is an agent for all GL based modules."""

    # rotation and translation
    transformUpdateSignal = Signal(np.ndarray, np.ndarray)

    # background color
    bgColorUpdateSignal = Signal(np.ndarray)

    def __init__(self, parent, datatree):
        """Creates an agent for GL type modules."""
        super(GLAgent, self).__init__(parent, datatree)

        self.receiveModuleSceneSignal.connect(self.processModuleScene)

    @Slot(ModuleScene)
    def processModuleScene(self, module_scene):
        """Handles module-specific scene changes in all GL type modules.

           If subclassing GLModuleScene, override this class and be
           sure to call the superclass' version of this method.
        """
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


class GLFrame(ModuleFrame):
    """This is a base class for a rendering in OpenGL.
       Subclasses need to define this method:
           createView(self)
               Must return a subclass of GLWidget that displays the scene
               in the view.
    """
    def __init__(self, parent, parent_frame = None, title = None):
        """Creates the View skeleton for GL type Modules."""
        # Need to set this before the module initialization so that createView can use it.
        # TODO: not sure whether I like this order.  It's not very intuitive, but seems necessary.
        super(GLFrame, self).__init__(parent, parent_frame, title)

        self.agent.transformUpdateSignal.connect(self.updateTransform)
        self.agent.bgColorUpdateSignal.connect(self.updateBGColor)

        self.glview.transformChangeSignal.connect(self.transformChanged)

        self.color_tab_type = GLColorTab

    def transformChanged(self, rotation, translation):
        """Called when the GLWidget within this view's transform changes."""
        self.agent.module_scene.rotation = rotation
        self.agent.module_scene.translation = translation
        self.agent.module_scene.announceChange()

    @Slot(np.ndarray, np.ndarray)
    def updateTransform(self, rotation, translation):
        """Slot for transform changes coming from ModuleScene information."""
        self.glview.set_transform(rotation, translation)

    @Slot(np.ndarray)
    def updateBGColor(self, color):
        """Slot for background color changes coming from ModuleScene
           information.
        """
        self.glview.change_background_color(color)

    def buildTabDialog(self):
        """Adds a tab for colors (e.g. background color) to the Tab Dialog.

           To add more functionality to the color tab, subclass GLColorTab
           and set the ModuleView's color_tab_type member to the new class.
           See GLColorTab class for tips on subclassing it.
        """
        super(GLFrame, self).buildTabDialog()
        self.tab_dialog.addTab(self.color_tab_type(self.tab_dialog,
            self), "Colors")


class GLModuleScene(ModuleScene):
    """Contains scene information for propagation between GL-based
       modules such as transform state and background color.
    """

    def __init__(self, agent_type, module_type, rotation = None,
        translation = None, background_color = None):
        """Create a GLModuleScene."""
        super(GLModuleScene, self).__init__(agent_type, module_type)

        self.rotation = rotation
        self.translation = translation
        self.background_color = np.array([1.0, 1.0, 1.0, 1.0])
        if background_color is not None:
            self.background_color = background_color

    def __eq__(self, other):
        if self.rotation == other.rotation \
            and self.translation == other.translation \
            and self.background_color == other.background_color:
            return True
        return False

    def __ne__(self, other):
        return not self == other

    def copy(self):
        return GLModuleScene(self.agent_type, self.module_name,
            self.rotation.copy() if self.rotation is not None else None,
            self.translation.copy() if self.translation is not None
                else None,
            self.background_color.copy()
                if self.background_color is not None else None)


class GLColorTab(QWidget):
    """This is the widget for changing color related information in
       GL Frames. The base takes care of GL background colors.

       Subclass this Tab by adding widgets and spacers to the class' layout
       member by overriding createContent.
    """

    def __init__(self, parent, mframe):
        """Construct a GLColorTab with given parent (TabDialog) and
           ModuleFrame.
        """
        super(GLColorTab, self).__init__(parent)

        self.mframe = mframe

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)

        self.createContent()

        self.setLayout(self.layout)

    def createContent(self):
        """Adds the elements (e.g. widgets, items) to the Tab's layout."""
        self.layout.addWidget(self.buildBGColorWidget())

    # TODO: Factor out this color widget builder to something reusable 
    # like the ColorMapWidget
    def buildBGColorWidget(self):
        """Creates the controls for altering the GL background colors."""
        widget = QWidget()
        layout = QHBoxLayout()
        label = QLabel("Background Color")
        self.bgColorBox = ClickFrame(self, QFrame.Panel | QFrame.Sunken)
        self.bgColorBox.setLineWidth(0)
        self.bgColorBox.setMinimumHeight(12)
        self.bgColorBox.setMinimumWidth(36)
        self.bgColorBox.clicked.connect(self.bgColorChange)

        self.bgcolor = ColorMaps.gl_to_rgb(
            self.mframe.agent.module_scene.background_color)
        self.bgColorBox.setStyleSheet("QFrame {\n background-color: "\
            + ColorMaps.rgbStylesheetString(self.bgcolor) + ";\n"
            + "border: 1px solid black;\n border-radius: 2px;\n }")

        layout.addWidget(label)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.bgColorBox)

        widget.setLayout(layout)
        return widget

    def bgColorChange(self):
        """Handles change events to the background color."""
        color = QColorDialog.getColor(QColor(*self.bgcolor), self)

        self.bgcolor = [color.red(), color.green(), color.blue(), self.bgcolor[3]]
        self.bgColorBox.setStyleSheet("QFrame {\n background-color: "\
            + ColorMaps.rgbStylesheetString(self.bgcolor) + ";\n"
            + "border: 1px solid black;\n border-radius: 2px;\n }")
        self.mframe.agent.module_scene.background_color = np.array(
            [x / 255.0 for x in self.bgcolor])
        self.mframe.agent.module_scene.announceChange()

        # Normally we shouldn't have to do this but when I try opening the 
        # TabDialog with show() which gives back control, unfortunate things
        # can happen, so I use .exec_() which halts processing events
        # outside the dialog, so I force this color change here
        # Sadly this appears to only solve the problem for modules created
        # after this one. Will need to fix some other time...
        self.mframe.updateBGColor(self.mframe.agent.module_scene.background_color)

        QApplication.processEvents()


