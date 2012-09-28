import ColorMaps
from PySide.QtCore import Slot,Signal,QObject

class Scene(QObject):
    """Parent class for all Scene classes."""

    causeChangeSignal = Signal(QObject) # For changes originating w/this scene
    changeSignal = Signal(QObject) # For changes applied to this scene

    def __init__(self):
        super(Scene, self).__init__()

    def announceChange(self):
        """This should be called whenever a Scene object is changed due
           to a user action.

           Example: When a user selects highlights.
        """
        self.causeChangeSignal.emit(self)

    def acceptChanges(self):
        self.changeSignal.emit(self)


class HighlightScene(Scene):
    """This holds highlight scene information for propagating amongst
       views.
    """

    def __init__(self, highlight_sets = list()):
        """Constructs a HighlightScene

           highlight_sets
              A list of HighlightSet objects which together describe all
              of the highlighted objects.
        """
        super(HighlightScene, self).__init__()

        self.highlight_sets = highlight_sets

    def copy(self):
        highlights = list()
        for highlight_set in self.highlight_sets:
            highlights.appen(highlight_set.copy())
        return HighlightScene(highlights)


class HighlightSet(object):
    """This class holds information regarding a single SubDomain of
       highlights.
    """

    def __init__(self, highlights, run):
        """Construct a highlight set.

           highlights
               A SubDomain containing the highlighted ids.

           run
               The DataTree index of the run under which these
                 highlights fall.
        """
        super(HighlightSet, self).__init__()
        self.highlights = highlights # Subdomain
        self.run = run # QModelIndex

    def copy(self):
        return HighlightSet(self.highlights[:], self.run)
        


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
        """Construct a ModuleScene object.

           agent_type
               The type of the ModuleAgent used by this module

           module_name
               The display_name of the module using this class.
        """
        super(ModuleScene, self).__init__()

        self.agent_type = agent_type
        self.module_name = module_name

    def copy(self):
        return ModuleScene(self.agent_type, self.module_name)

