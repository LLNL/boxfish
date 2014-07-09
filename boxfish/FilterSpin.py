from PySide.QtCore import Qt, Signal, Slot
from PySide.QtGui import QWidget, QHBoxLayout, QLabel, QSpinBox,\
    QSpacerItem
from ModuleFrame import *
from ModuleAgent import *
from GUIUtils import *
from Query import *
from Table import Table
from DataModel import *
from Filter import *

class FilterSpinAgent(ModuleAgent):
    """Agent for all FilterSpin modules, associates filters with modules.

       The Filter Spin takes a single numeric field and adds a filter
       setting all data under it to whatever a specific value in that field is.
       The idea is that using a spin control, the user can move through
       all the values of the field separately. For example, if that field is
       time, it would be akin to animation.

       The Filter Spin respects the filters above it when coming up with the
       spin range.
    """

    spinUpdateSignal = Signal(str, list) # field name, values

    def __init__(self, parent, datatree):
        """Constructor for FilterBoxAgent."""
        super(FilterSpinAgent, self).__init__(parent, datatree)

        self.addRequest("spinfield")
        self.requestUpdatedSignal.connect(self.buildSpin)
        self.spin_values = list()
        self.spin_field = ""
        self.spin_selected = -1


    def addDataIndices(self, indexList):
        """This function handles an added list of DataTree indices by
           associated them with the agent's Request. We only accept
           a single index in the Filter Spin so we truncate the list.
        """

        if len(indexList) > 1:
            indexList = list(indexList[0])
        self.requestAddIndices("spinfield", indexList)

    @Slot(str)
    def buildSpin(self):
        tables, runs, ids, headers, data_lists \
            = self.requestGetRows("spinfield")
        if not data_lists:
            return
        self.spin_values = sorted(list(set(data_lists[0][0])))
        self.spin_field = headers[0][0]
        self.spinUpdateSignal.emit(self.spin_field, self.spin_values)


    def createSimpleFilter(self, index = -1):
        """Creates a SimpleFilter from the given conditions (a Clause
           object) and associates the new filter with all data requests
           passing through this module. If conditions is None, will
           effectively remove the filter from this Agent and all data
           requests passing through it.
        """
        self.spin_selected = index
        self.filters = list()
        if self.spin_selected not in range(len(self.spin_values)):
            for coupler in self.requests.values():
                coupler.modifier = None
            for coupler in self.child_requests:
                coupler.modifier = None
        else:
            self.filters.append(SimpleWhereFilter(
                Clause('=', TableAttribute(self.spin_field),
                    self.spin_values[self.spin_selected])))
            for coupler in self.requests.values():
                coupler.modifier = self.filters[0]
            for coupler in self.child_requests:
                coupler.modifier = self.filters[0]


@Module("Filter Spin", FilterSpinAgent)
class FilterSpinFrame(ModuleFrame):
    """ModuleFrame for handling spin filter operations.
    """

    def __init__(self, parent, parent_frame = None, title = None):
        """Constructor for FilterSpinFrame."""
        super(FilterSpinFrame, self).__init__(parent, parent_frame, title)

        self.allowDocks(True)

        self.agent.spinUpdateSignal.connect(self.updateSpinner)
        self.droppedDataSignal.connect(self.droppedData)

    def createView(self):
        """Creates the module-specific view for the FilterBox module."""
        view = QWidget()

        layout = QHBoxLayout()

        self.filter_label = QLabel("")
        layout.addWidget(self.filter_label)

        layout.addItem(QSpacerItem(3,3))

        self.spinner = FilterSpinBox(self, list())
        self.spinner.valueChanged.connect(self.spinnerValueChanged)
        layout.addWidget(self.spinner)

        view.setLayout(layout)
        view.resize(200, 20)
        return view


    @Slot(list, str)
    def droppedData(self, indexList):
        """Overrides the superclass method to send the agent the dropped
           data indices.
        """
        self.agent.addDataIndices(indexList)


    @Slot(str, list)
    def updateSpinner(self, field, values):
        self.filter_label.setText(field + " = ")
        self.spinner.true_values = values

    @Slot(int)
    def spinnerValueChanged(self, index):
        self.agent.createSimpleFilter(index)


class FilterSpinBox(QSpinBox):
    """Special spin box shows the value of the given field rather than
       the index of the spin box.
    """

    def __init__(self, parent, values):
        super(FilterSpinBox, self).__init__(parent)

        self._true_values = values

    @property
    def true_values():
        return self._true_values

    @true_values.setter
    def true_values(self, values):
        # Save old stuff if it is pertinent
        if len(self._true_values):
            oldtrue = self._true_values[self.value()]
            oldvalue = self.value()
        else:
            oldtrue = 0
            oldvalue = 0

        # Change to new stuff
        self._true_values = values
        self.setRange(0, len(values))

        # See if we can match new with old
        index = 0
        if oldtrue in self._true_values:
            index = self._true_values.index(oldtrue)

        # Set the value
        self.setValue(index)

        # Emit this just in case we're changing fields
        if index == oldvalue:
            self.valueChanged.emit(index)

    def valueFromText(self, text):
        current = self.value() # Save current
        if int(text) in self.true_values:
            current = self.true_values.index(int(text))

        return current

    def textFromValue(self, value):
        if len(self._true_values) \
            and value in range(len(self._true_values)):
            return str(self._true_values[value])
        else:
            return ""
