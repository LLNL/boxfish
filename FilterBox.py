from PySide.QtCore import *
from PySide.QtGui import *
from SubDomain import *
from Module import *
#from Query import *
#from QueryEngine import *
from DataModel import *
from Filter import *

class FilterBox(ModuleAgent):

    def __init__(self, parent, datatree):
        super(FilterBox, self).__init__(parent, datatree)

    def createSimpleFilter(self, attribute, value):
        self.filters = list()
        self.filters.append(SimpleWhereFilter(attribute, value))
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

    def createAgent(self):
        return FilterBox(self.parent_view.agent, \
            self.parent_view.agent.datatree)

    def createView(self):
        view = QWidget() # Later this may be a FilterBoxWidget w/Filter controls

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
        #mytext = self.fake_label.text()
        #for index in indexList:
        #    print self.agent.datatree.getItem(index).name
        #    mytext = mytext + "\n" + self.agent.datatree.getItem(index).name + \
                #        " from " + self.agent.datatree.getItem(index).parent().name
        #self.fake_label.setText(mytext)
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
    def mouseDoubleClickEvent(self, e):
        dial = FakeDialog(self, self.windowTitle(), "")
        dial.show()

    # Goes with FakeDialog
    def fakeNewVals(self, title, filtertext):
        self.agent.createSimpleFilter(title, int(filtertext))
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
class FakeDialog(QDialog):

    def __init__(self, parent, title, filtertext = ""):
        super(FakeDialog, self).__init__(parent, Qt.Dialog)

        self.setModal(False)
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
        self.parent.fakeNewVals(self.nameEdit.text(), self.filterEdit.text())
        self.close()

# ??? Not sure what I was thinking here... previous ideas on filtering.
# This has all of the information that actually gets shown in the filter
# Will need to subscribe to the DocTree datatree as well as its own internal datatree
# of what data it has which is subscribed to something more specific as well
# as up the tree and the highlight selection
class FilterModel():

    def __init__(self):
        pass

