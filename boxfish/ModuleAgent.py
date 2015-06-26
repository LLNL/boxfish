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
    """ModuleAgent is the base class for all nodes that form the Boxfish
       data flow tree. This class handles wiring of parent and child agents
       to form the tree, scene information propagation, and data requests
       for itself and its children.
    """

    # Signals that I send 
    addCouplerSignal           = Signal(FilterCoupler, QObject)
    requestUpdatedSignal       = Signal(str)

    # Scene Signals I send... really necessary with parent/child structure?
    sceneChangedSignal         = Signal(Scene, object) # my scene info changed
    receiveModuleSceneSignal   = Signal(ModuleScene) # we receive scene info
    highlightSceneChangeSignal = Signal() # my highlight Scene changed
    attributeSceneUpdateSignal = Signal() # my attribute Scene updated
    requestScenesSignal        = Signal(QObject)

    def __init__(self, parent, datatree = None):
        """Constructor for ModuleAgent.

           parent
               The parent ModuleAgent in the Boxfish tree.

           datatree
               Reference to the model holding the data.
        """
        super(ModuleAgent,self).__init__(parent)

        self.datatree = datatree

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
        self.highlights = HighlightScene() # Local highlights
        self._highlights_ref = HighlightScene() # Ref highlights for subtree

        # Attribute Scene information - we need to keep track of all of these
        # possible combinations. Since there can be so many of these, we do
        # not keep all valid ones even when no one is using. Instead, every
        # time we have a change in attributes, we search the subtree that
        # matters and clear out the ones we are no longer using.
        self.attribute_scenes_dict = dict()
        self.apply_attribute_scenes = True
        self._propagate_attribute_scenes = False



    # factory method for subclasses
    @classmethod
    def instantiate(cls, module_name, parent):
        """Create a ModuleAgent object of type module_name with the
           given parent.
        """
        if cls.__name__ == module_name:
            return cls(parent)
        else:
            for s in cls.__subclasses__():
                result = s.instantiate(module_name, parent)
                if result is not None:
                    return result
            return None


    def addRequest(self, name, subdomain = None):
        """Add a request stream to be handled by this ModuleAgent."""
        coupler = FilterCoupler(name, self, None)
        self.requests[name] = ModuleRequest(self.datatree, name, coupler,
            subdomain)

        # Connect signals
        self.requests[name].indicesChangedSignal.connect(self.requestUpdatedSignal.emit)
        self.requests[name].attributesChangedSignal.connect(
            self.requestAttributesChanged)
        self.requests[name].attributeSceneChangedSignal.connect(
            self.sceneChanged)
        coupler.changeSignal.connect(self.requestedCouplerChanged)

        #Now send this new one to the parent
        self.addCouplerSignal.emit(coupler, self)


    @Slot(FilterCoupler)
    def requestedCouplerChanged(self, coupler):
        """Called whenever a FilterCoupler associated with a request
           signals an update. Finds the associated request and emits
           the requestUpdatedSignal.
        """
        request = self.requests[coupler.name]
        self.requestUpdatedSignal.emit(coupler.name)


    def requestScene(self, tag):
        """Returns the attribute scene from the request denoted by tag."""
        return self.requests[tag].scene

    def requestAddIndices(self, name, indices):
        """Associates the given DataTree indices with the named request."""
        if name not in self.requests:
            raise ValueError("No request named " + name)
        self.requests[name].indices = indices


    def requestOnDomain(self, name, domain_table, row_aggregator,
        attribute_aggregator):
        """Gets results of the request, aggregated by the domain of
           the domain table.

           name
               The tag of the request on which to perform this operation.

           domain_table
               Domain table on which to process a request. Requested indices
               will be projected onto this domain.

           row_aggregator
               Aggregation operator for combining rows on an ID

           attribute_aggregator
               Aggregation operator for combining attributes (columns) for
               each row if multiple indices have been added to this Request.

           Returns:
               ids
                  List of ids from the domain_table.

               values
                   List of lists that go with the ids. The first list is the
                   aggregated request. All additional lists are the
                   requested domain_attributes
        """
        if name not in self.requests:
            raise ValueError("No request named " + name)

        return self.requests[name].aggregateDomain(domain_table,
            row_aggregator, attribute_aggregator)


    def requestGetRows(self, name):
        """Gets all rows of all tables for the attributes associated with
           the indices of the named request. Returns the list of tables,
           runs, list of identifier lists for the rows returned for each
           table, list of header lists for each table, and a list of lists
           of values for each attribute requested for each table.

           If the request has no indices yet, all return values will be None.
        """
        if name not in self.requests:
            raise ValueError("No request named " + name)
        return self.requests[name].getRows()


    # Signal decorator attached after the class.
    # @Slot(FilterCoupler, ModuleAgent)
    def addChildCoupler(self, coupler, child):
        """Creates and adds a coupler to the set of those this module handles.
           Usually signaled into action by a child agent's request.
        """
        my_filter = None
        if self.filters:
            my_filter = self.filters[0]
        new_coupler = coupler.createUpstream(child, my_filter)
        self.child_requests.append(new_coupler)
        self.addCouplerSignal.emit(new_coupler, self)

    def getCouplerRequests(self):
        """Creates and returns a list of couplers that this module handles."""
        reqs = list()
        for request in self.requests.itervalues():
            reqs.append(request.coupler)
        reqs.extend(self.child_requests)
        return reqs

    @Slot(FilterCoupler)
    def deleteCoupler(self, coupler):
        """When signalled by a coupler, removes it from the set of those
           this agent handles.
        """
        if coupler in self.child_requests:
            self.child_requests.remove(coupler)
        else:
            for key, request in self.requests.iteritems():
                if coupler == request.coupler:
                    del self.requests[key]

    def registerChild(self, child):
        """Registers the given Agent as a chlid of this Agent."""
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
        """Unregisters the given Agent as a child of this Agent."""
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
        """Changes the parent of this Agent to a new Agent."""
        self.parent().unregisterChild(self)
        self.setParent(new_parent)
        if self.parent() is not None and \
            isinstance(self.parent(), ModuleAgent):
            self.parent().registerChild(self)

    def delete(self):
        """Deletes this Agent and all its children."""
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
        if self.propagate_attribute_scenes:
            for key, scene in self.attribute_scenes_dict.iteritems():
                child.receiveSceneFromParent(scene)

    def refreshSceneInformation(self):
        """This function is called to poll the parent agent for any
           SceneInformation it has of interest to this agent and its
           children. It may be used onCreation of a Module or when a
           subtree is moved in the hierarchy.
        """
        self.requestScenesSignal.emit(self)

    @property
    def highlights(self):
        """The HighlightScene representing what is highlighted/selected
           in this Agent.
        """
        return self._highlights

    @highlights.setter
    def highlights(self, highlight):
        self._highlights = highlight
        self._highlights.causeChangeSignal.connect(self.sceneChanged)

    @property
    def propagate_highlights(self):
        """True if this Agent propagates highlights/selections to its
           children.
        """
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
        """Signals that highlights have changed from this Boxfish subtree."""
        self.highlightSceneChangedSignal.emit(self.highlights.copy(), self)

    def getHighlightIDs(self, table, run):
        """Applies the module's HighlightScene to the given table's domain
           to determine the domain IDs that need to be highligted.

           If the table's domain is in the set of highlights, only those
           highlights will be considered. If the table's domain is not in
           the set of highlights, then EVERY domain in the set of highlights
           will be projected onto the table to find the set of IDs.

           Example: Suppose the module's highlights include both NODE and
           LINK domain IDs. If the given table is in the NODE domain, then
           only the NODE highlights will be applied. If the table is in
           the RANK domain, then both the NODE and LINK domain highlights
           will be projected to determine the list of highlighted RANK IDs.

           If multiple highlight lists in the HighlightScene have the same
           domain as the table, all will be applied.

           table
               TableItem or string name of a table in the DataTree.

           run
               RunItem or string name of the corresponding run in the DataTree


           Note, at this time, assumes identity projections between
           runs. This may change.
        """
        if not isinstance(run, RunItem):
            runItem = self.datatree.getRun(run)
            if runItem is None:
                return
        else:
            runItem = run

        if not isinstance(table, TableItem):
            tableItem = runItem.getTable(table)
            if tableItem is None:
                return
        else:
            tableItem = table

        tableDomain = tableItem._table.subdomain()
        highlights = SubDomain.instantiate(tableDomain)
        for hs in self._highlights.highlight_sets:
            if hs.highlights.subdomain() == tableDomain:
                highlights.extend(hs.highlights)

        if len(highlights) > 0: # We found a SubDomain match
            return highlights

        # Since there was no direct way, we need to find and apply projections
        for hs in self._highlights.highlight_sets:
            projection = runItem.getProjection(tableDomain,
                hs.highlights.subdomain())
            if projection is not None:
                highlights.extend(projection.project(hs.highlights, tableDomain))

        return highlights

    def setHighlights(self, tables, runs, ids):
        """Sets the highlight of this particular agent and announces the change.

           tables
               A list of table names or items for the highlights

           runs
               A list of run names or items for the highlights

           ids
               A list of lists of ids, one for each table, of the highlights.
        """
        highlight_sets = list()
        for table, run, ids in zip(tables, runs, ids):
            if isinstance(run, RunItem):
                runItem = run
            else:
                runItem = self.datatree.getRun(run)

            if isinstance(table, TableItem):
                tableItem = table
            else:
                tableItem = runItem.getTable(table)
            domain = tableItem._table.subdomain()

            highlight_sets.append(HighlightSet(
                SubDomain.instantiate(domain, ids),
                runItem))
        self._highlights.highlight_sets = highlight_sets
        self._highlights.announceChange()


    @property
    def propagate_module_scenes(self):
        """True if this Agent propagates all ModuleScene data to its
           children.
        """
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
        """The ModuleScene associated with this Agent."""
        return self._module_scene

    @module_scene.setter
    def module_scene(self, module_scene):
        self._module_scene = module_scene
        self._module_scene.causeChangeSignal.connect(self.sceneChanged)


    @property
    def propagate_attribute_scenes(self):
        """True if this Agent propagates attribute scenes to its
           children.
        """
        return self._propagate_attribute_scenes

    # TODO: Factor this for all scenes by putting these values into
    # a dict keyed by the type of policy
    @propagate_attribute_scenes.setter
    def propagate_attribute_scenes(self, policy):
        # You can only turn off (policy is False) if your parent is
        # also False. 
        if policy or self.parent().propagate_attribute_scenes == policy:
            self._propagate_attribute_scenes = policy
        if policy: # Push policy on to all children
            for child in self.children:
                child.propagate_attribute_scenes = policy

    @Slot(Scene, QObject)
    def requestAttributesChanged(self, scene, request):
        """When the attribute set of a request changes, it should merge with
           existing scene information. If no scene information is found, it
           should add itself to the scene dict for this hierarchy.
        """
        if scene.attributes in self.attribute_scenes_dict:
            if request.receiveAttributeScene(
                    self.attribute_scenes_dict[scene.attributes]):
                self.attributeSceneUpdateSignal.emit()
        else:
            self.sceneChanged(scene)

    # TODO: While this does recalculate the attribute ranges for the 
    # scene's new attributes, it must be retriggered for the attributes
    # that got replaced too...
    def unionRanges(self, attributes):
        """Finds the union of all ranges of AttributeScenes with the given
           attributes that exist in this subtree.
        """
        range_list = self.getRanges(attributes)

        min_range = range_list[0][0]
        max_range = range_list[0][1]
        for r in range_list:
            min_range = r[0] if r[0] < min_range else min_range
            max_range = r[1] if r[1] > max_range else max_range

        return (min_range, max_range)

    def getRanges(self, attributes):
        """Creates a list of all ranges of AttributeScenes with the given
           attributes that exist in this subtree.
        """
        range_list = list()

        for child in self.children:
            range_list.extend(child.getRanges(attributes))

        for request in self.requests.values():
            if request.scene.attributes == attributes:
                range_list.append(request.scene.local_max_range)

        return range_list

    def cleanAttributeScenes(self):
        """Remove all entries from the attribute scenes store that are no
           longer found in the subtree.
        """
        if not self.propagate_attribute_scenes:
            return

        attribute_sets = self.currentAttributes()
        self.pruneAttributeScenes(attribute_sets)


    def pruneAttributeScenes(self, valid_sets):
        """Remove all attribute scenes from the store that are not in valid_set
           from the entire subtree.
        """
        for child in self.children:
            child.pruneAttributeScenes(valid_sets)

        for attribute_set in self.attribute_scenes_dict:
            if attribute_set not in valid_sets:
                del self.attribute_scenes_dict[attribute_set]

    def currentAttributes(self):
        """Returns a list of all active attribute sets in this subtree."""
        attribute_sets = set()
        for child in self.children:
            attribute_sets = attribute_sets.union(child.currentAttributes())

        for request in self.requests.values():
            attribute_sets.add(request.scene.attributes)

    @Slot(Scene)
    def sceneChanged(self, scene):
        """Signals a Scene in this subtree has changed."""
        self.sceneChangedSignal.emit(scene.copy(), self)

    # Slot(Scene, ModuleAgent) decorator after class definition
    def receiveSceneFromChild(self, scene, source_agent):
        """Called when a child alerts that Scene information has changed.
           Based on the Scene type and propagation values for this Agent,
           either passes the change up or down.

           If the Agent propagates this type of Scene information, it sends
           the Scene to its parent. If not, the Agent will send the Scene
           back to the originating child which will start the process of
           applying the Scene downstream.
        """
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
        elif isinstance(scene, AttributeScene):
            if self.propagate_attribute_scenes:
                # Continue to propagate up
                self.sceneChangedSignal.emit(scene, self)
            else: # Not propagating up anymore
                # Since this is an attribute scene, we need to calculate the 
                # range of all such attribute scenes in the source_agent's
                # subtree. We cannot simply union this one and the existing one
                # because the existing one may have been based on what the one 
                # we received used to be.
                if scene.use_max_range:
                    range_union = source_agent.unionRanges(scene.attributes)
                    scene.total_range = range_union
                # If we're not using the max range, we just use 
                # the given total range in this scene. This is 
                # very magical.

                # Give back to child
                source_agent.receiveSceneFromParent(scene)

                # Now that that has finished, clean up attribute dictionary
                self.cleanAttributeScenes()

    def receiveSceneFromParent(self, scene):
        """When a Scene is received from the parent, the Agent propagates
           the Scene to all of its children and then, based on the Scene
           type and Agent policy, may signal itself to process the
           given Scene information as well.
        """
        # If this function is being called, we know we propagate things
        # so we send to all our children
        for child in self.children:
            child.receiveSceneFromParent(scene)

        if isinstance(scene, HighlightScene):
            self._highlights_ref = scene

            if self.apply_highlights:
                self._highlights.highlight_sets = scene.highlight_sets
                self.highlightSceneChangeSignal.emit()
        elif isinstance(scene, ModuleScene):
            # And we update our module scene dict
            self.module_scenes_dict[scene.module_name] = scene

            # Then we determine how we should handle it
            if self.apply_module_scenes \
                and isinstance(scene, type(self.module_scene)):
                self.receiveModuleSceneSignal.emit(scene)
        elif isinstance(scene, AttributeScene):
            # Add/update to scene dict
            self.attribute_scenes_dict[scene.attributes] = scene

            # Determine how to handle this
            if self.apply_attribute_scenes:
                changes = False
                for request in self.requests.values():
                    changes = request.receiveAttributeScene(scene) or changes
                if changes: # If any of these caused a change, alert the module
                    self.attributeSceneUpdateSignal.emit()



# The slots need to be added down here because ModuleAgent is not defined
# at the time that the functions are defined
ModuleAgent.addChildCoupler = Slot(FilterCoupler, ModuleAgent)(ModuleAgent.addChildCoupler)
ModuleAgent.receiveSceneFromChild = Slot(Scene, ModuleAgent)(ModuleAgent.receiveSceneFromChild)
ModuleAgent.sendAllScenes = Slot(ModuleAgent)(ModuleAgent.sendAllScenes)




class ModuleRequest(QObject):
    """Holds all of the requested information including the desired
       attributes and the operation to perform on them. This is identified
       by the name member of the class. Please keep names unique within a
       single module as they are used to differentiate requests.
    """
    operator = {
        'sum' : sum,
        'mean' : lambda x: sum(x) / float(len(x)),
        'max' : max,
        'min' : min,
    }

    indicesChangedSignal = Signal(str)
    attributesChangedSignal = Signal(frozenset, QObject)
    attributeSceneChangedSignal = Signal(AttributeScene)

    def __init__(self, datatree, name, coupler, subdomain = None,
        indices = list()):
        """Construct a ModuleRequest object with the given name, coupler,
           optional associated subdomain and DataTree indices. The
           ModuleRequest requires a reference to the DataTree.
        """
        super(ModuleRequest, self).__init__()

        self.datatree = datatree
        self.name = name
        self.coupler = coupler
        self.subdomain = subdomain
        self._indices = indices

        if self._indices is None:
            self.scene = AttributeScene(frozenset())
        else:
            self.scene = AttributeScene(self.attributeNameSet())
        self.scene.causeChangeSignal.connect(self.sceneChanged)

    @property
    def indices(self):
        """The DataTree indices associated with this ModuleRequest."""
        return self._indices

    @indices.setter
    def indices(self, indices):
        self._indices = indices
        if self._indices is None or len(self._indices) == 0:
            self.scene.attributes = set()
        else:
            new_set = self.attributeNameSet()
            if self.scene.attributes != new_set:
                self.scene.attributes = new_set
                self.attributesChangedSignal.emit(self.scene, self)
        self.indicesChangedSignal.emit(self.name)

    def attributeNameSet(self):
        """Returns a set of all attribute names represented by this
           object's list of DataTree indices.
        """
        attribute_set = set()
        for index in self._indices:
            attribute_set.add(self.datatree.getItem(index).name)
        return frozenset(attribute_set)

    def receiveAttributeScene(self, scene):
        """Process received scene. If the received scene has the same set
           of attributes and is different than the existing one, the
           ModuleRequest's scene will make changes and return True. Otherwise,
           this function returns False.
        """
        if self.scene.attributes != scene.attributes: # Does not apply
            return False

        if self.scene == scene: # No change
            return False


        self.scene.merge(scene)
        # Don't do copy like other Scenes, we want to save local 
        # information. 
        #self.scene.causeChangeSignal.disconnect(self.sceneChanged)
        #self.scene = scene.copy()
        #self.scene.causeChangeSignal.connect(self.sceneChanged)

        if self.scene.attributes == frozenset([]):
            # We've accepted the scene info but since we don't have any
            # attributes, we don't trigger a re-draw
            return False

        return True

    @Slot(Scene)
    def sceneChanged(self, scene):
        """Propagate signal that this request's attribute scene has changed."""
        self.attributeSceneChangedSignal.emit(scene)

    def sortIndicesByTable(self, indexList):
        """Creates an iterator of passed indices grouped by the tableItems
           that they come from.
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

    def aggregateDomain(self, domain_table, row_aggregator,
        attribute_aggregator):
        """Gets results of the request, aggregated by the domain of
           the domain table.

           domain_table
               Domain table on which to process a request. Requested indices
               will be projected onto this domain.

           row_aggregator
               Aggregation operator for combining rows on an ID

           attribute_aggregator
               Aggregation operator for combining attributes (columns) for
               each row if multiple indices have been added to this Request.

           Returns:
               ids
                  List of ids from the domain_table.

               values
                   List of values that go with the ids.
        """
        if not self.preprocess():
            return  list(), list()

        # Get mapping of group_by_attributes to their subdomain ID
        # THIS IS PAINFULLY SLOW

        # This is where we store intermediate values
        aggregate_values = dict()

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

            if isinstance(projection, IdentityProjection):
                # Since the projection is Identity, we don't need to process it
                for row_values in zip(*attribute_values):
                    domain_id = row_values[0]
                    if domain_id in aggregate_values:
                        aggregate_values[domain_id].extend(row_values[1:])
                    else:
                        aggregate_values[domain_id] = list(row_values[1:])
            else: # Other type of projection
                # Find relevant projection per id. Each id may appear in 
                # in multiple rows, so we build this on the unique set of
                # ids to minimize calculated projections. Then we use 
                # the built dict to put the rest of the row values in 
                # the proper place
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
        for domain_id, agge_values in aggregate_values.iteritems():
            ids.append(domain_id)
            values.append(self.operator[attribute_aggregator](agge_values))

        return ids, values


    def getRows(self):
        """Gets all of the attributes from the request, grouped by
           the table from which they come from. There is no other grouping,
           this returns the raw rows which may have rows with duplicate
           IDs if IDs is one of the attributes

           This returns five lists:

           table_list
               A list of names of all tables represented by the indicies
               associated with this ModuleRequest

           run_list
               A list of the names of the runs associated with the tables

           id_list
               A list of lists, one per table, of the identifiers associated
               with each returned row.

           headers
               A list of lists, one per table, of the headers (attribute
               names) of all the columns requested from the table.

           data_list
               A list of lists, one per table. Each table's list contains
               a list for each attribute in headers that contains the
               values (rows data) for those attributes.

        """
        if not self.preprocess():
            return None, None, None, None, None # Ewww, FIXME

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

    def generalizedGroupBy(self, desired_indices, desired_operator,
        group_operator):
        """Groups some function of desired_indices by some function of
           the Request's indices.

           desired_indices
               An indexList

           desired_operator
               Function with which to aggregate the desired_attributes

           grouped_operator
               Function with which to aggregate the group by (our) indices


            The returned ids refer to the domain of the first attribute in
            this Request's indices.

            Returns domain, ids, grouped_values, desired_values
        """
        # CAUTION: Note that this is aggregating by IDs. That means if there
        # are multiple rows per ID in one table that is being used, it
        # could be that the desired value that is matched up with some of
        # the group values isn't what you would think logically. For
        # example, suppose there is just one table with columns id, A, B, C:
        # id A B C
        #  0 1 1 0
        #  0 2 2 1
        #  1 3 3 0
        #  1 4 4 1
        # If we have group value B and desired value A, the points we would
        # get would be:
        # group desired
        #     1       1
        #     1       2
        #     2       1
        #     2       2
        #     3       3
        #     3       4
        #     4       3
        #     4       4
        # This is because there is a projection going through the id field.
        # In the future, when we have a buffer query language, we may be
        # able to yield:
        # group desired
        #     1       1
        #     2       2
        #     3       3
        #     4       4

        # APPROACH
        # First we need to find all possible combinations of the group by
        # indices. We take the first table given as the primary domain that
        # we will group with. We then project all other tables onto that
        # table. Then we have all possible values associated with IDs.
        # Then we form Cartesian products of the attributes where each 
        # product shares the same associated id. Finally we apply the
        # grouped_operator to each of these to form the group-by groups.

        # group by aggregator dict
        group_dict, group_table = self.projectToFirstTable(self._indices)

        # Next we repeat the process for the desired_indices
        desired_dict, desired_table = self.projectToFirstTable(desired_indices)

        # Now we do the Cartesian product on each group_dict[domain_id]
        # At this point, group_dict[domain_id] is a dict table->row_values
        # By the end of this operation, each domain_id should be associated
        # with a list of products. Each product is a list of lists of 
        # row_values, one for each table.
        group_cart = self.cartesianCompress(group_dict, group_operator)
        desired_cart = self.cartesianCompress(desired_dict, desired_operator)

        # Then we project the desired_indices domain ids onto the 
        # group_indices domain_ids.
        projection = group_table.getRun().getProjection(
            group_table._table.subdomain(), desired_table._table.subdomain())
        if projection is None:
            raise ValueError("Cannont combine grouped values, no projection"
                + " between " + str(group_table.name) + " and "
                + str(desired_table.name))

        import itertools
        ids = list()
        group_values = list()
        desired_values = list()
        if isinstance(projection, IdentityProjection):
            for desired_id, d_values in desired_cart.items():
                g_values = group_cart[desired_id]
                cart_product = itertools.product(d_values, g_values)
                for d, g in cart_product:
                    ids.append(desired_id)
                    desired_values.append(d)
                    group_values.append(g)
        else:
            for desired_id, d_values in desired_cart.items():
                group_ids = projection.project(
                    SubDomain.instantiate(desired_table._table.subdomain(),
                        [desired_id]),
                    group_table._table.subdomain())
                for group_id in group_ids:
                    if group_id in group_cart:
                        g_values = group_cart[group_id]
                        cart_product = itertools.product(d_values, g_values)
                        for d, g in cart_product:
                            ids.append(group_id)
                            desired_values.append(d)
                            group_values.append(g)

        return group_table, ids, group_values, desired_values


    def cartesianCompress(self, cart_dict, operator):
        """Takes a dict of the type returned from projectToFirstTable and
           compresses it to:

               first_table_id -> list of values

           where each value in the list of values represents the operator
           applied to a product from the Cartesian product of the lists
           in the cart_dict.

           Example: cart_dict[0][t1] = [[0, 1], [2, 3]]
                    cart_dict[0][t2] = [[1, 1, 1], [2, 2, 2]]

                    return_dict[0] = unique[ operator([0, 1], [1, 1, 1]),
                                             operator([0, 1], [2, 2, 2]),
                                             operator([2, 3], [1, 1, 1]),
                                             operator([2, 3], [2, 2, 2]) ]
        """

        return_dict = dict()

        import itertools
        for key in cart_dict: # id
            values = list() # Aggregated values
            tables = list()  # Participating Tables
            counts = list()  # How many rows saved for each table
            for table in cart_dict[key]:
                #table_list.append(cart_dict[key][table])
                tables.append(table)
                counts.append(range(len(cart_dict[key][table])))

            #value_tuples = itertools.product(*table_list)
            indices = itertools.product(*counts)
            for index_set in indices:
                vals_to_combine = list()
                for i, index in enumerate(list(index_set)):
                    vals_to_combine.extend(cart_dict[key][tables[i]][index])

                values.append(self.operator[operator](vals_to_combine))

            return_dict[key] = list(set(values))

        return return_dict


    def projectToFirstTable(self, indices):
        """Gets the data from a set of indicies and and projects that
           data onto the ids of the first table represented in those
           indices.

           This is returned as a dict of dict of lists of lists:
               first_table_id -> dict_of_all_tables -> list of lists of
                                                       returned row values

           Also returns the first_table corresponding to the first_table_ids
        """
        # Break our indices into Tables
        attribute_groups = self.sortIndicesByTable(indices)

        domain_table = None
        group_dict = dict()
        for table, attribute_group in attribute_groups:
            if domain_table is None: # First table is our domain table
                domain_table = table
            else:
                # Determine if projection exists, if not, error
                projection = domain_table.getRun().getProjection(
                    domain_table._table.subdomain(),
                    table._table.subdomain())
                if projection is None:
                    raise ValueError("Cannot combine grouped values, no"
                        + " projection between " + str(domain_table.name)
                        + " and " + str(table.name))

            # Get attributes, starting with ID of interest
            attributes = [self.datatree.getItem(x).name
                for x in attribute_group]
            attributes.insert(0, table['field'])

            # Apply filters
            identifiers = table._table.identifiers()
            for modifier in self.coupler.modifier_chain:
                identifiers = modifier.process(table, identifiers)

            # Get values
            attribute_values = table._table.attributes_by_identifiers(
                identifiers, attributes, False)

            # Add these values to the dict
            # In the first table we add indiscriminately
            if domain_table == table:
                for row_values in zip(*attribute_values):
                    domain_id = row_values[0]
                    if domain_id in group_dict:
                        if table not in group_dict[domain_id]:
                            group_dict[domain_id][table] = list()
                        group_dict[domain_id][table].append(row_values[1:])
                    else:
                        group_dict[domain_id] = dict()
                        group_dict[domain_id][table] = list()
                        group_dict[domain_id][table].append(row_values[1:])
            # In the second table, we add only if the ID already exists
            # and we delete any ID that is unmarked at the end of it.
            # The reason is because we are crossing the IDs in all tables
            # and if one Table does not map, that entire ID is going to
            # cross to no values
            else:
                current_ids = group_dict.keys()
                if isinstance(projection, IdentityProjection):
                    # Since projection is identity, we can skip doing it
                    for row_values in zip(*attribute_values):
                        domain_id = row_values[0]
                        if domain_id in group_dict:
                            # Only add that which has an id already
                            current_ids.remove(domain_id)
                            if table not in group_dict[domain_id]:
                                group_dict[domain_id][table] = list()
                            group_dict[domain_id][table].append(row_values[1:])
                    for domain_id in current_ids:
                        # Delete the ones that didn't appear in this table
                        del group_dict[domain_id]
                else: # Other type of projection (ugh)
                    # Find relevant projection per id. Each id may appear in 
                    # in multiple rows, so we build this on the unique set of
                    # ids to minimize calculated projections. Then we use 
                    # the built dict to put the rest of the row values in 
                    # the proper place
                    projection_memo = dict() # store projections
                    for table_id in set(*attribute_values[0]):
                        domain_ids = projection.project(
                            Subdomain.instantiate(table._table.subdomain(),
                                [table_id]), domain_table._table.subdomain())
                        projection_memo[table_id] = domain_ids

                    for row_values in zip(*attribute_values):
                        domain_ids = projection_memo[row_values[0]]
                        for domain_id in domain_ids:
                            if domain_id in group_dict:
                                current_ids.remove(domain_id)
                                if table not in group_dict[domain_id]:
                                    group_dict[domain_id][table] = list()
                                group_dict[domain_id][table].append(
                                    row_values[1:])

                    for domain_id in current_ids:
                        # Delete the ones that didn't appear in this table
                        del group_dict[domain_id]

        return group_dict, domain_table
