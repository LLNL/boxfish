from PySide.QtCore import *
from PySide.QtGui import *
import sys
import os.path
from Table import *
from SubDomain import *
from Projection import *
import YamlLoader as yl
import functools

class AbstractTreeItem(object):
    """Base class for items that are in our data datatree.
    """

    def __init__(self, name, parent=None):

        self.name = name
        self._children = []
        self._parent = parent

        if parent is not None:
            parent.addChild(self)

    def typeInfo(self):
        return "ABSTRACT"

    def addChild(self, child):
        self._children.append(child)

    def insertChild(self, position, child):

        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child._parent = self
        return True

    def removeChild(self, position):

        if position < 0 or position > len(self._children):
            return False

        child = self._children.pop(position)
        child._parent = None

        return True

    def child(self, row):
        return self._children[row]

    def childCount(self):
        return len(self._children)

    def parent(self):
        return self._parent

    def row(self):
        if self._parent is not None:
            return self._parent._children.index(self)


class RunItem(AbstractTreeItem):
    """Item representing an entire run. Holds the run
       metadata. Its children are divided into tables
       and projections.
    """

    def __init__(self, name, metadata, parent=None):
        super(RunItem, self).__init__(name, parent)

        self._metadata = metadata
        self.subdomains = None
        self._table_subdomains = None
        self._projection_subdomains = None

    def typeInfo(self):
        return "RUN"

    def __contains__(self, key):
        return self.hasMetaData(key)

    def __getitem__(self, key):
        return self.getMetaData(key)

    def hasMetaData(self, key):
        if self._metadata is not None \
            and key in self._metadata:
            return True

        return False

    def getMetaData(self, key):
        if self._metadata is not None \
            and key in self._metadata:
            if isinstance(self._metadata[key], dict):
                # Caution: not deep copy, bad modules could do bad things 
                return self._metadata[key].copy()
            else:
                return self._metadata[key]
        return None

    def getRun(self):
        return self

    def refreshSubdomains(self):
        """The Run searches its tree to determine which subdomains
           it has available and what projections it can perform.
           This is intended to be called by the DataTree itself 
           to update a Run after adding/remove tables and projections.
           This does not occur automatically so we do not waste
           time recalculating when several tables are being added en masse.
        """
        for child in self._children:
            if child.name == "tables":
                tables = child
            else:
                projections = child

        # Table subdomains
        self._table_subdomains = list()
        for table in tables._children:
            if table._table.subdomain() not in self._table_subdomains:
                self._table_subdomains.append(table._table.subdomain())

        # Projection subdomains
        self.subdomains = list()
        for projection in projections._children:
            if projection._projection.source not in self.subdomains:
                self.subdomains.append(projection._projection.source)
            if projection._projection.destination not in self.subdomains:
                self.subdomains.append(projection._projection.destination)

        self._projection_subdomains = self.subdomains[:]

        # All subdomains
        for subdomain in self._table_subdomains:
            if subdomain not in self.subdomains:
                self.subdomains.append(subdomain)

        # Subdomain adjaceny matrix
        self.subdomain_matrix = list()
        for i in range(len(self._projection_subdomains)):
            self.subdomain_matrix.append([None] 
                * len(self._projection_subdomains))
               
        for projection in projections._children:
            i = self._projection_subdomains.index(
                projection._projection.source)
            j = self._projection_subdomains.index(
                projection._projection.destination)
            self.subdomain_matrix[i][j] = projection
            self.subdomain_matrix[j][i] = projection
            

    def getTable(self, table_name):
        """Look up a table by name."""
        for child in self._children:
            if child.name == "tables":
                tables = child

        for table in tables._children:
            if table.name == table_name:
                return table

        return None

    # This can find a projection within a Run. We still need
    # something that can do projections between Runs, where we
    # will assume identity projections on domains of interest
    # if we can
    #
    # Note to self: We should probably only do cross-run projections
    # where the second run needs no projections otherwise otherwise
    # things could get kind of weird or at least we should try to 
    # minimize the number of projections in the second run. 
    def getProjection(self, subdomain1, subdomain2):
        """Look up projection by subdomains. Returns
           None if there is no such projection.
        """
        if subdomain1.subdomain() == subdomain2.subdomain():
            return IdentityProjection(subdomain1, subdomain2)

        s1_index = self._projection_subdomains.index(subdomain1.subdomain())
        s2_index = self._projection_subdomains.index(subdomain2.subdomain())
        if self.subdomain_matrix[s1_index][s2_index] is not None:
            # We can do this in a single projection
            return self.subdomain_matrix[s1_index][s2_index]

        # We're going to have to create a composition
        # Let's Dijkstra!
        distance = [inf] * len(self._projection_subdomains)
        previous = [None] * len(self._projection_subdomains)
        distance[s1_index] = 0
        subdomain_set = self._projection_subdomains[:]
        while len(subdomain_set) > 0:
            closest = subdomain_set[0]
            for subdomain in subdomain_set:
                if distance[self._projection_subdomains.index(subdomain)] < \
                    distance[self._projection_subdomains.index(closest)]:
                    closest = subdomain
            
            index = self._projection_subdomains.index(closest)
            if distance[index] == inf:
                return None

            for j in len(self._projection_subdomains):
                if self.subdomain_matrix[index][j] is not None:
                    other_distance = distance[index] + 1
                    if other_distance < distance[j]:
                        distance[j] = other_distance
                        previous[j] = index

        # No path found
        if distance[s2_index] == inf:
            return None

        # Create composition filter:
        index = s2_index
        projection_list = list()
        while previous[index] is not None:
            projection_list.insert(0, (
                self.subdomain_matrix[previous[index][index]],
                self._projection_subdomains[previous[index]],
                self._projection_subdomains[index]))
            index = previous[index]

        return CompositionProjection(subdomain1, subdomain2, projection_list = 
            projection_list)
            
class SubRunItem(AbstractTreeItem):
    """Item that falls below a Run in the hierarchy."""

    def __init__(self, name, parent = None):
        super(SubRunItem, self).__init__(name, parent)
    
    def __contains__(self, key):
        return self.hasMetaData(key)

    def __getitem__(self, key):
        return self.getMetaData(key)

    # Passed metadata calls up to parent
    def hasMetaData(self, key):
        if self.parent() is not None:
            return self.parent().hasMetaData(key)
        return False

    def getMetaData(self, key):
        if self.parent() is not None and self.parent().hasMetaData(key):
            return self.parent().getMetaData(key)
        return None

    def getRun(self):
        if self.parent() is not None:
            return self.parent().getRun()
        return None



class DataObjectItem(SubRunItem):
    """Item attached to a data object and also having
       metda data. Examples: Table, Projection.
    """

    def __init__(self, name, metadata, parent = None):
        super(DataObjectItem, self).__init__(name, parent)

        self._metadata = metadata

    def __contains__(self, key):
        return self.hasMetaData(key)

    def __getitem__(self, key):
        return self.getMetaData(key)

    # It first searches its parent data, then its own
    # This means the run metadata takes precedence
    def hasMetaData(self, key):

        if self.parent() is not None and self.parent().hasMetaData(key):
            return True

        if self._metadata is not None \
            and key in self._metadata:
            return True

        return False


    def getMetaData(self, key):

        if self.parent() is not None and self.parent().hasMetaData(key):
            return self.parent().getMetaData(key)

        if self._metadata is not None \
            and key in self._metadata:
            if isinstance(self._metadata[key], dict):
                return self._metadata[key].viewitems()
            else:
                return self._metadata[key]

        return None



class GroupItem(SubRunItem):
    """Item for grouping items of similar type, e.g. tables.
    """

    def __init__(self, name, parent=None):
        super(GroupItem, self).__init__(name, parent)

    def typeInfo(self):
        return "GROUP"


class ProjectionItem(DataObjectItem):
    """Item for holding a projection and its metadata. The data types
       of the projection are represented as children.
    """

    def __init__(self, name, projection, metadata, parent = None):
        super(ProjectionItem, self).__init__(name, metadata, parent)

        self._projection = projection

    def typeInfo(self):
        return "PROJECTION"
    


class TableItem(DataObjectItem):
    """Item for holding a table and its metadata. The columns of the
       table are the children.
    """

    def __init__(self, name, table, metadata, parent = None):
        super(TableItem, self).__init__(name, metadata, parent)

        self._metadata = metadata
        self._table = table

    def typeInfo(self):
        return "TABLE"

    def hasAttribute(self, attribute):
        for child in self._children:
            if child.name == attribute:
                return True
        return False


# Projection Attribute may be different from table attribute,
# we may want to separate those out.
class AttributeItem(SubRunItem):
    """Item for containing individual attributes. Access to these
       will be done through parent items.
    """

    # These are more intimately connected with their table/projection and
    # we will only think of them by name (and potentially type)
    def __init__(self, name, parent=None):
        super(AttributeItem, self).__init__(name, parent)

    def typeInfo(self):
        return "ATTRIBUTE"
    


class DataTree(QAbstractItemModel):
    """Data is accessed through this datatree. It is organized as a tree
       with Runs as level 1, Groups as level 2, Tables/Projections at
       level 3 and Attributes at level 4.
    """

    def __init__(self, root = AbstractTreeItem("BoxFish"), parent=None):
        super(DataTree, self).__init__(parent)
        self._rootItem = root


    def rowCount(self, parent):
        if not parent.isValid():
            parentItem = self._rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    # We only show the names of things for now, so one row
    def columnCount(self, parent):
        return 1

    # Given data for each row for each role
    def data(self, index, role = Qt.UserRole):

        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return item.name

        # Boxfish specific stuff can be done under UserRole
        # if we think of anything to use it for.
        elif role == Qt.UserRole:
            pass

    # Display name of each column of information
    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if section == 0:
                return "Data"


    def flags(self, index):
        if not index.isValid():
            return 0

        # We use selection to determine data, so it should only be by attribute
        # We will allow name changes for Table and Run, hence the IsEditable
        item = index.internalPointer()
        if item.typeInfo() == "ATTRIBUTE":
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsDragEnabled

        if item.typeInfo() == "TABLE":
            return Qt.ItemIsEnabled | Qt.ItemIsEditable

        # RUN needs to be draggable for meta information only.
        if item.typeInfo() == "RUN":
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsDragEnabled | Qt.ItemIsSelectable

        if item.typeInfo() == "PROJECTION":
            return Qt.ItemIsEnabled | Qt.ItemIsEditable

        if item.typeInfo() == "GROUP":
            return Qt.ItemIsEnabled


    def parent(self, index):

        item = self.getItem(index)
        parentItem = item.parent()

        if parentItem == self._rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)


    def index(self, row, column, parent):

        parentItem = self.getItem(parent)
        childItem = parentItem.child(row)

        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()


    def getItem(self, index):
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self._rootItem

    # Add a projection and its domains to the datatree.
    def insertProjection(self, name, projection, metadata, position=-1, \
        rows=1, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if position == -1:
            position = parentItem.childCount()

        # Create projection
        self.beginInsertRows(parent, position, position + rows - 1)
        projectionItem = ProjectionItem(name, projection, metadata, \
            parentItem)
        self.endInsertRows()

        #Create attributes
        self.beginInsertRows(self.createIndex(position, 0, projectionItem), \
            0, 2)
        attItem = AttributeItem(projection.source, projectionItem)
        attItem = AttributeItem(projection.destination, projectionItem)
        self.endInsertRows()

        return True


    # Add a table and its attributes to the datatree.
    def insertTable(self, name, table, metadata, position=-1, rows=1, \
        parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if position == -1:
            position = parentItem.childCount()

        # Create table
        self.beginInsertRows(parent, position, position + rows - 1)
        tableItem = TableItem(name, table, metadata, parentItem)
        self.endInsertRows()

        #Create attributes
        self.beginInsertRows(self.createIndex(position, 0, tableItem), 0, \
            len(table.attributes()))
        for position, attribute in enumerate(table.attributes()):
            attItem = AttributeItem(attribute, tableItem)
        self.endInsertRows()

        return True


    # This function does too much. Some of the table/projection stuff should
    # be moved to a different class, especially the file handling.
    # This is currently the only way to really add files. Eventually we want
    # to be able to add pieces of a run after the fact or have files that
    # go to a default run for orphans.
    # Runs are inserted at root level.
    def insertRun(self, filename, position = -1, rows = 1):
        """Insert a run with all of its child tables and projections
           into the data datatree/data store. The input filename should
           refer to the meta file denoting the run.
        """
        parentItem = self._rootItem
        metadata, filelist = yl.load_meta(filename)
        if position == -1:
            position = parentItem.childCount()

        # Create RunItem
        self.beginInsertRows(QModelIndex(), position, position + rows - 1)
        runItem = RunItem(os.path.basename(filename), metadata, parentItem)
        self.endInsertRows()

        # Create groups for Tables and Projections
        self.beginInsertRows(self.createIndex(position, 0, runItem), 0, 2)
        tablesItem = GroupItem("tables", parent = runItem)
        projectionsItem = GroupItem("projections", parent = runItem)
        self.endInsertRows()

        # Create TableItems and ProjectionItems
        for filedict in filelist:
            if filedict['filetype'].upper() == "TABLE":
                type_string = filedict['domain'] + "_" + filedict['type']
                data_type = SubDomain().instantiate(type_string)
                if data_type is None:
                    print "No matching type found for", filedict['type'], \
                        "! Skipping table..."
                    continue

                filepath = os.path.join(os.path.dirname(filename), 
                    filedict['filename'])
                metadata, data = yl.load_table(filepath)
                combined_meta = dict(metadata.items() + filedict.items())
                atable = Table()
                atable.fromRecArray(data_type, filedict['field'], data)
                self.insertTable(filedict['filename'], atable, combined_meta, \
                    parent = self.createIndex(position, 0, tablesItem))
            elif filedict['filetype'].upper() == "PROJECTION":
                domainlist = filedict['subdomain']
                mydomains = list()
                mykeys = list()
                for subdomaindict in domainlist:
                    type_string = subdomaindict['domain'] + "_" \
                        + subdomaindict['type']
                    data_type = SubDomain().instantiate(type_string)
                    if data_type is None:
                        print "No matching type found for", \
                            subdomaindict['type'], "! Skipping projection..."
                        continue
                    else:
                        mydomains.append(data_type)
                        mykeys.append(subdomaindict['field'])

                if len(mydomains) != 2:
                    print "Not enough domains for projection. Skipping..."
                    continue

                # Different projections created here per type. Again, probably
                # should be moved to different class.
                if filedict['type'].upper() == "FILE":
                    filepath = os.path.join(os.path.dirname(filename),
                        filedict['filename'])
                    metadata, data = yl.load_table(filepath)
                    combined_meta = dict(metadata.items() + filedict.items())
                    atable = Table()
                    atable.fromRecArray(mydomains[0], mykeys[0], data)
                    aprojection = TableProjection(mydomains[0], mydomains[1],
                        source_key = mykeys[0], destination_key = mykeys[1],
                        table = atable)
                    self.insertProjection(mydomains[0].typename() + "<->"
                        + mydomains[1].typename(), aprojection, combined_meta,
                        parent = self.createIndex(position, 0, projectionsItem))
                else:
                    aprojection = Projection(mydomains[0],
                        mydomains[1]).instantiate(filedict['type'],
                        mydomains[0], mydomains[1], run = runItem, **filedict)
                    self.insertProjection(mydomains[0].typename() + "<->"
                        + mydomains[1].typename(), aprojection, filedict,
                        parent = self.createIndex(position, 0, projectionsItem))


        runItem.refreshSubdomains()
        return True

    # TODO: Add the ability to remove elements
    def removeTable(self, position, rows, parent=QModelIndex()):
        pass

    def removeRun(self, position, rows, parent=QModelIndex()):
        pass

    # Instead of the default hard for us to parse type, we just pass it around
    # as objects. Note this causes the drop actions on standard views to fail
    # most likely unless we also override dropMimeData(). For now we don't
    # want drop actions on standard views anyway.
    def mimeData(self, indices):
        return DataIndexMime(indices)


    def findTableBySubdomain(self, index):
        """Given a subdomain attribute (from a projection), find
           a list of indices from some other table.
        """
        if self.getItem(index).parent().typeInfo() == "PROJECTION":
            my_type = self.getItem(index).name
        else:
            pass


    # Query evaluation
    def evaluate(self, conditions, table, identifiers):
        def unique_identifiers(l1, l2):
            l2 = set(l2)
            return [x for x in l1 if x in l2]

        if isinstance(conditions.clauses[0], TableAttribute):
        # We need to process every pair completely separately and then
        # and them together.
            identifiers_lists = list()
            prev_clause = conditions.clauses[0]
            for clause in conditions.clauses[1:]:
                identifiers_lists.append(evaluate_pair(conditions, table,
                    identifiers, prev_clause, clause))
                prev_clause = clause
            return functools.reduce(unique_identifiers, identifiers_lists) 
        elif isinstance(conditions.clauses[0], Clause):
        # This means everything in the list is a clause so they 
        # evaluate in this realm to lists of identifiers which 
        # we will AND together with unique_ids
            return functools.reduce(unique_identifiers, 
                (c.evaluate(table, identifiers) for c in conditions.clauses))
        else:
            raise ValueError("Malformed query: " + str(conditions))

    def evaluate_pair(self, conditions, table, identifiers, c1, c2):
        if isinstance(c1, TableAttribute):
            if isinstance(c2, TableAttribute): # Comparing attributes
                if (c1.table is None and table.hasAttribute(c1.name)) \
                    or c1.table == table:
                    if (c2.table is None and table.hasAttribute(c2.name)) \
                        or c2.table == table:
                        return table._table.subset_by_conditions(identifiers,
                            Clause(conditions.relation, c1, c2))
                    else:
                        # c2 requires projection
                        pass
                else: # c1 requires projection
                    if (c2.table is None and table.hasAttribute(c2.name)) \
                        or c2.table == table:
                        pass
                    else:
                        pass

            else: # Not comparing attributes, comparing literal
                if (c1.table is None and table.hasAttribute(c1.name)) \
                    or c1.table == table:
                    return table._table.subset_by_conditions(identifiers,
                        Clause(relation, c1, c2))
                elif c1.table is not None and c1.table != table \
                    and c1.table._table.subdomain() == table.subdomain():
                        # Same subdomain, no projection needed

                        # Get Ids from c1's table. This finds the unique
                        # ones:
                        keys = c1.table._table.attributes_by_conditions(
                            c1.table._table.identifiers(), # identifiers
                            [c1.table["field"]], # subdomain id
                            Clause(conditions.relation, c1.name, c2)) #condition

                        # Implicit identity projection since subdomain
                        # is the same, so get identifiers by key from
                        # table we care about
                        return table._table.subset_by_key(
                            table._table.identifiers(),
                            Subdomain().instantiate(table._table.subdomain(),
                            keys))
                else:
                    # Find the projection
                    pass 
        else:
            raise ValueError("Malformed query: " + str(conditions))


class DataIndexMime(QMimeData):
    """For passing around datatree indices using drag and drop.
    """

    def __init__(self, data_index):
        super(DataIndexMime, self).__init__()

        self.data_index = data_index

    def getDataIndices(self):
        return self.data_index



if __name__ == '__main__':

    app = QApplication(sys.argv)

    datatree = DataTree()

    treeView = QTreeView()
    treeView.show()
    treeView.setModel(datatree)

    datatree.insertRun("dummy_meta.yaml")

    sys.exit(app.exec_())
