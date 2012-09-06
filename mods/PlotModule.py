from SubDomain import *
from Module import *
from DataModel import *

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
        self.addRequirement("x")
        self.addRequirement("y")

    def setXData(self, indexList):
        self.requestAddIndices("x", indexList)

    def setYData(self, indexList):
        self.requestAddIndices("y", indexList)

@Module("Plotter")
class PlotterView(ModuleView):

    def __init__(self, parent, parent_view = None, title = None):
        super(PlotterView, self).__init__(parent, parent_view, title)

        self.selected = []

    def createAgent(self):
        return PlotterAgent(self.parent_view.agent,
                            self.parent_view.agent.datatree)

    def createView(self):
        view = QWidget()

        self.viewarea = QScrollArea()
        self.viewarea.setWidget(PlotterWidget())
        self.viewarea.setWidgetResizable(True)
        self.viewarea.setMinimumSize(300,300)

        # TODO: Use panels to make the attrs flush with the first label
        # and/or change this entirely so we drop into parts of the
        # MPL window.
        self.xlabel = BFDropLabel("X: ", self, self.droppedXData)
        self.ylabel = BFDropLabel("Y: ", self, self.droppedYData)
        self.xattrs = BFDropLabel("", self, self.droppedXData)
        self.yattrs = BFDropLabel("", self, self.droppedYData)

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
        self.agent.setXColumns(indexList)
        self.xattrs.setText(self.buildAttributeString(indexList))

    def droppedYData(self, indexList):
        self.agent.setYColumns(indexList)
        self.yattrs.setText(self.buildAttributeString(indexList))

    def buildAttributeString(self, indexList):
        mytext = ""
        for index in indexList:
            mytext = mytext + self.agent.datatree.getItem(index).name + ", "
        return mytext[:len(mytext) - 2]


class PlotterWidget(QWidget):

    def __init__(self, parent=None):
        super(PlotterWidget, self).__init__(parent)

        self.fig = Figure(figsize=(300,300), dpi=72, facecolor=(1,1,1), \
            edgecolor=(0,0,0))

        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self)
        self.canvas.mpl_connect('pick_event', self.onPick)
        #Toolbar Doesn't get along with Kate's MPL at the moment
        #self.toolbar = NavigationToolbar(self.canvas, self.canvas)
        self.axes = self.fig.add_subplot(111)

        vbox = QVBoxLayout()
        vbox.addWidget(self.canvas)
        vbox.setContentsMargins(0,0,0,0)
        self.setLayout(vbox)

        # Test
        self.axes.plot([1,2,3,4,5],[1,2,3,4,5], 'ob')
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

        print "self.selected is ", self.selected
        if old_selection == self.selected and old_selection != []:
            self.selected = []
            # HIGHLIGHT_CHANGE
            # alert agent about this - need SceneGraph done

        self.plotData(self.ids, self.traffic, True)

        if self.selected != []:
            # HIGHLIGHT_CHANGE
            # alert agent about this -- need SceneGraph done
            pass


    def dragEnterEvent(self, event):
        if isinstance(event.mimeData(), DataIndexMime):
            event.accept()
        else:
            super(PlotterWidget, self).dragEnterEvent(event)

    def dropEvent(self, event):
        if isinstance(self.mimeData(), DataIndexMime):
            # if this point is below the bottom of the axes y coordinate
            # transformed to display coords and inverted (because
            # matplotlib starts at bottom left), then it is xdata
            # otherwise it is ydata
            drop_point = event.pos()
        else:
            super(PlotterWidget, self).dropEvent(event)
