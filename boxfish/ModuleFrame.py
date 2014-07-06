from PySide.QtCore import Slot,Signal,QObject,QMimeData,Qt,QSize
from PySide.QtGui import QWidget,QMainWindow,QDockWidget,\
    QLabel,QDrag,QPixmap,QDialog,QFrame,QGridLayout,QSizePolicy,\
    QVBoxLayout,QPalette,QPainter,QTabWidget,QCheckBox,QScrollArea,\
    QBrush,QSpacerItem,QPainterPath,QGroupBox
from SceneInfo import *
from GUIUtils import *
from DataModel import DataIndexMime

def Module(display_name, agent_type, scene_type = ModuleScene):
    """This decorator denotes a ModuleFrame as a module creatable by
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


# This class must be a QMainWindow as that is the only widget that
# can accept QDockWidgets which are used for all of our module
# drag/drop/re-parenting.
class ModuleFrame(QMainWindow):
    """This is the parent of what we will think of as a
       agent/extension/plug-in. It has the interface to create the single
       ModuleAgent it represents as well as the GUI elements to handle its
       specific actions. Both need to be written by the inheriting object.

       This class handles the reparenting and docking elements of all such
       modules.
    """

    droppedDataSignal = Signal(list, str)

    def __init__(self, parent, parent_frame, title = None):
        """Construct a ModuleFrame.

           parent
               The GUI parent of this window as necessary for Qt

           parent_frame
               The ModuleFrame that is the logical parent to this one.
        """
        super(ModuleFrame, self).__init__(parent)

        self.title = title
        self.parent_frame = parent_frame
        self.agent = None

        # Only realize if we have a parent and a parent frame
        if self.parent_frame is not None and self.parent() is not None:
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
        if self.parent_frame is not None:
            self.heightHint = self.parent_frame.height() - 20

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
        self.agent = self.agent_type(self.parent_frame.agent,
            self.parent_frame.agent.datatree)
        self.agent.module_scene = self.scene_type(self.agent_type,
            self.display_name)
        self.parent_frame.agent.registerChild(self.agent)

        # Create and place the module-specific view elements
        self.view = self.createView()
        self.centralWidget = QWidget()

        layout = QGridLayout()
        if isinstance(self.parent(), BFDockWidget):
            layout.addWidget(DragDockLabel(self.parent()),0, 0, 1, 2)

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
    def instantiate(cls, module_name, parent, parent_frame, title = None):
        """Creates a module and inserts it into the Boxfish tree.

           module_name
               The display name of the module used to determine the
               specific type of ModuleFrame/ModuleAgent to create.

           parent
               The GUI parent of the module to be created.

           parent_frame
               The ModuleFrame that is the logical parent to the one we
               are creating.
        """
        if hasattr(cls, 'display_name') and cls.display_name == module_name:
            return cls(parent, parent_frame, title)
        else:
            for s in cls.__subclasses__():
                result = s.instantiate(module_name, parent, parent_frame, title)
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
        else: # parent_frame is boxfish main, get absolute coords
            return self.parent_frame.geometry().x() + self.x(),\
                self.parent_frame.geometry().y() + self.y()


    def allowDocks(self, dockable):
        """Sets whether or not the module will accept other modules as
           children.
        """
        self.acceptDocks = dockable

    def createDragOverlay(self, tags, texts, images = None):
        """Creates a DragOverlay for this ModuleFrame with the given
           text and optional images. When DataIndexMimes (DataTree indices)
           are dropped on the text/images of this overlay, they are
           associated with the tag of the same index of the text/image.

           This is a user interface for when a ModuleFrame wants to
           accept drops for multiple purposes.
        """
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

        # Add a Close button to deal with lack of cancel signal 
        # for drag/drop
        class CloseLabel(QLabel):

            closeSignal = Signal()

            def __init__(self):
                super(CloseLabel, self).__init__("Close")

                self.setStyleSheet("QLabel { color : white; }")

            def mousePressEvent(self, e):
                self.closeSignal.emit()

        closeButton = CloseLabel()
        closeButton.closeSignal.connect(self.killRogueOverlays)
        layout.addWidget(closeButton, len(tags), 0, 1, 1)
        layout.setRowStretch(len(tags), 0)

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
            self.parent_frame.propagateKillRogueOverlayMessage()
        else:
            self.killRogueOverlays()

    def closeOverlay(self):
        """Close the DragOverlay for this ModuleFrame."""
        if self.overlay_dialog is not None:
            self.overlay_dialog.close()
            self.overlay_dialog = None
            self.overlay.setVisible(False)

    def overlayDroppedData(self, indexList, tag):
        """Called when indexList is dropped on the DragOverlay on widgets
           associated with tag. Handles closing the DragOverlay and
           passing the parameters through the droppedDataSignal.
        """
        self.closeOverlay()
        self.propagateKillRogueOverlayMessage()
        self.droppedDataSignal.emit(indexList, tag)

    def dragLeaveEvent(self, event):
        """Close any DragOverlays when the drag leaves this widget."""
        self.closeOverlay()

    # We only accept events that are of our type, indicating
    # a dock window change
    def dragEnterEvent(self, event):
        """Accept dragged DataTree indices and optionally dragged
           Modules.
        """
        if self.acceptDocks and isinstance(event.mimeData(), ModuleFrameMime):
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
            super(ModuleFrame, self).dragEnterEvent(event)

    # If the event has a DockWidget in it, we check if it is our
    # parent or if we are its widget. If so, do nothing
    # If not, we add it to our dock and change its parent to us
    def dropEvent(self, event):
        """Accepts dragged DataTree indices and optionally dragged
           modules. When a module is dropped (already existing or from
           its name), this handles any creation and parenting needed.
           When indices are dropped, they are passed to droppData unless
           a DragOverlay is present in which case they are ignored.
        """
        # Dropped DockWidget
        if self.acceptDocks and isinstance(event.mimeData(), ModuleFrameMime):
            if event.mimeData().getDockWindow().parent() != self and \
               event.mimeData().getDockWindow().widget() != self:
                self.addDockWidget(Qt.BottomDockWidgetArea, \
                    event.mimeData().getDockWindow())
                event.mimeData().getDockWindow().widget().agent.changeParent(self.agent)
                event.mimeData().getDockWindow().widget().parent_frame = self
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
            new_mod = ModuleFrame.instantiate(mod_name, dock, self, mod_name)
            new_mod.agent.refreshSceneInformation()
            dock.setWidget(new_mod)
            self.addDockWidget(Qt.BottomDockWidgetArea, dock)
        # Dropped Attribute Data
        elif isinstance(event.mimeData(), DataIndexMime) \
            and not self.dragOverlay:
            # Note, because Qt will let drops fall through if unhandled,
            # we need to check if there's a DragOverlay and ignore if
            # there is.
            indexList = event.mimeData().getDataIndices()
            event.accept()
            self.propagateKillRogueOverlayMessage()
            self.droppedDataSignal.emit(indexList, None)
        else:
            self.propagateKillRogueOverlayMessage()
            super(ModuleFrame, self).dropEvent(event)


    def buildTabDialog(self):
        """Create the TabDialog associated with this ModuleFrame and
           add associated Tabs to it.

           Subclasses adding other Tabs should override this function
           and call super in order to get the Tabs associated with all
           ModuleFrames. Then the Subclasses may construct their own Tabs.
        """
        self.tab_dialog = TabDialog(self)
        self.tab_dialog.addTab(SceneTab(self.tab_dialog, self.agent),
            "Scene Policy")


    def mouseDoubleClickEvent(self, event):
        """Double-clicking launches the TabDialog if enabled in this
           module. Note that if you disable the TabDialog, the user
           won't have the ability to change the propagation effects
           of the Scene information, so the defaults for that module's
           Agent must be chosen wisely.

           Note this action constructs the TabDialog anew each time.
           This means the Tabs may also be re-created, allowing them
           to be passed the most current values from the ModuleFrame
           and ModuleAgent rather than having to keep the Tabs in
           synch at all times.
        """
        if self.enable_tab_dialog:
            self.buildTabDialog()
            self.tab_dialog.exec_()


class BFDockWidget(QDockWidget):
    """BFDockWidgets contain modules (and their child modules). This
       class sets all of our QDockWidget policies.

       This also attempts to make moving Modules between subtrees in
       Boxfish easier but that doesn't work currently.
    """

    def __init__(self, title, parent):
        """Construct the Boxfish DockWidget with given title and Qt
           GUI parent.
        """
        super(BFDockWidget, self).__init__(title, parent)

        self.setAttribute(Qt.WA_NoMousePropagation)
        self.setAcceptDrops(True)
        self.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.setFeatures(QDockWidget.DockWidgetClosable
            | QDockWidget.DockWidgetMovable)

    def findPosition(self):
        """Determines the absolute position of this DockWidget
           recursively.
        """
        # I have relative coords to add because I am a dockwidget
        x, y = self.parent().findPosition()
        return x + self.x(), y + self.y()

    def changeParent(self, new_parent):
        """Changes the parent of this DockWidget, thereby changing the
           location this DockWidget sits and where it behaves most
           naturally.
        """
        self.setParent(new_parent)

    # Attempts to reserve two modifiers for this subclass
    def mousePressEvent(self, e):
        if (e.buttons() != Qt.MidButton and
            e.modifiers() != Qt.ShiftModifier):
            super(BFDockWidget, self).mousePressEvent(e)

    # Attempts to have DockWidget be drag/droppable between DockWidgets
    # with modifier buttons. I haven't been able to do this with a
    # mouse button and even though the keyboard modifier works, there
    # has been some odd behavior with widgets momentarily jumping out
    # of their parent visually.
    def mouseMoveEvent(self, e):
        if (e.buttons() == Qt.MidButton): # dropAction Doesn't work :(
            drag = QDrag(self)
            drag.setMimeData(ModuleFrameMime(self))
            dropAction = drag.start(Qt.MoveAction)
        elif (e.modifiers() == Qt.ShiftModifier): # dropAction works here
            drag = QDrag(self)
            drag.setMimeData(ModuleFrameMime(self))
            dropAction = drag.start(Qt.MoveAction)
        else:
            super(BFDockWidget, self).mouseMoveEvent(e)


    def closeEvent(self, e):
        """Handle module close events."""
        self.widget().agent.delete()
        super(BFDockWidget, self).closeEvent(e)


class DragDockLabel(QLabel):
    """This creates a label that can be used for BFDockWidget
       Drag & Drop operations. This is the black bar found under
       the title bar of all DockWidgets that can be used to drag
       and drop the Modules.
    """

    def __init__(self, dock):
        """Construct a DragDockLabel for the given dock."""
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
        """On drag, create a ModuleFrameMime containing the dock that
           contains this label.
        """
        drag = QDrag(self)
        drag.setMimeData(ModuleFrameMime(self.dock))
        dropAction = drag.start(Qt.MoveAction)



class DragToolBar(QToolBar):
    """This creates a toolbar that can be used for BFDockWidget
       Drag & Drop operations to drag the containing DocKWidget.
    """

    def __init__(self, title, parent, dock):
        """Construct a DragToolBar with the given title and Qt parent and
           belonging to the given dock.
        """
        super(DragToolBar, self).__init__(title, parent)

        self.dock = dock

    def mousePressEvent(self, e):
        pass

    def mouseMoveEvent(self, e):
        """On drag, create a ModuleFrameMime containing the dock that
           contains this toolbar.
        """
        drag = QDrag(self)
        drag.setMimeData(ModuleFrameMime(self.dock))
        dropAction = drag.start(Qt.MoveAction)


class ModuleFrameMime(QMimeData):
    """This allows passing of the QDockWidget between windows
       during Drag & Drop.
    """

    def __init__(self, dock_window):
        """Construct a ModuleFrameMime containing the given BFDockWidget."""
        super(ModuleFrameMime, self).__init__()

        self.dock_window = dock_window

    def getDockWindow(self):
        """Returns the BFDockWidget associated with this Mime data."""
        return self.dock_window


class ModuleNameMime(QMimeData):
    """This is for passing module display_names during
       Drag & Drop operations.
    """

    def __init__(self, name):
        """Construct a ModuleNameMime containing the given module name."""
        super(ModuleNameMime, self).__init__()

        self.name = name

    def getName(self):
        """Return the contained module name."""
        return self.name


class TabDialog(QDialog):
    """This dialog contains tabs with options for everything related
       to the module. Inheriting modules can add their own tabs
       to this dialog by overriding buildTagDialog in ModuleFrame. They
       should all super in order to keep the original tabs.

       Example: a module might create a tab that determines what
       the default aggregation method is for dropped data
    """

    def __init__(self, parent, title = ""):
        """Construct a TabDialog with the ModuleFrame parent and the
           given title.
        """
        super(TabDialog, self).__init__(parent)

        self.setWindowTitle(title)
        self.tabs = QTabWidget(self)
        self.setModal(True)

        # Need a layout to get resizing to work
        layout = QGridLayout()
        layout.addWidget(self.tabs, 0, 0)
        self.setLayout(layout)

    def addTab(self, tab, name, index = 0):
        """Add the given tab to the TabDialog under the given name
           at the given index. The index 0 means the tab will be
           the active one when the TabDialog is raised.
        """
        viewArea = QScrollArea()
        viewArea.setWidget(tab)
        viewArea.setWidgetResizable(True)
        self.tabs.insertTab(index, viewArea, name)
        self.tabs.setCurrentIndex(0)


class SceneTab(QWidget): #FIXME I'm Ugly.
    """This widget is for changing the Scene propagation policies
       of the module.
    """

    def __init__(self, parent, agent):
        """Construct the SceneTab with the given parent (TabDialog) and
           ModuleAgent.
        """
        super(SceneTab, self).__init__(parent)

        self.agent = agent

        self.layout = QVBoxLayout()
        self.layout.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.buildHighlightGroupBox())
        self.layout.addItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildModuleGroupBox())
        self.layout.addItem(QSpacerItem(5,5))
        self.layout.addWidget(self.buildAttributeGroupBox())

        self.setLayout(self.layout)


    def buildHighlightGroupBox(self):
        """Layout/construct the highlight UI for this tab."""
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
        """Called when highlight propagtion is changed to update the
           Agent.
        """
        self.agent.propagate_highlights = self.highlights_propagate.isChecked()


    def applyHighlightsChanged(self):
        """Called when highlight application is changed to update the
           Agent.
        """
        self.agent.apply_highlights = self.applyHighlights.isChecked()


    def buildModuleGroupBox(self):
        """Layout/construct the ModuleScene UI for this tab."""
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
        """Called when ModuleScene propagtion is changed to update the
           Agent.
        """
        self.agent.propagate_module_scenes = self.module_propagate.isChecked()


    def moduleApplyChanged(self):
        """Called when ModuleScene application is changed to update the
           Agent.
        """
        self.agent.apply_module_scenes = self.module_applyScene.isChecked()


    def buildAttributeGroupBox(self):
        """Layout/construct the AttributeScene UI for this tab."""
        groupBox = QGroupBox("Attribute Policy (Colors)")
        layout = QVBoxLayout()

        # agent.propagate_attribute_scenes
        self.attr_propagate = QCheckBox("Propagate attribute scene "
            + "information (e.g. color maps) to other modules.")
        self.attr_propagate.setChecked(self.agent.propagate_attribute_scenes)
        self.attr_propagate.stateChanged.connect(self.attrPropagateChanged)
        # We only allow this change if the parent does not propagate
        if self.agent.parent().propagate_attribute_scenes:
            self.attr_propagate.setDisabled(True)

        # agent.apply_attribute_scenes
        self.attr_applyScene = QCheckBox("Apply attribute scene information "
            + "from other modules.")
        self.attr_applyScene.setChecked(self.agent.apply_attribute_scenes)
        self.attr_applyScene.stateChanged.connect(self.attrApplyChanged)

        layout.addWidget(self.attr_applyScene)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.attr_propagate)
        groupBox.setLayout(layout)
        return groupBox


    def attrPropagateChanged(self):
        """Called when AttributeScene propagtion is changed to update the
           Agent.
        """
        self.agent.propagate_attribute_scenes = self.attr_propagate.isChecked()


    def attrApplyChanged(self):
        """Called when AttributeScene application is changed to update the
           Agent.
        """
        self.agent.apply_attribute_scenes = self.attr_applyScene.isChecked()


class OverlayDialog(QDialog):
    """The OverlayDialog is a semitransparent window that is drawn over
       a module to allow the user to associate their drag/drop operations
       with a more specific concept.
    """

    def __init__(self, parent, widget):
        """Construct an OverlayDialog with the given Qt GUI parent and
           displaying the given widget.
        """
        super(OverlayDialog, self).__init__(parent, Qt.SplashScreen)

        self.setAcceptDrops(True)

        self.setAttribute(Qt.WA_TranslucentBackground)
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
        """Display this OverlayDialog int he correct positon."""
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
    """Creates a rounded rectangular translucent frame and accepts drops.
    """

    def __init__(self, parent):
        """Construct an OverlayFrame with the given Qt GUI parent."""
        super(OverlayFrame, self).__init__(parent)

        self.setVisible(False)
        self.setAcceptDrops(True)

    # Adapted from developer.nokia.com/Community/Wiki/Qt_rounded_rect_widget
    def paintEvent(self, event):
        """Display a translucent rounded rectangle."""
        roundness = 10
        rect = self.rect()
        bgcolor = self.palette().color(QPalette.Background)
        alpha_bgcolor = QColor(50, 50, 50, 150)
        #alpha_bgcolor = QColor(bgcolor.red(), bgcolor.green(),
        #    bgcolor.blue(), 150)

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

