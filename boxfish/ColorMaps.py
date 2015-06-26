import sys
import matplotlib.colors
import matplotlib.cm as cm

from PySide.QtCore import Slot,Signal,QObject,Qt
from PySide.QtGui import QWidget,QLabel,QPixmap,QLineEdit,QHBoxLayout,qRgba,\
    QImage,QVBoxLayout,QComboBox,QCheckBox,QSpacerItem,QIntValidator

from OpenGL.GL import *
from OpenGL.GL.glget import *
from boxfish.gl.glutils import *
from boxfish.gl.GLWidget import TextDraw
#from OpenGL.GLUT import glutStrokeCharacter, GLUT_STROKE_ROMAN

# maybe instead of separate we should use register_cmap()
boxfish_maps = dict()

#HOWTO Make another colormap
#For each colormap, there is a red, green and blue list
#Each element in the list is:
#(normalized value between 0 and 1, value between 0 and 1, the same value again)
#So (0.5, 1.0, 1.0) in the red list means "At normalized value 0.5, the red
# value of the color is 1.0 (=xFF)".
# Unspecified values will be interpolated between the given values

# Example 1
# Goes from purple to green
bdict = {'red':   ((0.0, 0.686,    0.686),
    (1.0, 0.5, 0.5)),
    'green': ((0.0, 0.55,    0.55),
    (1.0, 0.75,    0.75)),
    'blue':  ((0.0, 0.765,    0.765),
    (1.0, 0.482,    0.483))}
BFPuGrmap = matplotlib.colors.LinearSegmentedColormap('BFPuGrmap',bdict,256)
boxfish_maps['BFPuGr'] = BFPuGrmap

# Example 2
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

# Example 3
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

#   Collin's for VPA
#   Dark Blue [0.0] = (0, 70, 195), Light Blue [0.4] = (0, 175, 225), Orange [0.6] = (225, 150, 0), Red [1.0] = (255, 60, 0)
bdict = {'red':   ((0.0, 0.0, 0.0), 
    (0.4, 0.0, 0.0),
    (0.6, 225.0/255.0, 225.0/255.0),
    (1.0, 255.0/255.0, 255.0/255.0)),
    'green': ((0.0, 70.0/255.0, 70.0/255.0), 
    (0.4, 175.0/255.0, 175.0/255.0),
    (0.6, 150.0/255.0, 150.0/255.0),
    (1.0, 60.0/255.0, 60.0/255.0)),
    'blue':  ((0.0, 195.0/255.0, 195.0/255.0), 
    (0.4, 225.0/255.0, 225.0/255.0),
    (0.6, 0.0, 0.0),
    (1.0, 0.0, 0.0))}
BlGrOrRdmap = matplotlib.colors.LinearSegmentedColormap('BlGrOrRdmap',bdict,256)
boxfish_maps['BlGrOrRd'] = BlGrOrRdmap


# Rubik color map
# Note that we divide the first one between the beginning and the end so color
# cycling works
bdict = {'red': (
        (0.00000, 0.0, 0.0), # blueberry
        (0.03120, 0.0, 0.0), # blueberry
        (0.03125, 1.0, 1.0), # maraschino
        (0.09370, 1.0, 1.0), # maraschino
        (0.09375, 0.25, 0.25), # fern
        (0.15620, 0.25, 0.25), # fern
        (0.15625, 1.0, 1.0), # lemon
        (0.21870, 1.0, 1.0), # lemon
        (0.21875, 0.0, 0.0), # agua
        (0.28120, 0.0, 0.0), # agua
        (0.28125, 1.0, 1.0), # magenta
        (0.34370, 1.0, 1.0), # magenta
        (0.34375, 0.2, 0.2), # tungsten
        (0.40620, 0.2, 0.2), # tungsten
        (0.40625, 1.0, 1.0), # tangerine
        (0.46870, 1.0, 1.0), # tangerine
        (0.46875, 0.7, 0.7), # magnesium
        (0.53120, 0.7, 0.7), # magnesium
        (0.53125, 0.0, 0.0), # sea foam
        (0.59370, 0.0, 0.0), # sea foam
        (0.59375, 0.5, 0.5), # mocha
        (0.65620, 0.5, 0.5), # mocha
        (0.65625, 0.5, 0.5), # grape
        (0.71870, 0.5, 0.5), # grape
        (0.71875, 0.0, 0.0), # turquoise
        (0.78120, 0.0, 0.0), # turquoise
        (0.78125, 0.0, 0.0), # spring
        (0.84370, 0.0, 0.0), # spring
        (0.84375, 1.0, 1.0), # salmon
        (0.90620, 1.0, 1.0), # salmon
        (0.90625, 0.5, 0.5), # aspargus
        (0.96875, 0.5, 0.5), # aspargus
        (0.96875, 0.0, 0.0), # blueberry (other half)
        (1.0, 0.0, 0.0)), # blueberry (other half)
    'green': (
        (0.00000, 0.0, 0.0), # blueberry
        (0.03120, 0.0, 0.0), # blueberry
        (0.03125, 0.0, 0.0), # maraschino
        (0.09370, 0.0, 0.0), # maraschino
        (0.09375, 0.5, 0.5), # fern
        (0.15620, 0.5, 0.5), # fern
        (0.15625, 1.0, 1.0), # lemon
        (0.21870, 1.0, 1.0), # lemon
        (0.21875, 0.5, 0.5), # agua
        (0.28120, 0.5, 0.5), # agua
        (0.28125, 0.0, 0.0), # magenta
        (0.34370, 0.0, 0.0), # magenta
        (0.34375, 0.2, 0.2), # tungsten
        (0.40620, 0.2, 0.2), # tungsten
        (0.40625, 0.5, 0.5), # tangerine
        (0.46870, 0.5, 0.5), # tangerine
        (0.46875, 0.7, 0.7), # magnesium
        (0.53120, 0.7, 0.7), # magnesium
        (0.53125, 1.0, 1.0), # sea foam
        (0.59370, 1.0, 1.0), # sea foam
        (0.59375, 0.25, 0.25), # mocha
        (0.65620, 0.25, 0.25), # mocha
        (0.65625, 0.0, 0.0), # grape
        (0.71870, 0.0, 0.0), # grape
        (0.71875, 1.0, 1.0), # turquoise
        (0.78120, 1.0, 1.0), # turquoise
        (0.78125, 1.0, 1.0), # spring
        (0.84370, 1.0, 1.0), # spring
        (0.84375, 0.4, 0.4), # salmon
        (0.90620, 0.4, 0.4), # salmon
        (0.90625, 0.5, 0.5), # aspargus
        (0.96870, 0.5, 0.5), # aspargus
        (0.96875, 0.0, 0.0), # blueberry (other half)
        (1.0, 0.0, 0.0)), # blueberry (other half)
    'blue': (
        (0.00000, 1.0, 1.0), # blueberry
        (0.03120, 1.0, 1.0), # blueberry
        (0.03125, 0.0, 0.0), # maraschino
        (0.09370, 0.0, 0.0), # maraschino
        (0.09375, 0.0, 0.0), # fern
        (0.15620, 0.0, 0.0), # fern
        (0.15625, 0.0, 0.0), # lemon
        (0.21870, 0.0, 0.0), # lemon
        (0.21875, 1.0, 1.0), # agua
        (0.28120, 1.0, 1.0), # agua
        (0.28125, 1.0, 1.0), # magenta
        (0.34370, 1.0, 1.0), # magenta
        (0.34375, 0.2, 0.2), # tungsten
        (0.40620, 0.2, 0.2), # tungsten
        (0.40625, 0.0, 0.0), # tangerine
        (0.46870, 0.0, 0.0), # tangerine
        (0.46875, 0.7, 0.7), # magnesium
        (0.53120, 0.7, 0.7), # magnesium
        (0.53125, 0.5, 0.5), # sea foam
        (0.59370, 0.5, 0.5), # sea foam
        (0.59375, 0.0, 0.0), # mocha
        (0.65620, 0.0, 0.0), # mocha
        (0.65625, 1.0, 1.0), # grape
        (0.71870, 1.0, 1.0), # grape
        (0.71875, 1.0, 1.0), # turquoise
        (0.78120, 1.0, 1.0), # turquoise
        (0.78125, 0.0, 0.0), # spring
        (0.84370, 0.0, 0.0), # spring
        (0.84375, 0.4, 0.4), # salmon
        (0.90620, 0.4, 0.4), # salmon
        (0.90625, 0.0, 0.0), # aspargus
        (0.96870, 0.0, 0.0), # aspargus
        (0.96875, 1.0, 1.0), # blueberry (other half)
        (1.0, 1.0, 1.0)) # blueberry (other half)
    }
Rubikmap = matplotlib.colors.LinearSegmentedColormap('Rubik',bdict,256)
boxfish_maps['Rubik'] = Rubikmap


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

    def __init__(self, base_color_map = 'copper',
        color_step = 0, step_size = 0.1):
        """Create a ColorMap object.

           base_color_map
               the matplotlib colormap this object is based around

           color_step
               the number of different values for color cycling. If this is
               zero, color cycling is off

           step_size
               the default value separating two neighboring elements being
               color cycled.
        """
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
        """The value separating two neighboring elements when color cycling
           is on.
        """
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

    def getColor(self, value, preempt_range = 0):
        """Gets the color associated with the given value.

           preempt_range
               When color cycling is on and preempt_range is not zero,
               preempt_range is used to calculate the spaccin between
               colors rather than step_size. Note that preempt_range is
               the entire data range to scale the [0, 1] value by, while
               step_size will divide the value.
        """
        if self.color_step == 0:
            return self.color_map(value)
        elif preempt_range != 0: # Fix until I change the way ranges/dataModel is handled AGAIN.
            stepped_value = round(value * preempt_range) % self.color_step
            return self.color_map(1.0 / self.color_step * stepped_value)
        else:
            stepped_value = round(value / self.step_size) % self.color_step
            return self.color_map(1.0 / self.color_step * stepped_value)

class ColorBarImage(QImage):
    """QImage representing the color bar, will incorporate cycling."""

    def __init__(self, color_map, width, height):
        """Creates a QImage of width by height from the given colormap."""
        super(ColorBarImage, self).__init__(width, height,
            QImage.Format_ARGB32_Premultiplied)

        # Qborder - this is black all the way around
        # The commented out parts were for white in one corner
        # but didn't come out nicely
        for w in range(width):
            #self.setPixel(w, 0, qRgba(255, 255, 255, 255))
            self.setPixel(w, 0, qRgba(0, 0, 0, 255))
            self.setPixel(w, height - 1, qRgba(0, 0, 0, 255))
        for h in range(height):
            self.setPixel(0, h, qRgba(0, 0, 0, 255))
            self.setPixel(width - 1, h, qRgba(0, 0, 0, 0))
            #self.setPixel(width - 1, h, qRgba(255, 255, 255, 255))

        # Draws the color map lineby line
        pixel_value = 1.0 / width
        for w in range(width-2):
            color_np = color_map(w * pixel_value)
            color_rgba = qRgba(*[round(255 * x) for x in color_np])
            for h in range(height-2):
                self.setPixel(w + 1, h + 1, color_rgba)


# TODO: Make the selector much slicker
class ColorMapWidget(QWidget):
    """Interface for changing ColorMap information. It shows the current
       color map selection, a selector for other colormaps, and the option
       to cycle the color map by any number of ordinal values.

       This widget was designed for use with the tab dialog. It can be used by
       itself or it can be used as part of a bigger color tab.

       Changes to this widget are emitted via a changeSignal as a ColorMap
       object and this widget's tag.
    """

    changeSignal = Signal(ColorMap, str)

    def __init__(self, parent, initial_map, tag):
        """Creates a ColorMap widget.

           parent
               The Qt parent of this widget.

           initial_map
               The colormap set on creation.

           tag
               A name for this widget, will be emitted on change.
        """
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
        """Builds the portion of this widget for color map selection."""
        widget = QWidget()
        layout = QHBoxLayout()

        label = QLabel(self.color_map_label)
        self.colorbar = QLabel(self)
        self.colorbar.setPixmap(QPixmap.fromImage(ColorBarImage(
            self.color_map, 180, 15)))

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
        """Handles a selection of a different colormap.

           ind
               Index of the selected colormap.
        """
        indx = self.mapCombo.currentIndex()
        self.color_map_name = map_names[indx]
        self.color_map = getMap(self.color_map_name)
        self.colorbar.setPixmap(QPixmap.fromImage(ColorBarImage(
            self.color_map, 180, 12)))
        self.changeSignal.emit(ColorMap(self.color_map_name, self.color_step,
            self.step_size), self.tag)

    def buildColorStepsControl(self):
        """Builds the portion of this widget for color cycling options."""
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
        """Handles a change in the state of the color cycling for this
           colormap.
        """
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


def gl_to_rgb(color):
    """Switch from gl colors to rgb colors."""
    if color is None:
        return [0, 0, 0, 0]

    return [int(255 * x) for x in color]

def rgbStylesheetString(color):
    """Creates a stylesheet style string out of an rgb color."""
    return "rgb(" + str(color[0]) + "," +  str(color[1]) + ","\
        + str(color[2]) + ")"


def drawGLColorBar(colors, bar_x, bar_y, bar_width, bar_height, label = "", total_height = 0):
    """Draws a single colorbar at bar_x, bar_y with width bar_width
       and height bar_height.

       colors
           A list of sampled 11 sampled colors spanning the colormap.
    """
    setup_overlay2D(bar_x, bar_y, bar_width, bar_height + 12)

    with glMatrix():
        glLoadIdentity()
        glTranslatef(bar_x, bar_y, 0)

        segment_size = int(float(bar_height) / 10.0)

        for i in range(10):

            with glMatrix():
                glTranslatef(0, i*segment_size, 0)
                with glSection(GL_QUADS):
                    glColor3f(colors[i][0], colors[i][1], colors[i][2])
                    glVertex3f(0, 0, 0)
                    glVertex3f(bar_width, 0, 0)
                    glColor3f(colors[i+1][0], colors[i+1][1],
                        colors[i+1][2])
                    glVertex3f(bar_width, segment_size, 0)
                    glVertex3f(0, segment_size, 0)


        # black box around gradient
        prev_lineWidth = glGetFloatv(GL_LINE_WIDTH)
        glLineWidth(1.0)
        glColor3f(0.0, 0.0, 0.0)
        with glMatrix():
            with glSection(GL_LINES):
                glVertex3f(0.01, 0.01, 0.01)
                glVertex3f(bar_width, 0.01, 0.01)
                glVertex3f(bar_width, 0.01, 0.01)
                glVertex3f(bar_width, bar_height, 0.01)
                glVertex3f(bar_width, bar_height, 0.01)
                glVertex3f(0.01, bar_height, 0.01)
                glVertex3f(0.01, bar_height, 0.01)
                glVertex3f(0.01, 0.01, 0.01)

        # TODO: Make this whole section much less magical
        #default_text_height = 152.38
        #scale_factor = 1.0 / default_text_height * segment_size
        #scale_factor = 0.08
        #if len(label) > 0:
        #    with glMatrix():
        #        glTranslatef(7, bar_height + 3, 0.2)
        #        glScalef(scale_factor, scale_factor, scale_factor)
        #        for c in label:
        #            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(c))
        #glLineWidth(prev_lineWidth)

        if len(label) > 0:
            return TextDraw(label, bar_x + 6, total_height - (bar_y + bar_height + 3))
