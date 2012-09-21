from PySide.QtCore import Slot,Signal,QObject,QMimeData,Qt
from PySide.QtGui import QWidget,QMainWindow,QDockWidget,QToolBar,\
    QLabel,QDrag,QPixmap
import numpy as np
from SubDomain import *
from Table import *
#from Query import *
from Projection import *
from DataModel import *
from FilterCoupler import *
import ColorMaps
from SceneInfo import *

class ModuleAgent(QObject):

    # Timo - probably getting rid of these. While it makes sense for Subdomain
    # based Scene info, there are way too many attribute-based scene infos
    # and I don't want to needlessly create signals for all of them
    # Because we probably won't have too many children at any level, we
    # might as well just go through all of them and determine who needs
    # to be notified.
    subscribeSignal          = Signal(object,str)
    unsubscribeSignal        = Signal(object,str)
    highlightSignal          = Signal(SubDomain)

    # Signals that I send 
    addCouplerSignal         = Signal(FilterCoupler, QObject)

    # Scene Signals I send... really necessary with parent/child structure?
    moduleSceneChangedSignal = Signal(ModuleScene, object) # my scene info changed
    receiveModuleSceneSignal = Signal(ModuleScene) # we receive scene info
    requestScenesSignal      = Signal(QObject)

    # Name template for the highlight signal
    highlightSignal_base = "%s_highlight_signal"

    # The list of registered signals for highlights and yes the exec stuff is
    # necessary since PySide seems to mangle the signal otherwise. It is not
    # allowed to create the signals in the __init__ function nor can we create
    # a list of signale or a dict(). Either code runs but the resulting signals
    # are castrated (they have no connect function for example). Thus we use
    # this hack to create a bunch of named static variables
    for name in SubDomain().subclasses():
        exec highlightSignal_base % name + ' = Signal(SubDomain)'

    # INIT IS DOWN HERE
    def __init__(self, parent, datatree = None):
        super(ModuleAgent,self).__init__(parent)

        self.datatree = datatree
        self.listenerCount = dict()
        self.highlights = dict() # domain based information
        self.domain_scenes = dict()
        self.attribute_scenes = dict()
        for name in SubDomain().subclasses():
            self.listenerCount[name] = 0
            exec 'self.highlights[\"%s\"] = self.' % name \
                + self.highlightSignal_base % name

        self.children = list()

        # List of filter streams (couplers) the agent wants
        self.requirements = dict()

        # List of filter streams (couplers) the children want
        self.child_requirements = list()

        self.filters = list()

        # Module Scene information
        self.module_scenes_dict = dict()
        self.apply_module_scenes = True
        self._propagate_module_scenes = False


    # factory method for subclasses
    def instantiate(self, module_name, parent):

        if self.__class__.__name__ == module_name:
            return self.__class__(parent)
        else:
            for s in self.__class__.__subclasses__():
                result = s().instantiate(module_name, parent)
                if result is not None:
                    return result
            return None


    def addRequirement(self, name, subdomain = None):
        coupler = FilterCoupler(name, self, None)
        self.requirements[name] = ModuleRequest(self.datatree, name, coupler,
            subdomain)
        coupler.changeSignal.connect(self.requiredCouplerChanged)
        #Now send this new one to the parent
        self.addCouplerSignal.emit(coupler, self)

    def requestUpdated(self, name):
        pass

    @Slot(FilterCoupler)
    def requiredCouplerChanged(self, coupler):
        request = self.requirements[coupler.name]
        self.requestUpdated(coupler.name)

    # TODO: Maybe instead of having next few functions we should
    # move the functionality out of ModuleRequest and over here,
    # leaving the request to just hold the coupler and the indices
    def requestAddIndices(self, name, indices):
        if name not in self.requirements:
            raise ValueError("No requirement named " + name)
        self.requirements[name].indices = indices

    def requestGroupBy(self, name, group_by_attributes, group_by_table,
        row_aggregator, attribute_aggregator):
        if name not in self.requirements:
            raise ValueError("No requirement named " + name)
        return self.requirements[name].groupby(group_by_attributes,
            group_by_table, row_aggregator, attribute_aggregator)

    def requestGetRows(self, name):
        if name not in self.requirements:
            raise ValueError("No requirement named " + name)
        return self.requirements[name].getRows()

    # Signal decorator attached after the class.
    # @Slot(FilterCoupler, ModuleAgent)
    def addChildCoupler(self, coupler, child):
        my_filter = None
        if self.filters:
            my_filter = self.filters[0]
        new_coupler = coupler.createUpstream(child, my_filter)
        self.child_requirements.append(new_coupler)
        self.addCouplerSignal.emit(new_coupler, self)

    def getCouplerRequests(self):
        reqs = list()
        for request in self.requirements.itervalues():
            reqs.append(request.coupler)
        reqs.extend(self.child_requirements)
        return reqs

    # Remove coupler that has sent a delete signal
    @Slot(FilterCoupler)
    def deleteCoupler(self, coupler):
        if coupler in self.child_requirements:
            self.child_requirements.remove(coupler)
        else:
            for key, request in self.requirements.iteritems():
                if coupler == request.coupler:
                    del self.requirements[key]

    def registerChild(self, child):
        self.children.append(child)
        child.subscribeSignal.connect(self.subscribe)
        child.unsubscribeSignal.connect(self.unsubscribe)
        child.highlightSignal.connect(self.highlight)
        child.addCouplerSignal.connect(self.addChildCoupler)
        child.moduleSceneChangedSignal.connect(self.receiveModuleSceneFromChild)
        child.requestScenesSignal.connect(self.sendAllScenes)

        if self.propagate_module_scenes:
            child.propagate_module_scenes = True

        # "Adopt" child's requests
        for coupler in child.getCouplerRequests():
            my_filter = None
            if self.filters:
                my_filter = self.filters[0]
            new_coupler = coupler.createUpstream(child, my_filter)
            self.child_requirements.append(new_coupler)
            self.addCouplerSignal.emit(new_coupler, self)

    def unregisterChild(self, child):
        self.children.remove(child)
        child.subscribeSignal.disconnect(self.subscribe)
        child.unsubscribeSignal.disconnect(self.unsubscribe)
        child.highlightSignal.disconnect(self.highlight)
        child.addCouplerSignal.disconnect(self.addChildCoupler)
        child.moduleSceneChangedSignal.disconnect(
            self.receiveModuleSceneFromChild)
        child.requestScenesSignal.disconnect(self.sendAllScenes)

        # Abandon child's requests
        for coupler in self.child_requirements:
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
                child.receiveModuleSceneFromParent(scene)

    def refreshSceneInformation(self):
        """This function is called to poll the parent agent for any 
           SceneInformation it has of interest to this agent and its
           children. It may be used onCreation of a Module or when a
           subtree is moved in the hierarchy.
        """
        self.requestScenesSignal.emit(self)

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
        self._module_scene.causeChangeSignal.connect(self.moduleSceneChanged)

    @Slot(ModuleScene)
    def moduleSceneChanged(self, module_scene):
        self.moduleSceneChangedSignal.emit(self.module_scene.copy(), self)

    # Slot(ModuleScene, ModuleAgent) decorator after class definition
    def receiveModuleSceneFromChild(self, module_scene, source_agent):
        if self.propagate_module_scenes: 
            # Continue to propagate up
            self.moduleSceneChangedSignal.emit(module_scene, self)
        else: # Not propagating, just give back to child
            source_agent.receiveModuleSceneFromParent(module_scene)

    def receiveModuleSceneFromParent(self, module_scene):
        # If this function is being called, we know we propagate things
        # so we send to all our children
        for child in self.children:
            child.receiveModuleSceneFromParent(module_scene)

        # And we update our module scene dict
        self.module_scenes_dict[module_scene.module_name] = module_scene

        # Then we determine how we should handle it
        if self.apply_module_scenes \
            and isinstance(module_scene, type(self.module_scene)):
            self.receiveModuleSceneSignal.emit(module_scene)



    # EVERYTHING UNDER HERE (in this class) NOT CURRENTLY IN USE, LEFTOVER FROM
    # ORIGINAL QT BOXFISH, TO BE CONVERTED WHEN WE ADD HIGHLIGHTS

    # REWRITEME to apply child policy and use projections through the
    # data datatree as well as handle other Scenegraph changes
    @Slot(SubDomain)
    def highlight(self,subdomain):
        """This slot is called whenever a child agent changes
           subdomain-dependent scene information. The agent cycles through
           all subscribed listeners. Those of the same subdomain will
           get all of the scene info. For those of different domains, we
           check the highlight set to see if we can project.
        """

        # For all possible listeners
        for key in self.listenerCount:

            # If somebody issubscribed to this somain
            if self.listenerCount[key] > 0:

                # If this somebody is listening for exactly this signal
                if key == subdomain.subdomain():
                    # We pass the message on
                    self.highlights[key].emit(subdomain)

                # Otherwise, if our context can project the highlight into the
                # correct subdomain
                #elif self.context.relates(subdomain,key):
                #    self.highlights[key].emit(self.context.project(subdomain,key))


    # Slot must be added after class definition
    #@Slot(ModuleAgent,str)
    def subscribe(self,agent,name):

        # If we are the first one subscribing to this subdomain
        if name not in self.listenerCount:
            raise ValueError("Could not find subdomain %s." \
                + "Must be a subclass of SubDomain" % name)

        self.listenerCount[name] = self.listenerCount[name] + 1

        self.connectSubscription(agent,name)


    # Slot must be added after class definition
    #@Slot(ModuleAgent,str)
    def unsubscribe(self,agent,name):

        # If we are the first one subscribing to this subdomain
        if name not in self.listenerCount:
            raise ValueError("Could not find subdomain %s." \
                + "Must be a subclass of SubDomain" % name)

        if self.listenerCount[name] == 0:
            raise ValueError("No listener left to unsubscribe")

        self.listenerCount[name] = self.listenerCount[name] - 1

        self.disconnectSubscription(agent,name)

    def connectSubscription(self,agent,name):

        self.highlights[name].connect(agent.highlightChanged)


    def disconnectSubscription(self,agent,name):

        self.highlights[name].disconnect(agent.highlightChanged)

    @Slot(SubDomain)
    def highlightChanged(self,subdomain):
        print "Highlight", subdomain.subdomain()


# The slots need to be added down here because ModuleAgent is not defined
# at the time that the functions are defined
ModuleAgent.subscribe = Slot(ModuleAgent, str)(ModuleAgent.subscribe)
ModuleAgent.unsubscribe = Slot(ModuleAgent, str)(ModuleAgent.unsubscribe)
ModuleAgent.addChildCoupler = Slot(FilterCoupler, ModuleAgent)(ModuleAgent.addChildCoupler)
ModuleAgent.receiveModuleSceneFromChild = Slot(ModuleScene, ModuleAgent)(ModuleAgent.receiveModuleSceneFromChild)
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
                        SubDomain().instantiate(table._table.subdomain(),
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
            return None, None, None

        self.attribute_groups = self.sortIndicesByTable(self._indices)
        data_list = list()
        headers = list()
        table_list = list()
        for table, attribute_group in self.attribute_groups:
            table_list.append(table.name)
            attributes = [self.datatree.getItem(x).name
                for x in attribute_group]
            headers.append(attributes)
            identifiers = table._table.identifiers()
            for modifier in self.coupler.modifier_chain:
                identifiers = modifier.process(table, identifiers)
            attribute_list = table._table.attributes_by_identifiers(
                identifiers, attributes, False)
            data_list.append(attribute_list)

        return table_list, headers, data_list


# -------------------------- VIEW -------------------------------------

def Module(display_name, agent_type, scene_type = ModuleScene,
    enabled = True):
    """Module decorator :
       display_name - name of agent the user will see
       agent_type - type of the agent that goes with this module
       scene_type - type of the module scene info that goes with this module
       enabled - true if the user can created one
    """
    def module_inner(cls):
        cls.display_name = display_name
        cls.agent_type = agent_type
        cls.scene_type = scene_type
        cls.enabled = enabled
        return cls
    return module_inner

# All ModuleWindows must be decorated with their display name and
# optionally a bool indicating they are not for user creation.
@Module("Module Window", ModuleScene, enabled = False)
class ModuleView(QMainWindow):
    """This is the parent of what we will think of as a
       agent/extension/plug-in. It has the interface to create the single
       ModuleAgent it represents as well as the GUI elements to handle its
       specific actions. Both need to be written by the inheriting object.

       This class handles the reparenting and docking elements of all such
       modules.
    """

    def __init__(self, parent = None, parent_view = None, title = None):
        super(ModuleView, self).__init__(parent)

        self.title = title
        self.parent_view = parent_view
        self.agent = None

        # Only realize if we have a parent and a parent view
        if self.parent_view is not None and self.parent() is not None:
            self.realize()

        self.acceptDocks = False # Set to True to have child windows
        self.dragOverlay = False # For having a drag overlay window
        self.overlay_dialog = None

        self.setAcceptDrops(True)
        self.setWindowFlags(Qt.Widget) # Or else it will try to be a window

        # Makes color bar flush with top
        left, top, right, bottom = self.layout().getContentsMargins()
        self.layout().setContentsMargins(0, 0, right, bottom)

        # If we have a parent, set the height hint to be tall
        self.heightHint = self.size().height()
        if self.parent_view is not None:
            self.heightHint = self.parent_view.height() - 100

        self.setSizePolicy(QSizePolicy(QSizePolicy.Preferred, \
            QSizePolicy.Preferred))

        # Yellow Boxfishy border
        self.setStyleSheet("QMainWindow::separator { background:"\
            + "rgb(240, 240, 120); width: 2px; height: 2px; }")


    # This sets up the plug-in by generating the agent and registering
    # it to the parent and by placing the view elements in the overall
    # layout
    def realize(self):
        self.agent = self.agent_type(self.parent_view.agent,
            self.parent_view.agent.datatree)
        self.agent.module_scene = self.scene_type(self.agent_type,
            self.display_name)
        self.parent_view.agent.registerChild(self.agent)

        self.view = self.createView()
        self.centralWidget = QWidget()

        layout = QGridLayout()
        if isinstance(self.parent(), BFDockWidget):
            layout.addWidget(DragDockLabel(self.parent(), 0),0, 0, 1, 2)

        # TODO: Replace magic number with not-magic constant
        layout.addWidget(self.view, 100, 0, 1, 2) # Add view at bottom
        layout.setRowStretch(100, 5) # view has most row stretch

        left, top, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(0, 0, 0, 0)
        self.centralWidget.setLayout(layout)

        self.setCentralWidget(self.centralWidget)

        # Tab Dialog stuff
        self.enable_tab_dialog = True
        self.dialog = list()

    
    # Must be implemented by inheritors
    def createView(self):
        raise NotImplementedError("Realize not implemented,"\
            + " cannot create view")

    # factory method for creating subclasses based on their display_name
    def instantiate(self, module_name, parent, parent_view, title = None):

        if self.__class__.display_name == module_name:
            return self.__class__(parent, parent_view, title)
        else:
            for s in self.__class__.__subclasses__():
                result = s(None).instantiate(module_name, parent, parent_view,\
                    title)
                if result is not None:
                    return result
            return None

    # Get the list of subclasses
    def subclassList(self, scList = None):
        if scList is None:
            scList = list()
        if self.enabled:
            scList.append(self.display_name)
        for s in self.__class__.__subclasses__():
            scList.extend(s(None).subclassList())
        return scList


    # For sizing the doc window appropriately with respect to its parent
    def sizeHint(self):
        return QSize(200, self.heightHint)
        #return QSize(self.size().width(), self.heightHint)

    def findPosition(self):
        if isinstance(self.parent(), BFDockWidget):
            # parent is a dockwidget, so coords are relative
            x, y = self.parent().findPosition()
            return x + self.x(), y + self.y()
        else: # parent_view is boxfish main, get absolute coords
            return self.parent_view.geometry().x() + self.x(),\
                self.parent_view.geometry().y() + self.y()

    # Determine if this window is allowed to have child windows
    def allowDocks(self, dockable):
        self.acceptDocks = dockable

    def createDragOverlay(self, tags, texts, images = None):
        self.dragOverlay = True

        self.overlay = OverlayFrame(self)

        layout = QGridLayout(self.overlay)
        layout.setAlignment(Qt.AlignCenter)
        layout.setColumnStretch(0, 5)
        if images is not None:
            for i, tag, text, image in zip(range(len(tags)), tags, texts, images):
                layout.addWidget(DropPanel(tag, text, self.overlay,
                    self.overlayDroppedData, image), i, 0, 1, 1)
                layout.setRowStretch(i, 5)
        else:
            for i, tag, text in zip(range(len(tags)), tags, texts):
                layout.addWidget(DropPanel(tag, text, self.overlay,
                    self.overlayDroppedData), i, 0, 1, 1)
                layout.setRowStretch(i, 5)

        self.overlay.setLayout(layout)

    def killRogueOverlays(self):
        """Sometimes an overlay doesn't close on dragEventLeave.
           This kills any such overlays and is called when someone
           else takes that drop event.
        """
        self.closeOverlay()
        if self.acceptDocks:
            childDocks = self.findChildren(BFDockWidget)
            for dock in childDocks:
                dock.widget().killRogueOverlays()

    def propagateKillRogueOverlayMessage(self):
        """Propagate the message to kill rogue overlays to the
           top of the Boxfish module hierarchy.
        """
        #TODO: Need to also do this when drag operation is aborted
        # (back to the tree view). This is currently unknown
        if isinstance(self.parent(), BFDockWidget):
            self.parent_view.propagateKillRogueOverlayMessage()
        else:
            self.killRogueOverlays()

    def closeOverlay(self):
        if self.overlay_dialog is not None:
            self.overlay_dialog.close()
            self.overlay_dialog = None
            self.overlay.setVisible(False)

    def overlayDroppedData(self, indexList, tag):
        self.closeOverlay()
        self.propagateKillRogueOverlayMessage()
        self.droppedData(indexList, tag)

    def droppedData(self, indexList, tag = None):
        """Handle DataModel indices dropped into this window.
        """
        pass

    def dragLeaveEvent(self, event):
        self.closeOverlay()


    # We only accept events that are of our type, indicating
    # a dock window change
    def dragEnterEvent(self, event):
        if self.acceptDocks and isinstance(event.mimeData(), ModuleViewMime):
            event.accept()
        elif isinstance(event.mimeData(), DataIndexMime):
            if self.dragOverlay and self.overlay_dialog is None:
                self.overlay.setVisible(True)
                self.overlay_dialog = OverlayDialog(self, self.overlay)
                self.overlay_dialog.show()
            else:
                event.accept()
        elif self.acceptDocks and isinstance(event.mimeData(), ModuleNameMime):
            event.accept()
        else:
            super(ModuleView, self).dragEnterEvent(event)

    # If the event has a DockWidget in it, we check if it is our
    # parent or if we are its widget. If so, do nothing
    # If not, we add it to our dock and change its parent to us
    # In the future we should have some sort of event that
    # re-goodifies the view since the filter/data has changed
    def dropEvent(self, event):
        # Dropped DockWidget
        if self.acceptDocks and isinstance(event.mimeData(), ModuleViewMime):
            if event.mimeData().getDockWindow().parent() != self and \
               event.mimeData().getDockWindow().widget() != self:
                self.addDockWidget(Qt.BottomDockWidgetArea, \
                    event.mimeData().getDockWindow())
                event.mimeData().getDockWindow().widget().agent.changeParent(self.agent)
                event.mimeData().getDockWindow().widget().parent_view = self
                event.mimeData().getDockWindow().changeParent(self)
                event.mimeData().getDockWindow().widget().agent.refreshSceneInformation()
                event.setDropAction(Qt.MoveAction)
                event.accept()
            else:
                event.ignore()
        # Dropped Module Name
        elif self.acceptDocks and isinstance(event.mimeData(), ModuleNameMime):
            mod_name = event.mimeData().getName()
            dock = BFDockWidget(mod_name, self)
            # TODO: figure out how to make instantiate a class method
            new_mod = ModuleView().instantiate(mod_name, dock, self, mod_name)
            new_mod.agent.refreshSceneInformation()
            dock.setWidget(new_mod)
            self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        # Dropped Attribute Data
        elif isinstance(event.mimeData(), DataIndexMime) \
            and not self.dragOverlay:
            indexList = event.mimeData().getDataIndices()
            event.accept()
            self.propagateKillRogueOverlayMessage()
            self.droppedData(indexList)
        else:
            self.propagateKillRogueOverlayMessage()
            super(ModuleView, self).dropEvent(event)

    def buildTabDialog(self):
        self.tab_dialog = TabDialog(self)
        self.tab_dialog.addTab(SceneTab(self.tab_dialog, self.agent),
            "Scene Policy")


    def mouseDoubleClickEvent(self, event):
        if self.enable_tab_dialog:
            self.buildTabDialog()
            self.tab_dialog.show()


class BFDockWidget(QDockWidget):
    """We can move windows using the QDockWidget. This class sets all of
       or QDockWidget policies and attempts to allow movement between
       Docks, but that doesn't currently work as intended.
    """

    def __init__(self, title, parent):
        super(BFDockWidget, self).__init__(title, parent)

        self.setAttribute(Qt.WA_NoMousePropagation)
        self.setAcceptDrops(True)
        self.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable)

    def findPosition(self):
        # I have relative coords to add because I am a dockwidget
        x, y = self.parent().findPosition()
        return x + self.x(), y + self.y()

    def changeParent(self, new_parent):
        self.setParent(new_parent)
        #self.setVisible(True)

    def mousePressEvent(self, e):
        if (e.buttons() != Qt.MidButton and e.modifiers() != Qt.ShiftModifier):
            super(BFDockWidget, self).mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if (e.buttons() == Qt.MidButton): # dropAction Doesn't work :(
            drag = QDrag(self)
            drag.setMimeData(ModuleViewMime(self))
            dropAction = drag.start(Qt.MoveAction)
        elif (e.modifiers() == Qt.ShiftModifier): # dropAction works here
            drag = QDrag(self)
            drag.setMimeData(ModuleViewMime(self))
            dropAction = drag.start(Qt.MoveAction)
        else:
            super(BFDockWidget, self).mouseMoveEvent(e)


    def closeEvent(self, e):
        self.widget().agent.delete()
        super(BFDockWidget, self).closeEvent(e)


class ModuleViewMime(QMimeData):
    """This allows passing of the QDockWidget between windows
       during Drag & Drop.
    """

    def __init__(self, dock_window):
        super(ModuleViewMime, self).__init__()

        self.dock_window = dock_window

    def getDockWindow(self):
        return self.dock_window


class ModuleNameMime(QMimeData):
    """This is for passing ModuleView display_names during
       Drag & Drop operations.
    """

    def __init__(self, name):
        super(ModuleNameMime, self).__init__()

        self.name = name

    def getName(self):
        return self.name


# TODO: Add a manager so we save all the pieces but only construct
# on double click to get around the out-of-date problems on some of 
# the information
class TabDialog(QDialog):
    """This dialog contains tabs with options for everything related
       to the module. Inheriting modules can add their own tabs
       to this dialog.

       Example: a module might create a tab that determines what
       the default aggregation method is for dropped data
    """

    def __init__(self, parent, title = ""):
        super(TabDialog, self).__init__(parent)

        self.setWindowTitle(title)
        self.tabs = QTabWidget(self)
        self.setModal(True)

        # Need a layout to get resizing to work
        layout = QGridLayout()
        layout.addWidget(self.tabs, 0, 0)
        self.setLayout(layout)

    def addTab(self, widget, label, index = 0):

        viewArea = QScrollArea()
        viewArea.setWidget(widget)
        viewArea.setWidgetResizable(True)
        self.tabs.insertTab(index, viewArea, label)
        self.tabs.setCurrentIndex(0)


class SceneTab(QWidget):
    """This widget is for changing the Scene policies of
       the module.
    """

    def __init__(self, parent, agent):
        super(SceneTab, self).__init__(parent)

        self.agent = agent

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)

        # self.propagate_module_scenes
        self.propagate = QCheckBox("Propagate module scene to other modules.")
        self.propagate.setChecked(self.agent.propagate_module_scenes)
        self.propagate.stateChanged.connect(self.propagateChanged)
        # We only allow this change if the parent does not propagate
        if self.agent.parent().propagate_module_scenes:
            self.propagate.setDisabled(True)

        # self.apply_module_scenes
        self.applyScene = QCheckBox("Apply module scene from other modules.")
        self.applyScene.setChecked(self.agent.apply_module_scenes)
        self.applyScene.stateChanged.connect(self.applyChanged)

        self.layout.addWidget(self.applyScene)
        self.layout.addItem(QSpacerItem(5,5))
        self.layout.addWidget(self.propagate)

        self.setLayout(self.layout)

    def propagateChanged(self):
        self.agent.propagate_module_scenes = self.propagate.isChecked()

    def applyChanged(self):
        self.agent.apply_module_scenes = self.applyScene.isChecked()


# Some of these should probably be broken out into a Utils class
class DragDockLabel(QLabel):
    """This creates a label that can be used for BFDockWidget
       Drag & Drop operations.
    """

    def __init__(self, dock, color):
        super(DragDockLabel,self).__init__("Drag Me")

        self.dock = dock
        self.setAcceptDrops(True)
        self.setScaledContents(True)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.setToolTip("Click and drag to change parent.")

        pm = QPixmap(1,10)
        pm.fill(Qt.black)
        self.setPixmap(pm)

    def mousePressEvent(self, e):
        pass

    def mouseMoveEvent(self, e):
        drag = QDrag(self)
        drag.setMimeData(ModuleViewMime(self.dock))
        dropAction = drag.start(Qt.MoveAction)


class DragToolBar(QToolBar):
    """This creates a toolbar that can be used for BFDockWidget
       Drag & Drop operatioxtns.
    """

    def __init__(self, title, parent, dock):
        super(DragToolBar, self).__init__(title, parent)

        self.dock = dock

    def mousePressEvent(self, e):
        pass

    def mouseMoveEvent(self, e):
        drag = QDrag(self)
        drag.setMimeData(ModuleViewMime(self.dock))
        dropAction = drag.start(Qt.MoveAction)


class DragTextLabel(QLabel):
    """This creates a label that can be used for text toolbox
       Drag & Drop operations.
    """

    def __init__(self, text, size_sample = "<<"):
        super(DragTextLabel,self).__init__(text)

        self.text = text
        self.setAcceptDrops(True)
        #self.setScaledContents(True)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.setToolTip("Drag me.")

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)

        font_metric = QFontMetrics(QFont())
        two_size = font_metric.size(Qt.TextSingleLine, size_sample)
        max_size = max([two_size.width(), two_size.height()]) + 4
        self.setMaximumHeight(max_size)
        self.setMinimumHeight(max_size)
        self.setMaximumWidth(max_size)
        self.setMinimumWidth(max_size)

    def mousePressEvent(self, e):
        pass

    def mouseMoveEvent(self, e):
        drag = QDrag(self)
        drag.setMimeData(LabelTextMime(self.text))
        drag.setPixmap(QPixmap.fromImage(self.createPixmap()))
        dropAction = drag.start(Qt.MoveAction)

    def createPixmap(self):
        font_metric = QFontMetrics(QFont())
        text_size = font_metric.size(Qt.TextSingleLine, self.text)
        image = QImage(text_size.width() + 4, text_size.height() + 4,
            QImage.Format_ARGB32_Premultiplied)
        image.fill(qRgba(240, 240, 120, 255))

        painter = QPainter()
        painter.begin(image)
        painter.setFont(QFont())
        painter.setBrush(Qt.black)
        painter.drawText(QRect(QPoint(2, 2), text_size), Qt.AlignCenter,
            self.text)
        painter.end()
        return image


class LabelTextMime(QMimeData):
    """This is for passing text from DragTextLabels during
       Drag & Drop operations.
    """

    def __init__(self, text):
        super(LabelTextMime, self).__init__()

        self.text = text

    def getText(self):
        return self.text

class DropTextLabel(QLabel):
    """This creates a label that accepts LabelTextMime Drops.
    """

    def __init__(self, text, size_sample = "<<"):
        super(DropTextLabel, self).__init__(text)

        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        #self.setScaledContents(True)
        #self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        
        # FACTORME and make me optional
        font_metric = QFontMetrics(QFont())
        two_size = font_metric.size(Qt.TextSingleLine, size_sample)
        max_size = max([two_size.width(), two_size.height()]) + 4
        self.setMaximumHeight(max_size)
        self.setMinimumHeight(max_size)
        self.setMaximumWidth(max_size)
        self.setMinimumWidth(max_size)

    def dragEnterEvent(self, e):
        if isinstance(e.mimeData(), LabelTextMime):
            e.accept()
        else:
            super(DropTextLabel, self).dragEnterEvent(e)

    def dropEvent(self, e):
        if isinstance(e.mimeData(), LabelTextMime):
            self.setText(e.mimeData().getText())
        else:
            super(DropTextLabel, self).dropEvent(e)



class DropLineEdit(QLineEdit):
    """This creates a LineEdit (textfield) for datatree drop operations.
    """

    def __init__(self, parent, datatree, default_text = "", completer = None):
        super(DropLineEdit, self).__init__(default_text, parent)

        self.datatree = datatree
        if completer:
            self.setCompleter(completer)

    def dragEnterEvent(self, e):
        if isinstance(e.mimeData(), DataIndexMime):
            e.accept()
        else:
            super(DropLineEdit, self).dragEnterEvent(e)

    def dropEvent(self, e):
        if isinstance(e.mimeData(), DataIndexMime):
            indices = e.mimeData().getDataIndices()
            for index in indices:
                self.setText(self.datatree.getItem(index).name)
        else:
            super(DropLineEdit, self).dropEvent(e)


class DropPanel(QWidget):
    """This creates a panel that can be datatree index drag/drop operations.

       handler - the datatree index list (and only the datatree index list)
                 will be passed to this function if not None.
    """

    def __init__(self, tag, text, parent, handler, icon = None):
        super(DropPanel, self).__init__(parent)

        self.setAcceptDrops(True)
        self.handler = handler
        self.tag = tag
        self.setPalette(QColor(0,0,0,0))

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        if icon is not None:
            label = QLabel("", parent = self)
            label.setPixmap(icon)
            layout.addWidget(label)
            layout.addSpacing(5)
        layout.addWidget(QLabel(text))

    def dragEnterEvent(self, event):
        if isinstance(event.mimeData(), DataIndexMime):
            event.accept()
        else:
            super(DropPanel, self).dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        super(DropPanel, self).dragLeaveEvent(event)

    def dropEvent(self, event):
        # Dropped Attribute Data
        if isinstance(event.mimeData(), DataIndexMime):
            indexList = event.mimeData().getDataIndices()
            event.accept()
            self.droppedData(indexList)
        else:
            super(DropPanel, self).dropEvent(event)

    def droppedData(self, indexList):
        self.handler(indexList, self.tag)


class OverlayDialog(QDialog):
    """Transparent dialog for overlays."""

    def __init__(self, parent, widget):
        super(OverlayDialog, self).__init__(parent, Qt.SplashScreen)

        self.setAcceptDrops(True)

        #self.setAttribute(Qt.WA_TranslucentBackground)
        bgcolor = self.palette().color(QPalette.Background)
        self.setPalette(QColor(bgcolor.red(), bgcolor.green(), bgcolor.blue(),
            0)) # alpha

        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.addWidget(widget)
        self.setLayout(layout)

        self.resize(0.8 * parent.size().width(), 0.8 * parent.size().height())
        widget.resize(self.width(), self.height())


    def show(self):
        super(OverlayDialog, self).show()

        # Get absolute position of parent widget by finding the
        # relative positions up the chain until the top level window
        # which will give us the absolute position to add to it.
        # Then we magical-numerically offset by 0.1 because that's
        # half of the 20% we don't cover.
        x, y = self.parent().findPosition()
        self.move(x + 0.1 * self.parent().size().width(),
            y + 0.1 * self.parent().size().height())


class OverlayFrame(QFrame):
    """Creates a rounded rectangular translucent frame and
       accepts drops.
    """

    def __init__(self, parent):
        super(OverlayFrame, self).__init__(parent)

        self.setVisible(False)
        self.setAcceptDrops(True)

    # Adapted from developer.nokia.com/Community/Wiki/Qt_rounded_rect_widget
    def paintEvent(self, event):
        roundness = 10
        rect = self.rect()
        bgcolor = self.palette().color(QPalette.Background)
        alpha_bgcolor = QColor(bgcolor.red(), bgcolor.green(),
            bgcolor.blue(), 150)

        painter = QPainter()
        painter.begin(self)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.red)
        rounded_rect = QPainterPath()
        rounded_rect.addRoundRect(1, 1, rect.width() - 2, rect.height() - 2,
            roundness, roundness)
        painter.setClipPath(rounded_rect)
        self.setMask(painter.clipRegion())
        painter.setOpacity(1.0)
        painter.fillPath(rounded_rect, QBrush(alpha_bgcolor))
        painter.restore()
        painter.end()
