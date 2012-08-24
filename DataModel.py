from PySide.QtCore import *
from PySide.QtGui import *
import sys
import os.path
from BFTable import *
from SubDomain import *
from Projection import *
import YamlLoader as yl

class AbstractTreeItem(object):
    """Base class for items that are in our data model.
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



class BFRunItem(AbstractTreeItem):
    """Item representing an entire run. Holds the run
       metadata. Its children are divided into tables
       and projections.
    """

    def __init__(self, name, metadata, parent=None):
        super(BFRunItem, self).__init__(name, parent)

        self._metadata = metadata

    def typeInfo(self):
        return "RUN"

    def hasMetaData(self, key):

        if self._metadata is not None \
            and key in self._metadata:
            return True

        return False

    def getMetaData(self, key):

        if self._metadata is not None \
            and key in self._metadata:
            if isinstance(self._metadata[key], dict):
                return self._metadata[key].viewitems()
            else:
                return self._metadata[key]


class BFGroupItem(AbstractTreeItem):
    """Item for grouping items of similar type, e.g. tables.
    """

    def __init__(self, name, parent=None):
        super(BFGroupItem, self).__init__(name, parent)

    def typeInfo(self):
        return "GROUP"

    # Passed metadata calls up to parent (run)
    def hasMetaData(self, key):
        if self.parent() is not None:
            self.parent().hasMetaData(key)

    def getMetaData(self, key):
        if self.parent() is not None:
            self.parent().getMetaData(key)


# REFACTORME: BFProjectionItem and BFTableItem share metadata functions
class BFProjectionItem(AbstractTreeItem):
    """Item for holding a projection and its metadata. The data types
       of the projection are represented as children.
    """

    def __init__(self, name, projection, metadata, parent = None):
        super(BFProjectionItem, self).__init__(name, parent)

        self._metadata = metadata
        self._projection = projection

    def typeInfo(self):
        return "PROJECTION"


    # It first searches its own meta data. Then it passes up the tree.
    def hasMetaData(self, key):

        if self._metadata is not None \
            and key in self._metadata:
            return True

        if self.parent() is not None:
            return self.parent().hasMetaData(key)


    def getMetaData(self, key):

        if self._metadata is not None \
            and key in self._metadata:
            if isinstance(self._metadata[key], dict):
                return self._metadata[key].viewitems()
            else:
                return self._metadata[key]

        if self.parent() is not None:
            return self.parent().getMetaData(key)


class BFTableItem(AbstractTreeItem):
    """Item for holding a table and its metadata. The columns of the
       table are the children.
    """

    def __init__(self, name, table, metadata, parent = None):
        super(BFTableItem, self).__init__(name, parent)

        self._metadata = metadata
        self._table = table

    def typeInfo(self):
        return "TABLE"

    # It first searches its own meta data. Then it passes up the tree.
    def hasMetaData(self, key):

        if self._metadata is not None \
            and key in self._metadata:
            return True

        if self.parent() is not None:
            return self.parent().hasMetaData(key)


    def getMetaData(self, key):

        if self._metadata is not None \
            and key in self._metadata:
            if isinstance(self._metadata[key], dict):
                return self._metadata[key].viewitems()
            else:
                return self._metadata[key]

        if self.parent() is not None:
            return self.parent().getMetaData(key)


# Projection Attribute may be different from table attribute,
# we may want to separate those out.
class BFAttributeItem(AbstractTreeItem):
    """Item for containing individual attributes. Access to these
       will be done through parent items.
    """

    # These are more intimately connected with their table/projection and
    # we will only think of them by name (and potentially type)
    def __init__(self, name, parent=None):
        super(BFAttributeItem, self).__init__(name, parent)

    def typeInfo(self):
        return "ATTRIBUTE"


class BFDataModel(QAbstractItemModel):
    """Data is accessed through this model. It is organized as a tree
       with Runs as level 1, Groups as level 2, Tables/Projections at
       level 3 and Attributes at level 4.
    """

    def __init__(self, root = AbstractTreeItem("BoxFish"), parent=None):
        super(BFDataModel, self).__init__(parent)
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
            return Qt.ItemIsEnabled | Qt.ItemIsEditable | Qt.ItemIsDragEnabled

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

    # Add a projection and its domains to the model.
    def insertProjection(self, name, projection, metadata, position=-1, \
        rows=1, parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if position == -1:
            position = parentItem.childCount()

        # Create projection
        self.beginInsertRows(parent, position, position + rows - 1)
        projectionItem = BFProjectionItem(name, projection, metadata, \
            parentItem)
        self.endInsertRows()

        #Create attributes
        self.beginInsertRows(self.createIndex(position, 0, projectionItem), \
            0, 2)
        attItem = BFAttributeItem(projection.source, projectionItem)
        attItem = BFAttributeItem(projection.destination, projectionItem)
        self.endInsertRows()

        return True


    # Add a table and its attributes to the model.
    def insertTable(self, name, table, metadata, position=-1, rows=1, \
        parent=QModelIndex()):
        parentItem = self.getItem(parent)
        if position == -1:
            position = parentItem.childCount()

        # Create table
        self.beginInsertRows(parent, position, position + rows - 1)
        tableItem = BFTableItem(name, table, metadata, parentItem)
        self.endInsertRows()

        #Create attributes
        self.beginInsertRows(self.createIndex(position, 0, tableItem), 0, \
            len(table.attributes()))
        for position, attribute in enumerate(table.attributes()):
            attItem = BFAttributeItem(attribute, tableItem)
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
           into the data model/data store. The input filename should
           refer to the meta file denoting the run.
        """
        parentItem = self._rootItem
        metadata, filelist = yl.load_meta(filename)
        if position == -1:
            position = parentItem.childCount()

        # Create RunItem
        self.beginInsertRows(QModelIndex(), position, position + rows - 1)
        runItem = BFRunItem(os.path.basename(filename), metadata, parentItem)
        self.endInsertRows()

        # Create groups for Tables and Projections
        self.beginInsertRows(self.createIndex(position, 0, runItem), 0, 2)
        tablesItem = BFGroupItem("tables", parent = runItem)
        projectionsItem = BFGroupItem("projections", parent = runItem)
        self.endInsertRows()

        # Create TableItems and ProjectionItems
        for filedict in filelist:
            if filedict['filetype'].upper() == "TABLE":
                type_string = filedict['domain'] + "_" + filedict['type']
                data_type = SubDomain().findSubdomain(type_string)
                if data_type is None:
                    print "No matching type found for", filedict['type'], \
                        "! Skipping table..."
                    continue

                filepath = os.path.join(os.path.dirname(filename), filedict['filename'])
                metadata, data = yl.load_table(filepath)
                combined_meta = dict(metadata.items() + filedict.items())
                atable = BFTable()
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
                    data_type = SubDomain().findSubdomain(type_string)
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
                    filepath = os.path.join(os.path.dirname(filename), filedict['filename'])
                    metadata, data = yl.load_table(filepath)
                    combined_meta = dict(metadata.items() + filedict.items())
                    atable = BFTable()
                    atable.fromRecArray(mydomains[0], mykeys[0], data)
                    aprojection = TableProjection(mydomains[0], mydomains[1], \
                            mykeys[0], mykeys[1], atable)
                    self.insertProjection(mydomains[0].typename() + "<->" \
                        + mydomains[1].typename(), aprojection, combined_meta, \
                        parent = self.createIndex(position, 0, projectionsItem))


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
        return BFDataMime(indices)


    def findTableBySubdomain(self, index):
        """Given a subdomain attribute (from a projection), find
           a list of indices from some other table.
        """
        if self.getItem(index).parent().typeInfo() == "PROJECTION":
            my_type = self.getItem(index).name
        else:
            pass



class BFDataMime(QMimeData):
    """For passing around model indices using drag and drop.
    """

    def __init__(self, data_index):
        super(BFDataMime, self).__init__()

        self.data_index = data_index

    def getDataIndices(self):
        return self.data_index



if __name__ == '__main__':

    app = QApplication(sys.argv)

    model = BFDataModel()

    treeView = QTreeView()
    treeView.show()
    treeView.setModel(model)

    model.insertRun("dummy_meta.yaml")

    sys.exit(app.exec_())
