from BFModule import *
import os
os.environ['QT_API'] = 'pyside' 
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as pyplot
from matplotlib.widgets import Lasso
from matplotlib.nxutils import points_inside_poly
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle
from PySide.QtGui import QFrame, QGridLayout, QMenuBar, QFileDialog, QLabel,QComboBox, QPushButton
from PySide.QtCore import SIGNAL, SLOT
from YamlLoader import *


class PlotWindow(BFModule):
  """A PlotWindow implements a wrapper around a matplotlib canvas.
  """

  def __init__(self, parent=None, flags=0):
    """Initializes the window
       Parameters:

          parent : The parent widget (default None)
          flags  : Qt Flags
"""
    super(PlotWindow, self).__init__(parent)
      
    self.createLayout()

    # The canvas object that represents the highlight
    self.focus = None

    # Do we accept highlights from other sources. If true my highlight will
    # change each time a relevant object has been highlighted by some (not
    # necessarily my own) window
    self.acceptHighlight = True

    # Do we accept data from other sources. If true the window will draw the
    # last relevant data that was queried througout the system
    self.acceptData = False

    # This is *our* currently active query which is used to recognize the data
    # we asked for
    self.activeQuery = None

  def createLayout(self):

    # Create a figure
    self.figure = Figure(figsize=(600,600), dpi=72, facecolor=(1,1,1), edgecolor=(0,0,0))
    self.axes = self.figure.add_subplot(111)
    self.canvas = FigureCanvas(self.figure)
    self.canvas.mpl_connect('pick_event', self.onPick)

    
    # Create a menu bar
    self.menuBar = QMenuBar(self)
    self.fileMenu = self.menuBar.addMenu('File')
    action = self.fileMenu.addAction("Load File")
    action.triggered.connect(self.loadFile)
    
    self.layout = QGridLayout()
    self.layout.addWidget(self.menuBar,0,0,1,2)
    self.layout.addWidget(self.canvas,1,0)

    self.selection = self.createSelection()
    self.layout.addWidget(self.selection,1,1)
    
    self.setLayout(self.layout)

  def createSelection(self):

    frame = QFrame(self)
    layout = QGridLayout()
    layout.setSpacing(5)
    layout.addWidget(QLabel("X-Axis"),0,0)
    self.xaxis_combo = QComboBox(frame)
    layout.addWidget(self.xaxis_combo,0,1)
    
    layout.addWidget(QLabel("Y-Axis"),1,0)
    self.yaxis_combo = QComboBox(frame)
    layout.addWidget(self.yaxis_combo,1,1)
    
    layout.addWidget(QLabel("Operator"),2,0)
    self.operator_combo = QComboBox(frame)
    layout.addWidget(self.operator_combo,2,1)

    for op in BFTable.operator:
      self.operator_combo.addItem(op)

    plot = QPushButton('Plot',frame)
    plot.released.connect(self.plotData)
    layout.addWidget(plot)

    frame.setLayout(layout)
    return frame
    
    
  @Slot()
  def loadFile(self):
      
    
    filename = QFileDialog.getOpenFileName(self,"Open Yaml",".",
                                           "Yaml Files (*.yaml)")
    table = BFTable()
    table.fromYAML(Ranks,'mpirank',filename[0])
    
    self.addTable(table)
      
  def attributesChanged(self,attributes):
    self.attributes =  dict(attributes)

    while self.xaxis_combo.count() > 0:
      self.xaxis_combo.removeItem(0)
    
    for domain in attributes:
      for subdomain in attributes[domain]:
        self.xaxis_combo.addItem(subdomain)
        self.xaxis_combo.activated[str].connect(self.xaxisChanged)

    self.xaxisChanged(self.xaxis_combo.currentText())
        
  @Slot(str)
  def xaxisChanged(self,subdomain):

    #If we used to have another subdomain we were listining to that domain
    if hasattr(self,'subdomain') and self.subdomain.subdomain() != subdomain:
      # And now need to unsubscribe
      self.unsubscribe(self.subdomain.subdomain())

    while self.yaxis_combo.count() > 0:
      self.yaxis_combo.removeItem(0)

    # First, we add all the avaiable attributes to the combobox
    for domain in self.attributes:
      if subdomain in self.attributes[domain]:
        for att in self.attributes[domain][subdomain]:
          self.yaxis_combo.addItem(att)
        break

    # Ask for the new subdomain which will set our self.subdomain variable to
    # the entire subDomain
    self.getSubDomain(subdomain)

    # And start listening for the new domain
    self.subscribe(subdomain)

    # Clear the plot
    self.axes.clear()
    self.canvas.draw()
   

  @Slot()
  def plotData(self):

    self.activeQuery = Query(self.subdomain,self.yaxis_combo.currentText(),self.operator_combo.currentText())
    self.evaluate(self.activeQuery)

  @Slot(Query,np.ndarray)
  def receive(self,query,data):
    #print "BFModule got an answer for ", query,data

    if (self.activeQuery and self.activeQuery == query) or self.acceptData:
      self.activeQuery = None
      self.data = data
      
      self.axes.clear()
      self.data_plot = self.axes.plot(query.subdomain,data,picker=3,zorder=0)[0]
      self.axes.set_xlabel(query.subdomain.typename())
      self.axes.set_ylabel(query.attribute)
      self.canvas.draw()

  def onPick(self, event):

    if True or event.mouseevent.button == 1:

      try:
        
        if isinstance(event.artist, Line2D):
          ind = event.ind
          i = ind[len(ind)/2]
          self.highlight(self.subdomain[i:i+1])
        
        elif isinstance(event.artist, Rectangle):
          patch = event.artist
          print 'onpick1 patch:', patch.get_path()
      except:
        pass


  def highlightChanged(self,subdomain):
    
    try:
      self.focus.remove()
    except:
      pass
    
    self.focus = None

    if not hasattr(self,'data'):
      return 

    # Figure out the data we need to draw
    index = np.searchsorted(self.subdomain,subdomain)
    x = subdomain[0]
    y = self.data[max(index-1,0)]

    # Now we figure out the size of the highlight. We would like a size of 3
    # pixels centered at the data object.

    # First we transform the data into screen space
    img = self.data_plot.get_transform().transform([x,y])

    # Then we transform the pixel + (3,3) back into data space
    diff = self.data_plot.get_transform().inverted().transform([img[0]+3,img[1]+3])

    diff[0] -= x
    diff[1] -= y

    # Finally we create a rectangle around the data item
    r = Rectangle([x-diff[0],y-diff[1]],2*diff[0],2*diff[1],color='red',zorder=2)

    # And add it to the plot
    self.focus = self.axes.add_patch(r)
    self.canvas.draw()


if __name__ == '__main__':

  from PySide.QtGui import QApplication
  from sys import argv,exit
  from BFEngine import *

  # Create a basic app to handle the signals
  app = QApplication(argv)

  # Create an engine
  engine = BFEngine()

  # Create a plot window
  win = PlotWindow()  
  win.show()

  engine.registerModule(win)

  table = BFTable()
  table.fromYAML(Ranks,'mpirank','dummy_ranks.yaml')
  win.addTable(table)


  win2 = PlotWindow()
  win2.show()
  engine.registerModule(win2)

  table = BFTable()
  table.fromYAML(Cores,'coreid','dummy_cores.yaml')
  win2.addTable(table)
  
  win.addProjection(Identity(Cores(),Ranks()))
  
  exit(app.exec_())
