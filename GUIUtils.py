from PySide.QtCore import Slot,Signal,QObject,QMimeData,Qt,QSize,QRect,\
    QPoint
from PySide.QtGui import QWidget,QToolBar,QLabel,QDrag,QPixmap,QLineEdit,\
    QColor,QHBoxLayout,QVBoxLayout,QFontMetrics,QPainter,QImage,QFont,\
    QFrame,qRgba
from DataModel import DataIndexMime

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
