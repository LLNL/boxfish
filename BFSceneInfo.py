import BFMaps
from PySide.QtCore import Slot,Signal,QObject

class BFSubdomainScene(QObject):
    """This holds subdomain specific scene information that we might want to
       propogate among views.
    """

    changeSignal = Signal(QObject)

    def __init__(self, subdomain, highlight_set = None, run = None):
        super(BFSubdomainScene, self).__init__()

        self.subdomain = subdomain
        self.color_map = color_map
        self.color_range = color_range
        self.highlight_set = highlight_set # Subdomain
        self.run = run # QModelIndex

    def announceChange(self):
        self.changeSignal.emit(self)

class BFAttributeScene(QObject):
    """This holds attribute-specific scene information that we might
       want to propogate among views.
    """

    changeSignal = Signal(QObject)

    def __init__(self, attributes, color_map = BFMaps.getMap('gist_eart_r'),\
        color_range = (0.0, 1.0)):
        super(BFAttributeScene, self).__init__()

        self.attributes = attributes
        self.color_map = color_map
        self.color_range = color_range

    def announceChange(self):
        self.changeSignal.emit(self)

class BFModuleScene(QObject):
    """This holds module-specific scene information that we might
       want to propogate among views.

       Example: May be used to hold ModelView matrix.
    """

    changeSignal = Signal(QObject)

    def __init__(self, info = None):
        super(BFModuleScene, self).__init__()

        self.info = info

    def announceChange(self):
        self.changeSignal.emit(self)




