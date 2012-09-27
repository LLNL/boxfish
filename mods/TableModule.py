from Module import *

import sys
from PySide.QtCore import *
from PySide.QtGui import *

class TableAgent(ModuleAgent):
    """This is the agent for the Table Module. It is relatively
       simple with a single requirement.
    """

    tableUpdateSignal = Signal(list, list, list, list)

    def __init__(self, parent, datatree):
        """Like all agent subclasses, the init should only require:

           parent
               The parent agent in the Boxfish agent tree.

           datatree
               A reference to the DataTree which stores tables and
               projections.
        """
        super(TableAgent, self).__init__(parent, datatree)

        # Right now the Table module has a single Request. This
        # means that all data it acquires will always pass through
        # the same filters. Potentially we could make a Request per
        # table based on the indicies, but we have something simple for now
        self.addRequirement("table columns")

    def addDataIndices(self, indexList):
        """This function handles an added list of DataTree indices by
           associated them with the agent's Request.
        """
        self.requestAddIndices("table columns", indexList)
        self.presentData()

    def requestUpdated(self, name):
        """This overloads the ModuleAgent function called when a Request
           has been updated. It handles the update notification by verifying
           the Request tag is recognized and then processing the changed
           request.
        """
        if name != "table columns":
            raise ValueError("Table Module: Unrecognized Request!")
        self.presentData()

    def presentData(self):
        """This function is called by requestUpdated to retrieve the
           appropriate data from the Request and pass it to all those
           listening for its signal. The TableModule presents data 'as is'
           instead of aggregating by some domain like other modules do.
           Therefore it simply gains the rows associated with the Request
           and broadcasts them.
        """
        tables, ids, headers, data_lists \
            = self.requestGetRows("table columns")
        self.tableUpdateSignal.emit(tables, ids, headers, data_lists)

# For a Module to appear in Boxfish's GUI, as ModuleView must be decorated
# with @Module and given the display name ("Table") and the corresponding
# agent class the View uses (TableAgent).
@Module("Table", TableAgent)
class TableView(ModuleView):
    """This is the View class of the TableModule.
    """

    def __init__(self, parent, parent_view = None, title = None):
        """Like all subclasses of ModuleView, the constructor requires:

            parent
                The GUI parent of this view.

            parent_view
                The ModuleView that is logically the parent to this one.

           Optionally, a title can be passed, but this is not yet in use.

           The Boxfish system handles the creation of ModuleViews and will
           pass these values and only these values to any ModuleView.
        """
        super(TableView, self).__init__(parent, parent_view, title)

        self.selected = []
        self.tableWidget = None

        # self.agent may not be accessible of parent_view is None,
        # so any actions in the constructor involving agent should 
        # do this check. All other functions are only accessible when
        # agent is not None, so the check is not required hereafter.
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
