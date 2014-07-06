import ColorMaps
from ColorMaps import ColorMap
from PySide.QtCore import Slot,Signal,QObject
from PySide.QtGui import QWidget,QVBoxLayout,QHBoxLayout,\
QCheckBox,QSpacerItem,QLineEdit,QLabel
import sys

class Scene(QObject):
    """Parent class for all Scene classes."""

    causeChangeSignal = Signal(QObject) # For changes originating w/this scene
    changeSignal = Signal(QObject) # For changes applied to this scene

    def __init__(self):
        """Construct a Scene object."""
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
        """Creates a copy of this HighlightScene."""
        highlights = list()
        for highlight_set in self.highlight_sets:
            highlights.append(highlight_set.copy())
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
               The DataTree item of the run under which these
               highlights fall.
        """
        super(HighlightSet, self).__init__()
        self.highlights = highlights # Subdomain
        self.run = run # RunItem

    def copy(self):
        """Creates a copy of this HighlightSet."""
        return HighlightSet(self.highlights[:], self.run)



class AttributeScene(Scene):
    """This holds attribute-specific scene information that we might
       want to propogate among views.

       Color map ranges only make sense with respect to a specific
       combination of attributes.
    """

    def __init__(self, attributes, color_map = ColorMap(),
            total_range = (0.0, 1.0), use_max = True):
        """Construct an AttributeScene pertaining to the given attributes,
           with the given colormap and color range.
        """
        super(AttributeScene, self).__init__()

        self.attributes = attributes
        # Needs to identify combination of attrs, but for now we will
        # just use a set and go by that. Eventually we will need to 
        # consider the whole expression

        self.color_map = color_map # Move to something completely general?

        # The total range of all attributes being grouped in this fashion
        # Individual findings may have smaller ranges, this is the 
        # min of all of those to the max of all of those 
        # (the union plus any contained holes)
        self.total_range = total_range

        # Determines whether this scene still needs processing by its host
        # Right now this is sort of a hack to make things update
        # through the colormap changer but not through the attribute
        # changer. This should be named/accessed better in the future
        # and/or taken care of automatically
        self.processed = True

        self.local_max_range = total_range
        self.use_max_range = use_max


    def __eq__(self, other):
        if self.attributes != other.attributes:
            return False
        if self.color_map != other.color_map:
            return False
        if self.total_range != other.total_range:
            return False
        if self.processed != other.processed:
            return False
        if self.use_max_range != other.use_max_range:
            return False

        return True

    def __ne__(self, other):
        return not self == other

    def copy(self):
        return AttributeScene(frozenset(self.attributes.copy()),
            self.color_map.copy(), (self.total_range[0], self.total_range[1]),
            self.use_max_range)

    # Only do this if attributes are the same or the local range
    # will not make sense
    def merge(self, other):
        """Merge with another AttributeScene but preserve local information.

           DO NOT USE if attributes are not the same.
        """
        self.color_map = other.color_map
        self.total_range = other.total_range
        self.processed = other.processed
        self.use_max_range = other.use_max_range

    def cmap_range(self):
        """Use to normalize ranges for color maps.  Given an set of values,
        this will return a function that will normalize those values to
        something in [0..1] based on their range.
        """

        myrange = self.total_range[1] - self.total_range[0]
        if myrange <= sys.float_info.epsilon:
            myrange = 1.0
        def evaluator(val):
            return (val - self.total_range[0]) / myrange
        return evaluator


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
        """Create and return a copy of this ModuleScene."""
        return ModuleScene(self.agent_type, self.module_name)



class RangeWidget(QWidget):
    """Interface for changing Range information. It shows the current
       range and range policy.
       This widget was designed for use with the tab dialog. It can be used by
       itself or it can be used as part of a bigger color tab.

       Changes to this widget are emitted via a changeSignal as a boolean
       on policy, range tuple and this widget's tag.
    """

    changeSignal = Signal(bool, float, float, str)

    def __init__(self, parent, use_max, current_range, max_range, tag):
        """Creates a ColorMap widget.

           parent
               The Qt parent of this widget.

           use_max
               Whether the policy is to use max possible or set range.

           current_range
               The min and max range on creation.

           tag
               A name for this widget, will be emitted on change.
        """
        super(RangeWidget, self).__init__(parent)
        self.edit_range = (current_range[0], current_range[1])
        self.max_range = max_range
        self.use_max = use_max
        self.tag = tag

        layout = QVBoxLayout()


        self.range_check = QCheckBox("Use maximum range across applicable "
            + "modules.")
        layout.addWidget(self.range_check)
        if self.use_max:
            self.range_check.setChecked(True)
        else:
            self.range_check.setChecked(False)
        self.range_check.stateChanged.connect(self.checkChanged)
        layout.addItem(QSpacerItem(3,3))

        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("Set range: "))
        self.range_min = QLineEdit(str(current_range[0]), self)
        self.range_min.editingFinished.connect(self.rangeChanged)
        hlayout.addWidget(self.range_min)
        hlayout.addWidget(QLabel(" to "))
        self.range_max = QLineEdit(str(current_range[1]), self)
        self.range_max.editingFinished.connect(self.rangeChanged)
        hlayout.addWidget(self.range_max)
        layout.addLayout(hlayout)

        self.setStates()
        self.setLayout(layout)

    def setStates(self):
        if self.use_max:
            self.range_min.setDisabled(True)
            self.range_max.setDisabled(True)
        else:
            self.range_min.setDisabled(False)
            self.range_max.setDisabled(False)

    @Slot()
    def checkChanged(self):
        """Handles check/uncheck of use max."""
        self.use_max = self.range_check.isChecked()
        self.setStates()

        if self.use_max:
            self.changeSignal.emit(self.use_max, self.max_range[0],
                self.max_range[1], self.tag)
        else:
            self.changeSignal.emit(self.use_max, self.edit_range[0],
                self.edit_range[1], self.tag)


    @Slot()
    def rangeChanged(self):
        self.edit_range = (float(self.range_min.text()),
                float(self.range_max.text()))

        self.changeSignal.emit(self.use_max, self.edit_range[0],
                self.edit_range[1], self.tag)

