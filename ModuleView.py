from PySide.QtCore import Slot,Signal,QObject,QMimeData,Qt,QSize
from PySide.QtGui import QWidget,QMainWindow,QDockWidget,\
    QLabel,QDrag,QPixmap,QDialog,QFrame,QGridLayout,QSizePolicy,\
    QVBoxLayout,QPalette,QPainter,QTabWidget,QCheckBox,QScrollArea,\
    QBrush,QSpacerItem,QPainterPath,QGroupBox
from SceneInfo import *
from GUIUtils import *
from DataModel import DataIndexMime

def Module(display_name, agent_type, scene_type = ModuleScene):
    """This decorator denotes a ModuleView as a module creatable by 
       users.
       
       display_name
           name of module the user will see.

       agent_type
           type of the ModuleAgent that goes with this module.

       scene_type
           type of the ModuleScene that goes with this module.
    """
    def module_inner(cls):
        cls.display_name = display_name
        cls.agent_type = agent_type
        cls.scene_type = scene_type
        return cls
    return module_inner


class ModuleView(QMainWindow):
    """This is the parent of what we will think of as a
       agent/extension/plug-in. It has the interface to create the single
       ModuleAgent it represents as well as the GUI elements to handle its
       specific actions. Both need to be written by the inheriting object.

       This class handles the reparenting and docking elements of all such
       modules.

       parent
           The GUI parent of this window as necessary for Qt

       parent_view
           The ModuleView that is the logical parent to this one.
    """

    def __init__(self, parent, parent_view, title = None):
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


    def realize(self):
        """This function is part of initialization where it handles
           ModuleAgent creation and wiring and subclass view placement.
        """
        # Create and wire the Agent into the Boxfish tree
        self.agent = self.agent_type(self.parent_view.agent,
            self.parent_view.agent.datatree)
        self.agent.module_scene = self.scene_type(self.agent_type,
            self.display_name)
        self.parent_view.agent.registerChild(self.agent)

        # Create and place the module-specific view elements
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


    def createView(self):
        """This function should be re-implemented to create and return
           the subclass-specific view/GUI as a single widget. This widget
           will then be placed in the overstructure of the ModelView
           GUI elements.
        """
        raise NotImplementedError("Realize not implemented,"\
            + " cannot create view")

    @classmethod
    def instantiate(cls, module_name, parent, parent_view, title = None):
        """Creates a module and inserts it into the Boxfish tree.

           module_name
               The display name of the module used to determine the 
               specific type of ModelView/ModelAgent to create.

           parent
               The GUI parent of the module to be created.

           parent_view
               The ModelView that is the logical parent to the one we
               are creating.
        """
        if hasattr(cls, 'display_name') and cls.display_name == module_name:
            return cls(parent, parent_view, title)
        else:
            for s in cls.__subclasses__():
                result = s.instantiate(module_name, parent, parent_view, title)
                if result is not None:
                    return result
            return None

    @classmethod
    def subclassList(cls, scList = None):
        """Creates a list of modules we can create.
        """
        if scList is None:
            scList = list()
        if hasattr(cls, 'display_name'):
            scList.append(cls.display_name)
        for s in cls.__subclasses__():
            scList.extend(s.subclassList())
        return scList


    def sizeHint(self):
        """Overrides the QWidget method so the initial size of this
           module is sane.
        """
        return QSize(200, self.heightHint) # TODO: figure out better values
        #return QSize(self.size().width(), self.heightHint)


    def findPosition(self):
        """This finds the absolute position of this particular module
           in screen coordinates.
        """
        if isinstance(self.parent(), BFDockWidget):
            # parent is a dockwidget, so coords are relative
            x, y = self.parent().findPosition()
            return x + self.x(), y + self.y()
        else: # parent_view is boxfish main, get absolute coords
            return self.parent_view.geometry().x() + self.x(),\
                self.parent_view.geometry().y() + self.y()

    
    def allowDocks(self, dockable):
        """Sets whether or not the module will accept other modules as
           children.
        """
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
            new_mod = ModuleView.instantiate(mod_name, dock, self, mod_name)
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

        self.layout.addWidget(self.buildHighlightGroupBox())
        self.layout.addItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildModuleGroupBox())

        self.setLayout(self.layout)
    
    
    def buildHighlightGroupBox(self):
        groupBox = QGroupBox("Highlight Policy")
        layout = QVBoxLayout()

        # agent.propagate_highlights
        self.highlights_propagate = QCheckBox("Propagate highlights to "
            + "other modules.")
        self.highlights_propagate.setChecked(self.agent.propagate_highlights)
        self.highlights_propagate.stateChanged.connect(
            self.highlightsPropagateChanged)
        # We only allow this change if the parent does not propagate
        if self.agent.parent().propagate_highlights:
            self.highlights_propagate.setDisabled(True)

        # agent.apply_highlights
        self.applyHighlights = QCheckBox("Apply highlights from "
            + "other modules.")
        self.applyHighlights.setChecked(self.agent.apply_highlights)
        self.applyHighlights.stateChanged.connect(self.applyHighlightsChanged)

        layout.addWidget(self.applyHighlights)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.highlights_propagate)
        groupBox.setLayout(layout)
        return groupBox


    def highlightsPropagateChanged(self):
        self.agent.propagate_highlights = self.highlights_propagate.isChecked()


    def applyHighlightsChanged(self):
        self.agent.apply_highlights = self.applyHighlights.isChecked()


    def buildModuleGroupBox(self):
        groupBox = QGroupBox("Module Policy")
        layout = QVBoxLayout()

        # agent.propagate_module_scenes
        self.module_propagate = QCheckBox("Propagate module scene information "
            + "to other modules.")
        self.module_propagate.setChecked(self.agent.propagate_module_scenes)
        self.module_propagate.stateChanged.connect(self.modulePropagateChanged)
        # We only allow this change if the parent does not propagate
        if self.agent.parent().propagate_module_scenes:
            self.module_propagate.setDisabled(True)

        # agent.apply_module_scenes
        self.module_applyScene = QCheckBox("Apply module scene information "
            + "from other modules.")
        self.module_applyScene.setChecked(self.agent.apply_module_scenes)
        self.module_applyScene.stateChanged.connect(self.moduleApplyChanged)

        layout.addWidget(self.module_applyScene)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.module_propagate)
        groupBox.setLayout(layout)
        return groupBox


    def modulePropagateChanged(self):
        self.agent.propagate_module_scenes = self.module_propagate.isChecked()


    def moduleApplyChanged(self):
        self.agent.apply_module_scenes = self.module_applyScene.isChecked()


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

