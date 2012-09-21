from PySide.QtCore import *
from PySide.QtGui import *
from SubDomain import *
from Module import *
from Query import *
from Table import Table
from DataModel import *
from Filter import *

class FilterBox(ModuleAgent):

    def __init__(self, parent, datatree):
        super(FilterBox, self).__init__(parent, datatree)

    def createSimpleFilter(self, conditions):
        self.filters = list()
        self.filters.append(SimpleWhereFilter(conditions))
        for coupler in self.requirements:
            coupler.modifier = self.filters[0]
        for coupler in self.child_requirements:
            coupler.modifier = self.filters[0]

@Module("Filter Box", FilterBox)
class FilterBoxView(ModuleView):
    """Window for handling filtering operations.
    """

    def __init__(self, parent, parent_view = None, title = None):
        super(FilterBoxView, self).__init__(parent, parent_view, title)

        self.allowDocks(True)

    def createView(self):
        view = QWidget()

        layout = QGridLayout()
        self.fake_label = QLabel("")
        layout.addWidget(self.fake_label, 0, 0, 1, 1)
        view.setLayout(layout)
        view.resize(200, 100)
        return view

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

    def droppedData(self, indexList):
        self.filter_tab.setAttribute(self.agent.datatree.getItem(indexList[0]).name)
        self.tab_dialog.show()


    # Demonstration of changing Drag & Drop behavior for window unique data
    # May not be necessary for other modules.
    def dropEvent(self, event):
        # Dropped Filter
        if isinstance(event.mimeData(), FilterMime):
            myfilter = event.mimeData().getFilter()
            # Do something with it.
            event.accept()
        else:
            super(FilterBoxView, self).dropEvent(event)

    # Goes with FakeDialog
    def fakeNewVals(self, title, filtertext):
        self.agent.createSimpleFilter(Clause("=", TableAttribute(title),
            filtertext))
        self.fake_label.setText("Filter: " + title + " = " + filtertext)
        #self.setTitle(title)
        #self.parent().setWindowTitle(title)

    def buildTabDialog(self):
        super(FilterBoxView, self).buildTabDialog()
        self.filter_tab = SimpleFilterTab(self.tab_dialog, self, self.windowTitle(), "")
        self.tab_dialog.addTab(self.filter_tab, "Filters")
        self.new_filter_tab = FilterTab(self.tab_dialog, self)
        self.tab_dialog.addTab(self.new_filter_tab, "Advanced Filters")


class FilterMime(QMimeData):
    """This is for passing Filter information between filter windows.
    """

    def __init__(self, myfilter):
        super(FilterMime, self).__init__()

        self.myfilter = myfilter

    def getFilter(self):
        return self.myfilter

# Convenient way for me to rename the window and added text for
# Boxfish poster. May want to change this into something permanent
# involving actual filtering.
class SimpleFilterTab(QWidget):

    def __init__(self, parent, view, title, filtertext = ""):
        super(SimpleFilterTab, self).__init__(parent)

        self.view = view
        self.parent = parent

        nameLabel = QLabel("Attribute: ")
        filterLabel = QLabel("Value: ")

        self.nameEdit = QLineEdit(title)
        self.filterEdit = QLineEdit(filtertext)

        changeButton = QPushButton("Set")
        changeButton.clicked.connect(self.sendBack)

        mainLayout = QGridLayout()
        mainLayout.addWidget(nameLabel, 0, 0)
        mainLayout.addWidget(self.nameEdit, 0, 1)
        mainLayout.addWidget(filterLabel, 1, 0)
        mainLayout.addWidget(self.filterEdit, 1, 1)
        mainLayout.addWidget(changeButton, 2, 0)

        self.setLayout(mainLayout)

    def sendBack(self):
        self.view.fakeNewVals(self.nameEdit.text(), self.filterEdit.text())
        self.parent.close()

    def setAttribute(self, attribute):
        self.nameEdit.setText(attribute)

class FilterTab(QWidget):

    applySignal = Signal(Clause)

    def __init__(self, parent, view):
        super(FilterTab, self).__init__(parent)

        self.view = view
        self.parent = parent
        self.attributes = self.view.agent.datatree.generateAttributeList()
        self.clause_list = list()
        self.clause_dict = dict()

        layout = QHBoxLayout(self)
        self.sidesplitter = QSplitter(Qt.Horizontal)

        # You can only select one at a time
        self.data_view = QTreeView(self)
        self.data_view.setModel(self.view.agent.datatree)
        self.data_view.setDragEnabled(True)
        self.data_view.setDropIndicatorShown(True)
        self.data_view.expandAll()
        self.sidesplitter.addWidget(self.data_view)
        self.sidesplitter.setStretchFactor(0,1)

        self.filter_widget = self.buildFilterWidget()
        self.sidesplitter.addWidget(self.filter_widget)
        self.sidesplitter.setStretchFactor(1,0)

        layout.addWidget(self.sidesplitter)
        self.setLayout(layout)


    def buildFilterWidget(self):
        filter_widget = QWidget()
        filter_layout = QVBoxLayout(filter_widget)

        filter_layout.addWidget(self.buildRelationsWidget())
        filter_layout.addItem(QSpacerItem(5,5))
        filter_layout.addWidget(self.buildWorkFrame())
        filter_layout.addItem(QSpacerItem(5,5))
        self.list_view = QListView

        filter_widget.setLayout(filter_layout)
        return filter_widget

    def buildWorkFrame(self):
        groupBox = QGroupBox("Clause Workspace")
        layout = QHBoxLayout(groupBox)

        self.dropAttribute = DropLineEdit(self, self.view.agent.datatree, "",
            QCompleter(self.attributes))
        self.dropRelation = DropTextLabel("__")
        self.dropValue = FilterValueLineEdit(groupBox,
            self.view.agent.datatree, self.dropAttribute)
        layout.addWidget(self.dropAttribute)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.dropRelation)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.dropValue)

        groupBox.setLayout(layout)
        return groupBox

    def buildRelationsWidget(self):
        relations_widget = QWidget()
        layout = QHBoxLayout(relations_widget)

        for relation in Table.relations:
            layout.addWidget(DragTextLabel(relation))

        relations_widget.setLayout(layout)
        return relations_widget



class FilterValueLineEdit(QLineEdit):
    
    def __init__(self, parent, datatree, watchLineEdit):
        super(FilterValueLineEdit, self).__init__("", parent)

        self.datatree = datatree
        self.watchLineEdit = watchLineEdit

    def focusInEvent(self, e):
        super(FilterValueLineEdit, self).focusInEvent(e)
        values = self.datatree.getAttributeValues(self.watchLineEdit.text())
        self.setCompleter(None)
        self.setCompleter(QCompleter(values))
