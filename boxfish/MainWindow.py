#!/usr/bin/env python

import signal
import sys
from PySide.QtCore import *
from PySide.QtGui import *
from FilterBox import *
from FilterSpin import *
from DataModel import *
from ModuleAgent import *

class MainWindow(QMainWindow):
    """This is the actual main Window of boxfish, containing all other
       non-dialog widgets. It is in charge of the top level ModuleAgent,
       top-level FilterBox, non-module-based GUI , menus, and
       initialization.
    """

    def __init__(self):
        """Construct Boxfish."""
        super(MainWindow, self).__init__(None)

        self.datatree = DataTree()
        self.agent = TopAgent(self, self.datatree)
        self.centralWidget = QSplitter(Qt.Horizontal)

        # Control Frame
        self.control_frame = QFrame(self)
        self.makeControlFrame()
        self.centralWidget.addWidget(self.control_frame)
        self.centralWidget.setStretchFactor(0, 0)

        # Filter group
        self.filter_box = FilterBoxFrame(self, \
            title = "Boxfish", parent_frame = self)
        self.centralWidget.addWidget(self.filter_box)
        self.centralWidget.setStretchFactor(1, 1)

        self.setCentralWidget(self.centralWidget)

        self.createMenus()
        self.setWindowTitle("Boxfish")
        self.resize(1008, 704)

        self.setAcceptDrops(True) # For Rogue overlay problem

    def makeControlFrame(self):
        """This does the GUI creation and layout for everything but
           the top-level FilterBox.
        """
        layout = QVBoxLayout(self.control_frame)
        self.sidesplitter = QSplitter(Qt.Vertical)

        # Data tree
        self.data_view = QTreeView(self.control_frame)
        self.data_view.setModel(self.datatree)
        self.data_view.setDragEnabled(True)
        self.data_view.setDropIndicatorShown(True)
        self.data_view.setSelectionMode(QAbstractItemView.ExtendedSelection)
        #self.data_view.setHeaderHidden(True)
        self.sidesplitter.addWidget(self.data_view)
        self.sidesplitter.setStretchFactor(0,1)

        # Module list
        module_view = QTreeView(self.control_frame)
        module_model = ModuleListModel(self.findModules())
        module_view.setModel(module_model)
        module_view.setDragEnabled(True)
        module_view.setDropIndicatorShown(True)
        self.sidesplitter.addWidget(module_view)
        self.sidesplitter.setStretchFactor(1,0)


        layout.addWidget(self.sidesplitter)
        self.control_frame.setLayout(layout)

    # The following drag/drop event handlers are to deal with the
    # Rogue overlay problem. Not the most elegant solution but it
    # seems to work.
    def dragLeaveEvent(self, e):
        self.filter_box.killRogueOverlays()
        super(MainWindow, self).dragLeaveEvent(e)

    def dragEnterEvent(self, e):
        if isinstance(e.mimeData(), DataIndexMime):
            e.accept()
        else:
           super(MainWindow, self).dragEnterEvent(e)

    def dropEvent(self, e):
        if isinstance(e.mimeData(), DataIndexMime):
            self.filter_box.killRogueOverlays()
            e.accept()
        else:
            super(MainWindow, self).dropEvent(e)

    def createMenus(self):
        """This defines the menu actions and shortcuts."""
        self.fileMenu = self.menuBar().addMenu("&File")
        self.fileMenu.addAction(QAction("&Open Run", self,
            shortcut = QKeySequence.Open, triggered=self.runOpen))
        self.fileMenu.addAction(QAction("&Quit", self,
            shortcut = "Ctrl+Q", triggered = self.close))

    def runOpen(self):
        """This launches a File dialog for opening Runs."""
        filename, filtr = QFileDialog.getOpenFileName(self)
        if filename == u'':
            return

        self.openRun(filename)

    def openRun(self, *runs):
        """User callable method to tell boxfish to open a file."""
        for run in runs:
            self.datatree.insertRun(run)
        self.data_view.expandAll() #For now

    #TODO: Read other directories to add from config file and add them
    def findModules(self):
        """This imports the Python module defined by the mods directory.
           This allows Boxfish to load whatever Boxfish module and related
           functionality is found there.
        """
        modules = list()

        import mods

        modules = ModuleFrame.subclassList()
        return modules

class TopAgent(ModuleAgent):
    """Module for handling top of agent tree interactions.
    """

    def __init__(self, parent, datatree):
        """Construct the TopAgent."""
        super(TopAgent, self).__init__(parent, datatree)


    # You can't add requests to this agent
    def addRequest(self, coupler):
        """This should never be called as this module should never
           need to handle requests."""
        raise UserWarning("Top agent should not have own requests.")

    @Slot(FilterCoupler, ModuleAgent)
    def addChildCoupler(self, coupler, child):
        """This is called when the child ModuleAgent (the top FilterBox)
           adds a coupler. All coupler chains will eventually reach here.
           Because this is the top of the Boxfish module tree, it starts
           the signalling process to let the original request know that
           a full data/filter path has been established.
        """
        super(TopAgent, self).addChildCoupler(coupler, child)
        # emit on new child column to start the chain
        self.child_requests[-1].changeSignal.emit(self.child_requests[-1])


class ModuleListModel(QStringListModel):
    """Simple datatree for interactions with list of available modules.
    """

    def __init__(self, slist):
        """Constructs the ModuleListModel. The parameter is a list of
           display_names of the existing Boxfish modules.
        """
        super(ModuleListModel, self).__init__(slist)
        pass

    def mimeData(self, index):
        """This creates and returns a ModuleNameMime that includes the
           display_name associated with the first given index.
        """
        return ModuleNameMime(self.data(index[0], 0))

    def headerData(self, section, orientation, role):
        """This sets up the header for this model."""
        if role == Qt.DisplayRole:
            if section == 0:
                return "Modules"
