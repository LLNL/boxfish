from ModuleAgent import *
from ModuleView import *

import sys
from PySide.QtCore import Signal, Slot
from PySide.QtGui import QTabWidget, QTableWidget, QAbstractItemView, \
    QItemSelectionModel


class TableAgent(ModuleAgent):
    """This is the agent for the Table Module. It is relatively
       simple with a single requirement.
    """

    tableUpdateSignal = Signal(list, list, list, list)

    def __init__(self, parent, datatree):
        """Like all agent subclasses, the init requires:

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

        # self.agent may not be accessible of parent_view is None,
        # so any actions in the constructor involving agent should 
        # do this check. All other functions are only accessible when
        # agent is not None, so the check is not required hereafter.
        if self.agent is not None:
            self.agent.tableUpdateSignal.connect(self.updateTables)


    def createView(self):
        """This required function creates the main view container for 
           this module, in this case a QTabWidget to hold all the table
           views. The rest of the GUI is handled by the superclass.
        """
        self.tabs = QTabWidget()
        return self.tabs

    
    def droppedData(self, indexList):
        """Overrides the superclass method to send the agent the dropped
           data indices.
        """
        self.agent.addDataIndices(indexList)

    
    @Slot(list, list, list, list)
    def updateTables(self, tables, ids, headers, values):
        """Creates table views.

           tables
               A list of tables for which we have data.

           ids
               A list of lists of the corresponding SubDomain ids for 
               each row of each table's returned values.

           headers
               A list of lists of the column names that go with the 
               given values for each table.

           values
              A list of list of lists, one for each column of each table.
        """

        # We need to save tables, id_lists for selection later
        self.tables = tables 
        self.id_lists = ids
        
        if tables is None:
            return
        
        self.tabs.clear() # Get rid of old data

        # For each table, create a table view and populate it with the
        # given values for that table
        for table, ids_list, header_list, value_lists \
            in zip(tables, ids, headers, values):
            tableWidget = TableTab(table, ids_list, header_list, value_lists)
            tableWidget.idsChanged.connect(self.selectionChanged)
            self.tabs.addTab(tableWidget, table)

    @Slot(str, set)
    def selectionChanged(self, table, ids):
        print table
        print ids


class TableTab(QTableWidget):

    idsChanged = Signal(str, set)

    def __init__(self, table, ids, headers, values):
        """Represent the given sub-table using a TableWidget.

           table
               The table name from which this data is fetched.

           ids
               The identifier that goes with each row

           headers
               The column names.

           value
               List of lists of values for each column
        """
        super(TableTab, self).__init__(min(100, len(values[0])), len(headers))
        # TODO: Change the number of rows/make configurable

        self.user_selection = True
        self.table = table
        self.ids = ids

        # Set behavior
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setHorizontalHeaderLabels(headers)
        self.itemSelectionChanged.connect(self.handleSelection)
            
        # Populate table
        for index, value_list in enumerate(values):
            for i in range(self.rowCount()):
                self.setItem(i, index, QTableWidgetItem(str(value_list[i])))

    def handleSelection(self):
        if not self.user_selection: # only handle if user did this
            return

        id_set = set()
        selected_items = self.selectedItems()
        for item in selected_items:
            id_set.add(self.ids[item.row()])
        
        self.idsChanged.emit(self.table, id_set)


    def selectRows(self, rows):
        if self.rowCount() <= 0:
            return
        self.user_selection = False # We don't want to cause this to emit anything
        
        selectionModel = self.selectionModel()
        self.selectRow(rows[0])
        selection = selectionModel.selection()
        for row in rows[1:]:
            self.selectRow(row)
            selection.merge(selectionModel.selection(),
                QItemSelectionModel.Select)

        selectionModel.clearSelection()
        selectionModel.select(selection, QItemSelectionModel.Select)


        self.user_selection = True
