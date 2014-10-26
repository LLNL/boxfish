import math
import numpy as np
import operator
from OpenGL.GL import *
from OpenGL.GLU import *
from Torus5dModule import *
from boxfish.gl.glutils import *
from OpenGL.GLUT import *

class Torus5dViewSlice3d(Torus5dGLWidget):
    ''' Draws a view of a 3d torus.  The 3d torus is selected as a subset of the
    5d torus holding two dimensions constant.  The view is drawn with the three
    dimensions being mapped to OpenGL x, y, and z in a 3d-mesh like drawing.  
    Wrap-around links are drawn leaving the source node, disconnected from the
    destination node.
    '''

    # ***************************    Initialize    *****************************

    def __init__(self, parent, dataModel):
        super(Torus5dViewSlice3d, self).__init__(parent, dataModel)

        self.seam = [0, 0, 0]  # Offsets for seam of the torus
        self.link_width = self.node_size * .1   # Radius of link cylinders
        self.numIcons = 4 # upper and lower limit sliders for nodes and links
        # offsets are 0 for lower bound sliders, 1 for upper bound sliders
        self.sliderOffsets = [0 if i%2==0 else 1 for i in range(self.numIcons)]
        self.sliderPos = {'L': [0, 0], 'N': [0, 0]} # min, max position of color bar
        self.iconSelected = [False for j in range(self.numIcons)]

        self.widget2dLists = []
        self.toolBarList = DisplayList(self.drawToolBar)
        self.widget2dLists.append(self.toolBarList)

        self.widget3dLists = []
        self.nodeList = DisplayList(self.drawNodes)
        self.linkList = DisplayList(self.drawLinks)
        self.gridList = DisplayList(self.drawGrid)
        
        self.widget3dLists.append(self.nodeList)
        self.widget3dLists.append(self.linkList)
        self.widget3dLists.append(self.gridList)
        
        # keep display list for axis separate since it needs own drawing setup
        self.axisList = DisplayList(self.drawAxisLines)
        # settings for the axis
        self.axisLength = 0.3
        self.toolBarSelected = False
        self.toolBarPos = 'right'
        self.toolBarFlip = False
        Qt.ShiftModifier = False # to fix the weird vertical translation bug

        self.resizeSignal.connect(self.updateDrawing)
   
        self.update() # necessary?

    boundsUpdateSignal = Signal(float, float, bool)
    shape = property(fget = lambda self: self.dataModel.shape)
    current_planes = property(fget = lambda self: self.dataModel.current_planes)
    
    def initializeGL(self):
        """We use transparency simply here, so we enable GL_BLEND."""
        super(Torus5dViewSlice3d, self).initializeGL()

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    # ***************************      Update      *****************************

    def resetView(self):
        slice_shape = self.getSliceShape()
        w_span, h_span = slice_shape[0], slice_shape[1]
        if w_span != 0 and h_span != 0:
            spans = self.getSliceSpan()
            aspect = self.width() / float(self.height())

            # Check both distances instead of the one with the larger span
            # as we don't know how aspect ratio will come into play versus shape

            # Needed vertical distance
            fovy = float(self.fov) * math.pi / 360.
            disty = spans[1] / 2. / math.tan(fovy) #spans[1] = spans[height]

            # Needed horizontal distance
            fovx = fovy * aspect
            distx = spans[0] / 2. / math.tan(fovx) #spans[0] = spans[width]

            #self.translation = [0, 0, -3*max(distx, disty)]
            self.translation = [0, 0, -1.5*max(distx, disty)]  

    def update(self, colors = True, reset = True, barLists = True):
        if colors: super(Torus5dViewSlice3d, self).update()
        if reset: self.resetView()
        self.updateDrawing(barLists)

    def updateAxis(self, axis, axis_index = -1):
        ''' Slot for agent.axisUpdateSignal.  
        '''
        if self.axis != axis or self.axis_index != axis_index:
            if axis_index == -1: #keyboard change axis command
                if self.axis == axis: #increment axis_index
                    self.axis_index = self.getNextAxisIndex()
                else:
                    self.axis_index = 0
                    self.axis = axis
            else: #mouse click i/o
                self.axis = axis
                self.axis_index = axis_index
            #print 'Axis = ' + str(self.axis) + ', Index = ' + str(self.axis_index)
        
            self.update()

    def updateDrawing(self, nodes = True, links = True, grid = True, axis = False, toolBar = True):
        if nodes: self.nodeList.update()
        if links: self.linkList.update()
        if toolBar:
            self.updateToolBarPos()
            self.toolBarList.update()
        if axis: self.axisList.update()
        #self.updateGL()
        self.paintEvent(None)

    def updateIconHitBoxes(self, indicies, vals):
        ''' Increment all hit boxes with index in indicies by the values in vals.'''

        for i in indicies:
            self.iconHitBoxes[i][0][0] += vals[0][0]
            self.iconHitBoxes[i][0][1] += vals[0][1]
            self.iconHitBoxes[i][1][0] += vals[1][0]
            self.iconHitBoxes[i][1][1] += vals[1][1]

    def updateToolBarPos(self):
        ''' Recalculates the possible tool bar positions based on window width
        and height.
        '''
        w_horiz = self.width()
        eff_size = min(self.width(), self.height())
        w_vert = max(int(eff_size*0.16), 50) # by experimenting
        w_vert = min(w_vert, 120)
        h_horiz = max(int(eff_size*0.16), 50)
        h_horiz = min(h_horiz, 120)
        #print 'updateToolBarPos:  eff_size * 0.15 =',eff_size*0.15,', w_vert =',w_vert,', h_hoiz =',h_horiz
        h_vert = self.height()
        x_right = int(self.width()-w_vert)
        y_top = int(self.height()-h_horiz)
        y_right = x_left = y_left = x_top = x_bottom = y_bottom = 0

        self.toolBarDims = {'left': [[x_left, x_left + w_vert], [y_left, y_left + h_vert]],
        'right': [[x_right, x_right + w_vert], [y_right, y_right + h_vert]],
        'top': [[x_top, x_top + w_horiz], [y_top, y_top + h_horiz]],
        'bottom': [[x_bottom, x_bottom + w_horiz], [y_bottom, y_bottom + h_horiz]]}

    # ***************************    Calculate     *****************************

    def getFullNode(self, slice_node):
        node = [-1 for i in self.shape]
        w, h, d = self.getSliceDims()
        slice_axis = [w, h, self.axis]
        for i in range(len(self.shape)):
            slice_index = 0
            for j in slice_axis:
                if j == i:    
                    node[i] = slice_node[slice_index]
                    break
                slice_index += 1
            if slice_index == len(slice_axis):
                node[i] = self.current_planes[i]
        return tuple(node)

    def getSliderParams(self, icon_num, min_x, range_x, min_y, range_y):
        if self.toolBarPos == 'left' or self.toolBarPos == 'right':
            icon_x = min_x
            icon_y = min_y + self.sliderOffsets[icon_num] * range_y
            icon_range = [min_y, min_y+range_y]
        else:
            icon_y = min_y
            icon_x = min_x + self.sliderOffsets[icon_num] * range_x
            icon_range = [min_x, min_x+range_x]

        return icon_x, icon_y, icon_range

    def getNextAxisIndex(self):
        numIndicies = len(self.axis_map[self.axis]) # num_views for that axis
        if self.axis_index == numIndicies - 1: #wraparound
            return 0
        else: return self.axis_index + 1

    def getNodePos3d(self, node, shape = None):
        """Translate view to coords where we want to render the node (x,y,z)"""
        if shape == None:
            shape = self.getSliceShape()

        node = (np.array(node, int) + self.seam) % shape
        node *= self.axis_directions
        return node
        #glTranslatef(*node)

    def getSliceDims(self):
        """Get the dimensions that span width, height, depth of screen"""
        return self.axis_map[self.axis][self.axis_index]

    def getSliceNode(self, node5d):
        w, h, d = self.getSliceDims()
        return [node5d[w], node5d[h], node5d[self.axis]]

    def getSliceShape(self):
        ''' Slice is a selection of 3 dimensions for a 4D projection.  The
        dimensions are {a, b, c, d, e} = {0, 1, 2, 3, 4}.
        '''
        w, h, d = self.getSliceDims()
        return [self.shape[w], self.shape[h], self.shape[self.axis]]

    def getSliceSpan(self, shape = None):
        if shape == None:
            shape = self.getSliceShape()

        return np.array(shape, np.float)        


    # ***************************     Render      ******************************

    # ------------------------    Render, Level 0    ---------------------------

    #def paintGL(self):
    #    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    #    glGetError()
    #    self.orient_scene()
    #    self.draw()
    #    super(Torus5dViewSlice3d, self).paintGL()    

    def paintEvent(self, event):
        with setupPaintEvent(self):
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glGetError()
            self.orient_scene()
            self.draw()
            super(Torus5dViewSlice3d, self).paintEvent(event)    

    # ------------------------    Render, Level 1    ---------------------------

    def draw(self):
        for func in self.widget3dLists:
            func() # display lists: call drawLinks(), drawNodes(), drawGrid()

        with overlays2D(self.width(), self.height(), self.bg_color):
            for func in self.widget2dLists:
                func() # call drawLinkColorBar() and drawNodeColorBar()

        #self.drawAxis() # do this seperately, needs extra setup

    # ------------------------    Render, Level 2    ---------------------------

    def drawAxis(self):
        """This function does the actual drawing of the lines in the axis."""

        #TODO:  Fix this to be size/position you want it to be in

        size = 80
        gap = 5
        #x_start = self.width()-(size+gap)
        #y_start = self.height()-(size+gap)
        x_start = int(self.width()/2.)
        y_start = int(self.height()/2.)
        #print 'self.width = ' + str(self.width()) + ', self.height = ' + str(self.height())

        glViewport(x_start,y_start,x_start+size,y_start+size)

        glPushMatrix()
        with attributes(GL_CURRENT_BIT, GL_LINE_BIT):
            glLoadIdentity()
            glTranslatef(0,0, -self.axisLength)
            glMultMatrixd(self.rotation)
            with disabled(GL_DEPTH_TEST):
                self.axisList()

        glPopMatrix()
        glViewport(0, 0, self.width(), self.height())

    def drawGrid(self):
        ''' Draws a grid in the xz-plane to go under the 5d torus drawing.'''

        # TODO:  Redo this so it works with the 3d torus
        """

        offset_y = -3 # how far to push the grid below the torus drawing
        step_size = 3 # grid spacing

        # get the node position extends - draw the grid below the minimum y pos,
        #   and from the below minimum x to above max x, from min z to max z
        start_x, start_y, start_z = self.getNodePos3d([0, 0, 0, 0, 0])

        if self.insetEDim: 
            # when insetting two planes that differ in e-dim, e=0 is on outside
            #   and e=1 is on inside - need outermost node pos, so use e=0
            end_node = [self.shape[i]-1 if i != self.axis and i != len(self.shape)-1
                else 0 for i in range(len(self.shape))] 
        else: 
            # when instead just offsetting e=1 in the x-dir, want e=1 to get
            #   maximum x-value
            end_node = [self.shape[i]-1 if i != self.axis else 0 
                for i in range(len(self.shape))] 
        end_x, end_y, end_z = self.getNodePos3d(end_node)
        
        grid_y = min(start_y, end_y) + offset_y
        grid_x_start = min(start_x, end_x) - 0.125*abs(start_x-end_x)
        grid_x_end = max(start_x, end_x) + 0.125*abs(start_x-end_x)
        grid_z_start = min(start_z, end_z) - 0.25*abs(start_z-end_z)
        grid_z_end = max(start_z, end_z) + 0.075*abs(start_z-end_z)

        glColor4f(0.5, 0.5, 0.5, 0.5)
        glLineWidth(1.)
        with glMatrix():
            self.centerView(self.getSliceShape())
            for i in np.arange(grid_x_start, grid_x_end, step_size): # x value
                for j in np.arange(grid_z_start, grid_z_end, step_size): # z value
                    with glSection(GL_LINE_LOOP):
                        glVertex3f(i, grid_y, j)
                        glVertex3f(i+step_size, grid_y, j)
                        glVertex3f(i+step_size, grid_y, j+step_size)
                        glVertex3f(i, grid_y, j+step_size)

        #print 'slice_span =',slice_span        
        """

    def drawLinks(self):
        glMaterialfv(GL_FRONT_AND_BACK,GL_DIFFUSE,[1.0, 1.0, 1.0, 1.0])
        glPushMatrix()
        self.centerView()
        w, h, d = self.axis_map[self.axis][self.axis_index]

        #print 'Main3D, drawLinks: current_planes = ' + str(self.current_planes)

        # origin-relative poly cylinder points for each dimension
        poly_cylinders =[[(-1, 0, 0), (0, 0,  0), (1, 0, 0), (2, 0, 0)],
                         [(0, -2, 0), (0, -1, 0), (0, 0, 0), (0, 1, 0)],
                         [(0, 0, -2), (0, 0, -1), (0, 0, 0), (0, 0, 1)]]

        for node in np.ndindex(*self.shape):
            if self.current_planes[d] == node[d] and self.current_planes[4] == node[4]:
                glPushMatrix()
                glTranslatef(*self.getNodePos3d(self.getSliceNode(node)))
                colors = self.link_colors[node]

                # Draw links for each dim as poly cylinders
                polyDim = 0
                for dim in w, h, self.axis:
                    glColor4f(*colors[dim])
                    notGlePolyCylinder(poly_cylinders[polyDim], None, self.link_width)
                    polyDim += 1

                glPopMatrix()
        glPopMatrix()        

    def drawNodes(self):
        glPushMatrix()
        self.centerView()
        w, h, d = self.axis_map[self.axis][self.axis_index]

        #print 'Main3D, drawNodes: current_planes = ' + str(self.current_planes)

        for node in np.ndindex(*self.shape):
            if self.current_planes[d] == node[d] and self.current_planes[4] == node[4]:
                # draw a dataed cube with its center at (0,0,0)
                glPushMatrix()
                glTranslatef(*self.getNodePos3d(self.getSliceNode(node)))
                glColor4f(*self.node_colors[node])
                notGlutSolidCube(self.node_size)
                glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()       

    def drawToolBar(self):

        if max(self.shape) == 0: # since need to know parent to get coords label
            return

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.bright_bg_color = ((self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) /  3) >= 0.5

        [[x_min, x_max], [y_min, y_max]] = self.toolBarDims[self.toolBarPos]
        w = x_max - x_min
        h = y_max - y_min
        #print 'DIMS: toolBarDims =',str(self.toolBarDims[self.toolBarPos]),', w =',w,', h =',h

        # calculate color bar dimensions - to keep size same regardless of toolBarPos
        if self.width() > self.height(): # toolBarPos left or right dictates size
            [[temp_xmin, temp_xmax], [temp_ymin, temp_ymax]] = self.toolBarDims['right']
            bar_long_dim =  int((temp_ymax - temp_ymin)*0.3)
            bar_short_dim = int((temp_xmax - temp_xmin)*0.6)
            space = int(((temp_xmax - temp_xmin) - bar_short_dim)/2.)
        else: # toolBarPos top or bottom dictates size
            [[temp_xmin, temp_xmax], [temp_ymin, temp_ymax]] = self.toolBarDims['top']
            bar_long_dim = int((temp_xmax - temp_xmin)*0.3)
            bar_short_dim = int((temp_ymax - temp_ymin)*0.6)
            space = int(((temp_ymax - temp_xmin) - bar_short_dim)/2.)

        if self.toolBarPos == 'left' or self.toolBarPos == 'right':
            bar_w = bar_short_dim
            bar_h = bar_long_dim
        else:
            bar_w = bar_long_dim
            bar_h = bar_short_dim

        # create hit boxes
        self.iconHitBoxes = [[[0, 0], [0, 0]] for i in range(self.numIcons)]
        self.iconPosBounds = [0 for i in range(self.numIcons)]

        #print 'setup_overlay2D: x =',x_min,', y =',y_min,', w =',w,', h =',h
        setup_overlay2D(x_min, y_min, w, h)

        with glMatrix():
            glLoadIdentity() # must have this to not be affected by resetView()

            if self.toolBarSelected:
                if self.bright_bg_color:
                    glColor4f(0., 0., 0., 0.1)
                else:
                    glColor4f(1., 1., 1., 0.1)

                with glSection(GL_QUADS):
                    glVertex3f(x_min, y_min, -0.1)
                    glVertex3f(x_max, y_min, -0.1)
                    glVertex3f(x_max, y_max, -0.1)
                    glVertex3f(x_min, y_max, -0.1)

            if self.toolBarPos == 'left' or self.toolBarPos == 'right':
                if self.toolBarPos == 'right':
                    link_bar_x = node_bar_x = x_min + int(space*3/2.)
                else:
                    link_bar_x = node_bar_x = x_min + int(space/2.)
                link_bar_y = y_max - bar_h - int(space/2.)
                node_bar_y = link_bar_y - bar_h
                label_pos = 'top'
                if self.toolBarFlip:
                    node_bar_y = y_min # keep on bottom
                    link_bar_y = node_bar_y + bar_h
            else:
                node_bar_x = x_max - bar_w
                if self.toolBarPos == 'top':
                    node_bar_y = link_bar_y = y_min + int(space*3/2.)
                else:
                    node_bar_y = link_bar_y = y_min + int(space/2.)
                link_bar_x = node_bar_x - int(space/2.) - bar_w 
                label_pos = 'left'
                if self.toolBarFlip:
                    link_bar_x = x_min + int(space/2.)
                    node_bar_x = link_bar_x + bar_w + int(space/2.)

            
            self.drawColorBarSlider(link_bar_x, link_bar_y, bar_w, bar_h, 'L', label_pos)
            self.drawColorBarSlider(node_bar_x, node_bar_y, bar_w, bar_h, 'N', label_pos)

        glDisable(GL_BLEND)
        
    # ------------------------    Render, Level 3    ---------------------------
    
    def centerView(self, shape = None, axis = 2):
        """ First we move the coordinate system by half the size of the total
            grid. This will allow us to draw boxes and links at (0,0,0),
            (1,0,0),... etc. but they will appear centered around the global
            origin.
        """
        if shape == None:
            shape = self.getSliceShape()

        '''
        # first push the view back
        w_span, h_span = shape[0], shape[1]
        if w_span != 0 and h_span != 0:
            spans = self.getSliceSpan()
            aspect = self.width() / float(self.height())

            # Check both distances instead of the one with the larger span
            # as we don't know how aspect ratio will come into play versus shape

            # Needed vertical distance
            fovy = float(self.fov) * math.pi / 360.
            disty = spans[1] / 2. / math.tan(fovy) #spans[1] = spans[height]

            # Needed horizontal distance
            fovx = fovy * aspect
            distx = spans[0] / 2. / math.tan(fovx) #spans[0] = spans[width]

            glTranslatef(0., 0., -1.5*max(distx, disty))'''

        half_spans = self.getSliceSpan(shape) / -2
        half_spans[axis] = 0
        half_spans *= self.axis_directions
        glTranslatef(*half_spans)


        #spans = np.array(shape, float)
        #half_spans = (spans - 1) / -2 * self.axis_directions
        #glTranslatef(*half_spans)
    
    def drawAxisLines(self):
        """This function does the actual drawing of the lines in the axis."""
        # TODO:  Draw cones for arrows at the end of these lines

        prevLineWidth = glGetFloatv(GL_LINE_WIDTH)
        glLineWidth(2.0)
        with glSection(GL_LINES):
            glColor4f(1.0, 0.0, 0.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(self.axisLength, 0, 0)

            glColor4f(0.0, 1.0, 0.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, -self.axisLength, 0)

            glColor4f(0.0, 0.0, 1.0, 1.0)
            glVertex3f(0, 0, 0)
            glVertex3f(0, 0, -self.axisLength)    
        glLineWidth(prevLineWidth)

    def drawColorBarSlider(self, x, y, w, h, label, label_pos = 'top'):
        """Draw the color bar for links."""

        # need to call again to make sure this area is setup for overlay - only
        #   necessary because drawColorBar calls setup_overlay2D with the 
        #   color bar dims and now we need to change it back
        #print 'called drawColorBarSlider(x=',x,', y=',y,', w =',w,', h =',h,', label =',label,')'

        setup_overlay2D(x, y, w, h)
        num_pts = 100

        #glColor4f(0.25, 0.25, 0.25, 0.5) # remove this section after debugging
        #with glSection(GL_QUADS):
        #    glVertex3f(x, y, -0.1)
        #    glVertex3f(x + w, y, -0.1)
        #    glVertex3f(x + w, y + h, -0.1)
        #    glVertex3f(x, y + h, -0.1)

        #print 'drawColorBarSlider:  x =',x,', y =',y,', w =',w,', h =',h,', label =',label

        bar = []
        for i in range(num_pts+1):
            if label == 'L':
                val = float(i)/float(num_pts)
                color = self.map_link_color(val)
                if val < self.sliderOffsets[0] or val > self.sliderOffsets[1]:
                    # segment is outside of the sliders, make semi-transparent
                    color = list(color)
                    color[3] = 0.2
                    color = tuple(color)
                else:
                    color = list(color)
                    color[3] = 1.
                    color = tuple(color)
                bar.append(color)
            elif label == 'N':
                val = float(i)/float(num_pts)
                color = self.map_node_color(val)
                if val < self.sliderOffsets[2] or val > self.sliderOffsets[3]:
                    # segment is outside of the sliders, make semi-transparent
                    color = list(color)
                    color[3] = 0.2
                    color = tuple(color)
                else:
                    color = list(color)
                    color[3] = 1.
                    color = tuple(color)
                bar.append(color)

        if self.bright_bg_color:
            border_color = (0.3, 0.3, 0.3, 1.)
            fill_color = (0.7, 0.7, 0.7, 0.9)
        else:
            border_color = (0.7, 0.7, 0.7, 1.)
            fill_color = (0.3, 0.3, 0.3, 0.9)

        # the actual color bar is smaller, and re-aligned if toolBarPos is right
        #   or top so there is room for the slider-style mouse i/o on inside edge

        if self.toolBarPos == 'left' or self.toolBarPos == 'right':
            slider_offset = int(h * 0.1) # for the bottom triangle slider
            eff_w = int(w * 0.6) # how close the label is to the color bar
            eff_h = int(h * 0.8) - slider_offset # experimentally determined
        else:
            slider_offset = int(w * 0.1)
            eff_w = int(w * 0.8) - slider_offset # experimentally determined
            eff_h = int(h * 0.6) 

        # align the color bar
        if self.toolBarPos == 'right':
            aligned_x = x + w-eff_w # align bottom right
            aligned_y = y + slider_offset
        elif self.toolBarPos == 'bottom':
            aligned_x = x + w-eff_w - slider_offset # align bottom right
            aligned_y = y
        elif self.toolBarPos == 'top': # align top right
            aligned_y = y + h-eff_h
            aligned_x = x + w-eff_w - slider_offset
        elif self.toolBarPos == 'left':
            aligned_x = x
            aligned_y = y + slider_offset

        # offset the position of the color bar label to be centered on the bar
        if label_pos == 'top': 
            scale_factor = eff_w * 0.006 # scale by width
            char_width = glutStrokeWidth(GLUT_STROKE_ROMAN, ord(label)) * scale_factor
            x_offset = (eff_w-char_width)/2.
            y_offset = eff_h + char_width/2.
            tri_height = (w - eff_w)*0.75
            
        elif label_pos == 'left':
            scale_factor = eff_h * 0.006 # scale by height
            x_offset = 0
            y_offset = 3
            tri_height = (h - eff_h)*0.75

        # draw label
        with glMatrix():
            prevLineWidth = glGetFloatv(GL_LINE_WIDTH)
            glLineWidth(1.)
            # center the color bar label
            if self.toolBarPos == 'right':
                glTranslatef(w-eff_w, slider_offset, 0.)
            elif self.toolBarPos == 'left':
                glTranslatef(0., slider_offset, 0.)
            elif self.toolBarPos == 'top':
                glTranslatef(0, h-eff_h, 0.)
            glColor4f(*border_color)
            #print '\n\tdrawing char',label,'at x =',str(x+x_offset),', y =',\
            #    str(y+y_offset),', scale_factor =',scale_factor,', pixel_width =',glutStrokeWidth(GLUT_STROKE_ROMAN, ord(label))
            glTranslatef(x + x_offset, y + y_offset, 0.)
            glScalef(scale_factor, scale_factor, 1.)
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(label))
            glLineWidth(prevLineWidth)

        # draw arrows
        offset_low_x = 0
        offset_low_y = 0
        offset_high_x = 0
        offset_high_y = 0
        if self.toolBarPos == 'right':
            # offsets from bottom left corner of color bar
            offset_low_x = offset_high_x = -tri_height - 2 # -2 for border + 1 pixel extra
            offset_low_y = -tri_height/2.
            offset_high_y = eff_h - tri_height/2.
            direction = 'right'
        elif self.toolBarPos == 'left':
            offset_low_x = offset_high_x = eff_w + 2
            offset_low_y = -tri_height/2.
            offset_high_y = eff_h - tri_height/2.
            direction = 'left'
        elif self.toolBarPos == 'top':
            offset_low_y = offset_high_y = -tri_height - 2
            offset_low_x = -tri_height/2.
            offset_high_x = eff_w - tri_height/2.
            direction = 'up'
        elif self.toolBarPos == 'bottom':
            offset_low_y = offset_high_y = eff_h + 2
            offset_low_x = -tri_height/2.
            offset_high_x = eff_w - tri_height/2.
            direction = 'down'

        # Handle icon offsets by keeping track of normalized slider offset
        #   between 0 ( slider_low_x, slider_low_y) and 1 (slider_high_x, slider_high_y)
        
        #   TODO: check min/max slider bounds, and finally check
        #   other slider bar positions

        # triangle border
        slider_low_x = aligned_x + offset_low_x  # lower slider, min x pos
        slider_low_y = aligned_y + offset_low_y # lower slider, min y pos
        slider_high_x = aligned_x + offset_high_x # upper slider, max x pos
        slider_high_y = aligned_y + offset_high_y # upper slider, max y pos
        slider_range_x = slider_high_x - slider_low_x
        slider_range_y = slider_high_y - slider_low_y

        if label == 'L': # icon 0 is link bar slider, lower limit
            icon = 0
        else: # nodes, label == 'N'; icons 2 is node bar slider, lower limit
            icon = 2
        icon_low_x, icon_low_y, icon_range = self.getSliderParams(icon, 
            slider_low_x, slider_range_x, slider_low_y, slider_range_y)
        self.sliderPos[label] = icon_range

        # lower bound triangle
        glColor4f(*border_color) # for debugging
        with glMatrix():
            glTranslatef(icon_low_x, icon_low_y, 0.)
            self.drawTriangle(tri_height, tri_height, 0., 1., direction)
            #print 'DRAW_COLOR_BAR: before, iconHitBoxes =',self.iconHitBoxes,'; after, iconHitBoxes =',
            
        self.updateIconHitBoxes([icon], [[icon_low_x, icon_low_x + tri_height], 
            [icon_low_y, icon_low_y + tri_height]])

        if label == 'L': # icon 1 is link bar slider, upper limit
            icon = 1
        else: # nodes, label == 'N'; icon 3 is node bar slider, upper limit
            icon = 3
        icon_high_x, icon_high_y, icon_range = self.getSliderParams(icon, 
            slider_low_x, slider_range_x, slider_low_y, slider_range_y)
        self.sliderPos[label] = icon_range

        # upper bound triangle
        with glMatrix():
            glTranslatef(icon_high_x, icon_high_y, 0.)
            self.drawTriangle(tri_height, tri_height, 0., 1., direction)
            #print str(self.iconHitBoxes)

        self.updateIconHitBoxes([icon], [[icon_high_x, icon_high_x + tri_height], 
            [icon_high_y, icon_high_y + tri_height]])

        # fill
        glColor4f(*fill_color)
        border = 1
        with glMatrix():
            glTranslatef(icon_low_x + border, icon_low_y + border, 0.)
            self.drawTriangle(tri_height - 2*border, tri_height - 2*border, 0.1, 1., direction)
        with glMatrix():
            glTranslatef(icon_high_x + border, icon_high_y + border, 0.)
            self.drawTriangle(tri_height - 2*border, tri_height - 2*border, 0.1, 1., direction)

        if self.toolBarPos == 'top' or self.toolBarPos == 'bottom':
            flipColorBar = True
        else:
            flipColorBar = False

        # no label, do it manually to support label being on left not just top
        self.drawColorBar(bar, aligned_x, aligned_y, eff_w, eff_h, "", border_color, flipColorBar, num_pts)

    def drawColorBar(self, colors, bar_x, bar_y, bar_width, bar_height, label = "", 
        border_color = (0, 0, 0), flip_bar = False, num_pts = 100):
        """Draws a single colorbar at bar_x, bar_y with width bar_width
           and height bar_height.  If flip_bar, segments are drawn left to right
           instead of bottom to top.  Label is used to calculate the slider
           positions, and does not actually draw the label character.

           colors
               A list of sampled 11 sampled colors spanning the colormap.
            border_color
                Either black or white depending on the grey value of background.
        """
        setup_overlay2D(bar_x-1, bar_y-1, bar_width+2, bar_height + 14) #offsets to make room for borders

        prev_blend_on = glGetBoolean(GL_BLEND)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        with glMatrix():
            glLoadIdentity()
            glTranslatef(bar_x, bar_y, 0)

            if flip_bar:
                eff_size = bar_width
            else:
                eff_size = bar_height
            segment_size = float(eff_size) / float(num_pts)

            if flip_bar:
                seg_pts = [(0., bar_height, 0.), (0., 0., 0.), (segment_size, 0., 0.), (segment_size, bar_height, 0.)]
            else:
                seg_pts = [(0., 0., 0.), (bar_width, 0., 0.), (bar_width, segment_size, 0.), (0., segment_size, 0.)]

            for i in range(num_pts):
                if flip_bar:
                    trans_x = i*segment_size
                    trans_y = 0.
                else:
                    trans_x = 0.
                    trans_y = i*segment_size

                with glMatrix():
                    glTranslatef(trans_x, trans_y, 0.)
                    with glSection(GL_QUADS):
                        glColor4f(colors[i][0], colors[i][1], colors[i][2],
                            colors[i][3])
                        glVertex3f(*seg_pts[0])
                        glVertex3f(*seg_pts[1])
                        glColor4f(colors[i+1][0], colors[i+1][1],
                            colors[i+1][2], colors[i+1][3])
                        glVertex3f(*seg_pts[2])
                        glVertex3f(*seg_pts[3])


            # black box around gradient
            prev_lineWidth = glGetFloatv(GL_LINE_WIDTH)
            glLineWidth(2.)
            glColor4f(*border_color)
            with glMatrix():
                with glSection(GL_LINES):
                    glVertex3f(0., 0., 0.)
                    glVertex3f(bar_width, 0., 0.)
                    glVertex3f(bar_width, 0., 0.)
                    glVertex3f(bar_width, bar_height, 0.)
                    glVertex3f(bar_width, bar_height, 0.)
                    glVertex3f(0., bar_height, 0.)
                    glVertex3f(0., bar_height, 0.)
                    glVertex3f(0., 0., 0.)
            glLineWidth(prev_lineWidth)

            # Section copied from Boxfish.ColorBars.drawGLColorBar()
            default_text_height = 152.38
            scale_factor = 1.0 / default_text_height * segment_size
            scale_factor = 0.08
            if len(label) > 0:
                with glMatrix():
                    glTranslatef(7, bar_height + 3, 0.2)
                    glScalef(scale_factor, scale_factor, scale_factor)
                    for c in label:
                        glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(c))


        if not prev_blend_on:
            glDisable(GL_BLEND)

    # ------------------------    Render, Level 4    ---------------------------

    def drawTriangle(self, w, h, z_dist, size, direction):
        ''' Draws an arrow head pointing left, right, up, down depending on
        direction.  Size is normalized, 0 to 1.
        '''
        if direction == 'left':
            glTranslatef(-1, 0., 0.)
            with glSection(GL_TRIANGLES):
                glVertex3f(w, 0., z_dist)
                glVertex3f(w, h, z_dist)
                glVertex3f(w*(1-size), h*0.5, z_dist)
        elif direction == 'right':
            glTranslatef(1, 0., 0.)
            with glSection(GL_TRIANGLES):
                glVertex3f(0., 0., z_dist)
                glVertex3f(w*size, h*0.5, z_dist)
                glVertex3f(0., h, z_dist)
        elif direction == 'up':
            glTranslatef(0., 1., 0.)
            with glSection(GL_TRIANGLES):
                glVertex3f(0., 0., z_dist)
                glVertex3f(w, 0., z_dist)
                glVertex3f(w*0.5, h*size, z_dist)
        elif direction == 'down':
            glTranslatef(0., -1., 0.)
            with glSection(GL_TRIANGLES):
                glVertex3f(0., h, z_dist)
                glVertex3f(w, h, z_dist)
                glVertex3f(w*0.5, h*(1-size), z_dist)


    # **************************        I/O       ******************************

    def changeLinkWidth(self, inc = True):
        val = self.link_width*0.1 if inc else -self.link_width*0.1
        self.link_width += val
        if not inc: self.link_width = max(0.001,self.link_width)
        glLineWidth(self.link_width)
        self.updateDrawing()

    def changeNodeLinkBounds(self, lower, upper, links = True):
        if links:
            self.lowerBoundLinks = lower
            self.upperBoundLinks = upper
        else: 
            self.lowerBoundNodes = lower
            self.upperBoundNodes = upper

    def changeNodeSize(self, inc):
        val = 0.025 if inc else -0.025
        self.node_size += val
        if not inc: self.node_size = max(0.025, self.node_size)
        #print 'self.node_size = ' + str(self.node_size)
        self.updateDrawing() 

    def changeSliderOffsets(self, num, x, y):
        ''' Calculate the difference between initial icon click and current x, y
        position of the mouse, and adjust the offset to the right level.'''
        if num < 2:
            label = 'L'
        else:
            label = 'N'

        if num%2 == 0:
            lower = True
        else:
            lower = False

        if self.toolBarPos == 'left' or self.toolBarPos == 'right':
            self.sliderOffsets[num] = (y-self.sliderPos[label][0])/ \
              (self.sliderPos[label][1] - self.sliderPos[label][0])
        elif self.toolBarPos == 'top' or self.toolBarPos == 'bottom':
            self.sliderOffsets[num] = (x-self.sliderPos[label][0])/ \
              (self.sliderPos[label][1] - self.sliderPos[label][0])

        if lower:
            self.sliderOffsets[num] = min(self.sliderOffsets[num],
                self.sliderOffsets[num+1])
            self.sliderOffsets[num] = max(0, self.sliderOffsets[num])
        else:
            self.sliderOffsets[num] = max(self.sliderOffsets[num],
                self.sliderOffsets[num-1])
            self.sliderOffsets[num] = min(1, self.sliderOffsets[num])

    def keyPressEvent(self, event):
        key_map = {"r" : lambda : self.resetColorBarSliders(),
                   "R" : lambda : self.resetColorBarSliders(),
                   "l" : lambda : self.changeLinkWidth(inc = True),
                   "L" : lambda : self.changeLinkWidth(inc = False),
                   "n" : lambda : self.changeNodeSize(inc = True),
                   "N" : lambda : self.changeNodeSize(inc = False)
                   }

        if event.text() in key_map:
            key_map[event.text()]()
        else:
            super(Torus5dViewSlice3d, self).keyPressEvent(event)

    def mousePressEvent(self, event):
        """We capture right clicking for picking here."""
        super(Torus5dViewSlice3d, self).mousePressEvent(event)

        # Return if haven't dragged module onto the data tree yet to prevent
        #   the error when mouse I/O fails to return, causing any keyboard
        #   modifier (shift, contrl..) to be mis-interpreted as mouseEvent
        if max(self.shape) == 0:
            return

        x = event.x()
        y = self.height() - event.y()

        if event.button() == Qt.LeftButton:
            # first check if clicking an icon
            found = False
            self.iconSelected = [False for j in range(self.numIcons)]
            for i in range(self.numIcons):
                #print 'x =',y,', y =',y,', iconHitBoxes['+str(i)+'] =',self.iconHitBoxes[i]
                if x >= self.iconHitBoxes[i][0][0] and x <= self.iconHitBoxes[i][0][1] \
                  and y >= self.iconHitBoxes[i][1][0] and y <= self.iconHitBoxes[i][1][1]:
                    found = True
                    self.iconSelected[i] = True
                    #print 'HIT, icon ',i,', iconSelected =',self.iconSelected

            # next check if clicking outside an icon but inside the toolbar area
            if not found and x >= self.toolBarDims[self.toolBarPos][0][0] \
              and x <= self.toolBarDims[self.toolBarPos][0][1] \
              and y >= self.toolBarDims[self.toolBarPos][1][0] \
              and y <= self.toolBarDims[self.toolBarPos][1][1]:
                self.toolBarSelected = True
                self.updateDrawing(nodes = False, links = False, grid = False)

            #print 'x =',x,', y =',y,', iconHitBoxes =',self.iconHitBoxes

        elif event.button() == Qt.RightButton:
            self.parent.agent.selectionChanged([["nodes", self.selectionPick(event)]])

    def mouseReleaseEvent(self, event):
        """We keep track of whether a drag occurred with right-click."""
        super(Torus5dViewSlice3d, self).mouseReleaseEvent(event)

        # Return if haven't dragged module onto the data tree yet to prevent
        #   the error when mouse I/O fails to return, causing any keyboard
        #   modifier (shift, contrl..) to be mis-interpreted as mouseEvent
        if max(self.shape) == 0:
            return

        if self.toolBarSelected:
            self.toolBarSelected = False
            self.updateDrawing(nodes = False, links = False, grid = False)

        for i in [0, 1]: # i = 0 for Links color bar, i = 1 for Nodes
            if self.iconSelected[2*i] or self.iconSelected[2*i+1]:
                if i == 0: # links
                    self.boundsUpdateSignal.emit(self.sliderOffsets[2*i],
                      self.sliderOffsets[2*i+1], True)
                else:
                    self.boundsUpdateSignal.emit(self.sliderOffsets[2*i],
                      self.sliderOffsets[2*i+1], False) # update node bounds


    def mouseMoveEvent(self, event):
        x = event.x()
        y = self.height()-event.y() # since x,y pos is from bottom left
        
        if self.toolBarSelected:
            
            pos = self.toolBarPos

            # check if we've dragged outside of the tool bar position, and if so
            #   move the tool bar onto that new area
            outside = (x < self.toolBarDims[pos][0][0] or
                x > self.toolBarDims[pos][0][1] or
                y < self.toolBarDims[pos][1][0] or
                y > self.toolBarDims[pos][1][1])
            check_list = set(['top', 'bottom', 'left', 'right'])
            check_list.remove(pos)

            # even if we're not outside, check which half we're in to maybe flip
            half_w = self.toolBarDims[pos][0][0] + \
              (self.toolBarDims[pos][0][1]-self.toolBarDims[pos][0][0])/2.
            half_h = self.toolBarDims[pos][1][0] + \
              (self.toolBarDims[pos][1][1]-self.toolBarDims[pos][1][0])/2.
            if ((pos == 'right' or pos == 'left') and y < half_h) or \
              ((pos == 'top' or pos == 'bottom') and x < half_w):
                if not self.toolBarFlip:
                    self.toolBarFlip = True
                    self.updateDrawing(nodes = False, links = False, grid = False)
            else:
                if self.toolBarFlip:
                    self.toolBarFlip = False
                    self.updateDrawing(nodes = False, links = False, grid = False)

            if outside:
            # check other possible toolbar positions
                for pos in check_list:
                    if (x >= self.toolBarDims[pos][0][0] and x <=
                      self.toolBarDims[pos][0][1] and y >=
                      self.toolBarDims[pos][1][0] and y <=
                      self.toolBarDims[pos][1][1]):
                        self.toolBarPos = pos
                        self.updateDrawing(nodes = False, links = False, grid = False)
                        break
            #print 'MOVE: toolBarFlip =',self.toolBarFlip
        else:
            # check if selected an icon, and handle the slider movement
            found = False
            for i in range(self.numIcons):
                if self.iconSelected[i]: # clicked this icon
                    self.changeSliderOffsets(i, x, y)
                    found = True
                    break
            if found:
                self.updateDrawing()
            else:
                super(Torus5dViewSlice3d, self).mouseMoveEvent(event)                

    def resetColorBarSliders(self):
        for i in np.arange(0, self.numIcons, 2):
            lower_slider = self.sliderOffsets[i]
            upper_slider = self.sliderOffsets[i+1]
            #print 'i =',i,', lower_slider =',lower_slider,', upper_slider =',upper_slider
            if lower_slider > sys.float_info.epsilon or upper_slider < \
              1-sys.float_info.epsilon:
                self.boundsUpdateSignal.emit(0., 1., True) # update links
                self.boundsUpdateSignal.emit(0., 1., False) # update nodes
        self.sliderOffsets = [0 if i%2==0 else 1 for i in range(self.numIcons)]
        self.updateDrawing()

    def selectionPick(self, event):
        """Allow the user to pick nodes."""
        # Adapted from Josh Levine's version in Boxfish 0.1
        #steps:
        #render the scene with labeled nodes
        #find the color of the pixel @self.x, self.y
        #map color back to id and return




        #disable unneded
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
        glDisable(GL_BLEND)

        #set up the selection buffer
        select_buf_size = reduce(operator.mul, self.shape) + 10
        glSelectBuffer(select_buf_size)

        #switch to select mode
        glRenderMode(GL_SELECT)

        #initialize name stack
        glInitNames()
        glPushName(0)

        #set up the pick matrix to draw a narrow view
        viewport = glGetIntegerv(GL_VIEWPORT)
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        #this sets the size and location of the pick window
        #changing the 1,1 will change sensitivity of the pick
        gluPickMatrix(event.x(),(viewport[3]-event.y()),
            1,1,viewport)
        set_perspective(self.fov, self.width()/float(self.height()),
            self.near_plane, self.far_plane)
        #switch back to modelview and draw the scene
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        glTranslatef(*self.translation[:3])
        glMultMatrixd(self.rotation)

        #let's draw some red boxes, color is inconsequential
        box_size = self.node_size
        glColor3f(1.0, 0.0, 0.0)

        # Redo the drawing
        glPushMatrix()
        #self.resetView()  # need this?
        self.centerView()

        # And draw all the cubes
        # color index variable
        w, h, d = self.axis_map[self.axis][self.axis_index]

        slice_shape = tuple(self.getSliceShape())

        # TODO:  Figure out why the link_ids coming back after selecting a node
        #   aren't correct (or aren't drawn correctly)

        for node in np.ndindex(*self.shape):
        # do this to reduce the number of nodes to index through,
        # since we're only doing this for a specific plane
        #for slice_node in np.ndindex(*slice_shape):
            #node = self.getFullNode(slice_node)
            #print 'loaddName = ' + str(self.dataModel.coord_to_node[node])
            glLoadName(self.dataModel.coord_to_node[node])
            glPushMatrix()
            if node[d] == self.current_planes[d] and node[4] == self.current_planes[4]:
                glTranslatef(*self.getNodePos3d(self.getSliceNode(node)))
                notGlutSolidCube(box_size)
            glPopMatrix()

        glPopMatrix()

        #pop projection matrix
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glFlush()

        #get the hit buffer
        glMatrixMode(GL_MODELVIEW)
        pick_buffer = glRenderMode(GL_RENDER)
 
        #this code finds the nearest hit.  
        #Otherwise, populate hitlist with hit[2] for all
        #pick_buffer has a 3-tuple of info, [near, far, name]
        nearest = 4294967295
        hitlist = []
        for hit in pick_buffer :
            #print 'SELECTION:  hit[0] = ' + str(hit[0]) + ', hit[1] = ' + str(hit[1]) + ', hit[2] = ' + str(hit[2])
            if hit[0] < nearest :
              nearest = hit[0]
              hitlist = [hit[2][0]]

        #go back to normal rendering
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        #print hitlist
        return hitlist

