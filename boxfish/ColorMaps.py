import sys
import matplotlib.colors
import matplotlib.cm as cm

from PySide.QtCore import Slot,Signal,QObject,Qt
from PySide.QtGui import QWidget,QLabel,QPixmap,QLineEdit,QHBoxLayout,qRgba,\
    QImage,QVBoxLayout,QComboBox,QCheckBox,QSpacerItem,QIntValidator

# maybe instead of separate we should use register_cmap()
boxfish_maps = dict()

#HOWTO Make another colormap
#For each colormap, there is a red, green and blue list
#Each element in the list is:
#(normalized value between 0 and 1, value between 0 and 1, the same value again)
#So (0.5, 1.0, 1.0) in the red list means "At normalized value 0.5, the red
# value of the color is 1.0 (=xFF)".
# Unspecified values will be interpolated between the given values

# Goes from purple to green
bdict = {'red':   ((0.0, 0.686,    0.686),
    (1.0, 0.5, 0.5)),
    'green': ((0.0, 0.55,    0.55),
    (1.0, 0.75,    0.75)),
    'blue':  ((0.0, 0.765,    0.765),
    (1.0, 0.482,    0.483))}
BFPuGrmap = matplotlib.colors.LinearSegmentedColormap('BFPuGrmap',bdict,256)
boxfish_maps['BFPuGr'] = BFPuGrmap

# Goes from blue to red with yellow in the middle
bdict = {'red':   ((0.0, 145.0/255.0,    145.0/255.0),
    (0.5, 1.0, 1.0),
    (1.0, 252.0/255.0, 252.0/255.0)),
    'green': ((0.0, 191.0/255.0, 191.0/255.0),
    (0.5, 1.0, 1.0),
    (1.0, 141.0/255.0,  141.0/255.0)),
    'blue':  ((0.0, 219.0/255.0,  219.0/255.0),
    (0.5, 191.0/255.0, 191.0/255.0),
    (1.0, 89.0/255.0, 89.0/255.0))}
BFBlYeRdmap = matplotlib.colors.LinearSegmentedColormap('BFBlYeRdmap',bdict,256)
boxfish_maps['BFBlYeRd'] = BFBlYeRdmap

# Blue, Red with grey in the middle
bdict = {'red':   ((0.0, 0.0,    0.0),
    (0.5, 0.83, 0.83),
    (1.0, 1.0, 1.0)),
    'green': ((0.0, 0.0, 0.0),
    (0.5, 0.83, 0.83),
    (1.0, 0.0,  0.0)),
    'blue':  ((0.0, 1.0,  1.0),
    (0.5, 0.83, 0.83),
    (1.0, 0.0, 0.0))}
BFBlGyRdmap = matplotlib.colors.LinearSegmentedColormap('BFBlGyRdmap',bdict,256)
boxfish_maps['BFBlGyRd'] = BFBlGyRdmap

def hasMap(colormap):
    """Returns True if the given colormap String is found in our list
       of custom colormaps.
    """
    return colormap in boxfish_maps

def getMap(colormap):
    """Returns the matplotlib colormap object associated with the given
       name parameter. It searches both the custom colormaps and the
       matplotlib colormaps.
    """
    if hasMap(colormap):
        return boxfish_maps[colormap]
    else:
        return cm.get_cmap(colormap)

map_names = []
for mpl_map in cm.datad:
    map_names.append(mpl_map)
map_names.extend(boxfish_maps.keys())
map_names.sort()

class ColorMap(object):
    """This class wraps colormaps for extended options on how colors are
       computed from the existing colormaps.

       Note that all colormaps in here are normalized on [0.0, 1.0].
    """

    def __init__(self, base_color_map = 'jet',
        color_step = 0, step_size = 0.1):
        super(ColorMap, self).__init__()
        self.color_map = getMap(base_color_map)
        self.color_map_name = base_color_map

        # If color_step is not 0, we sample the color bar at each
        # of the n steps and assign all values as one of those steps,
        # modding by the step_size
        self.color_step = color_step
        self._step_size = step_size

    @property
    def step_size(self):
        return self._step_size

    @step_size.setter
    def step_size(self, size):
        if size <= sys.float_info.epsilon:
            self._step_size = 1
        else:
            self._step_size = size

    def __eq__(self, other):
        if self.color_map_name != other.color_map_name:
            return False
        if self.color_step != other.color_step:
            return False
        if self.step_size != other.step_size:
            return False

        return True

    def __ne__(self, other):
        return not self == other

    def copy(self):
        return ColorMap(self.color_map_name, self.color_step, self.step_size)

    def getColor(self, value):
        if self.color_step == 0:
            return self.color_map(value)
        else:
            stepped_value = round(value / self.step_size) % self.color_step
            return self.color_map(1.0 / self.color_step * stepped_value)

class ColorBarImage(QImage):
    """Pixmap representing the color bar."""

    def __init__(self, color_map, width, height):
        super(ColorBarImage, self).__init__(width, height,
            QImage.Format_ARGB32_Premultiplied)

        # QFrame-like border
        for w in range(width):
            self.setPixel(w, 0, qRgba(255, 255, 255, 255))
            self.setPixel(w, height - 1, qRgba(0, 0, 0, 255))
        for h in range(height):
            self.setPixel(0, h, qRgba(0, 0, 0, 255))
            self.setPixel(width - 1, h, qRgba(255, 255, 255, 255))

        pixel_value = 1.0 / width
        for w in range(width-2):
            color_np = color_map(w * pixel_value)
            color_rgba = qRgba(*[round(255 * x) for x in color_np])
            for h in range(height-2):
                self.setPixel(w + 1, h + 1, color_rgba)


class ColorMapWidget(QWidget):
    """Interface for changing ColorMap information.

       This widget was designed for use with the tab dialog. It can be used by
       itself or it can be used as part of a bigger color tab.
    """

    changeSignal = Signal(ColorMap, str)

    def __init__(self, parent, initial_map, tag):
        super(ColorMapWidget, self).__init__(parent)
        self.color_map = initial_map.color_map
        self.color_map_name = initial_map.color_map_name
        self.color_step = initial_map.color_step
        self.step_size = initial_map.step_size
        self.tag = tag

        self.color_map_label = "Color Map"
        self.color_step_label = "Cycle Color Map"
        self.number_steps_label = "Colors"

        self.color_step_tooltip = "Use the given number of evenly spaced " \
            + " colors from the map and assign to discrete values in cycled " \
            + " sequence."

        layout = QVBoxLayout()

        layout.addWidget(self.buildColorBarControl())
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.buildColorStepsControl())

        self.setLayout(layout)

    def buildColorBarControl(self):
        widget = QWidget()
        layout = QHBoxLayout()

        label = QLabel(self.color_map_label)
        self.colorbar = QLabel(self)
        self.colorbar.setPixmap(QPixmap.fromImage(ColorBarImage(
            self.color_map, 180, 12)))

        self.mapCombo = QComboBox(self)
        self.mapCombo.addItems(map_names)
        self.mapCombo.setCurrentIndex(map_names.index(self.color_map_name))
        self.mapCombo.currentIndexChanged.connect(self.colorbarChange)

        layout.addWidget(label)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.mapCombo)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.colorbar)

        widget.setLayout(layout)
        return widget

    @Slot(int)
    def colorbarChange(self, ind):
        indx = self.mapCombo.currentIndex()
        self.color_map_name = map_names[indx]
        self.color_map = getMap(self.color_map_name)
        self.colorbar.setPixmap(QPixmap.fromImage(ColorBarImage(
            self.color_map, 180, 12)))
        self.changeSignal.emit(ColorMap(self.color_map_name, self.color_step,
            self.step_size), self.tag)

    def buildColorStepsControl(self):
        widget = QWidget()
        layout = QHBoxLayout()

        self.stepBox = QCheckBox(self.color_step_label)
        self.stepBox.stateChanged.connect(self.colorstepsChange)

        self.stepEdit = QLineEdit("8", self)
        # Setting max to sys.maxint in the validator causes an overflow! D:
        self.stepEdit.setValidator(QIntValidator(1, 65536, self.stepEdit))
        self.stepEdit.setEnabled(False)
        self.stepEdit.editingFinished.connect(self.colorstepsChange)

        if self.color_step > 0:
            self.stepBox.setCheckState(Qt.Checked)
            self.stepEdit.setEnabled(True)

        layout.addWidget(self.stepBox)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(QLabel("with"))
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(self.stepEdit)
        layout.addItem(QSpacerItem(5,5))
        layout.addWidget(QLabel(self.number_steps_label))

        widget.setLayout(layout)
        return widget


    def colorstepsChange(self):
        if self.stepBox.checkState() == Qt.Checked:
            self.stepEdit.setEnabled(True)
            self.color_step = int(self.stepEdit.text())
            self.changeSignal.emit(ColorMap(self.color_map_name,
                self.color_step, self.step_size), self.tag)
        else:
            self.stepEdit.setEnabled(False)
            self.color_step = 0
            self.changeSignal.emit(ColorMap(self.color_map_name,
                self.color_step, self.step_size), self.tag)
