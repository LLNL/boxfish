from SubDomain import *
from Module import *
from DataModel import *

import sys
from PySide.QtCore import *
from PySide.QtGui import *

class TableAgent(ModuleAgent):

    columnSignal = Signal(int, list)

    def __init__(self, parent, datatree):
        super(TableAgent, self).__init__(parent, datatree)

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
            item = self.datatree.getItem(index)
            if item.name == attribute \
                and item.parent().name == col.table.name:
                return i

@Module("Table")
class TableView(ModuleView):

    def __init__(self, parent, parent_view = None, title = None):
        super(TableView, self).__init__(parent, parent_view, title)

        self.selected = []

        if self.agent is not None:
            print "connect!"
            self.agent.columnSignal.connect(self.displayColumn)

    def createModule(self):
        return TableAgent(self.parent_view.agent,
                            self.parent_view.agent.datatree)

    def createView(self):
        self.tabwidget = QTableWidget(10,2)
        return self.tabwidget

    def droppedData(self, indexList):
        self.tabwidget.setColumnCount(len(indexList))

        def make_full_name(i):
            item = self.agent.datatree.getItem(i)
            return "%s:%s" % (item.parent().name, item.name)

        def make_name(i):
            return self.agent.datatree.getItem(i).name

        labels = [make_name(i) for i in indexList]
        self.tabwidget.setHorizontalHeaderLabels(labels)
        self.agent.addDataIndices(indexList)

    @Slot(int, list)
    def displayColumn(self, index, values):
        rows = 100
        if len(values) < 100:
            rows = len(values)
        self.tabwidget.setRowCount(rows)
        for i in range(rows):
            self.tabwidget.setItem(i, index,
                    QTableWidgetItem(str(values[i])))

