from PySide.QtCore import Slot,Signal,QObject,QMimeData,Qt
from PySide.QtGui import QWidget,QMainWindow,QDockWidget,QToolBar,\
    QLabel,QDrag,QPixmap
import numpy as np
from SubDomain import *
from BFTable import *
#from Query import *
from Projection import *
from DataModel import *
from BFColumn import *
import BFMaps
from BFSceneInfo import *

class BFModule(QObject):

    # Signals that I send
    subscribeSignal          = Signal(object,str)
    unsubscribeSignal        = Signal(object,str)
    highlightSignal          = Signal(SubDomain)
    addColumnSignal          = Signal(BFColumn, QObject)
    #evaluateSignal           = Signal(Query)
    getSubDomainSignal       = Signal(object,str)

    # Name template for the highlight signal
    highlightSignal_base = "%s_highlight_signal"

    # Name template for the data publishing signal
    publishSignal_base = "%s_publish_signal"

    # The list of registered signals for highlights and yes the exec stuff is
    # necessary since PySide seems to mangle the signal otherwise. It is not
    # allowed to create the signals in the __init__ function nor can we create
    # a list of signale or a dict(). Either code runs but the resulting signals
    # are castrated (they have no connect function for example). Thus we use
    # this hack to create a bunch of named static variables
    for name in SubDomain().subclasses():
        exec highlightSignal_base % name + ' = Signal(SubDomain)'
        #exec publishSignal_base % name + ' = Signal(Query,np.ndarray)'

    # INIT IS DOWN HERE
    def __init__(self, parent, model = None):
        super(BFModule,self).__init__(parent)

        self.model = model
        self.listenerCount = dict()
        self.highlights = dict() # domain based information
        self.domain_scenes = dict()
        self.attribute_scenes = dict()
        self.module_scenes = dict()
        self.publish = dict()
        for name in SubDomain().subclasses():
            self.listenerCount[name] = 0
            exec 'self.highlights[\"%s\"] = self.' % name \
                + self.highlightSignal_base % name
            #exec 'self.publish[\"%s\"] = self.' % name \
                # + self.publishSignal_base % name

        #self.context = Context()
        #self.queryEngine = QueryEngine()

        # List of BFColumns the module wants
        self.requirements = list()

        # List of BFColumns the children want
        self.child_columns = list()

        self.filters = list()


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

    def buildColumnsFromIndices(self, indexList):
        column_list = list()

        get_parent = lambda x: self.model.getItem(x).parent()
        sorted_indices = sorted(indexList, key = get_parent)
        attr_groups = itertools.groupby(sorted_indices, key = get_parent)

        for key, group in attr_groups:
            attrs = [self.model.getItem(x).name for x in group]
            column_list.append(BFColumn(key, attrs,
                parent = self))

        return column_list


    def addRequirement(self, cols):
        for col in cols:
            self.requirements.append(col)
            col.changeSignal.connect(self.requiredColumnChanged)
            #Now send this new one to the parent
            self.addColumnSignal.emit(col, self)

    @Slot(BFColumn)
    def requiredColumnChanged(self, col):
        pass

    # Signal decorator attached after the class.
    def addChildColumn(self, col, child):
        new_col = col.createUpstream(child)
        self.child_columns.append(new_col)
        self.addColumnSignal.emit(new_col, self)

    def getColumnRequests(self):
        reqs = list()
        reqs.extend(self.requirements)
        reqs.extend(self.child_columns)
        return reqs

    # Remove column that has sent a delete signal
    @Slot(BFColumn)
    def deleteColumn(self, col):
        if col in self.requirements:
            self.requirements.remove(col)
        elif col in self.child_columns:
            self.child_columns.remove(col)

    def registerChild(self, child):
        child.subscribeSignal.connect(self.subscribe)
        child.unsubscribeSignal.connect(self.unsubscribe)
        child.highlightSignal.connect(self.highlight)
        child.addColumnSignal.connect(self.addChildColumn)
        #child.evaluateSignal.connect(self.evaluate)
        child.getSubDomainSignal.connect(self.getSubDomain)

        # "Adopt" child's column requests
        for col in child.getColumnRequests():
            self.child_columns.append(col.createUpstream(child))

    def unregisterChild(self, child):
        child.subscribeSignal.disconnect(self.subscribe)
        child.unsubscribeSignal.disconnect(self.unsubscribe)
        child.highlightSignal.disconnect(self.highlight)
        child.addColumnSignal.disconnect(self.addChildColumn)
        #child.evaluateSignal.disconnect(self.evaluate)
        child.getSubDomainSignal.disconnect(self.getSubDomain)

        # Abandon child's column requests
        for col in self.child_columns:
            if col.parent() == child:
                col.delete()

    # Change the parent of the module.
    def changeParent(self, new_parent):
        self.parent().unregisterChild(self)
        self.setParent(new_parent)
        if self.parent() is not None and \
            isinstance(self.parent(), BFModule):
            self.parent().registerChild(self)

    # REWRITEME to apply child policy and use projections through the
    # data model as well as handle other Scenegraph changes
    @Slot(SubDomain)
    def highlight(self,subdomain):
        """This slot is called whenever a child module changes
           subdomain-dependent scene information. The module cycles through
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
    #@Slot(BFModule,str)
    def subscribe(self,module,name):

        # If we are the first one subscribing to this subdomain
        if name not in self.listenerCount:
            raise ValueError("Could not find subdomain %s." \
                + "Must be a subclass of SubDomain" % name)

        self.listenerCount[name] = self.listenerCount[name] + 1

        self.connectSubscription(module,name)


    # Slot must be added after class definition
    #@Slot(BFModule,str)
    def unsubscribe(self,module,name):

        # If we are the first one subscribing to this subdomain
        if name not in self.listenerCount:
            raise ValueError("Could not find subdomain %s." \
                + "Must be a subclass of SubDomain" % name)

        if self.listenerCount[name] == 0:
            raise ValueError("No listener left to unsubscribe")

        self.listenerCount[name] = self.listenerCount[name] - 1

        self.disconnectSubscription(module,name)


    #@Slot(Query)
    def evaluate(self,query):
        pass
        #answer, success = self.queryEngine.evaluate(query,self.context)
        #if success:
        #    self.publish[query.subdomain.subdomain()].emit(query,answer)

    # Slot must be added after class definition
    #@Slot(BFModule,str)
    def getSubDomain(self,module,subdomain):
        pass
        #data,success = self.queryEngine.getSubDomain(subdomain)
        #if success:
        #    module.setSubDomain(data)

    def connectSubscription(self,module,name):

        self.highlights[name].connect(module.highlightChanged)
        self.publish[name].connect(module.receive)


    def disconnectSubscription(self,module,name):

        self.highlights[name].disconnect(module.highlightChanged)
        self.publish[name].disconnect(module.receive)

    def evaluate(self,query):
        pass
        #self.evaluateSignal.emit(query)

    def getSubDomain(self,subdomain):
        self.getSubDomainSignal.emit(self,subdomain)

    def setSubDomain(self,subdomain):
        self.subdomain = subdomain

    @Slot(SubDomain)
    def highlightChanged(self,subdomain):
        print "Highlight", subdomain.subdomain()

    #@Slot(Query,np.ndarray)
    def receive(self,query,data):
        print "BFModule got an answer for ", query


# The slots need to be added down here because BFModule is not defined
# at the time that the functions are defined
BFModule.subscribe = Slot(BFModule, str)(BFModule.subscribe)
BFModule.unsubscribe = Slot(BFModule, str)(BFModule.unsubscribe)
BFModule.getSubDomain = Slot(BFModule, str)(BFModule.getSubDomain)
BFModule.addChildColumn = Slot(BFColumn, BFModule)(BFModule.addChildColumn)


class BFModuleWindow(QMainWindow):
    """This is the parent of what we will think of as a
       module/extension/plug-in. It has the interface to create the single
       BFModule it represents as well as the GUI elements to handle its
       specific actions. Both need to be written by the inheriting object.

       This class handles the reparenting and docking elements of all such
       modules.
    """

    # display_name should be unique to the class and will show up in UI and
    # be available for instantiation if in_use is True
    display_name = "Module Window"
    in_use = False # This is an 'abstract' class, do not instantiate

    def __init__(self, parent = None, parent_view = None, title = None):
        super(BFModuleWindow, self).__init__(parent)

        self.title = title
        self.parent_view = parent_view
        self.module = None

        # Only realize if we have a parent and a parent view
        if self.parent_view is not None and self.parent() is not None:
            self.realize()

        self.acceptDocks = False # Set to True to have child windows

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


    # This sets up the plug-in by generating the module and registering
    # it to the parent and by placing the view elements in the overall
    # layout
    def realize(self):
        self.module = self.createModule()
        self.parent_view.module.registerChild(self.module)

        self.view = self.createView()
        self.centralWidget = QWidget()

        layout = QGridLayout()
        if isinstance(self.parent(), BFDockWidget):
            layout.addWidget(BFAttachLabel(self.parent(), 0),0, 0, 1, 2)

        # TODO: Replace magic number with not-magic constant
        layout.addWidget(self.view, 100, 0, 1, 2) # Added view is at bottom
        layout.setRowStretch(100, 5) # view has most row stretch

        left, top, right, bottom = layout.getContentsMargins()
        layout.setContentsMargins(0, 0, 0, 0)
        self.centralWidget.setLayout(layout)

        self.setCentralWidget(self.centralWidget)

        # Moving toolbar functionality elsewhere to save space for now,
        # may add it back later or create own widget of labels that have
        # same functionality but are not moveable and much smaller
        #self.createToolBar()


    # Must be implemented by inheritors
    def createModule(self):
        raise NotImplementedError("Realize not implemented,"\
            + " cannot create module")

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
        if self.in_use:
            scList.append(self.display_name)
        for s in self.__class__.__subclasses__():
            scList.extend(s(None).subclassList())
        return scList


    # For sizing the doc window appropriately with respect to its parent
    def sizeHint(self):
        return QSize(200, self.heightHint)
        #return QSize(self.size().width(), self.heightHint)


    # Determine if this window is allowed to have child windows
    def allowDocks(self, dockable):
        self.acceptDocks = dockable

    def droppedData(self, indexList):
        """Handle DataModel indices dropped into this window.
        """
        pass

    # We only accept events that are of our type, indicating
    # a dock window change
    def dragEnterEvent(self, event):
        if self.acceptDocks and isinstance(event.mimeData(), BFWindowMime):
            event.accept()
        elif isinstance(event.mimeData(), BFDataMime):
            event.accept()
        elif self.acceptDocks and isinstance(event.mimeData(), ModuleNameMime):
            event.accept()
        else:
            super(BFModuleWindow, self).dragEnterEvent(event)

    # If the event has a DockWidget in it, we check if it is our
    # parent or if we are its widget. If so, do nothing
    # If not, we add it to our dock and change its parent to us
    # In the future we should have some sort of event that
    # re-goodifies the view since the filter/data has changed
    def dropEvent(self, event):
        # Dropped DockWidget
        if self.acceptDocks and isinstance(event.mimeData(), BFWindowMime):
            if event.mimeData().getDockWindow().parent() != self and \
               event.mimeData().getDockWindow().widget() != self:
                self.addDockWidget(Qt.BottomDockWidgetArea, \
                    event.mimeData().getDockWindow())
                event.mimeData().getDockWindow().widget().module.changeParent(self.module)
                event.mimeData().getDockWindow().widget().parent_view = self
                event.mimeData().getDockWindow().changeParent(self)
                event.setDropAction(Qt.MoveAction)
                event.accept()
            else:
                event.ignore()
        # Dropped Module Name
        elif self.acceptDocks and isinstance(event.mimeData(), ModuleNameMime):
            mod_name = event.mimeData().getName()
            dock = BFDockWidget(mod_name, self)
            new_mod = BFModuleWindow().instantiate(mod_name, dock, self, \
                mod_name)
            dock.setWidget(new_mod)
            self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        # Dropped Attribute Data
        elif isinstance(event.mimeData(), BFDataMime):
            indexList = event.mimeData().getDataIndices()
            event.accept()
            self.droppedData(indexList)
        else:
            super(BFModuleWindow, self).dropEvent(event)


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
        self.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)

    def changeParent(self, new_parent):
        self.setParent(new_parent)
        #self.setVisible(True)

    def mousePressEvent(self, e):
        if (e.buttons() != Qt.MidButton and e.modifiers() != Qt.ShiftModifier):
            super(BFDockWidget, self).mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if (e.buttons() == Qt.MidButton): # dropAction Doesn't work :(
            drag = QDrag(self)
            drag.setMimeData(BFWindowMime(self))
            dropAction = drag.start(Qt.MoveAction)
        elif (e.modifiers() == Qt.ShiftModifier): # dropAction works here
            drag = QDrag(self)
            drag.setMimeData(BFWindowMime(self))
            dropAction = drag.start(Qt.MoveAction)
        else:
            super(BFDockWidget, self).mouseMoveEvent(e)


class BFWindowMime(QMimeData):
    """This allows passing of the QDockWidget between windows
       during Drag & Drop.
    """

    def __init__(self, dock_window):
        super(BFWindowMime, self).__init__()

        self.dock_window = dock_window

    def getDockWindow(self):
        return self.dock_window


class ModuleNameMime(QMimeData):
    """This is for passing BFModuleWindow display_names during
       Drag & Drop operations.
    """

    def __init__(self, name):
        super(ModuleNameMime, self).__init__()

        self.name = name

    def getName(self):
        return self.name

class BFAttachLabel(QLabel):
    """This creates a label that can be used for BFDockWidget
       Drag & Drop operations.
    """

    def __init__(self, dock, color):
        super(BFAttachLabel,self).__init__("Drag Me")

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
        drag.setMimeData(BFWindowMime(self.dock))
        dropAction = drag.start(Qt.MoveAction)

class BFDragToolBar(QToolBar):
    """This creates a toolbar that can be used for BFDockWidget
       Drag & Drop operations.
    """

    def __init__(self, title, parent, dock):
        super(BFDragToolBar, self).__init__(title, parent)

        self.dock = dock

    def mousePressEvent(self, e):
        pass

    def mouseMoveEvent(self, e):
        drag = QDrag(self)
        drag.setMimeData(BFWindowMime(self.dock))
        dropAction = drag.start(Qt.MoveAction)

class BFDropLabel(QLabel):
    """This creates a label that can be model index drag/drop operations.

       handler - the model index list (and only the model index list) will
                 be passed to this function if not None.
    """

    def __init__(self, text, parent = None, handler = None):
        super(BFDropLabel, self).__init__(text, parent = parent)

        self.handler = handler
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event):
        if isinstance(event.mimeData(), BFDataMime):
            event.accept()
        else:
            super(BFDropLabel, self).dragEnterEvent(event)

    def dropEvent(self, event):
        # Dropped Attribute Data
        if isinstance(event.mimeData(), BFDataMime):
            indexList = event.mimeData().getDataIndices()
            event.accept()
            self.droppedData(indexList)
        else:
            super(BFDropLabel, self).dropEvent(event)

    def droppedData(self, indexList):
        if self.handler is not None:
            self.handler(indexList)
