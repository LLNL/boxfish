from SubDomain import *
from BFModule import *
from DataModel import *

import sys
from PySide.QtCore import *
from PySide.QtGui import *

class TableModule(BFModule):

    def __init__(self, parent, model):
        super(TableModule, self).__init__(parent, model)

    def addDataIndices(self, indexList):
        columns = self.buildColumnsFromIndices(indexList)

class TableWindow(BFModuleWindow):

    display_name = "Table"
    in_use = True

    def __init__(self, parent, parent_view = None, title = None):
        super(TableWindow, self).__init__(parent, parent_view, title)

        self.selected = []

    def createModule(self):
        return TableModule(self.parent_view.module,
                            self.parent_view.module.model)

    def createView(self):
        view = QWidget()

        self.tablabel = QLabel("Attributes: ")
        self.tabattrs = QLabel("")

        self.tabattrs.setWordWrap(True)

        self.tabwidget = QTableWidget(10,2)

        layout = QGridLayout()
        layout.addWidget(self.tablabel, 0, 0, 1, 1)
        layout.addWidget(self.tabattrs, 0, 1, 1, 1)
        layout.addWidget(self.tabwidget,1,0,1,2)
        layout.setRowStretch(2, 10)
        layout.setContentsMargins(0, 0, 0, 0)
        view.setLayout(layout)

        return view

    def droppedData(self, indexList):
        # We assume generally dropped data is Y data
        self.tabattrs.setText(self.buildAttributeString(indexList))
        self.tabwidget.setColumnCount(len(indexList))
        self.module.addDataIndices(indexList)

    def buildAttributeString(self, indexList):
        mytext = ""
        for index in indexList:
            mytext = mytext + self.module.model.getItem(index).name + ", "
        return mytext[:len(mytext) - 2]


