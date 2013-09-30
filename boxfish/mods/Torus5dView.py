'''This module shows a lower dimensional projection of the 5D torus.  The user
can select from 2D projections of a 3D slice, or 3D projections of a 4D slice.
These are built upon the 2D view of a 3D torus, implemented in Torus3dModule.py.
The following classes build upon the main 5D torus module, Torus5dModule.py.

The agent, frame, and views inherit their respective objects from Torus5dModule.
The main view is actually a widget (Torus5dViewTopWidget) with a toolbar that
holds two sub-views.  The first sub-view is an overview, which consists of the
mini-maps and the color bars.  The second is the main view, which consists of 
the projections described above.  This allows the overview to be resized or
completely hidden at any time.  The toolbar allows the user to control the
parameters of the view, such as spacing and averaging methods.

The class heirarchy herein is as follows (see Torus5dModule for more info):
    Torus5dFrame -> Torus5dViewFrame
    Torus5dAgent -> Torus5dViewAgent
    QWidget -> Torus5dViewTopWidget
    Torus5dGLWidget -> Torus5dViewMinimaps
    Torus5dGLWidget -> Torus5dViewSlice4d
'''

#import sys, math
#import numpy as np
#import operator

from Torus5dModule import *
#from boxfish.gl.GLWidget import GLWidget, set_perspective
#from boxfish.gl.glutils import *
from PySide.QtGui import QToolBar, QWidget, QVBoxLayout
from Torus5dViewSlice4d import *
from Torus5dViewSlice3d import *
from Torus5dViewOverview import *
from Torus5dViewMinimaps import *
#from Torus5dViewNodecentric import *


class Torus5dViewAgent(Torus5dAgent):
    """Agent for the 5D Torus - 4D View. This adds axis parameter signalling.
    """

    axisUpdateSignal = Signal(int, int)
    # when color map is changed by the frame, the attribute scene changes 
    #   immediately and the agent doesn't think anything's changed so need update to make chages seen
    colorMapUpdateSignal = Signal() 

    def __init__(self, parent, datatree):
        super(Torus5dViewAgent, self).__init__(parent, datatree)

    @Slot(ModuleScene)
    def processModuleScene(self, module_scene):
        super(Torus5dViewAgent, self).processModuleScene(module_scene)
        #print 'Processing module_scene, view_planes = ' + str(self.module_scene.view_planes)
        if isinstance(module_scene, Torus5dScene):
            self.module_scene = module_scene.copy()
            self.axisUpdateSignal.emit(self.module_scene.axis, 
                self.module_scene.axis_index)
            #if self.module_scene.view_planes != []:
                #self.viewPlanesUpdateSignal.emit(self.module_scene.view_planes)


@Module("5D Torus", Torus5dViewAgent, Torus5dScene)
class Torus5dViewFrame(Torus5dFrame):
    """This is a back to front compositing of 2d renderings of a 3d sub-torus.
       The 5D torus is displayed in 4D (ignore e dim), by multiple 3d slices.
       Initial concept for this view by Aaditya Landge and Kate Isaacs.

       Frame instantiation, done when click-dragging the module name to the
       main drawing area, creates Agent and Scene, and Frame.createView() creates
       the View, ie. the descendent of Torus5dGLWidget(GLWidget)
    """
    def __init__(self, parent, parent_frame = None, title = None):
        super(Torus5dViewFrame, self).__init__(parent, parent_frame, title)
        self.glview.minimaps.axisUpdateSignal.connect(self.axisChanged)
        self.glview.overview.axisUpdateSignal.connect(self.axisChanged)
        self.glview.slice3d.boundsUpdateSignal.connect(self.boundsChanged)

        # TODO:  Make sure @Slot decorator is there for these, and find if it's necessary or not
        self.glview.minimaps.viewPlanesUpdateSignal.connect(self.viewPlanesChanged)
        self.glview.overview.viewPlanesUpdateSignal.connect(self.viewPlanesChanged)
        self.agent.axisUpdateSignal.connect(self.checkAxisChanged)
        self.agent.colorMapUpdateSignal.connect(self.colorMapChanged)

    def createView(self):
        '''Creates the view, i.e. OpenGL rendering context.  Instead of returning
        a QGLWidget here, we're returning a QWidget that contains four QGLWidget's.
        See the top-level QWidget for more on how this works.
        '''
        self.glview = Torus5dViewTopWidget(self, self.dataModel)
        return self.glview

    @Slot(int, int)
    def axisChanged(self, axis, axis_index):
        '''Handles axis, axis_index changing.  This propagates the moduleScene
        change but really isn't necessary because no other modules use this 
        information (i.e. there is only one module for the 5d torus), and it
        shouldn't be necessary to open multiple instances of the 5d torus module
        to compare data of the same run.
        '''
        if self.agent.module_scene.axis != axis or self.agent.module_scene.axis_index != axis_index:
            self.agent.module_scene.axis = axis
            self.agent.module_scene.axis_index = axis_index
            self.agent.module_scene.announceChange()

    @Slot()
    def colorMapChanged(self):
        self.agent.processAttributeScenes()

    @Slot(float, float, bool)
    def boundsChanged(self, lower, upper, links):
        self.glview.overview.changeNodeLinkBounds(lower, upper, links)
        self.glview.overview.update()
        self.glview.minimaps.changeNodeLinkBounds(lower, upper, links)
        self.glview.minimaps.update()
        self.glview.slice3d.changeNodeLinkBounds(lower, upper, links)
        self.glview.slice3d.update()
        self.glview.slice4d.changeNodeLinkBounds(lower, upper, links)
        self.glview.slice4d.update()

    @Slot(dict)
    def viewPlanesChanged(self, view_planes):
        '''Handles view planes being changed, but doesn't propagate to the agent
        because the module scene isn't being used in the 5d torus, because the 
        view is self contained (i.e. there is only one module for the 5d torus).
        '''
        self.dataModel.view_planes = view_planes
        self.glview.slice4d.updateDrawing()
        self.glview.overview.updateDrawing()
        self.glview.slice3d.updateDrawing()
        # for the minimaps, need to update the data each time view planes change
        #   since the minimap shows averages of only the selected planes
        self.glview.minimaps.update()

    @Slot(int, int)
    def checkAxisChanged(self, axis, axis_index):
        '''Handles updating the axis, axis_index for all windows except the one
        that already shows this change (i.e. the window the user selected the
        new axis, axis index from).
        '''
        if self.glview.slice4d.axis != axis or self.glview.slice4d.axis_index != axis_index:
            self.glview.slice4d.updateAxis(axis, axis_index)
        if self.glview.minimaps.axis != axis or self.glview.minimaps.axis_index != axis_index:
            self.glview.minimaps.updateAxis(axis, axis_index)
        if self.glview.overview.axis != axis or self.glview.overview.axis_index != axis_index:
            self.glview.overview.updateAxis(axis, axis_index)
        if self.glview.slice3d.axis != axis or self.glview.slice3d.axis_index != axis_index:
            self.glview.slice3d.updateAxis(axis, axis_index)


class Torus5dViewTopWidget(QWidget):
    ''' This widget extends QWidget to contain four QGLWidgets that will draw
    coordinated views for the 5D torus visualization.  Since frame.createView()
    is expecting a GLWidget extension, we must provide mechanisms to handle the
    two signals below and the two methods for changing the background color
    and transformation information (rotation, translation).
    '''

    # GLModule is expecting these signals for every view - they're inherited from
    #   GLWidget usually - so need to exist, but will not be used here
    transformChangeSignal = Signal(np.ndarray, np.ndarray)
    resizeSignal = Signal()

    def __init__(self, parent, dataModel):
        super(Torus5dViewTopWidget, self).__init__(parent)
        overviewWidth = 0.2
        mainToolbarWidth = 0.05
        overviewToolbarHeight = 0.1
        miniMapsHeight = 0.75
        
        mainWidth = 1-(overviewWidth + mainToolbarWidth)
        colorBarsHeight = 1 - overviewToolbarHeight - miniMapsHeight
        
        #self.egocentric = Torus5dViewNodecentric(parent, dataModel)

        self.minimaps = Torus5dViewMinimaps(parent, dataModel)
        self.slice4d = Torus5dViewSlice4d(parent, dataModel)
        self.overview = Torus5dViewOverview(parent, dataModel)
        self.slice3d = Torus5dViewSlice3d(parent, dataModel)

        overviewWidget = QSplitter()
        overviewWidget.setOrientation(Qt.Vertical)
        overviewWidget.addWidget(self.overview)
        overviewWidget.addWidget(self.minimaps)
        overviewWidget.setStretchFactor(0, 50)
        overviewWidget.setStretchFactor(1, 50)

        mainWidget = QSplitter()
        mainWidget.setOrientation(Qt.Vertical)
        mainWidget.addWidget(self.slice4d)
        mainWidget.addWidget(self.slice3d)
        mainWidget.setStretchFactor(0, 50)
        mainWidget.setStretchFactor(1, 50)
    
        view_splitter = QSplitter() # horizontal by default
        view_splitter.addWidget(overviewWidget)
        view_splitter.addWidget(mainWidget)
        #view_splitter.addWidget(self.egocentric)
        view_splitter.setStretchFactor(0, 30)
        view_splitter.setStretchFactor(1, 70)
        #view_splitter.setStretchFactor(2, 1)

        main_layout = QHBoxLayout()
        main_layout.addWidget(view_splitter)
        self.setLayout(main_layout)

        # Note:  Connect these signals if propagating transformations
        #self.slice4d.transformChangeSignal.connect(self.transformChanged)
        #self.slice3d.transformChangeSignal.connect(self.transformChanged)

    def transformChanged(self, rotation, translation):
        '''Propagates a transformChangeSignal from one of the sub-windows to
        the agent.  However, since the translation of the two main views are
        different at the start, due to resetView(), there is no good way to 
        make them the same without affecting the rotation because of the way
        GLWidget.orient_scene handles translation/rotation.  Thus the transform
        signals from the two main views aren't connected to this method now.
        ''' 
        self.transformChangeSignal.emit(rotation, translation)

    def change_background_color(self, color):
        '''Handles changing the background color for the four subwindows.  This
        is called whenever the ModuleScene information changes, usually from a
        transformation.  This explicitly checks that the new background color
        is different before changing it, since drawings need to be updated after
        changing the background color.'''

        # need the explicit calls to update drawing since line colors, etc
        #   depend on the background color - since change_background_color
        #   gets called every time module scene changes (translation, rotation)
        #   test to make sure color is really different before calling this
        if max(np.abs(np.subtract(self.slice4d.bg_color, color))) > 0.01:
            self.minimaps.change_background_color(color)
            self.overview.change_background_color(color)
            self.slice4d.change_background_color(color)
            self.slice3d.change_background_color(color)
            self.minimaps.updateDrawing() 
            self.overview.updateDrawing()
            self.slice4d.updateDrawing()
            self.slice3d.updateDrawing()
        
    def set_transform(self, rotation, translation):
        ''' Rotates and translates view based on transformChangeSignal.  Not
        currently used since two main views have different translations in
        resetView(), and this would force them to be the same.
        '''
        pass 
        #self.slice4d.set_transform(rotation, translation)
        #self.slice3d.set_transform(rotation, translation)











