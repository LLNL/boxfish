from Module import *

import sys
from PySide.QtCore import *
from PySide.QtGui import *

class TableAgent(ModuleAgent):

    tableUpdateSignal = Signal(list, list, list, list)

    def __init__(self, parent, datatree):
        super(TableAgent, self).__init__(parent, datatree)

        self.addRequirement("table columns")

    def addDataIndices(self, indexList):
        self.requestAddIndices("table columns", indexList)
        self.presentData()

    def requestUpdated(self, name):
        if name != "table columns":
            raise ValueError("Table Module: Unrecognized Request!")
        self.presentData()

    def presentData(self):
        tables, ids, headers, data_lists \
            = self.requestGetRows("table columns")
        self.tableUpdateSignal.emit(tables, ids, headers, data_lists)


@Module("Table", TableAgent)
class TableView(ModuleView):

    def __init__(self, parent, parent_view = None, title = None):
        super(TableView, self).__init__(parent, parent_view, title)

        self.selected = []
        self.tableWidget = None

        if self.agent is not None:
            self.agent.tableUpdateSignal.connect(self.updateTables)

    def createView(self):
        self.tabs = QTabWidget()
        self.tabs.addTab(self.createTable(100,2), "No Data")
        return self.tabs

    # We may want to add a QScrollArea around this and so forth
    def createTable(self, rows, cols):
        return QTableWidget(rows, cols)

    def droppedData(self, indexList):
        self.agent.addDataIndices(indexList)

    @Slot(list, list, list, list)
    def updateTables(self, tables, ids, headers, values):
        self.tables = tables
        self.id_lists = ids
        if tables is None:
            return
        rows = 100
        self.tabs.clear()
        for table, header_list, value_lists in zip(tables, headers, values):
            if len(value_lists[0]) < 100:
                rows = len(value_lists[0])
            self.tableWidget = self.createTable(rows, len(header_list))
            self.tableWidget.setSelectionBehavior(QAbstractItemView.SelectRows)
            self.tableWidget.setSelectionMode(
                QAbstractItemView.ExtendedSelection)
            self.tableWidget.setHorizontalHeaderLabels(header_list)
            for index, value_list in enumerate(value_lists):
                for i in range(rows):
                    tableWidget.setItem(i, index,
                        QTableWidgetItem(str(value_list[i])))
            self.tabs.addTab(tableWidget, table)

    def selectRows(self, rows):
        if not self.tableWidget or len(rows) == 0:
            return

        selectionModel = self.tableWidget.selectionModel()
        self.tableWidget.selectRow(rows[0])
        selection = selectionModel.selection()
        for row in rows[1:]:
            self.tableWidget.selectRow(row)
            selection.merge(selectionModel.selection(),
                QItemSelectionModel.Select)

        selectionModel.clearSelection()
        selectionModel.select(selection, QItemSelectionModel.Select)
