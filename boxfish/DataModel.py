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
        """Construct an AbstractTreeItem with give name and parent
           AbstractTreeItem.
        """
        super(AbstractTreeItem, self).__init__()
        self.name = name
        self._children = []
        self._parent = parent

        if parent is not None:
            parent.addChild(self)

    def typeInfo(self):
        """Return the type of model item."""
        return "ABSTRACT"

    def addChild(self, child):
        """Add a child item to this item at the end of the child list."""
        self._children.append(child)

    def insertChild(self, position, child):
        """Add a child item to this item at the given position in the
           child list.
        """
        if position < 0 or position > len(self._children):
            return False

        self._children.insert(position, child)
        child._parent = self
        return True

    def removeChild(self, position):
        """Remove the child item at the given position."""
        if position < 0 or position > len(self._children):
            return False

        child = self._children.pop(position)
        child._parent = None

        return True

    def child(self, row):
        """Return the child item at the given position."""
        return self._children[row]

    def childCount(self):
        """Return the number of children."""
        return len(self._children)

    def parent(self):
        """Return the parent item of this item."""
        return self._parent

    def row(self):
        """Return the position of this item relative to its parent item."""
        if self._parent is not None:
            return self._parent._children.index(self)

    def buildAttributeSet(self, attributes = set()):
        """Return a set of all AttributeItems found under this item."""
        for child in self._children:
            child.buildAttributeSet(attributes)

        return attributes

    def buildAttributeValues(self, attribute, values = set()):
        """Return a set of all known values for a given attribute any
           place it is found under this item.
        """
        for child in self._children:
            child.buildAttributeValues(attribute, values)

        return values


class RunItem(AbstractTreeItem):
    """Item representing an entire run. Holds the run metadata. Its
       children are divided into tables and projections.
    """

    def __init__(self, name, metadata, parent=None):
        """Construct a RunItem. The metadata should be represented as a
           dict.
        """
        super(RunItem, self).__init__(name, parent)

        self._metadata = metadata
        self.subdomains = None
        self._table_subdomains = None
        self._projection_subdomains = None

    def typeInfo(self):
        """Returns RUN"""
        return "RUN"

    def __contains__(self, key):
        """Determine if a key is present in the RunItem's metadata."""
        if self._metadata is not None \
            and key in self._metadata:
            return True

        return False

    def __getitem__(self, key):
        """Retrieve the value of the metadata associated ith the given key.
           Returns None if the key is not in the metadata.
        """
        if self._metadata is not None \
            and key in self._metadata:
            if isinstance(self._metadata[key], dict):
                # Caution: not deep copy, bad modules could do bad things
                return self._metadata[key].copy()
            else:
                return self._metadata[key]
        return None

    def getRun(self):
        """Returns this item. This is used for finding the RunItem from
           anywhere in the subtree.
        """
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
        """Look up a child table by name."""
        for child in self._children:
            if child.name == "tables":
                tables = child

        for table in tables._children:
            if table.name == table_name:
                return table

        return None


    def findAttribute(self, attribute, table):
        """Find a table with the given attribute. Preference is given
           to tables with the same subdomain as the given table,
           then to tables that are one projection away, then to all
           remaining tables.
        """

        for child in self._children:
            if child.name == "tables":
                tables = child

        # Subdomain is same
        for t in tables._children:
            if t._table.subdomain() == table._table.subdomain() \
                and t.hasAttribute(attribute):
                return t

        # Make sure we can project the given table
        if table._table.subdomain() in self._projection_subdomains:
            index = self._projection_subdomains.index(table._table.subdomain())

            # Subdomain is one hop
            for t in tables._children:
                if t._table.subdomain() in self._projection_subdomains:
                    t_index = self._projection_subdomains.index(
                        t._table.subdomain())
                    if self.subdomain_matrix[index][t_index] is not None \
                        and t.hasAttribute(attribute):
                        return t


        # Subdomain is more than one hop (may be infinite)
        for t in tables._children:
            if t.hasAttribute(attribute):
                return t

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
        if subdomain1 == subdomain2:
            return IdentityProjection(subdomain1, subdomain2)

        # Make sure projections exist between these subdomaisn
        if subdomain1 in self._projection_subdomains:
            s1_index = self._projection_subdomains.index(subdomain1)
        else:
            return None

        if subdomain1 in self._projection_subdomains:
            s2_index = self._projection_subdomains.index(subdomain2)
        else:
            return None


        if self.subdomain_matrix[s1_index][s2_index] is not None:
            # We can do this in a single projection
            return self.subdomain_matrix[s1_index][s2_index]._projection

        # We're going to have to create a composition
        # Let's Dijkstra!
        distance = [float('inf')] * len(self._projection_subdomains)
        previous = [None] * len(self._projection_subdomains)
        distance[s1_index] = 0
        subdomain_set = self._projection_subdomains[:]
        while len(subdomain_set) > 0:
            closest = subdomain_set[0]
            for subdomain in subdomain_set:
                if distance[self._projection_subdomains.index(subdomain)] < \
                    distance[self._projection_subdomains.index(closest)]:
                    closest = subdomain

            subdomain_set.remove(closest)
            index = self._projection_subdomains.index(closest)
            if distance[index] == float('inf'):
                return None

            for j in range(len(self._projection_subdomains)):
                if self.subdomain_matrix[index][j] is not None:
                    other_distance = distance[index] + 1
                    if other_distance < distance[j]:
                        distance[j] = other_distance
                        previous[j] = index

        # No path found
        if distance[s2_index] == float('inf'):
            return None

        # Create composition filter:
        index = s2_index
        projection_list = list()
        while previous[index] is not None:
            print self.subdomain_matrix[previous[index]][index].name
            projection_list.insert(0, (
                self.subdomain_matrix[previous[index]][index]._projection,
                self._projection_subdomains[previous[index]],
                self._projection_subdomains[index]))
            index = previous[index]

        return CompositionProjection(subdomain1, subdomain2, projection_list =
            projection_list)


class SubRunItem(AbstractTreeItem):
    """Item that falls below a Run in the hierarchy. Such items can
       find their governing RunItem and search/retrieve metadata up
       the tree.
    """

    def __init__(self, name, parent = None):
        """Construct a SubRunItem."""
        super(SubRunItem, self).__init__(name, parent)

    def __contains__(self, key):
        """Searches up tree for the presence of the key in some item's
           metadata.
        """
        if self.parent() is not None:
            return key in self.parent()
        return False

    def __getitem__(self, key):
        """Searches up the tree for the value associated with the given
           tree. Returns None if invalid or not found.
        """
        if self.parent() is not None and key in self.parent():
            return self.parent()[key]
        return None

    def getRun(self):
        """Returns the RunItem up the tree from this item."""
        if self.parent() is not None:
            return self.parent().getRun()
        return None



class DataObjectItem(SubRunItem):
    """Item attached to a data object and also having meta data.
       Examples: Table, Projection.
    """

    def __init__(self, name, metadata, parent = None):
        """Construct a DataObjectItem. The metadata should be a dict."""
        super(DataObjectItem, self).__init__(name, parent)

        self._metadata = metadata

    def __contains__(self, key):
        """Returns True if the given key is in the metadata of this item
           or an item up the tree from this item.
        """
        if self.parent() is not None and key in self.parent():
            return True

        if self._metadata is not None \
            and key in self._metadata:
            return True

        return False

    def __getitem__(self, key):
        """Returns the value associated with the given key in the metadata
           of this item or an item up the tree from this item. If it is
           found in multiple places, the one furthest up the tree will
           be returned.
        """
        if self.parent() is not None and key in self.parent():
            return self.parent()[key]

        if self._metadata is not None \
            and key in self._metadata:
            if isinstance(self._metadata[key], dict):
                return self._metadata[key].copy()
            else:
                return self._metadata[key]

        return None



class GroupItem(SubRunItem):
    """Item for grouping items of similar type, e.g. tables.
    """

    def __init__(self, name, parent=None):
        """Construct a GroupItem."""
        super(GroupItem, self).__init__(name, parent)

    def typeInfo(self):
        """Return GROUP."""
        return "GROUP"


class ProjectionItem(DataObjectItem):
    """Item for holding a projection and its metadata.
    """

    def __init__(self, name, projection, metadata, parent = None):
        """Construct a ProjectionItem. The projection is a Projection
           object. The metadata is a dict.
        """
        super(ProjectionItem, self).__init__(name, metadata, parent)

        self._projection = projection

    def typeInfo(self):
        """Return PROJECTION."""
        return "PROJECTION"



class TableItem(DataObjectItem):
    """Item for holding a table and its metadata. The columns of the
       table are the children.
    """

    def __init__(self, name, table, metadata, parent = None):
        """Construct a TableItem. The table is a Table object. The
           metadata is a dict.
        """
        super(TableItem, self).__init__(name, metadata, parent)

        self._table = table

    def typeInfo(self):
        """Return TABLE."""
        return "TABLE"

    def hasAttribute(self, attribute):
        """Returns True if this item has an AttributeItem with the given
           name.
        """
        for child in self._children:
            if child.name == attribute:
                return True
        return False

    def buildAttributeValues(self, attribute, values = set()):
        """If the contained Table contains an attribute of the given name,
           returns a set of all values that attribute takes. Returns an
           empty set otherwise.
        """
        if self.hasAttribute(attribute):
            attributes = [attribute]
            attribute_list = self._table.attributes_by_identifiers(
                self._table.identifiers(), attributes)
            for value in attribute_list[0]:
                values.add(str(value))

        return values


    # Query evaluation - maybe this should be put back into the
    # QueryEngine class that was at some point jettisoned.
    def evaluate(self, conditions, identifiers):
        """Evaluates the conditions on a particular table and set
           of starting identifiers. Returns a list of valid identifiers
           on the table.

           conditions
               A Clause object to be evaluated on the table.

           identifiers
               A list of identifiers from the table indicating which
               table rows should be evaluated over.
        """

        # Maybe we should just do this with sets, maintaing order
        # probably does not grant us any advantages
        def unique_identifiers(l1, l2):
            l2 = set(l2)
            return [x for x in l1 if x in l2]

        # Find tables needed by this query
        attribute_set = conditions.getAttributes()
        auxiliary_tables = set()
        for attribute in attribute_set:
            if attribute.table is not None:
                auxiliary_tables.add(attribute.table)
            elif not self.hasAttribute(attribute.name):
                aux_table = self.getRun().findAttribute(attribute.name, self)
                if aux_table is not None:
                    auxiliary_tables.add(aux_table)
                # For now, if we don't find this attribute, we'll just
                # ignore it since the table queries will. Later on 
                # we might want to kick this up to cross-run queries
                # or have some sort of error message.

        identifiers_lists = list()
        identifiers_lists.append(identifiers)
        for aux_table in auxiliary_tables:
            projection = self.getRun().getProjection(
                self._table.subdomain(),
                aux_table._table.subdomain())
            keys = aux_table._table.attributes_by_conditions(
                aux_table._table.identifiers(), # identifiers
                [aux_table._table._key], # id for table for projection
                conditions) # we want default unique=true since we want keys

            keys = list(keys[0])
            projected_keys = projection.project(keys, self._table.subdomain())

            identifiers_lists.append(self._table.subset_by_key(
                self._table.identifiers(),
                SubDomain.instantiate(self._table.subdomain(),
                    projected_keys)))

        # Question: Does not applying the original tables identifiers
        # to everything else via projection cause a problem?

        evaluated_identifiers = functools.reduce(unique_identifiers,
            identifiers_lists)

        # Now finally apply to target table
        return self._table.subset_by_conditions(evaluated_identifiers,
            conditions)

    #Unused
    def createIdAttributeMaps(self, attributes, aggregator = 'max'):
        """[UNUSED] Creates a forward and backward dict from the table's ID to
           a set of attributes, row-aggregated by the given aggregator.
        """
        attribute_groups, ids = self._table.group_attributes_by_attributes(
            self._table.identifiers(), attributes, [self['field']], aggregator)

        id_dict = dict()
        attr_dict = dict()
        for group, id in zip(attribute_groups, ids[0]):
            id_dict[id] = group
            if group in attr_dict:
                attr_dict[group] = list(np.array([attr_dict[group], id]).flatten())
            else:
                attr_dict[group] = id

        return id_dict, attr_dict




class AttributeItem(SubRunItem):
    """Item for containing individual attributes. Access to these
       will be done through parent items.
    """

    # These are more intimately connected with their table and
    # we will only think of them by name (and potentially type)
    def __init__(self, name, parent=None):
        """Construct an AttributeItem."""
        super(AttributeItem, self).__init__(name, parent)

    def typeInfo(self):
        """Return ATTRIBUTE."""
        return "ATTRIBUTE"

    def buildAttributeSet(self, attributes = set()):
        """Returns a set containing this attribute's name. This is the
           base cause of a recursive building of an attribute list on
           any subtree.
        """
        attributes.add(self.name)
        return attributes


class DataTree(QAbstractItemModel):
    """Data, largely in the form of input tables and projections, is
       accessed through this datatree. It is organized as a tree
       with Runs as level 1, Groups as level 2, Tables/Projections at
       level 3 and Attributes at level 4.
    """

    def __init__(self, root = AbstractTreeItem("BoxFish")):
        """Construct the DataTree for Boxfish."""
        super(DataTree, self).__init__(None)
        self._rootItem = root


    def rowCount(self, parent):
        """Return the number of children under the root node, which
           are all the Runs.
        """
        if not parent.isValid():
            parentItem = self._rootItem
        else:
            parentItem = parent.internalPointer()

        return parentItem.childCount()

    def columnCount(self, parent):
        """This returns 1 because we display only one piece of information
           for each tree node, its name.
        """
        return 1

    def data(self, index, role = Qt.UserRole):
        """In the DisplayRole case, returns the node name. No other
           roles are handled.
        """
        if not index.isValid():
            return None

        item = index.internalPointer()

        if role == Qt.DisplayRole:
            if index.column() == 0:
                return item.name

        # Boxfish specific stuff may be done under UserRole (future)
        elif role == Qt.UserRole:
            pass


    def headerData(self, section, orientation, role):
        """Returns 'Data' in the DisplayRole case. No other behavior."""
        if role == Qt.DisplayRole:
            if section == 0:
                return "Data"


    def flags(self, index):
        """Returns the flags required by the display for each type
           of node in the DataTree.
        """
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

        if item.typeInfo() == "SUBDOMAIN":
            return Qt.ItemIsEnabled

        if item.typeInfo() == "GROUP":
            return Qt.ItemIsEnabled


    def parent(self, index):
        """Returns the QModelIndex of the parent of any given item."""
        item = self.getItem(index)
        parentItem = item.parent()

        if parentItem == self._rootItem:
            return QModelIndex()

        return self.createIndex(parentItem.row(), 0, parentItem)


    def index(self, row, column, parent):
        """Returns a QModelIndex representing the child of the given
           parent at the given row and column position.
        """
        parentItem = self.getItem(parent)
        childItem = parentItem.child(row)

        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QModelIndex()


    def getItem(self, index):
        """Returns the tree item at the given QModelIndex."""
        if index.isValid():
            item = index.internalPointer()
            if item:
                return item

        return self._rootItem

    def getRun(self, run):
        """Returns a RunItem with the given name."""
        for child in self._rootItem._children:
            if child.name == run:
                return child
        return None

    def generateAttributeList(self):
        """Returns a sorted list of all attribute names in the
           entire DataTree.
        """
        return sorted(self._rootItem.buildAttributeSet(set()))

    def getAttributeValues(self, attribute):
        """Returns a sorted list of all known values of the given
           attribute across all runs and tables in which it appears.
        """
        return sorted(self._rootItem.buildAttributeValues(attribute, set()))


    def insertProjection(self, name, projection, metadata, position=-1, \
        rows=1, parent=QModelIndex()):
        """Adds a ProjectionItem to the DataTree with the given name,
           metadata, and Projection object. The ProjectionItem is added
           under the given ParentItem.
        """
        parentItem = self.getItem(parent)
        if position == -1:
            position = parentItem.childCount()

        # Create projection
        self.beginInsertRows(parent, position, position + rows - 1)
        projectionItem = ProjectionItem(name, projection, metadata, \
            parentItem)
        self.endInsertRows()

        return True


    # Add a table and its attributes to the datatree.
    def insertTable(self, name, table, metadata, position=-1, rows=1, \
        parent=QModelIndex()):
        """Adds a TableItem to the DataTree with the given name, metadata,
           and Table object. Also creates the AttributeItems under the
           TableItem. The TableItem is added under the given ParentItem.
        """
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
                data_type = SubDomain.instantiate(type_string)
                if data_type is None:
                    print "No matching type found for", filedict['type'], \
                        "! Skipping table..."
                    continue

                filepath = os.path.join(os.path.dirname(filename),
                    filedict['filename'])
                metadata, data = yl.load_table(filepath)
                if metadata:
                    combined_meta = dict(metadata.items() + filedict.items())
                else:
                    combined_meta = filedict
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
                    data_type = SubDomain.instantiate(type_string)
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
                    if metadata:
                        combined_meta = dict(metadata.items() + filedict.items())
                    else:
                        combined_meta = filedict
                    atable = Table()
                    atable.fromRecArray(mydomains[0], mykeys[0], data)
                    aprojection = TableProjection(mydomains[0], mydomains[1],
                        source_key = mykeys[0], destination_key = mykeys[1],
                        table = atable)
                    self.insertProjection(mydomains[0].typename() + "<->"
                        + mydomains[1].typename(), aprojection, combined_meta,
                        parent = self.createIndex(position, 0, projectionsItem))
                else:
                    aprojection = Projection.instantiate(filedict['type'],
                        mydomains[0], mydomains[1], run = runItem, **filedict)
                    self.insertProjection(mydomains[0].typename() + "<->"
                        + mydomains[1].typename(), aprojection, filedict,
                        parent = self.createIndex(position, 0, projectionsItem))


        runItem.refreshSubdomains()
        self.createSubDomainTables(runItem, projectionsItem, tablesItem)
        return True

    def createSubDomainTables(self, run, projections, tables):
        """If there are SubDomains represented by the projections in the
           run but not in any tables in that run, this function will create
           a table containing just the IDs for each SubDomain. This is
           calculated by performing all possible projections into that
           unrepresented Subdomain and taking the union of the results.
        """
        # Determine which subdomains are not covered by tables
        uncovered_subdomains = set(run._projection_subdomains) \
            - set(run._table_subdomains)
        for subdomain in uncovered_subdomains:
            # Find projections that cover this subdomain 
            projection_list = list()
            for projection in projections._children:
                if (subdomain == projection._projection.source
                    or subdomain == projection._projection.destination):
                    projection_list.append(projection._projection)

            # Create a Table Meta Information
            greater_subdomain = SubDomain.instantiate(subdomain)
            table_meta = dict()
            table_meta['filetype'] = 'table'
            table_meta['domain'] = greater_subdomain.domain()
            table_meta['type'] = greater_subdomain.typename()
            table_meta['flags'] = 0
            table_meta['field'] = table_meta['type'] + "_id"
            # Find a list of IDs for this subdomain from those projections
            id_list = list()
            for projection in projection_list:

                if subdomain == projection.source:
                    ids = projection.source_ids()
                    if isinstance(projection, TableProjection):
                        # If there's a TableProjection, use that field name
                        # instead
                        table_meta['field'] = projection._source_key
                else: # destination
                    ids = projection.destination_ids()
                    if isinstance(projection, TableProjection):
                        table_meta['field'] = projection._destination_key

                if ids is not None:
                    id_list.extend(ids)

            id_list = list(set(id_list))

            # Create Table
            data = np.rec.fromrecords([(x,) for x in id_list])
            data.dtype.names = (table_meta['field'],)
            atable = Table()
            atable.fromRecArray(greater_subdomain, table_meta['field'], data)

            # Insert Table
            self.insertTable(subdomain, atable, table_meta, \
                parent = self.createIndex(tables.childCount(), 0, tables))

            # Update subdomain list
            run._table_subdomains.append(subdomain)


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
        """Returns a DataIndexMime containing the given indices."""
        return DataIndexMime(indices)


class DataIndexMime(QMimeData):
    """For passing around datatree indices using drag and drop.
    """

    def __init__(self, data_index):
        """Constructs a DataIndexMime containing the given indices."""
        super(DataIndexMime, self).__init__()

        self.data_index = data_index

    def getDataIndices(self):
        """Returns the list of QModelIndex contained in this object."""
        return self.data_index



if __name__ == '__main__':

    app = QApplication(sys.argv)

    datatree = DataTree()

    treeView = QTreeView()
    treeView.show()
    treeView.setModel(datatree)

    datatree.insertRun("dummy_meta.yaml")

    sys.exit(app.exec_())
