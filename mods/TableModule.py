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
        self.tabwidget = QTableWidget(10,2)
        return self.tabwidget

    def droppedData(self, indexList):
        # We assume generally dropped data is Y data
        self.tabwidget.setColumnCount(len(indexList))

        def make_full_name(i):
            item = self.module.model.getItem(i)
            return "%s:%s" % (item.parent().name, item.name)

        def make_name(i):
            return self.module.model.getItem(i).name

        labels = [make_name(i) for i in indexList]
        self.tabwidget.setHorizontalHeaderLabels(labels)
        self.module.addDataIndices(indexList)
