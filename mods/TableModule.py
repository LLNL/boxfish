from SubDomain import *
from Module import *
from DataModel import *

import sys
from PySide.QtCore import *
from PySide.QtGui import *

class TableAgent(ModuleAgent):

    tableUpdateSignal = Signal(list, list)

    def __init__(self, parent, datatree):
        super(TableAgent, self).__init__(parent, datatree)

        self.indices = None
        self.table_coupler = None

        self.addRequirement("table columns")

    def addDataIndices(self, indexList):
        self.indices = indexList
        self.presentData()

    def makeHeaderLabels(self):
        headers = list()
        for table, attributes in self.attribute_groups:
            print table
            for attribute in attributes:
                print attributes
                headers.append(self.datatree.getItem(attribute).name)

        print headers, " are the headers"
        return headers

    @Slot(FilterCoupler)
    def requiredCouplerChanged(self, coupler):
        self.table_coupler = coupler
        self.presentData()

    def presentData(self):
        if self.indices is None:
            return
        self.attribute_groups = self.sortIndicesByTable(self.indices)
        data_list = list()
        headers = list()
        for table, attribute_group in self.attribute_groups:
            attributes = [self.datatree.getItem(x).name for x in
                attribute_group]
            headers.extend(attributes)
            identifiers = table._table.identifiers()
            for modifier in self.table_coupler.modifier_chain:
                identifiers = modifier.process(table._table, identifiers)
            attribute_list = table._table.attribute_by_identifiers(
                identifiers, attributes, False)
            for sub_list in attribute_list:
                data_list.append(sub_list)
        self.tableUpdateSignal.emit(headers, data_list)


@Module("Table")
class TableView(ModuleView):

    def __init__(self, parent, parent_view = None, title = None):
        super(TableView, self).__init__(parent, parent_view, title)

        self.selected = []

        if self.agent is not None:
            self.agent.tableUpdateSignal.connect(self.updateTable)

    def createAgent(self):
        return TableAgent(self.parent_view.agent,
                            self.parent_view.agent.datatree)

    def createView(self):
        self.table_widget = QTableWidget(10,2)
        return self.table_widget

    def droppedData(self, indexList):
        self.agent.addDataIndices(indexList)

    @Slot(list, list)
    def updateTable(self, headers, values):
        rows = 100
        print headers
        self.table_widget.setColumnCount(len(headers))
        self.table_widget.setHorizontalHeaderLabels(headers)
        self.table_widget.setRowCount(rows)
        for index, value_list in enumerate(values):
            for i in range(rows):
                self.table_widget.setItem(i, index,
                        QTableWidgetItem(str(value_list[i])))

