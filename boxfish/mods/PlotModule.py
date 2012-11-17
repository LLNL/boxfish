import sys
import matplotlib
import numpy as np
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4']='PySide'

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import \
    FigureCanvasQTAgg as FigureCanvas

from PySide.QtCore import *
from PySide.QtGui import *

from boxfish.ModuleAgent import *
from boxfish.ModuleFrame import *


class PlotterAgent(ModuleAgent):
    """This module does standard plotting via matplotlib."""

    plotUpdateSignal = Signal(list, list, list) # ids, x, y
    highlightUpdateSignal = Signal(list)

    def __init__(self, parent, datatree):
        """Creates the PlotterAgent."""
        super(PlotterAgent, self).__init__(parent, datatree)

        self.table = None
        self.addRequest("x")
        self.addRequest("y")
        self.requestUpdatedSignal.connect(self.presentData)

        self.highlightSceneChangeSignal.connect(self.processHighlights)
        self.apply_attribute_scenes = False # We don't do anything with these

    def setXData(self, indexList):
        """Update the x request."""
        self.requestAddIndices("x", indexList)

    def setYData(self, indexList):
        """Update the y request."""
        self.requestAddIndices("y", indexList)

    @Slot(str)
    def presentData(self):
        """If both x and y requests have attribute data, combines them
           via a generalized group by which falls into the domain of the
           first attribute of x.
        """
        if not self.requests['x'].indices or not self.requests['y'].indices:
            return

        self.table, self.ids, xs, ys = self.requests['x'].generalizedGroupBy(
            self.requests['y'].indices, "sum", "sum")
        self.plotUpdateSignal.emit(self.ids, xs, ys)

    @Slot(list)
    def selectionChanged(self, ids):
        """Should be called when a view using this agent has changed
           highlights.
        """
        if self.table:
            self.setHighlights([self.table], [self.table.getRun()], [[self.ids[x] for x in ids]])

    @Slot()
    def processHighlights(self):
        """When highlights have changed via HighlightScene information,
           processes them to the domain space of the x request.
        """
        if not self.table:
            return

        domain_indices = self.getHighlightIDs(self.table, self.table.getRun())
        highlight_indices = []
        for i, indx in enumerate(self.ids):
            if indx in domain_indices:
                highlight_indices.append(i)
        self.highlightUpdateSignal.emit(highlight_indices)

@Module("Plotter", PlotterAgent)
class PlotterFrame(ModuleFrame):
    """This is a ModuleFrame class for matplotlib style plotting."""

    def __init__(self, parent, parent_frame = None, title = None):
        """Create the PlotterFrame."""
        super(PlotterFrame, self).__init__(parent, parent_frame, title)

        self.ids = None
        self.droppedDataSignal.connect(self.droppedData)
        self.agent.plotUpdateSignal.connect(self.plotData)
        self.agent.highlightUpdateSignal.connect(self.plotter.setHighlights)
        self.plotter.selectionChangedSignal.connect(self.agent.selectionChanged)


    def createView(self):
        """The main view of this class is a PlotterWidget."""
        view = QWidget()
        self.plotter = PlotterWidget(self)

        self.viewarea = QScrollArea()
        self.viewarea.setWidget(self.plotter)
        self.viewarea.setWidgetResizable(True)
        self.viewarea.setMinimumSize(300,300)

        layout = QGridLayout()
        layout.addWidget(self.viewarea, 0, 0, 1, 2)
        layout.setRowStretch(0, 10)
        layout.setContentsMargins(0, 0, 0, 0)
        view.setLayout(layout)

        return view

    @Slot(list, list, list)
    def plotData(self, ids, xs, ys):
        """Passes x, y information from requests down to plotter."""
        self.ids = ids
        self.plotter.plotData(xs, ys)

    @Slot(list, str)
    def droppedData(self, indexList):
        """Dropped data defaults to y. """
        # We assume generally dropped data is Y data
        self.droppedYData(indexList)

    def droppedXData(self, indexList):
        """Handles dropped x data."""
        self.plotter.setXLabel(self.buildAttributeString(indexList))
        self.agent.setXData(indexList)

    def droppedYData(self, indexList):
        """Handles dropped y data."""
        self.plotter.setYLabel(self.buildAttributeString(indexList))
        self.agent.setYData(indexList)

    def buildAttributeString(self, indexList):
        """Builds a string representing an indexList."""
        # TODO: Make this a function of DataTree for and class to use
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
            super(PlotterFrame, self).dragEnterEvent(event)

    def dropEvent(self, event):
        """Overriden function sends the dropped data to x or y depending
           on whether it is dropped beneath the x axis (x data) or anywhere
           else (y dadta).
        """
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
            self.propagateKillRogueOverlayMessage()

            # Determine whether  x or y data
            if drop_point.x() > axes_corner[0] \
                and self.height() - drop_point.y() < axes_corner[1]:
                self.droppedXData(event.mimeData().getDataIndices())
            else:
                self.droppedYData(event.mimeData().getDataIndices())
        else:
            super(PlotterFrame, self).dropEvent(event)


class PlotterWidget(QWidget):
    """Widget surrounding matplotlib plotter."""

    selectionChangedSignal = Signal(list)

    def __init__(self, parent=None):
        """Create PlotterWidget."""
        super(PlotterWidget, self).__init__(parent)

        self.selected = []
        self.ylabel = ""
        self.xlabel = ""
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
        self.axes.plot(range(6),range(6), 'ob')
        self.axes.set_title("Drag attributes to change graph.")
        self.axes.set_xlabel("Drag here to set x axis.")
        self.axes.set_ylabel("Drag here to set y axis.")
        self.canvas.draw() # Why does this take so long on 4726 iMac?

    def setXLabel(self, label):
        """Changes the x label of the plot."""
        self.xlabel = label
        self.axes.set_xlabel(label)
        self.canvas.draw()

    def setYLabel(self, label):
        """Changes the y label of the plot."""
        self.ylabel = label
        self.axes.set_ylabel(label)
        self.canvas.draw()

    def plotData(self, xs, ys):
        """Plots the given x and y data."""
        self.axes.clear()
        self.axes.set_xlabel(self.xlabel)
        self.axes.set_ylabel(self.ylabel)
        self.xs = np.array(xs)
        self.ys = np.array(ys)
        self.axes.plot(xs, ys, 'ob', picker=3)
        if np.alen(self.selected) > 0:
            self.highlighted = self.axes.plot(self.xs[self.selected[0]],
                self.ys[self.selected[0]], 'or')[0]
        self.canvas.draw()

    def onPick(self, event):
        """Handles pick event, taking the closest single point.

           Note that since the id associated with a given point may be
           associated with many points, the final selection displayed to the
           user may be serveral points.
        """
        selected = np.array(event.ind)

        mouseevent = event.mouseevent
        xt = self.xs[selected]
        yt = self.ys[selected]
        d = np.array((xt - mouseevent.xdata)**2 + (yt-mouseevent.ydata)**2)
        thepoint = selected[d.argmin()]
        selected = []
        selected.append(thepoint)

        self.selectionChangedSignal.emit(selected)

    @Slot(list)
    def setHighlights(self, ids):
        """Sets highlights based on the given ids. These ids are the indices
           of the x and y data, not the domain.
        """
        old_selection = list(self.selected)
        self.selected = ids
        if ids is None:
            self.selected = []

        if (old_selection == self.selected and old_selection != [])\
            or self.selected != []:

            if self.selected != [] and old_selection != self.selected: # Color new selection
                for indx in self.selected:
                    self.highlighted = self.axes.plot(self.xs[indx],
                        self.ys[indx], 'or')[0]
            if old_selection == self.selected: # Turn off existing selection
                self.selected = []
            if old_selection != []: # Do not color old selection
                for indx in old_selection:
                    self.axes.plot(self.xs[indx], self.ys[indx],
                        'ob', picker = 3)

            self.canvas.draw()
            return True
        return False



# ---------------------- NAVIGATION CONTROLS ---------------------------

    # Mouse movement (with or w/o button press) handling
    def onMouseMotion(self, event):
        """Handles the panning."""
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

    # Note: the dtuple is in data coordinates, the motion is in pixels,
    # we estimate how much motion there is based on the figsize and then
    # scale it appropriately to the data coordinates to get the proper
    # offset in figure limits.
    def calcTranslate(self, dtuple, motion, figsize):
        """Calculates the translation necessary in one direction given a
           mouse drag in that direction.

           dtuple
               The current limits in a single dimension

           motion
               The number of pixels the mouse was dragged in the dimension.
               This may be negative.

           figsize
               The approximate size of the figure.
        """
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
        """Records start of drag event."""
        if event.button == 1:
            self.lastX = event.x
            self.lastY = event.y

    # On mouse wheel scrool, we zoom
    def onScroll(self, event):
        """Zooms on mouse scroll."""
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
        """Calculates the zoom in a single direction based on:

           dtuple
               The limits in the direction

           scale
               Fraction by which to increase/decrease the figure.
        """
        dmin, dmax = dtuple
        drange = dmax - dmin
        dlen = 0.5*drange
        dcenter = dlen + dmin
        newmin = dcenter - dlen*scale
        newmax = dcenter + dlen*scale
        return tuple([newmin, newmax])


