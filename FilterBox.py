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

@Module("Filter Box")
class FilterBoxView(ModuleView):
    """Window for handling filtering operations.
    """

    def __init__(self, parent, parent_view = None, title = None):
        super(FilterBoxView, self).__init__(parent, parent_view, title)

        self.allowDocks(True)
        if self.agent is not None:
            self.tab_dialog.addTab(SimpleFilterTab(self.tab_dialog, self,
                self.windowTitle(), ""), "Filters")

    def createAgent(self):
        return FilterBox(self.parent_view.agent, \
            self.parent_view.agent.datatree)

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
        dial = FakeDialog(self, self.agent.datatree.getItem(indexList[0]).name, "")
        dial.show()


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

class FilterTab(QWidget):

    def __init__(self, parent, view):
        super(FilterTTab, self).__init__(parent)

        self.view = view
        self.parent = parent
        self.attributes = self.view.agent.datatree.generateAttributeList()


        layout = QHBoxLayout(self)
        self.sidesplitter = QSplitter(Qt.Vertical)

        # You can only select one at a time
        self.data_view = QTreeView(self)
        self.data_view.setModel(self.view.agent.datatree)
        self.data_view.setDragEnabled(True)
        self.data_view.setDropIndicatorShown(True)
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

        filter_layout.addWidget(self.buildRelationsWidget)
        filter_layout.addItem(QSpacerItem(5,5))

        filter_widget.setLayout(filter_layout)
        return filter_widget

    def buildWorkFrame(self):

        DropLineEdit(self, self.view.agent.datatree, text,
            QCompleter(self.attributes))

    def buildRelationsWidget(self):
        relations_widget = QWidget()
        layout = QHBoxLayout(relations_widget)

        for relation in Table.relations:
            layout.addWidget(DragTextLabel(relation))

        relations_widget.setLayout(layout)
        return relations_widget
