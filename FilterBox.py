from PySide.QtCore import *
from PySide.QtGui import *
from SubDomain import *
from BFModule import *
#from Query import *
#from QueryEngine import *
from DataModel import *
import BFIcons

class FilterBox(BFModule):

    def __init__(self, parent, model):
        super(FilterBox, self).__init__(parent, model)


class FilterBoxWindow(BFModuleWindow):
    """Window for handling filtering operations.
    """

    display_name = "FilterBox"
    in_use = True

    def __init__(self, parent, parent_view = None, title = None):
        super(FilterBoxWindow, self).__init__(parent, parent_view, title)

        self.allowDocks(True)

    def createModule(self):
        return FilterBox(self.parent_view.module, \
            self.parent_view.module.model)

    def createView(self):
        view = QWidget() # Later this will be a FilterBoxView w/ Filter controls

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
        mytext = self.fake_label.text()
        for index in indexList:
            print self.module.model.getItem(index).name
            mytext = mytext + "\n" + self.module.model.getItem(index).name + \
                " from " + self.module.model.getItem(index).parent().name
        self.fake_label.setText(mytext)

    # Demonstration of changing Drag & Drop behavior for window unique data
    # May not be necessary for other modules.
    def dropEvent(self, event):
        # Dropped Filter
        if isinstance(event.mimeData(), FilterMime):
            myfilter = event.mimeData().getFilter()
            # Do something with it.
            event.accept()
        else:
            super(FilterBoxWindow, self).dropEvent(event)


    # Goes with FakeDialog
    def mouseDoubleClickEvent(self, e):
        dial = FakeDialog(self, self.windowTitle(), "")
        dial.show()

    # Goes with FakeDialog
    def fakeNewVals(self, title, filtertext):
        print title, filtertext
        self.setTitle(title)
        self.parent().setWindowTitle(title)


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

        nameLabel = QLabel("Title: ")
        filterLabel = QLabel("Filter: ")

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
# Will need to subscribe to the DocTree model as well as its own internal model
# of what data it has which is subscribed to something more specific as well
# as up the tree and the highlight selection
class FilterModel():

    def __init__(self):
        pass

