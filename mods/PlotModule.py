from ModuleAgent import *
from ModuleView import *

import sys
import matplotlib
import numpy as np
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4']='PySide'

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import \
    FigureCanvasQTAgg as FigureCanvas
#from matplotlib.backends.backend_qt4agg import \
#    NavigationToolbar2QT as NavigationToolbar

from PySide.QtCore import *
from PySide.QtGui import *

class PlotterAgent(ModuleAgent):

    def __init__(self, parent, datatree):
        super(PlotterAgent, self).__init__(parent, datatree)

        self.x_columns = list()
        self.y_columns = list()
        self.addRequest("x")
        self.addRequest("y")

    def setXData(self, indexList):
        self.requestAddIndices("x", indexList)

    def setYData(self, indexList):
        self.requestAddIndices("y", indexList)

@Module("Plotter", PlotterAgent)
class PlotterView(ModuleView):

    def __init__(self, parent, parent_view = None, title = None):
        super(PlotterView, self).__init__(parent, parent_view, title)

        self.selected = []

    def createView(self):
        view = QWidget()
        self.plotter = PlotterWidget(self)

        self.viewarea = QScrollArea()
        self.viewarea.setWidget(self.plotter)
        self.viewarea.setWidgetResizable(True)
        self.viewarea.setMinimumSize(300,300)

        # TODO: Use panels to make the attrs flush with the first label
        # and/or change this entirely so we drop into parts of the
        # MPL window.
        self.xlabel = QLabel("X: ")
        self.ylabel = QLabel("Y: ")
        self.xattrs = QLabel("")
        self.yattrs = QLabel("")

        self.xattrs.setWordWrap(True)
        self.yattrs.setWordWrap(True)

        layout = QGridLayout()
        layout.addWidget(self.xlabel, 0, 0, 1, 1)
        layout.addWidget(self.xattrs, 0, 1, 1, 1)
        layout.addWidget(self.ylabel, 1, 0, 1, 1)
        layout.addWidget(self.yattrs, 1, 1, 1, 1)
        layout.addWidget(self.viewarea, 2, 0, 1, 2)
        layout.setRowStretch(2, 10)
        layout.setContentsMargins(0, 0, 0, 0)
        view.setLayout(layout)

        return view

    def droppedData(self, indexList):
        # We assume generally dropped data is Y data
        self.droppedYData(indexList)

    def droppedXData(self, indexList):
        self.agent.setXData(indexList)
        self.xattrs.setText(self.buildAttributeString(indexList))

    def droppedYData(self, indexList):
        self.agent.setYData(indexList)
        self.yattrs.setText(self.buildAttributeString(indexList))

    def buildAttributeString(self, indexList):
        mytext = ""
        for index in indexList:
            mytext = mytext + self.agent.datatree.getItem(index).name + ", "
        return mytext[:len(mytext) - 2]

    def dragEnterEvent(self, event):
        if isinstance(event.mimeData(), DataIndexMime):
            # TODO: Depending on whether it will be x or y data where it
            # is, boldify that axis label. May need dragMoveEvent for this
            event.accept()
        else:
            super(PlotterView, self).dragEnterEvent(event)

    def dropEvent(self, event):
        if isinstance(event.mimeData(), DataIndexMime):
            # if this point is below the bottom of the axes y coordinate
            # transformed to display coords and inverted (because
            # matplotlib starts at bottom left), then it is xdata
            # otherwise it is ydata
            
            # Event position wrt widget
            drop_point = event.pos() 

            # Axes position wrt plotter coords
            axes_corner = self.plotter.axes.transAxes.transform((0,0))

            event.accept()
            if drop_point.x() > axes_corner[0] \
                and self.height() - drop_point.y() < axes_corner[1]:
                self.droppedXData(event.mimeData().getDataIndices())
            else:
                self.droppedYData(event.mimeData().getDataIndices())
        else:
            super(PlotterView, self).dropEvent(event)


class PlotterWidget(QWidget):

    def __init__(self, parent=None):
        super(PlotterWidget, self).__init__(parent)

        self.fig = Figure(figsize=(300,300), dpi=72, facecolor=(1,1,1), \
            edgecolor=(0,0,0))

        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.canvas.mpl_connect('pick_event', self.onPick)
        
        # Toolbar Doesn't get along with Kate's MPL at the moment so the
        # mpl_connects will handle that for the moment
        #self.toolbar = NavigationToolbar(self.canvas, self.canvas)
        self.canvas.mpl_connect('motion_notify_event', self.onMouseMotion)
        self.canvas.mpl_connect('scroll_event', self.onScroll)
        self.canvas.mpl_connect('button_press_event', self.onMouseButtonPress)
        self.lastX = 0
        self.lastY = 0
        
        self.axes = self.fig.add_subplot(111)

        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.setContentsMargins(0,0,0,0)
        self.setLayout(vbox)

        # Test
        self.axes.plot([1,2,3,4,5],[1,2,3,4,5], 'ob')
        self.axes.set_title("Drag attributes to change graph.")
        self.axes.set_xlabel("Drag here to set x axis.")
        self.axes.set_ylabel("Drag here to set y axis.")
        print "Drawing"
        self.canvas.draw() # Why does this take so long on 4726 iMac? 


    def plotData(self, ids, vals):
        self.axes.clear()
        self.axes.plot(ids, vals, 'ob', picker=3)
        if np.alen(self.selected) > 0:
            self.highlighted = self.axes.plot(ids[self.selected[0]], \
                vals[self.selcted[0]], 'or')[0]
        self.canvas.draw()

    def onPick(self, event):
        old_selection = list(self.selected)
        self.selected = np.array(event.ind)

        mouseevent = event.mouseevent
        xt = self.ids[self.selected]
        yt = self.traffic[self.selected]
        d = np.array((xt - mouseevent.xdata)**2 + (yt-mouseevent.ydata)**2)
        thepoint = self.selected[d.argmin()]
        self.selected = []
        self.selected.append(thepoint)

        if old_selection == self.selected and old_selection != []:
            self.selected = []
            # HIGHLIGHT_CHANGE
            # alert agent about this - need SceneGraph done

        self.plotData(self.ids, self.traffic, True)

        if self.selected != []:
            # HIGHLIGHT_CHANGE
            # alert agent about this -- need SceneGraph done
            pass



# ---------------------- NAVIGATION CONTROLS ---------------------------

    # Mouse movement (with or w/o button press) handling
    def onMouseMotion(self, event):
        if event.button == 1:
            xmotion = self.lastX - event.x
            ymotion = self.lastY - event.y
            self.lastX = event.x
            self.lastY = event.y
            figsize = min(self.fig.get_figwidth(), self.fig.get_figheight())
            xmin, xmax = self.calcTranslate(self.axes.get_xlim(),
                xmotion, figsize)
            ymin, ymax = self.calcTranslate(self.axes.get_ylim(),
                ymotion, figsize)
            self.axes.set_xlim(xmin, xmax)
            self.axes.set_ylim(ymin, ymax)
            self.canvas.draw()

    # Calculates the translate required by the drag for a single dimension
    # dtuple - the current limits in some dimension
    # motion - the movement of the drag in pixels in that dimension
    # figsize - estimate of the size of the figure 
    # Note: the dtuple is in data coordinates, the motion is in pixels,
    # we estimate how much motion there is based on the figsize and then
    # scale it appropriately to the data coordinates to get the proper
    # offset in figure limits.
    def calcTranslate(self, dtuple, motion, figsize):
        dmin, dmax = dtuple
        drange = dmax - dmin
        dots = self.fig.dpi * figsize
        offset = float(motion * drange) / float(dots) 
        newmin = dmin + offset
        newmax = dmax + offset
        return tuple([newmin, newmax])

    # When the user clicks the left mouse button, that is the start of 
    # their drag event, so we set the last-coordinates that are used to 
    # calculate drag
    def onMouseButtonPress(self, event):
        if event.button == 1:
            self.lastX = event.x
            self.lastY = event.y

    # On mouse wheel scrool, we zoom 
    def onScroll(self, event):
        zoom = event.step
        xmin, xmax = self.calcZoom(self.axes.get_xlim(), 1. + zoom*0.05)
        ymin, ymax = self.calcZoom(self.axes.get_ylim(), 1. + zoom*0.05)
        self.axes.set_xlim(xmin, xmax)
        self.axes.set_ylim(ymin, ymax)
        self.canvas.draw()

    # Calculates the zoom required by the wheel scroll for a single dimension
    # dtuple - the current limits in some dimension
    # scale - fraction to increase/decrease the image size
    # This does a zoom by scaling the limits in that direction appropriately
    def calcZoom(self, dtuple, scale):
        dmin, dmax = dtuple
        drange = dmax - dmin
        dlen = 0.5*drange
        dcenter = dlen + dmin
        newmin = dcenter - dlen*scale
        newmax = dcenter + dlen*scale
        return tuple([newmin, newmax])

            
