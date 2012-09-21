import ColorMaps
from PySide.QtCore import Slot,Signal,QObject

class Scene(QObject):
    """Parent class for all Scene classes."""

    causeChangeSignal = Signal(QObject) # For changes originating w/this scene
    changeSignal = Signal(QObject) # For changes applied to this scene

    def __init__(self):
        super(Scene, self).__init__()

    def announceChange(self):
        self.causeChangeSignal.emit(self)

    def acceptChanges(self):
        self.changeSignal.emit(self)


class SubdomainScene(Scene):
    """This holds subdomain specific scene information that we might want to
       propogate among views.
    """

    def __init__(self, subdomain, highlight_set = None, run = None):
        super(SubdomainScene, self).__init__()

        self.subdomain = subdomain
        self.highlight_set = highlight_set # Subdomain
        self.run = run # QModelIndex




class AttributeScene(Scene):
    """This holds attribute-specific scene information that we might
       want to propogate among views.

       Color map ranges only make sense with respect to a specific
       combination of attributes. 
    """

    def __init__(self, attributes,
        color_map = ColorMaps.getMap('gist_eart_r'),
        color_range = (0.0, 0.0)):
        super(AttributeScene, self).__init__()

        self.attributes = attributes # Needs to identify combination of attrs
        self.color_map = color_map # Move to something completely general?
        self.color_range = color_range



class ModuleScene(Scene):
    """This holds agent-specific scene information that we might
       want to propagate among views. Inherit from this class to
       handle this scene information.

       Example: May be used to hold ModelView matrix.
    """

    def __init__(self, agent_type, module_name):
        super(ModuleScene, self).__init__()

        self.agent_type = agent_type
        self.module_name = module_name

    def copy(self):
        return ModuleScene(self.agent_type, self.module_name)

