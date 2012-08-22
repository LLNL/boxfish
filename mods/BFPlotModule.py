from SubDomain import *
from BFModule import *
from DataModel import *

import sys
import matplotlib
import numpy as np
matplotlib.use('Qt4Agg')
matplotlib.rcParams['backend.qt4']='PySide'

from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import \
    FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import \
    NavigationToolbar2QT as NavigationToolbar

from PySide.QtCore import *
from PySide.QtGui import *

class BFPlotModule(BFModule):

    def __init__(self, parent, model):
        super(BFPlotModule, self).__init__(parent, model)

    def setXColumns(self, columns):
        pass

    def setYColumns(self, columns):
        pass


class BFPlotWindow(BFModuleWindow):

    display_name = "Plotter"
    in_use = True

    def __init__(self, parent, parent_view = None, title = None):
        super(BFPlotWindow, self).__init__(parent, parent_view, title)

        self.selected = []

    def createModule(self):
        print "Creating Module"
        return BFPlotModule(self.parent_view.module, self.parent_view.module.model)

    def createView(self):
        print "Creating View"
        view = QWidget()

        self.viewarea = QScrollArea()
        self.viewarea.setWidget(BFPlotView())
        self.viewarea.setWidgetResizable(True)
        self.viewarea.setMinimumSize(300,300)

        layout = QGridLayout()
        layout.addWidget(self.viewarea, 0, 0, 1, 1)
        layout.setRowStretch(0, 10)
        layout.setContentsMargins(0, 0, 0, 0)
        view.setLayout(layout)

        return view


class BFPlotView(QWidget):

    def __init__(self, parent=None):
        super(BFPlotView, self).__init__(parent)

        print "Adding Figure"
        self.fig = Figure(figsize=(300,300), dpi=72, facecolor=(1,1,1), edgecolor=(0,0,0))

        print "Adding Canvas"
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.canvas.mpl_connect('pick_event', self.onPick)
        print "Adding Toolbar"
        self.toolbar = NavigationToolbar(self.canvas, self.canvas)
        self.axes = self.fig.add_subplot(111)

        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.setContentsMargins(0,0,0,0)
        self.setLayout(vbox)

        # Test
        self.axes.plot([1,2,3,4,5],[1,2,3,4,5], 'ob')
        print "Drawing"
        self.canvas.draw()


    def plotData(self, ids, vals):
        self.axes.clear()
        self.axes.plot(ids, vals, 'ob', picker=3)
        if np.alen(self.selected) > 0:
            self.highlighted = self.axes.plot(ids[self.selected[0]], traffic[self.selcted[0]], 'or')[0]
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

        print "self.selected is ", self.selected
        if old_selection == self.selected and old_selection != []:
            self.selected = []
            # emit some signal about this

        # We haven't changed the data so we don't have to go through makePlottable
        self.plotData(self.ids, self.traffic, True)

        if self.selected != []:
            # emit some signal about this
            pass
