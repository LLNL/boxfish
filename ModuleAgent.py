from PySide.QtCore import Slot,Signal,QObject,QMimeData,Qt
from PySide.QtGui import QWidget,QMainWindow,QDockWidget,QToolBar,\
    QLabel,QDrag,QPixmap
from SubDomain import *
from Table import *
from Projection import *
from DataModel import *
from FilterCoupler import *
from SceneInfo import *

class ModuleAgent(QObject):

    # Signals that I send 
    addCouplerSignal         = Signal(FilterCoupler, QObject)

    # Scene Signals I send... really necessary with parent/child structure?
    sceneChangedSignal = Signal(Scene, object) # my scene info changed
    receiveModuleSceneSignal = Signal(ModuleScene) # we receive scene info
    receiveHighlightSignal   = Signal(HighlightScene)
    requestScenesSignal      = Signal(QObject)

    # INIT IS DOWN HERE
    def __init__(self, parent, datatree = None):
        super(ModuleAgent,self).__init__(parent)

        self.datatree = datatree
        self.attribute_scenes = dict()

        self.children = list()

        # List of filter streams (couplers) the agent wants
        self.requests = dict()

        # List of filter streams (couplers) the children want
        self.child_requests = list()

        self.filters = list()

        # Module Scene information - we keep track of several as different
        # modules may have different scenes that are all valid
        self.module_scenes_dict = dict() 
        self.apply_module_scenes = True
        self._propagate_module_scenes = False

        # Highlight Scene information - we keep track of one only as it would
        # be too confusing if there were highlights per domain in a subtree.
        # It wouldn't be clear what highlights belonged to what set, especially
        # with projections.
        self.apply_highlights = True
        self._propagate_highlights = False
        self._highlights = HighlightScene() # Local highlights
        
        # Reference highlights for subtree
        self._highlights_ref = HighlightScene()


    # factory method for subclasses
    @classmethod
    def instantiate(cls, module_name, parent):

        if cls.__name__ == module_name:
            return cls(parent)
        else:
            for s in cls.__subclasses__():
                result = s.instantiate(module_name, parent)
                if result is not None:
                    return result
            return None


    def addRequest(self, name, subdomain = None):
        coupler = FilterCoupler(name, self, None)
        self.requests[name] = ModuleRequest(self.datatree, name, coupler,
            subdomain)
        coupler.changeSignal.connect(self.requiredCouplerChanged)
        #Now send this new one to the parent
        self.addCouplerSignal.emit(coupler, self)

    def requestUpdated(self, name):
        pass

    @Slot(FilterCoupler)
    def requiredCouplerChanged(self, coupler):
        request = self.requests[coupler.name]
        self.requestUpdated(coupler.name)

    # TODO: Maybe instead of having next few functions we should
    # move the functionality out of ModuleRequest and over here,
    # leaving the request to just hold the coupler and the indices
    def requestAddIndices(self, name, indices):
        if name not in self.requests:
            raise ValueError("No request named " + name)
        self.requests[name].indices = indices

    def requestGroupBy(self, name, group_by_attributes, group_by_table,
        row_aggregator, attribute_aggregator):
        if name not in self.requests:
            raise ValueError("No request named " + name)
        return self.requests[name].groupby(group_by_attributes,
            group_by_table, row_aggregator, attribute_aggregator)

    def requestGetRows(self, name):
        if name not in self.requests:
            raise ValueError("No request named " + name)
        return self.requests[name].getRows()

    # Signal decorator attached after the class.
    # @Slot(FilterCoupler, ModuleAgent)
    def addChildCoupler(self, coupler, child):
        my_filter = None
        if self.filters:
            my_filter = self.filters[0]
        new_coupler = coupler.createUpstream(child, my_filter)
        self.child_requests.append(new_coupler)
        self.addCouplerSignal.emit(new_coupler, self)

    def getCouplerRequests(self):
        reqs = list()
        for request in self.requests.itervalues():
            reqs.append(request.coupler)
        reqs.extend(self.child_requests)
        return reqs

    # Remove coupler that has sent a delete signal
    @Slot(FilterCoupler)
    def deleteCoupler(self, coupler):
        if coupler in self.child_requests:
            self.child_requests.remove(coupler)
        else:
            for key, request in self.requests.iteritems():
                if coupler == request.coupler:
                    del self.requests[key]

    def registerChild(self, child):
        self.children.append(child)
        child.addCouplerSignal.connect(self.addChildCoupler)
        child.sceneChangedSignal.connect(self.receiveSceneFromChild)
        child.requestScenesSignal.connect(self.sendAllScenes)

        if self.propagate_module_scenes:
            child.propagate_module_scenes = True

        # "Adopt" child's requests
        for coupler in child.getCouplerRequests():
            my_filter = None
            if self.filters:
                my_filter = self.filters[0]
            new_coupler = coupler.createUpstream(child, my_filter)
            self.child_requests.append(new_coupler)
            self.addCouplerSignal.emit(new_coupler, self)

    def unregisterChild(self, child):
        self.children.remove(child)
        child.addCouplerSignal.disconnect(self.addChildCoupler)
        child.sceneChangedSignal.disconnect(self.receiveSceneFromChild)
        child.requestScenesSignal.disconnect(self.sendAllScenes)

        # Abandon child's requests
        for coupler in self.child_requests:
            if coupler.parent == child:
                coupler.delete()

    # Change the parent of the agent.
    def changeParent(self, new_parent):
        self.parent().unregisterChild(self)
        self.setParent(new_parent)
        if self.parent() is not None and \
            isinstance(self.parent(), ModuleAgent):
            self.parent().registerChild(self)

    def delete(self):
        for child in self.children:
            child.delete()
        self.parent().unregisterChild(self)

    # Slot(ModuleAgent) decorator after class definition
    def sendAllScenes(self, child):
        """Goes through stored scenes and sends all of them to requesting
           child as someone in the child's tree may be listening for them.
        """
        if self.propagate_module_scenes:
            for key, scene in self.module_scenes_dict.iteritems():
                child.receiveSceneFromParent(scene)
        if self.propagate_highlights:
            child.receiveSceneFromParent(self._highlights_ref)

    def refreshSceneInformation(self):
        """This function is called to poll the parent agent for any 
           SceneInformation it has of interest to this agent and its
           children. It may be used onCreation of a Module or when a
           subtree is moved in the hierarchy.
        """
        self.requestScenesSignal.emit(self)

    @property
    def highlights(self):
        return self._highlights

    @highlights.setter
    def highlights(self, highlight):
        self._highlights = highlight
        self._highlights.causeChangeSignal.connect(self.sceneChanged)

    @property
    def propagate_highlights(self):
        return self._propagate_highlights

    @propagate_highlights.setter
    def propagate_highlights(self, policy):
        # You can only turn off (policy is False) if your parent is
        # also False. 
        if policy or self.parent().propagate_highlights == policy:
            self._propagate_highlights = policy
        if policy: # Push policy on to all children
            for child in self.children:
                child.propagate_highlights = policy

    @Slot(HighlightScene)
    def highlightsChanged(self, highlight):
        self.highlightSceneChangedSignal.emit(self.highlights.copy(), self)

    @property
    def propagate_module_scenes(self):
        return self._propagate_module_scenes

    @propagate_module_scenes.setter
    def propagate_module_scenes(self, policy):
        # You can only turn off (policy is False) if your parent is
        # also False. 
        if policy or self.parent().propagate_module_scenes == policy:
            self._propagate_module_scenes = policy
        if policy: # Push policy on to all children
            for child in self.children:
                child.propagate_module_scenes = policy

    @property
    def module_scene(self):
        return self._module_scene

    @module_scene.setter
    def module_scene(self, module_scene):
        self._module_scene = module_scene
        self._module_scene.causeChangeSignal.connect(self.sceneChanged)

    @Slot(Scene)
    def sceneChanged(self, scene):
        self.sceneChangedSignal.emit(scene.copy(), self)

    # Slot(Scene, ModuleAgent) decorator after class definition
    def receiveSceneFromChild(self, scene, source_agent):
        if isinstance(scene, HighlightScene):
            if self.propagate_highlights:
                # Continue to propagate up
                self.sceneChangedSignal.emit(scene, self)
            else: # Not propagating, just give back to child
                source_agent.receiveSceneFromParent(scene)
        elif isinstance(scene, ModuleScene):
            if self.propagate_module_scenes:
                # Continue to propagate up
                self.sceneChangedSignal.emit(scene, self)
            else: # Not propagating, just give back to child
                source_agent.receiveSceneFromParent(scene)

    def receiveSceneFromParent(self, scene):
        # If this function is being called, we know we propagate things
        # so we send to all our children
        for child in self.children:
            child.receiveSceneFromParent(scene)

        if isinstance(scene, HighlightScene):
            self._highlights_ref = scene

            if self.apply_highlights:
                self.receiveHighlightSceneSignal.emit(scene)
        elif isinstance(scene, ModuleScene):
            # And we update our module scene dict
            self.module_scenes_dict[scene.module_name] = scene

            # Then we determine how we should handle it
            if self.apply_module_scenes \
                and isinstance(scene, type(self.module_scene)):
                self.receiveModuleSceneSignal.emit(scene)





# The slots need to be added down here because ModuleAgent is not defined
# at the time that the functions are defined
ModuleAgent.addChildCoupler = Slot(FilterCoupler, ModuleAgent)(ModuleAgent.addChildCoupler)
ModuleAgent.receiveSceneFromChild = Slot(Scene, ModuleAgent)(ModuleAgent.receiveSceneFromChild)
ModuleAgent.sendAllScenes = Slot(ModuleAgent)(ModuleAgent.sendAllScenes)




class ModuleRequest(QObject):
    """Holds all of the requested information including the
       desired attributes and the operation to perform on them.
       This is identified by the name member of the class.
       Please keep names unique within a single module.
    """
    operator = {
        'sum' : sum,
        'mean' : lambda x: sum(x) / float(len(x)),
        'max' : max,
        'min' : min,
    }

    def __init__(self, datatree, name, coupler, subdomain = None,
        indices = list()):
        super(ModuleRequest, self).__init__()

        self.datatree = datatree
        self.name = name
        self.coupler = coupler
        self.subdomain = subdomain
        self._indices = indices

        if self.subdomain:
            self.subdomain_scene = SubdomainScene(self.subdomain)
        else:
            self.subdomain_scene = None

        if self._indices is None:
            self.attribute_scene = AttributeScene(set())
        else:
            self.attribute_scene = AttributeScene(self.attributeNameSet())


    @property
    def indices(self):
        return self._indices

    @indices.setter
    def indices(self, indices):
        self._indices = indices
        if self._indices is None or len(self._indices) > 0:
            self.attribute_scene.attributes = set()
        else:
            self.attribute_scene.attributes = self.attributeNameSet()

    def attributeNameSet(self):
        attribute_set = set()
        for index in self._indices:
            attribute_set.add(self.datatree.getItem(index).name)
        return attribute_set

    def sortIndicesByTable(self, indexList):
        """Creates an iterator of passed indices grouped by
        the tableItem that they come from.
        """
        get_parent = lambda x: self.datatree.getItem(x).parent()
        sorted_indices = sorted(indexList, key = get_parent)
        attribute_groups = itertools.groupby(sorted_indices, key = get_parent)

        return attribute_groups


    def preprocess(self):
        """Verifies that this ModuleRequest can be fulfilled.
        """
        if self._indices is None or len(self._indices) <= 0:
            return False
        return True


    def groupby(self, group_by_attributes, group_by_table, row_aggregator,
        attribute_aggregator):
        """Gets results of the request, grouped by the given attributes
           and aggregated by the given aggregators.
           group_by_attributes - list of attribute names by which to group
           group_by_table - table from which those attributes come
           row_aggregator - how rows should be combined
           attribute_aggregator - how attributes (columns) should be
           combined.

           Note, if the groups have overlapping IDs associated with
           their table, then the values return will have double counting
           for those IDs in their groups.
        """
        if not self.preprocess():
            return None, None

        # Get mapping of group_by_attributes to their subdomain ID
        # THIS IS PAINFULLY SLOW

        # This is where we store intermediate values
        aggregate_values = dict()

        # The groups we need and their corresponding primary key so
        # we can project data onto them.
        groups, ids = group_by_table._table.group_attributes_by_attributes(
            group_by_table._table.identifiers(), group_by_attributes,
            [group_by_table._table._key], row_aggregator)

        self.attribute_groups = self.sortIndicesByTable(self._indices)
        for table, attribute_group in self.attribute_groups:
            # Determine if projection exists, if not, skip
            projection = group_by_table.getRun().getProjection(
                group_by_table._table.subdomain(),
                table._table.subdomain())
            if projection is None:
                continue

            # Apply filters
            identifiers = table._table.identifiers()
            for modifier in self.coupler.modifier_chain:
                identifiers = modifier.process(table, identifiers)

            # Determine the attributes
            attributes = [self.datatree.getItem(x).name
                for x in attribute_group]
            attributes.insert(0, table._table._key) # add key for projections

            # Get the attributes and ids for these identifiers
            attribute_values = table._table.attributes_by_identifiers(
                identifiers, attributes, False) # We don't want unique values

            if isinstance(projection, IdentityProjection):
                # Since the projection is Identity, we don't need to process it
                for row_values in zip(*attribute_values):
                    domain_id = row_values[0]
                    if domain_id in aggregate_values:
                        aggregate_values[domain_id].extend(row_values[1:])
                    else:
                        aggregate_values[domain_id] = list(row_values[1:])
            else: # Other type of projection
                # Find relevant projection per id
                projection_memo = dict() # store projections
                for table_id in set(attribute_values[0]): # unique ids
                    domain_ids = projection.project(
                        SubDomain.instantiate(table._table.subdomain(),
                            [table_id]),
                        group_by_table._table.subdomain())
                    projection_memo[table_id] = domain_ids

                # Collect attributes onto proper domain IDs
                for row_values in zip(*attribute_values):
                    domain_ids = projection_memo[row_values[0]]
                    for domain_id in domain_ids:
                        if domain_id in aggregate_values:
                            aggregate_values[domain_id].extend(row_values[1:])
                        else:
                            aggregate_values[domain_id] = list(row_values[1:])

        # Then get the IDs from the group by table that matter
        # and associate them with these attributes
        values = list()
        for domain_id in ids[0]:
            if int(domain_id) not in aggregate_values:
                values.append(0)
            else:
                values.append(self.operator[attribute_aggregator](
                    aggregate_values[int(domain_id)]))

        return groups, [values]


    def aggregateDomain(self, domain_table, row_aggregator,
        attribute_aggregator, domain_attributes = list(),
        domain_aggregator = "mean"):
        """Gets results of the request, aggregated by the domain of
           the domain table.

           Parameters:
           domain_table - domain table on which to process a request.
                          Requested indices will be projected onto this domain.

           row_aggregator - aggregation operator for combining rows on an ID

           attribute_aggregator - aggregation operator for combining
                                  attributes (columns) for each row

           domain_attributes - optional list of attributes from the
                               domain_table to fetch along with non-filtered
                               domain ID rows.

           domain_aggregator - aggregation operator for combining
                               rows with the same ID but potentially different
                               domain_attriute values.

           Returns:
           ids - list of ids from the domain_table
           values - list of lists that go with the ids. The first list is the
                    aggregated request. All additional lists are the
                    the requested domain_attributes
        """
        if not self.preprocess():
            return None, None

        # Get mapping of group_by_attributes to their subdomain ID
        # THIS IS PAINFULLY SLOW

        # This is where we store intermediate values
        aggregate_values = dict()

        if len(domain_attributes) > 0:
            get_domain_attributes = True
            domain_values = None

        self.attribute_groups = self.sortIndicesByTable(self._indices)

        for table, attribute_group in self.attribute_groups:
            # Determine if projection exists, if not, skip
            projection = domain_table.getRun().getProjection(
                domain_table._table.subdomain(),
                table._table.subdomain())
            if projection is None:
                continue

            # Apply filters
            identifiers = table._table.identifiers()
            for modifier in self.coupler.modifier_chain:
                identifiers = modifier.process(table, identifiers)

            # Determine the attributes
            attributes = [self.datatree.getItem(x).name
                for x in attribute_group]
            attributes.insert(0, table._table._key) # add key for projections

            # Get the attributes and ids for these identifiers
            attribute_values = table._table.attributes_by_identifiers(
                identifiers, attributes, False) # We don't want unique values

            # Since we've filtered this table already, might as well get
            # the domain attributes if we need them
            if table is domain_table and get_domain_attributes:
                domain_values = table._table.group_attributes_by_attributes(
                    identifiers, [table['field']], domain_attributes,
                    domain_aggregators)

            if isinstance(projection, IdentityProjection):
                # Since the projection is Identity, we don't need to process it
                for row_values in zip(*attribute_values):
                    domain_id = row_values[0]
                    if domain_id in aggregate_values:
                        aggregate_values[domain_id].extend(row_values[1:])
                    else:
                        aggregate_values[domain_id] = list(row_values[1:])
            else: # Other type of projection
                # Find relevant projection per id
                projection_memo = dict() # store projections
                for table_id in set(attribute_values[0]): # unique ids
                    domain_ids = projection.project(
                        SubDomain.instantiate(table._table.subdomain(),
                            [table_id]),
                        domain_table._table.subdomain())
                    projection_memo[table_id] = domain_ids

                # Collect attributes onto proper domain IDs
                for row_values in zip(*attribute_values):
                    domain_ids = projection_memo[row_values[0]]
                    for domain_id in domain_ids:
                        if domain_id in aggregate_values:
                            aggregate_values[domain_id].extend(row_values[1:])
                        else:
                            aggregate_values[domain_id] = list(row_values[1:])

        # Then get the IDs from the group by table that matter
        # and associate them with these attributes
        values = list()
        ids = list()
        for domain_id, agge_values in aggregate_values:
            ids.append(domain_id)
            values.append(self.operator[attribute_aggregator](
                aggregate_values[int(domain_id)]))

        return_values = list()
        return_values.append(values)

        # if we still haven't gotten the domain_attributes and we need them...
        if get_domain_attributes:
            if domain_values is None:
                # Apply filters
                identifiers = domain_table._table.identifiers()
                for modifier in self.coupler.modifier_chain:
                    identifiers = modifier.process(domain_table, identifiers)

                domain_values \
                    = domain_table._table.group_attributes_by_attributes(
                    identifiers, [domain_table['field']], domain_attributes,
                    domain_aggregators)

            return_values.appen(domain_values)


        return ids, return_values


    def getRows(self):
        """Gets all of the attributes from the request, grouped by
           the table from which they come from. There is no other grouping,
           this returns the raw rows which may have rows with duplicate
           IDs if IDs is one of the attributes

           This returns a list of tables and two lists of lists.
           The first is a list of lists of attribute names for each table.
           The second is a list of list of lists of the corresponding
           attribute values.
        """
        if not self.preprocess():
            return None, None, None, None

        self.attribute_groups = self.sortIndicesByTable(self._indices)
        data_list = list()
        headers = list()
        table_list = list()
        id_list = list()
        run_list = list()
        for table, attribute_group in self.attribute_groups:
            table_list.append(table.name)
            run_list.append(table.getRun().name)
            attributes = [self.datatree.getItem(x).name
                for x in attribute_group]
            headers.append(attributes[:])
            attributes.insert(0, table['field'])
            identifiers = table._table.identifiers()
            for modifier in self.coupler.modifier_chain:
                identifiers = modifier.process(table, identifiers)
            attribute_list = table._table.attributes_by_identifiers(
                identifiers, attributes, False)
            data_list.append(attribute_list[1:])
            id_list.append(attribute_list[0])

        return table_list, run_list, id_list, headers, data_list
