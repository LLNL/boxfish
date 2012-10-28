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
        if self.module_scene.background_color \
            != module_scene.background_color:
            self.module_scene.background_color \
                = module_scene.background_color
            self.bgColorUpdateSignal(self.module_scene.background_color)


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
