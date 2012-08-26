import ColorMaps
from PySide.QtCore import Slot,Signal,QObject

class SubdomainScene(QObject):
    """This holds subdomain specific scene information that we might want to
       propogate among views.
    """

    changeSignal = Signal(QObject)

    def __init__(self, subdomain, highlight_set = None, run = None):
        super(SubdomainScene, self).__init__()

        self.subdomain = subdomain
        self.highlight_set = highlight_set # Subdomain
        self.run = run # QModelIndex

    def announceChange(self):
        self.changeSignal.emit(self)

class AttributeScene(QObject):
    """This holds attribute-specific scene information that we might
       want to propogate among views.

       Color map ranges only make sense with respect to a specific
       combination of attributes. 
    """

    changeSignal = Signal(QObject)

    def __init__(self, attributes, color_map = ColorMaps.getMap('gist_eart_r'),\
        color_range = (0.0, 1.0)):
        super(AttributeScene, self).__init__()

        self.attributes = attributes # Needs to identify combination of attrs
        self.color_map = color_map # Move to something completely general?
        self.color_range = color_range

    def announceChange(self):
        self.changeSignal.emit(self)

class ModuleScene(QObject):
    """This holds module-specific scene information that we might
       want to propogate among views.

       Example: May be used to hold ModelView matrix.
    """

    moduleType = None #Change for subclass
    changeSignal = Signal(QObject)

    def __init__(self):
        super(ModuleScene, self).__init__()


    def announceChange(self):
        self.changeSignal.emit(self)




