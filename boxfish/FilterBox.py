from PySide.QtCore import Qt, Signal, Slot, QMimeData
from PySide.QtGui import QWidget, QGridLayout, QLabel, QToolBar, QAction,\
    QIcon, QStringListModel, QVBoxLayout, QTreeView, QSplitter,\
    QHBoxLayout, QPushButton, QSpacerItem, QGroupBox, QLineEdit, QListView,\
    QCompleter
from ModuleFrame import *
from ModuleAgent import *
from GUIUtils import *
from Query import *
from Table import Table
from DataModel import *
from Filter import *

class FilterBoxAgent(ModuleAgent):
    """Agent for all FilterBox modules, associates filters with modules.
    """

    def __init__(self, parent, datatree):
        """Constructor for FilterBoxAgent."""
        super(FilterBoxAgent, self).__init__(parent, datatree)

    def createSimpleFilter(self, conditions):
        """Creates a SimpleFilter from the given conditions (a Clause
           object) and associates the new filter with all data requests
           passing through this module. If conditions is None, will
           effectively remove the filter from this Agent and all data
           requests passing through it.
        """
        self.filters = list()
        if conditions is None:
            for coupler in self.requests.values():
                coupler.modifier = None
            for coupler in self.child_requests:
                coupler.modifier = None
        else:
            self.filters.append(SimpleWhereFilter(conditions))
            for coupler in self.requests.values():
                coupler.modifier = self.filters[0]
            for coupler in self.child_requests:
                coupler.modifier = self.filters[0]

@Module("Filter Box", FilterBoxAgent)
class FilterBoxFrame(ModuleFrame):
    """ModuleFrame for handling filtering operations.
    """

    def __init__(self, parent, parent_frame = None, title = None):
        """Constructor for FilterBoxFrame."""
        super(FilterBoxFrame, self).__init__(parent, parent_frame, title)

        self.allowDocks(True)


    def createView(self):
        """Creates the module-specific view for the FilterBox module."""
        view = QWidget()

        layout = QGridLayout()
        self.filter_label = QLabel("")
        layout.addWidget(self.filter_label, 0, 0, 1, 1)
        view.setLayout(layout)
        view.resize(20, 20)
        return view

    # Not currently in use
    # Toolbars are too big. Someday this may be done with a prettier label.
    def createToolBar(self):
        if isinstance(self.parent(), BFDockWidget):
            self.toolbar = BFDragToolBar('Filter Tools', self, self.parent())
        else:
            self.toolbar = QToolBar('Filter Tools', parent = self)


        if isinstance(self.parent(), BFDockWidget):
            dragAction = QAction(QIcon(":/filterbox_move.png"), \
                "Drag to Change Parent", self)
            self.toolbar.addAction(dragAction)

        createChildAction = QAction(QIcon(":/filterbox_new.png"), \
            "New Filterbox", self)
        createChildAction.triggered.connect(self.createChildWindow)

        self.toolbar.addAction(createChildAction)

        self.addToolBar(self.toolbar)


    # No functionality currently
    # Demonstration of changing Drag & Drop behavior for window unique data
    # May not be necessary for other modules.
    def dropEvent(self, event):
        # Dropped Filter
        if isinstance(event.mimeData(), FilterMime):
            myfilter = event.mimeData().getFilter()
            # Do something with it.
            event.accept()
        else:
            super(FilterBoxFrame, self).dropEvent(event)


    @Slot(Clause)
    def editFilter(self, clause):
        """Given a Clause object, passes it to the Agent to associate
           a fiter based on that Clause with this module. Updates the
           ModuleFrame to show the filter.
        """
        self.agent.createSimpleFilter(clause)
        self.filter_label.setText("Filter: " + str(clause))

    def buildTabDialog(self):
        """Appends the FilterBox specific filter-building GUI to the
           tab dialog for this module.
        """
        super(FilterBoxFrame, self).buildTabDialog()
        self.filter_tab = FilterTab(self.tab_dialog, self,
            self.agent.filters)
        self.filter_tab.applySignal.connect(self.editFilter)
        self.tab_dialog.addTab(self.filter_tab, "Filters")


# Not currently in use.
class FilterMime(QMimeData):
    """This is for passing Filter information between filter windows.
    """

    def __init__(self, myfilter):
        """Construct a FilterMime."""
        super(FilterMime, self).__init__()

        self.myfilter = myfilter

    def getFilter(self):
        """Returns the filter contained in this FilterMime."""
        return self.myfilter


class FilterTab(QWidget):
    """This class is the GUI for creating filters for the FilterBox
       module. This GUI will be added as a tab to the ModuleFrame
       tab dialog.
    """

    applySignal = Signal(Clause)

    def __init__(self, parent, mframe, existing_filters):
        """Create a FilterTab with the given parent TabDialog, logical
           parent ModuleFrame mframe, and existing_filters list of Clause
           objects.
        """
        super(FilterTab, self).__init__(parent)

        self.mframe = mframe
        self.parent = parent
        self.attributes = self.mframe.agent.datatree.generateAttributeList()

        self.clause_list = list()
        self.clause_dict = dict()
        # Right now we only look at the first passed in filter.
        # TODO: At GUI to switch between existing filters
        if existing_filters is not None and len(existing_filters) > 0:
            for clause in existing_filters[0].conditions.clauses:
                self.clause_list.append(str(clause))
                self.clause_dict[str(clause)] = clause

        self.clause_model = QStringListModel(self.clause_list)

        layout = QVBoxLayout(self)
        self.sidesplitter = QSplitter(Qt.Horizontal)

        # You can only select one attribute at a time to build the 
        # filter clauses
        self.data_view = QTreeView(self)
        self.data_view.setModel(self.mframe.agent.datatree)
        self.data_view.setDragEnabled(True)
        self.data_view.setDropIndicatorShown(True)
        self.data_view.expandAll()
        self.sidesplitter.addWidget(self.data_view)
        self.sidesplitter.setStretchFactor(1,1)

        self.filter_widget = self.buildFilterWidget()
        self.sidesplitter.addWidget(self.filter_widget)
        self.sidesplitter.setStretchFactor(1,0)

        layout.addWidget(self.sidesplitter)

        # Apply buttons
        buttonWidget = QWidget()
        buttonLayout = QHBoxLayout(buttonWidget)
        self.applyButton = QPushButton("Apply")
        self.applyButton.clicked.connect(self.applyFilter)
        self.closeButton = QPushButton("Apply & Close")
        self.closeButton.clicked.connect(self.applyCloseFilter)
        buttonLayout.addWidget(self.applyButton)
        buttonLayout.addWidget(self.closeButton)
        buttonWidget.setLayout(buttonLayout)

        layout.addWidget(buttonWidget)
        self.setLayout(layout)

    def applyFilter(self):
        """Emits the applySignal with the Clause object currently
           represented by this FilterTab.
        """
        num_clauses = len(self.clause_list)
        if num_clauses == 0:
            self.applySignal.emit(None)
        else:
            self.applySignal.emit(Clause("and", *self.clause_dict.values()))

    def applyCloseFilter(self):
        """Calls applyFilter and then closes the containing TabDialog."""
        self.applyFilter()
        self.parent.close()

    def buildFilterWidget(self):
        """Creates the filter portion of the widget by laying out
           the subwidgets for relations, workspace and existing
           clauses.
        """
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)

        filter_layout.addWidget(self.buildRelationsWidget())
        filter_layout.addItem(QSpacerItem(5,5))
        filter_layout.addWidget(self.buildWorkFrame())
        filter_layout.addItem(QSpacerItem(5,5))
        filter_layout.addWidget(self.buildFilterListView())

        filter_widget.setLayout(filter_layout)
        return filter_widget

    def buildFilterListView(self):
        """Creates the QListView that contains all of the basic Clause
           objects.
        """
        groupBox = QGroupBox("Clauses")
        layout = QVBoxLayout(groupBox)

        self.list_view = QListView(groupBox)
        self.list_view.setModel(self.clause_model)
        layout.addWidget(self.list_view)

        layout.addItem(QSpacerItem(5,5))
        self.delButton = QPushButton("Remove Selected Clause")
        self.delButton.clicked.connect(self.deleteClause)
        layout.addWidget(self.delButton)

        groupBox.setLayout(layout)
        return groupBox

    def buildWorkFrame(self):
        """Creates the grouped set of widgets that allow users to build
           basic Clause objects.
        """
        groupBox = QGroupBox("Clause Workspace")
        layout = QHBoxLayout(groupBox)

        attributeCompleter = QCompleter(self.attributes)
        attributeCompleter.setCompletionMode(QCompleter.InlineCompletion)
        self.dropAttribute = DropLineEdit(self, self.mframe.agent.datatree, "",
            attributeCompleter)
        self.dropRelation = DropTextLabel("__")
        self.dropValue = FilterValueLineEdit(groupBox,
            self.mframe.agent.datatree, self.dropAttribute)

        # Clear dropValue when dropAttribute changes
        self.dropAttribute.textChanged.connect(self.dropValue.clear)

        # Enter in dropValue works like addButton
        self.dropValue.returnPressed.connect(self.addClause)

        self.addButton = QPushButton("Add", groupBox)
        self.addButton.clicked.connect(self.addClause)
        layout.addWidget(self.dropAttribute)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.dropRelation)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.dropValue)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.addButton)

        groupBox.setLayout(layout)
        return groupBox

    def buildRelationsWidget(self):
        """Creates the set of draggable relations. These relations are
           whatever is available in the relations dict of Table.
        """
        relations_widget = QWidget()
        layout = QHBoxLayout(relations_widget)

        for relation in Table.relations:
            layout.addWidget(DragTextLabel(relation))

        relations_widget.setLayout(layout)
        return relations_widget

    def addClause(self):
        """Adds a basic Clause to the current filter."""
        if self.dropRelation.text() in Table.relations \
            and len(self.dropValue.text()) > 0 \
            and len(self.dropAttribute.text()) > 0:

            clause = Clause(self.dropRelation.text(),
                TableAttribute(self.dropAttribute.text()),
                self.dropValue.text())

            # Guard double add
            if str(clause) not in self.clause_dict:
                self.clause_list.append(str(clause))
                self.clause_dict[str(clause)] = clause
                self.clause_model.setStringList(self.clause_list)

    def deleteClause(self):
        """Removes the selected basic Clause objects from the current
           filter.
        """
        clause = self.clause_model.data(
            self.list_view.selectedIndexes()[0], Qt.DisplayRole)
        if clause is not None and clause in self.clause_list:
            self.clause_list.remove(clause)
            del self.clause_dict[clause]
            self.clause_model.setStringList(self.clause_list)



class FilterValueLineEdit(QLineEdit):
    """This QLineEdit dynamically updates its QCompleter on focus
       to give value hints for whatever attribute is currently
       represented in a different QLineEdit.
    """

    def __init__(self, parent, datatree, watchLineEdit):
        """Construct the FilterValueLineEdit. The watchLineEdit is
           another QLineEdit which will determine what QCompleter values
           this LineEdit has at any time. The parent is the Qt GUI parent
           and the datatree is the full Boxfish datatree.
        """
        super(FilterValueLineEdit, self).__init__("", parent)

        self.datatree = datatree
        self.watchLineEdit = watchLineEdit
        self.oldText = ""

    def focusInEvent(self, e):
        """On focus, this completer for this LineEdit will update its
           values based on the attribute named in the watchLineEdit.
        """
        super(FilterValueLineEdit, self).focusInEvent(e)
        if self.oldText != self.watchLineEdit.text():
            self.oldText = self.watchLineEdit.text()
            values = self.datatree.getAttributeValues(
                self.watchLineEdit.text())
            self.setCompleter(None)
            new_completer = QCompleter(values)
            new_completer.setCompletionMode(QCompleter.InlineCompletion)
            self.setCompleter(new_completer)

