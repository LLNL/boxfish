from PySide.QtCore import Slot,Signal,QObject,QMimeData,Qt,QSize,QRect,\
    QPoint
from PySide.QtGui import QWidget,QToolBar,QLabel,QDrag,QPixmap,QLineEdit,\
    QColor,QHBoxLayout,QVBoxLayout,QFontMetrics,QPainter,QImage,QFont,\
    QFrame,qRgba
from DataModel import DataIndexMime

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
        """On drag, create a ModuleViewMime containing the dock that
           contains this label.
        """
        drag = QDrag(self)
        drag.setMimeData(ModuleViewMime(self.dock))
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
        """On drag, create a ModuleViewMime containing the dock that
           contains this toolbar.
        """
        drag = QDrag(self)
        drag.setMimeData(ModuleViewMime(self.dock))
        dropAction = drag.start(Qt.MoveAction)


class DragTextLabel(QLabel):
    """This creates a label that can be used for text toolbox
       Drag & Drop operations.
    """

    def __init__(self, text, size = 0):
        """Construct a DragTextLabel with the given text. If size is
           positive, the label will be forced to a width representing
           size characters in the default font.
        """
        super(DragTextLabel,self).__init__(text)

        self.text = text
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.setToolTip("Drag me.")

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)

        if size > 0:
            size_sample = 'M' * size
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
        """Creates a QDrag object with a LabelTextMime containing this
           label's text.
        """
        drag = QDrag(self)
        drag.setMimeData(LabelTextMime(self.text))
        drag.setPixmap(QPixmap.fromImage(self.createPixmap()))
        dropAction = drag.start(Qt.MoveAction)

    def createPixmap(self):
        """Creates the pixmap shown when this label is dragged."""
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
        """Constructs a LabelTextMime containing the given text."""
        super(LabelTextMime, self).__init__()

        self.text = text

    def getText(self):
        """Returns the text contained in this LabelTextMime."""
        return self.text


class DropTextLabel(QLabel):
    """This creates a label that accepts LabelTextMime Drops.
    """

    def __init__(self, text, size = 0):
        """Construct a DropTextLabel with the given text. If size is
           positive, the label will be forced to a width representing
           size characters in the default font.
        """
        super(DropTextLabel, self).__init__(text)

        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

        # FACTORME
        if size > 0:
            size_sample = 'M' * size
            font_metric = QFontMetrics(QFont())
            two_size = font_metric.size(Qt.TextSingleLine, size_sample)
            max_size = max([two_size.width(), two_size.height()]) + 4
            self.setMaximumHeight(max_size)
            self.setMinimumHeight(max_size)
            self.setMaximumWidth(max_size)
            self.setMinimumWidth(max_size)

    def dragEnterEvent(self, e):
        """Accept LabelTextMime data."""
        if isinstance(e.mimeData(), LabelTextMime):
            e.accept()
        else:
            super(DropTextLabel, self).dragEnterEvent(e)

    def dropEvent(self, e):
        """Accept LabelTextMime data and assume its contained text."""
        if isinstance(e.mimeData(), LabelTextMime):
            self.setText(e.mimeData().getText())
        else:
            super(DropTextLabel, self).dropEvent(e)



class DropLineEdit(QLineEdit):
    """This creates a LineEdit (textfield) for datatree drop operations.
    """

    def __init__(self, parent, datatree, initial_text = "", completer = None):
        """Construct a DropLineEdit with Qt GUI parent, initial_text, and
           given completer. This requires a reference to the Boxfish DataTree
           to interpret dragged indices.
        """
        super(DropLineEdit, self).__init__(initial_text, parent)

        self.datatree = datatree
        if completer:
            self.setCompleter(completer)

    def dragEnterEvent(self, e):
        """Accept DataIndexMime data."""
        if isinstance(e.mimeData(), DataIndexMime):
            e.accept()
        else:
            super(DropLineEdit, self).dragEnterEvent(e)

    def dropEvent(self, e):
        """Accept DataIndexMime data and set the DropLineEdit text to the
           last DataTree item name in the DataIndexMime's index list.
        """
        if isinstance(e.mimeData(), DataIndexMime):
            indices = e.mimeData().getDataIndices()
            for index in indices:
                self.setText(self.datatree.getItem(index).name)
        else:
            super(DropLineEdit, self).dropEvent(e)


class DropPanel(QWidget):
    """A widget that accepts datatree index drop operations and passes
       them to a handnler function. It displays a single string and
       optionally a QIcon.
    """

    def __init__(self, tag, text, parent, handler, icon = None):
        """Constructs a DropPanel

           tag
               A string associated with this DropPanel

           text
               The text displayed on this DropPanel

           parent
               The Qt GUI parent of this panel

           handler
               The datatree index list and tag will be passed to this
               function.

           icon
               Optional QIcon to display on this panel.
        """
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
        """Accepts DataIndexMime data."""
        if isinstance(event.mimeData(), DataIndexMime):
            event.accept()
        else:
            super(DropPanel, self).dragEnterEvent(event)

    def dragLeaveEvent(self, event):
        super(DropPanel, self).dragLeaveEvent(event)

    def dropEvent(self, event):
        """Accepts DataIndexMime data and passes the contained index
           list to the handler function.
        """
        if isinstance(event.mimeData(), DataIndexMime):
            indexList = event.mimeData().getDataIndices()
            event.accept()
            self.handler(indexList, self.tag)
        else:
            super(DropPanel, self).dropEvent(event)
