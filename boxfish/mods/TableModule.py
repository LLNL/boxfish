import sys
from PySide.QtCore import Signal, Slot
from PySide.QtGui import QTabWidget, QTableWidget, QAbstractItemView, \
    QItemSelectionModel

from boxfish.ModuleAgent import *
from boxfish.ModuleFrame import *
from boxfish.SceneInfo import *

class TableAgent(ModuleAgent):
    """This is the agent for the Table Module. It is relatively
       simple with a single request.
    """

    tableUpdateSignal = Signal(list, list, list, list, list)
    highlightUpdateSignal = Signal(list)

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
        self.addRequest("table columns")
        self.tables = None
        self.runs = None


        # We handle updated data through self.presentData
        self.requestUpdatedSignal.connect(self.presentData)

        # We handle highlights throguh self.processHighlights
        self.highlightSceneChangeSignal.connect(self.processHighlights)

        self.apply_attribute_scenes = False # This modules doesn't use these

    def addDataIndices(self, indexList):
        """This function handles an added list of DataTree indices by
           associated them with the agent's Request.
        """
        self.requestAddIndices("table columns", indexList)

    @Slot(str)
    def presentData(self):
        """This function is called by requestUpdated to retrieve the
           appropriate data from the Request and pass it to all those
           listening for its signal. The TableModule presents data 'as is'
           instead of aggregating by some domain like other modules do.
           Therefore it simply gains the rows associated with the Request
           and broadcasts them.
        """
        tables, runs, ids, headers, data_lists \
            = self.requestGetRows("table columns")
        self.tables = tables
        self.runs = runs
        self.tableUpdateSignal.emit(tables, runs, ids, headers, data_lists)


    @Slot()
    def processHighlights(self):
        """When highlights have been received from another module,
           determine what currently in this module could be highlighted
           and alert any listening views.
        """
        if self.tables is None:
            return

        table_highlights = list()
        # Note, right now, via ModuleAgent, this is assuming that all
        # runs project to each other via Identity
        for table, run in zip(self.tables, self.runs):
            ids = self.getHighlightIDs(table, run)
            table_highlights.append(ids)

        self.highlightUpdateSignal.emit(table_highlights)

    def changeHighlights(self, table, run, ids):
        """Change the highlights associated with this module. This
           function is meant to be called by the view when it
           detects highlights have changed.
        """
        self.setHighlights([table], [run], [ids])



# For a Module to appear in Boxfish's GUI, as ModuleFrame must be decorated
# with @Module and given the display name ("Table") and the corresponding
# agent class the Frame uses (TableAgent).
@Module("Table", TableAgent)
class TableFrame(ModuleFrame):
    """This is the Frame class of the TableModule.
    """

    def __init__(self, parent, parent_frame = None, title = None):
        """Like all subclasses of ModuleFrame, the constructor requires:

            parent
                The GUI parent of this frame.

            parent_frame
                The ModuleFrame that is logically the parent to this one.

           Optionally, a title can be passed, but this is not yet in use.

           The Boxfish system handles the creation of ModuleFrames and will
           pass these values and only these values to any ModuleFrame.
        """
        super(TableFrame, self).__init__(parent, parent_frame, title)

        self.selected = []

        self.droppedDataSignal.connect(self.droppedData)
        self.agent.tableUpdateSignal.connect(self.updateTables)
        self.agent.highlightUpdateSignal.connect(self.updateSelection)


    def createView(self):
        """This required function creates the main view container for
           this module, in this case a QTabWidget to hold all the table
           views. The rest of the GUI is handled by the superclass.
        """
        self.tabs = QTabWidget()
        return self.tabs


    @Slot(list, str)
    def droppedData(self, indexList):
        """Overrides the superclass method to send the agent the dropped
           data indices.
        """
        self.agent.addDataIndices(indexList)


    @Slot(list, list, list, list, list)
    def updateTables(self, tables, runs, ids, headers, values):
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
        for table, run, ids_list, header_list, value_lists \
            in zip(tables, runs, ids, headers, values):
            tableWidget = TableTab(table, run, ids_list, header_list, value_lists)
            tableWidget.idsChanged.connect(self.selectionChanged)
            self.tabs.addTab(tableWidget, table)

    @Slot(list)
    def updateSelection(self, table_highlights):
        """Highlight the given table ids.

           table_highlights
               A list of lists of ids, one per table
        """
        for i, ids in enumerate(table_highlights):
            table = self.tabs.widget(i)
            table.selectRows(ids)


    @Slot(str, str, set)
    def selectionChanged(self, table, run, ids):
        """Pass along the selection information to the agent."""
        self.agent.changeHighlights(table, run, ids)


class TableTab(QTableWidget):
    """A TableTab is the display for a single Table in the TableWidget."""

    idsChanged = Signal(str, str, set)

    def __init__(self, table, run, ids, headers, values):
        """Represent the given sub-table using a TableWidget.

           table
               The table name from which this data is fetched.

           run
               The run from which the data is fetched

           ids
               The identifier that goes with each row

           headers
               The column names.

           values
               List of lists of values for each column
        """
        super(TableTab, self).__init__(min(100, len(values[0])), len(headers))
        # TODO: Change the number of rows/make configurable

        self.user_selection = True
        self.table = table
        self.run = run
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
        """Called when the selected rows change. If the selection was made
           by the user, it gets the IDs associated with the rows and signals
           those listening.
        """
        if not self.user_selection: # only handle if user did this
            return

        id_set = set()
        selected_items = self.selectedItems()
        for item in selected_items:
            id_set.add(self.ids[item.row()])

        self.idsChanged.emit(self.table, self.run, id_set)


    def selectRows(self, ids):
        """Given a set of ids, selects all the rows that are associated
           with those ids.
        """
        if self.rowCount() <= 0:
            return
        self.user_selection = False # We don't want to cause this to emit anything

        selectionModel = self.selectionModel()
        selectionModel.clearSelection()
        selection = selectionModel.selection()

        # Check if each row is in the id set and if so add it to the
        # selection
        for row in range(self.rowCount()):
            if self.ids[row] in ids:
                self.selectRow(row)
                selection.merge(selectionModel.selection(),
                    QItemSelectionModel.Select)

        selectionModel.clearSelection()
        selectionModel.select(selection, QItemSelectionModel.Select)


        self.user_selection = True
