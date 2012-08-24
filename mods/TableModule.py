from SubDomain import *
from BFModule import *
from DataModel import *

import sys
from PySide.QtCore import *
from PySide.QtGui import *

class TableModule(BFModule):

    columnSignal = Signal(int, list)

    def __init__(self, parent, model):
        super(TableModule, self).__init__(parent, model)

        self.indices = None

    def addDataIndices(self, indexList):
        self.indices = indexList
        columns = self.buildColumnsFromIndices(indexList)
        self.addRequirement(columns)

    @Slot(BFColumn)
    def requiredColumnChanged(self, col):
        print "Column changed!"
        identifiers = col.table._table.identifiers()
        for modifier in col.modifier_chain:
            identifiers = modifier.process(col, identifiers)
        attribute_list = col.table._table.attribute_by_identifiers(\
            identifiers, col.attributes, False)
        for i, att_list in enumerate(attribute_list):
            index = self.getIndex(col.attributes[i], col)
            self.columnSignal.emit(index, att_list)

    # This is the stupidest way possible to do this column connection
    # but I just want to see if the rest of this works. 
    def getIndex(self, attribute, col):
        for i, index in enumerate(self.indices):
            item = self.model.getItem(index)
            if item.name == attribute \
                and item.parent().name == col.table.name:
                return i

class TableWindow(BFModuleWindow):

    display_name = "Table"
    in_use = True

    def __init__(self, parent, parent_view = None, title = None):
        super(TableWindow, self).__init__(parent, parent_view, title)

        self.selected = []

        if self.module is not None:
            print "connect!"
            self.module.columnSignal.connect(self.displayColumn)

    def createModule(self):
        return TableModule(self.parent_view.module,
                            self.parent_view.module.model)

    def createView(self):
        self.tabwidget = QTableWidget(10,2)
        return self.tabwidget

    def droppedData(self, indexList):
        self.tabwidget.setColumnCount(len(indexList))

        def make_full_name(i):
            item = self.module.model.getItem(i)
            return "%s:%s" % (item.parent().name, item.name)

        def make_name(i):
            return self.module.model.getItem(i).name

        labels = [make_name(i) for i in indexList]
        self.tabwidget.setHorizontalHeaderLabels(labels)
        self.module.addDataIndices(indexList)

    @Slot(int, list)
    def displayColumn(self, index, values):
        self.tabwidget.setRowCount(len(values))
        for i in range(len(values)):
            self.tabwidget.setItem(i, index,
                    QTableWidgetItem(str(values[i])))

