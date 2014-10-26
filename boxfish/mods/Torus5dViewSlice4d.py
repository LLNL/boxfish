import math
import numpy as np
from OpenGL.GL import *
from Torus5dModule import *
from boxfish.gl.glutils import *
from OpenGL.GLUT import *
from OpenGL.GLE import glePolyCylinder

class Torus5dViewSlice4d(Torus5dGLWidget):
    ''' Draws a view of the 5d torus.  For each combination of fourth and fifth
    dimension values there is one three dimensional structure, drawn as a 
    lower 2-dimensional projection, i.e. plane, in OpenGL-xy space.  The fourth
    dimension values are mapped to OpenGL-z space, and the fifth is a position
    offset in OpenGL-x space.  See UserGuide_5dTorus.pdf for more information.
    '''

    # ***************************    Initialize    *****************************

    def __init__(self, parent, dataModel):
        ''' Set the parent for propagating signals up and load the data model 
        for drawing.
        '''
        super(Torus5dViewSlice4d, self).__init__(parent, dataModel, rotation=True)

        # class vars to initialize
        self.resizeSignal.connect(self.updateDrawing)
        self.drawELinks = False
        self.drawOnlyELinks = False
        self.plane_spacing = 10
        self.drawDepthLinks = False
        self.drawOnlyDepthLinks = False
        self.switchedCurrentEDim = False
        self.link_width = 12.
        self.right_drag = False
        self.insetEDim = True
        self.oldInsetEDim = False
        self.eDimSpacingFactor = 1.5
        self.toolBarSelected = False
        self.toolBarPos = 'right'
        self.toolBarFlip = False
        self.iconAspectRatio = 0.7
        self.numIcons = 5
        self.showGrid = True
        Qt.ShiftModifier = False # to fix the weird vertical translation bug

        # to create a new display list for rendering
        #   1.  Create object with constructor call DisplayList(render_function) 
        #   2.  Add the display list object to widget2dLists if the rendering
        #       is an overlaid 2d orthographic projection, or widget3dLists if 
        #       rendering a 3d perspective projection -see draw() and glutils.py
        #   3.  In updateDrawing(), call displayList.update()
        #   4.  In draw(), make sure widget2dLists and widget3dLists are called-
        #       func's in widget2dLists must be called 'with glutils.overlays2D()'
        #   5.  Render_function's of widget2dLists must have call to 
        #       setup_overlay2D() to set orthographic projection and clipping
        #   6.  Add all OpenGL calls to the render_function given in constructor
        #   7.  Whenever window needs updating, either implicitly from a resize
        #       event or explicitly by calls to updateGL() which calls paintGL()
        #       the display list is checked - if there was a call to
        #       displayList.update() since the last redraw, the render_function
        #       gets called and the OpenGL scene gets drawn

        # display lists for nodes and links, get called from draw()
        self.widget3dLists = []
        self.nodeList = DisplayList(self.drawNodes)
        self.linkList = DisplayList(self.drawLinks)
        self.gridList = DisplayList(self.drawGrid)
        self.widget3dLists.append(self.nodeList)
        self.widget3dLists.append(self.linkList)
        self.widget3dLists.append(self.gridList)

        self.widget2dLists = []
        self.toolBarList = DisplayList(self.drawToolBar)
        self.widget2dLists.append(self.toolBarList)
        
        # initially push view back since no updateAxis call
        self.updateAxis(0, 0)

    shape = property(fget = lambda self: self.dataModel.shape)
    view_planes = property(fget = lambda self: self.dataModel.view_planes)
    current_planes = property(fget = lambda self: self.dataModel.current_planes)

    def initializeGL(self):
        '''Turns up the ambient light for this view and enables simple
           transparency.
        '''
        super(Torus5dViewSlice4d, self).initializeGL()
        #glLightfv(GL_LIGHT0, GL_AMBIENT,  [1.0, 1.0, 1.0, 1.0])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glLineWidth(self.link_width)


    # ***************************      Update      *****************************

    def resetView(self):
        # Set initial position based on the size and axis of the model

        slice_shape = self.getSliceShape()
        w_span, h_span = slice_shape[0], slice_shape[1]
        if w_span != 0 and h_span != 0:
            spans = self.getSliceSpan(slice_shape)
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

    def update(self, colors = True, nodes = True, links = True, reset = True):
        ''' Resets the model view and re-draws the scene.'''
        if colors: super(Torus5dViewSlice4d, self).update()
        if reset: self.resetView()
        self.updateDrawing(nodes, links)
        
    def updateDrawing(self, nodes = True, links = True, grid = True, toolBar = True):
        ''' Re-draws the scene without resetting the model view.'''
        if nodes: self.nodeList.update()
        if links: self.linkList.update()
        if grid: self.gridList.update()
        if toolBar: 
            self.updateToolBarPos()
            self.toolBarList.update()
        #self.updateGL()
        self.paintEvent(None)

    def updateAxis(self, axis, axis_index = -1):
        ''' Slot for agent.axisUpdateSignal.  Updates the current axis which
        uniquely defines the particular view. 
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
        
            self.update(colors = False, links = True, nodes = True, reset = True)

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

    def updateIconHitBoxes(self, indicies, vals):
        ''' Increment all hit boxes with index in indicies by the values in vals.'''

        for i in indicies:
            self.iconHitBoxes[i][0][0] += vals[0][0]
            self.iconHitBoxes[i][0][1] += vals[0][1]
            self.iconHitBoxes[i][1][0] += vals[1][0]
            self.iconHitBoxes[i][1][1] += vals[1][1]


    # ***************************    Calculate     *****************************

    def getAxisLabelColor(self, val):
        if val == 'a': 
            color = (0.1, 0.6, 0.2, 1.)
        elif val == 'b': 
            color = (0.1, 0.1, 1., 1.)
        elif val == 'c': 
            color = (1., 0.5, 0.1, 1.) 
        elif val == 'd':  
            color = (0.45, 0.1, 0.65, 1.)
        elif val == 'e': # not currently used
            color = (0.8, 0.8, 0.1, 1.)
        elif val == 0: # selected
            color = (0.7, 0.2, 0.2, 1.)
        
        return tuple(list(np.add(color[:3], 0.2)) + [1.])

    def getCylinderIndex(self, node, shape, axis):
        """This function is for finding the index of the squared cylinder
           containing particular points in the torus.  Cylinders are
           defined for a shape, along a particular axis.
           i.e., if the axis is going into the screen, cylinders are:

               +---------------+  Cylinder 4 (outermost)
               | +-----------+ |  Cylinder 3
               | | +-------+ | |  Cylinder 2
               | | | +---+ | | |  Cylinder 1
               | | | | + | | | |  Cylinder 0 (innermost)
               | | | +---+ | | |
               | | +-------+ | |
               | +-----------+ |
               +---------------+

           In the case of odd dimensions (as in above), the innermost
           cylinder is really not a cylinder but leftover odd links.

           A cylinder is computed for a point by by finding distance
           from nearest edge in each dimension.
        """
        dims = shape[:axis] + shape[axis+1:]
        num_cylinders = (min(dims) + 1) / 2
        nonaxis = node[:axis] + node[axis+1:]
        d_near_edge = [min(abs(d - n - 1), n) for n, d in zip(nonaxis, dims)]
        return num_cylinders - min(d_near_edge) - 1

    def getNextAxisIndex(self):
        ''' Return the next axis index when changing view with keyboard change
        axis commands.
        '''
        numIndicies = len(self.axis_map[self.axis]) # num_views for that axis
        if self.axis_index == numIndicies - 1: #wraparound
            return 0
        else: return self.axis_index + 1

    def getNextNode(self, point, axis, amount):
        """Increments the <axis> dimension in the point by <amount>"""
        p = list(point)
        p[axis] += amount
        return tuple(p)

    def getNodePos2d(self, node, shape, axis = 2, scale = 1):
        ''' Returns the OpenGL xy position of this node.
        '''    
        dim = range(3)
        dim.remove(axis)
        node2d = np.zeros(3)
        for d in dim:
            node2d[d] = scale * self.getSliceCoord(shape, axis, node, d) # e-dim is now 3 not 4
        
        node2d[0] += self.getNodeXOffset(node[3])
        node2d *= self.axis_directions
        return node2d

    def getNodePos3d(self, node, shape = None, axis = None, scale = 1):
        ''' Returns the OpenGL xyz position of this node.  Calls getNodePos2d.
        '''
        if shape == None:
            shape = self.shape
        if axis == None:
            axis = self.axis

        w, h, d = self.getSliceDims()
        slice_shape = self.getSliceShape()
        #z_dist = node[d] * self.gap * self.plane_spacing * self.axis_directions[2]
        z_dist = node[d] * self.plane_spacing * self.axis_directions[2]
        # concatonate with the e-dimension explicitly
        node2d = self.getNodePos2d(tuple(self.getSliceNode(node) + [node[4]]), slice_shape)

        #node2d = self.getNodePos2d(tuple(self.getSliceNode(node)), slice_shape)
        return [node2d[0], node2d[1], z_dist]
    
    def getNodeXOffset(self, e_val):
        ''' Return offset in OpenGL x to keep view centered about the grid.'''
        # if insetting the e-dim, offset in pos x-dir slightly to be in the center
        #   of where the two tori are when not insetting - i.e. when switching
        #   from side-by-side to inset, the torus on the right slides left and
        #   the torus on the left slides right, to meet at the center
        if self.insetEDim:
            return (self.getSliceSpan()[0]*self.eDimSpacingFactor)/2.
        # offset in the positive x-direction if not insetting the e-dim and e-val == 1
        elif not self.insetEDim and e_val == 1: 
            return (self.getSliceSpan()[0]* self.eDimSpacingFactor)
        else:
            return 0
    
    def getSliceCoord(self, shape, axis, node, dim):
        # this is for e-links being on, len(node) = 4 not 3 now (axis = 2 still)

        # e-link value is node[3] not node[4], since the d-plane was removed
        lsize = self.link_pack_factor # spacing between lines
        #lsize = self.link_width * self.link_pack_factor
        center = float(shape[dim] - 1) / 2

        if center == node[dim]: # straight line
            if dim == 1: # offset mo3re for vertical axis, to make ~67 degree lines, not just 45
                offset_edim = lsize * self.elink_offset_center_y 
            else:
                offset_edim = lsize * self.elink_offset_center_x # could be -lsize as well, doesn't matter
        else:
            if dim == 1: # offset more for vertical axis
                offset_edim = np.sign(center - node[dim]) * lsize * self.elink_offset_diagonal_y
            else:   
                offset_edim = np.sign(center - node[dim]) * lsize * self.elink_offset_diagonal_x
        inset_axis = node[axis] * lsize * np.sign(center - node[dim])
        even = (shape[dim] % 2 == 0)
        if dim == 1: # to account for larger offset for vertical axis
            #lgroup = ((shape[axis]-1) * lsize) + (3 * lsize) + self.gap
            lgroup = (shape[axis]-1) + 3 + self.gap
        else:
            #lgroup = ((shape[axis]-1) * lsize) + ((3 * lsize) / 2) + self.gap
            lgroup = (shape[axis]-1) + 1.5 + self.gap

        if not self.insetEDim:
            offset_edim = 0 # take care of offsetting in getNodePos2d

        return lgroup * (node[dim] + int(even and node[dim] > center)) + node[3] * offset_edim + inset_axis

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

    def getSliceSpan(self, shape = None, axis = 2):
        """Span in OpenGL 2D space of each dimension of the 2D view"""
        if shape == None:
            shape = self.getSliceShape()

        if len(shape) != 3:
            #print 'ERROR:  Called sliceSpan with shape != 3'
            return 

        w_span = abs(self.getSliceCoord(shape, axis, [0, 0, 0, 0], 0) - 
            self.getSliceCoord(shape, axis, [shape[0]-1, 0, 0, 0], 0))
        h_span = abs(self.getSliceCoord(shape, axis, [0, 0, 0, 0], 1) - 
            self.getSliceCoord(shape, axis, [0, shape[1]-1, 0, 0], 1))
        d_span = abs(self.getSliceCoord(shape, axis, [0, 0, 0, 0], 2) - 
            self.getSliceCoord(shape, axis, [0, 0, shape[2]-1, 0], 2))
        return [w_span, h_span, d_span]


    # ****************************     Render      *****************************

    # ------------------------    Render, Level 0    ---------------------------

    #def paintGL(self):
    #    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    #    glGetError()
    #    self.orient_scene()
    #    self.draw()
    #    super(Torus5dViewSlice4d, self).paintGL()
    
    def paintEvent(self, event):
        with setupPaintEvent(self):
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glGetError()
            self.orient_scene()
            self.draw()
            super(Torus5dViewSlice4d, self).paintEvent(None)

    # ------------------------    Render, Level 1    ---------------------------
    
    def draw(self):
        for func in self.widget3dLists:
            func() # display lists, call drawLinks(), drawNodes(), drawGrid()

        with overlays2D(self.width(), self.height(), self.bg_color):
            for func in self.widget2dLists:
                func() # call drawToolBar()

    # ------------------------    Render, Level 2    ---------------------------
    
    def drawGrid(self):
        ''' Draws a grid in the xz-plane to go under the 5d torus drawing.'''

        if not self.showGrid:
            return

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

        grey_value = (self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) /  3
        if grey_value >= 0.35:
            line_color = (0.3, 0.3, 0.3, 0.3)
        else:
            line_color = (0.6, 0.6, 0.6, 0.3)

        glColor4f(*line_color) # was 0.5, 0.5, 0.5, 0.5
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

    def drawLinks(self):
        self.drawLinks3d(self.link_colors)

    def drawNodes(self):
        # to avoid error when dataModel is set but Torus5dModule.updateColors hasn't been called yet
        if self.node_colors.shape[0] == 0:
            return

        glPushMatrix()
        slice_shape = self.getSliceShape()
        self.centerView(slice_shape)
        w, h, d = self.getSliceDims()
        higher_dims = [i for i in range(len(self.shape)) if i not in [w, h, d, self.axis]] 

        for node5d in np.ndindex(*self.shape):
            glPushMatrix()
            #print '\tnodeID = ' + str(node5d)
            #print '\td = ' + str(d)
            #print '\tnode5d[d] = ' + str(node5d[d])
            #print '\tself.view_planes[d] = ' + str(sorted(self.view_planes[d]))
            if (node5d[d], node5d[4]) in self.view_planes[d]:
                # center around the mapped noded
                node3d = self.getNodePos3d(node5d, self.shape, self.axis)
                #print 'node3d = ' + str(node3d)

                #print '\tshape = ' + str(self.shape) + ', node_colors.shape = ' + str(self.node_colors.shape) + ', nodeID = ' + str(node5d)
                #print '\tnodePosition = ' + str(node3d)
                glTranslatef(*node3d)

                # Draw cube with node color from the model
                index = [node5d[i] for i in range(len(self.shape))]
                #print '\tindex = ' + str(index)
                glColor4f(*self.node_colors[index[0], index[1], index[2], index[3], index[4]])
                notGlutSolidCube(self.node_size)

            glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()        

    def drawToolBar(self):

        if max(self.shape) == 0: # since need to know parent to get coords label
            return

        self.bright_bg_color = ((self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) /  3) >= 0.5

        if self.bright_bg_color:
            fill_color = (0.7, 0.7, 0.7, 0.9)
            line_color = (0.2, 0.2, 0.2, 0.9)
        else:
            fill_color = (0.3, 0.3, 0.3, 0.9)
            line_color = (0.8, 0.8, 0.8, 0.9)

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        x = self.toolBarDims[self.toolBarPos][0][0]
        w = self.toolBarDims[self.toolBarPos][0][1]-x
        y = self.toolBarDims[self.toolBarPos][1][0]
        h = self.toolBarDims[self.toolBarPos][1][1]-y

        # three icons so far, create hit boxes
        self.iconHitBoxes = [[[0, 0], [0, 0]] for i in range(self.numIcons)]

        setup_overlay2D(x, y, w, h)

        with glMatrix():
            glLoadIdentity() # must have this to not be affected by resetView()
            glTranslatef(x, y, 0.)
            self.updateIconHitBoxes(range(self.numIcons), [[x, x], [y, y]])

            # draw transparent quad behind buttons to show toolbar is selected
            if self.toolBarSelected: 
                if self.bright_bg_color:
                    glColor4f(0., 0., 0., 0.1)
                else:
                    glColor4f(1., 1., 1., 0.1)

                if self.toolBarPos == 'top' or self.toolBarPos == 'bottom':
                    eff_w = w
                    eff_h = h * self.iconAspectRatio
                else:
                    eff_w = w
                    eff_h = h

                with glMatrix():
                    if self.toolBarPos == 'top': # translate up slightly
                        glTranslatef(0., h-eff_h, 0.)
                        self.updateIconHitBoxes(range(self.numIcons), [[0, 0], [h-eff_h, h-eff_h]])
                    with glSection(GL_QUADS):
                        glVertex3f(0., 0., -0.3)
                        glVertex3f(eff_w, 0., -0.3)
                        glVertex3f(eff_w, eff_h, -0.3)
                        glVertex3f(0., eff_h, -0.3)

            # draw icons/buttons - if toolBarPos is right/left the icon goes
            #   on top, buttons below; if toolBarPos is top/bottom the icon
            #   goes on the right, buttons to the left
            if self.toolBarPos == 'left' or self.toolBarPos == 'right':
                width_lrg = w*0.8
                height_lrg = width_lrg * self.iconAspectRatio
                width_sm = width_lrg
                height_sm = width_sm/2.
                center_sm = (width_lrg-width_sm)/2. # to center about large icon
            else:
                width_lrg = h*0.8
                height_lrg = width_lrg * self.iconAspectRatio
                width_sm = width_lrg
                height_sm = width_sm/2.
                center_sm = (height_lrg-height_sm)/2. # to center about large icon

            space = width_lrg * 0.1
            icon_x = w - width_lrg - space
            if self.toolBarPos == 'bottom':
                icon_y = space
            else:
                icon_y = h - height_lrg - space

            if self.toolBarPos == 'left' or self.toolBarPos == 'right':
                spread_button_x = w - space - width_sm - center_sm
                spread_button_y = icon_y - 2*space - height_sm
                link_button_x = spread_button_x
                link_button_y = spread_button_y - 2*space - height_sm
                if self.toolBarFlip:
                    icon_y = space
                    spread_button_y = icon_y + height_lrg + 2*space
                    link_button_y = spread_button_y + height_sm + 2*space
            else:
                spread_button_x = icon_x - 2*space - width_sm
                if self.toolBarPos == 'bottom':
                    spread_button_y = space + center_sm
                else:
                    spread_button_y = h - space - height_sm - center_sm
                link_button_x = spread_button_x - 2*space - width_sm
                link_button_y = spread_button_y
                if self.toolBarFlip:
                    icon_x = space
                    spread_button_x = icon_x + width_lrg + 2*space
                    link_button_x = spread_button_x + width_sm + 2*space

            self.drawButtonViewToggle(icon_x, icon_y, width_lrg, height_lrg, line_color, fill_color)
            self.drawButtonPlusMinus(spread_button_x, spread_button_y, width_sm, height_sm, line_color, fill_color)
            self.drawButtonLinkToggle(link_button_x, link_button_y, width_sm, height_sm, line_color, fill_color)

        glDisable(GL_BLEND)    

    # ------------------------    Render, Level 3    ---------------------------

    def centerView(self, slice_shape, axis = 2, scale = 1):
        half_spans = np.array(self.getSliceSpan(slice_shape), np.float) / -2
        half_spans[axis] = 0
        half_spans *= self.axis_directions
        half_spans *= scale
        # compensate for x-offset based on e-dimension value
        if self.insetEDim: 
            half_spans[0] -= self.getNodeXOffset(1) # /2 factor already in getNodeXOffset
        else:
            half_spans[0] -= self.getNodeXOffset(1)/2.
        glTranslatef(*half_spans)

    def drawButtonLinkToggle(self, x, y, w, h, line_color, fill_color):

        deselect_color = np.divide(np.add(line_color, fill_color), 2.) # mean

        with glMatrix():
            glTranslatef(x, y, 0.)
            self.updateIconHitBoxes([3], [[x, x+w/2.],[y, y+h]])
            self.updateIconHitBoxes([4], [[x+w/2., x+w],[y, y+h]])
            
            border_width = 1.
            # draw two rectangles side-by-side
            self.drawRectSplit(w, h, border_width, line_color, fill_color)

            # account for the border of the split box
            glTranslatef(border_width, border_width, 0.)
            w = (w-3*border_width)/2.
            h = h-2*border_width

            # draw the 4th dimension colored border
            w_dim, h_dim, d_dim = self.getSliceDims()
            d_char = self.parent.agent.coords[d_dim]
            if self.drawDepthLinks:
                glColor4f(*self.getAxisLabelColor(d_char))
            else:
                glColor4f(*deselect_color)
            self.drawBorderPrecise(w, h, 2., 0.1)

            # draw the 4th dimension char label
            glLineWidth(1.)
            glColor4f(*line_color)
            eff_size = min(w, h)
            scale_factor = eff_size*0.006 # by experiment
            with glMatrix():
                glTranslatef(w*0.25, h*0.22, 0.) # by experiment
                glScalef(scale_factor, scale_factor, 1.)
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(d_char))

            # draw 5th dimension colored border
            glTranslatef(w+border_width, 0., 0.)
            e_char = self.parent.agent.coords[4]
            if self.drawELinks:
                glColor4f(*self.getAxisLabelColor(e_char))
            else:
                glColor4f(*deselect_color)
            self.drawBorderPrecise(w, h, 2., 0.1)

            # draw 5th dimension char label
            glLineWidth(1.)
            glColor4f(*line_color)
            with glMatrix():
                glTranslatef(w*0.25, h*0.22, 0.) # by experiment
                glScalef(scale_factor, scale_factor, 1.)
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(e_char))

            # TODO: Draw coord labels with borders, verify w/ mouse I/O

    def drawButtonPlusMinus(self, x, y, w, h, line_color, fill_color):

        with glMatrix():
            glTranslatef(x, y, 0.)
            self.updateIconHitBoxes([1], [[x, x+w/2.],[y, y+h]])
            self.updateIconHitBoxes([2], [[x+w/2., x+w],[y, y+h]])
            
            border_width = 1.
            # draw two rectangles side-by-side
            self.drawRectSplit(w, h, border_width, line_color, fill_color)

            # account for the border of the split box
            glTranslatef(border_width, border_width, 0.)

            # draw a minus sign on the left half of the split box
            if self.bright_bg_color:
                offset = -0.1
            else:
                offset = 0.1
            sign_color = (line_color[0]+offset, line_color[1]+offset, line_color[2]+offset, line_color[3])
            w = (w-3*border_width)/2.
            h = h-2*border_width
            line_len = min(w, h) * 0.8
            x_start = w - line_len 
            x_end = w - x_start
            y_start = h - line_len
            y_end = h - y_start

            glLineWidth(1.)
            glColor4f(*sign_color)
            with glSection(GL_LINES):
                glVertex3f(x_start, h/2., 0.)
                glVertex3f(x_end, h/2., 0.)

            # draw a plus sign on the right half of the split box
            glTranslatef(border_width + w, 0., 0.)
            with glSection(GL_LINES):
                glVertex3f(x_start, h/2., 0.)
                glVertex3f(x_end, h/2., 0.)
                glVertex3f(w/2., y_start, 0.)
                glVertex3f(w/2., y_end, 0.)

    def drawButtonViewToggle(self, x, y, w, h, line_color, fill_color):
        ''' Draw an icon which when clicked changes e-dimension from inset to 
        side by side and vice-versa.'''

        e0_color = (0.1, 0.1, 0.9, 1.)
        e1_color = (0.9, 0.4, 0.1, 1.)

        with glMatrix():
            glTranslatef(x, y, 0.)
            self.updateIconHitBoxes([0], [[x, x+w], [y, y+h]])
            
            if self.drawELinks:
                alpha_offset = 0.6
                line_color = list(line_color)
                line_color[3] = max(0., line_color[3]-alpha_offset*0.75)
                line_color = tuple(line_color)
                #fill_color = list(fill_color)
                #fill_color[3] = max(0., fill_color[3]-alpha_offset)
                #fill_color = tuple(fill_color)
                e0_color = list(e0_color)
                e0_color[3] = max(0., e0_color[3]-alpha_offset)
                e0_color = tuple(e0_color)
                e1_color = list(e1_color)
                e1_color[3] = max(0., e1_color[3]-alpha_offset)
                e1_color = tuple(e1_color)

            # first draw a grey border - use drawRect to avoid off-by-1 pixel errors
            self.drawRect(w, h, -0.2, line_color)

            border_width = 1
            # then draw a more blended grey background
            glTranslatef(border_width, border_width, 0.) 
            self.drawRect(w-2*border_width, h-2*border_width, -0.1, fill_color)
            w -= 2*border_width # to keep everything inside the border
            h -= 2*border_width


            
            if self.insetEDim:
                arrow_dir = ['left', 'right']
                # draw two rectangular borders, one inset inside the other
                glColor4f(*e0_color)
                with glMatrix(): # draw first rectangle
                    # keep track of pos & area of rect so arrows don't overlap
                    size = h*0.6
                    rect_min_x = (w-(h*0.6))/2. 
                    rect_min_y = h*0.3
                    glTranslatef(rect_min_x, rect_min_y, 0.)
                    self.drawBorderRegular(size, size, 2., 0.) 

                glColor4f(*e1_color)
                with glMatrix(): # draw second rectangle
                    sm_rect_x = (w-(h*0.3))/2.
                    sm_rect_y = h*0.45
                    glTranslatef(sm_rect_x, sm_rect_y, 0.)
                    self.drawBorderRegular(h*0.3, h*0.3, 2., 0.)
            else:
                arrow_dir = ['right', 'left']
                border_width = 2.
                size = h*0.5
                space = (w-(2*size))/3.
                rect_min_x = space
                rect_min_y = h*0.3
                offset_y = (h - rect_min_y - size)/4. # to make look more centered
                # draw two rectangular borders, side-by-side
                glColor4f(*e0_color)
                with glMatrix(): # draw first rect
                    # rect_min_y + (h - rect_min_y - size)/2.
                    glTranslatef(rect_min_x, rect_min_y + offset_y, 0.) 
                    self.drawBorderRegular(size, size, border_width, 0.)

                glColor4f(*e1_color)
                with glMatrix(): # draw second rect
                    glTranslatef(rect_min_x + size + space, rect_min_y + offset_y, 0.) 
                    self.drawBorderRegular(size, size, border_width, 0.)

            arrow_w = w*0.4
            arrow_h = rect_min_y * 0.75
            arrow_y = (rect_min_y - arrow_h)/2.
            glColor4f(*e0_color)
            glLineWidth(1.) # drawBorder changed this to 2. when called
            with glMatrix(): # draw arrow for first rectangle
                glTranslatef(w*0.05, arrow_y, 0.)
                self.drawArrow(arrow_w, arrow_h, 0., arrow_dir[0])

            glColor4f(*e1_color)
            glLineWidth(1.) # drawBorder changed this to 2. when called
            with glMatrix(): # draw arrow for second rectangle
                glTranslatef(w*0.55, arrow_y, 0.)
                self.drawArrow(arrow_w, arrow_h, 0., arrow_dir[1])  

    def drawLinks3d(self, link_colors):
        # to avoid error when dataModel is set but Torus5dModule.updateColors hasn't been called yet
        if self.link_colors.shape[0] == 0:
            return

        glPushMatrix()
        slice_shape = self.getSliceShape()
        if max(slice_shape) != 0: self.centerView(slice_shape)
        w, h, d = self.getSliceDims()

        for start_node in np.ndindex(*self.shape):
            if (start_node[d], start_node[4]) in self.view_planes[d]:
                #z_dist = start_node[self.axis] * self.gap * 2 * self.axis_directions[2]
                #glTranslatef(0, 0, z_dist)
                colors = link_colors[start_node]
                start_cyl = self.getCylinderIndex((start_node[w], start_node[h], start_node[self.axis]),
                    slice_shape, 2)
                start = np.array(self.getNodePos3d(start_node, self.shape, self.axis))

                # draw depth links (ie. d-links for b, c, a = width, height, axis)
                if self.drawDepthLinks:
                    end_node = self.getNextNode(start_node, d, 1)
                    end = np.array(self.getNodePos3d(end_node, self.shape, self.axis))
                    glColor4f(*colors[d])
                    self.drawLinkCylinder(start, end)

                # iterate over dimensions. 4 is e dim
                if self.drawOnlyELinks or self.drawOnlyDepthLinks:
                    possible_dims = [4]
                else:
                    possible_dims = [w, h, self.axis, 4]
                for dim in possible_dims:
                    end_node = self.getNextNode(start_node, dim, 1)
                    # Draw e-links, don't need to check cylinders, all are drawn
                    
                    if self.drawELinks and dim == 4: #only draw e-links
                        if start_node[4] == 0: other_edim = 1
                        else: other_edim = 0
                        if ((start_node[d], 0) in self.view_planes[d] or 
                          (start_node[d], 1) in self.view_planes[d]): # showing both e-values
                            end = np.array(self.getNodePos3d(end_node, self.shape, self.axis))
                            glColor4f(*colors[dim])
                            self.drawLinkCylinder(start, end)
                            continue
                        continue # TODO:  Make this more efficient by setting dim array to [4] for this?

                    if dim == 4 and not self.drawELinks:
                        continue

                    # Skip torus wraparound links
                    if end_node[dim] >= self.shape[dim]:
                        continue

                    # Only render lines that connect points within the same cylinder
                    end_cyl = self.getCylinderIndex((end_node[w], end_node[h], end_node[self.axis]),
                        slice_shape, 2) # cylinder number based on 2d view
                    if start_cyl == end_cyl:
                        # Prevents occluding links on the innermost cylinder by not
                        # rendering links that would make T-junctions
                        if start_cyl == 0:
                            # find transverse dimension
                            for t in [w, h, self.axis]:
                                if t != self.axis and t != dim: break
                            left_node = self.getNextNode(start_node, t, -1)
                            left_cyl = self.getCylinderIndex((left_node[w], left_node[h], left_node[self.axis]),
                                slice_shape, 2)
                            right_node = self.getNextNode(start_node, t, 1)
                            right_cyl = self.getCylinderIndex((right_node[w], right_node[h], right_node[self.axis]),
                                slice_shape, 2)
                            if end_cyl == right_cyl and end_cyl == left_cyl:
                                continue

                        end = np.array(self.getNodePos3d(end_node, self.shape, self.axis))
                        glColor4f(*colors[dim])
                        self.drawLinkCylinder(start, end) 
        glPopMatrix()

    # ------------------------    Render, Level 4    ---------------------------

    def drawArrow(self, w, h, z_dist, direction):
        ''' Draws an arrow with an arrow head and a tail.'''
        # TODO:  Write this to draw the arrow using drawArrowHead
        if direction == 'left' or direction == 'right':
            arrow_w = 0.4 # normalized width of the arrow
            with glSection(GL_LINES):
                glVertex3f(0., h*0.5, 0.)
                glVertex3f(w, h*0.5, 0.)

            if direction == 'right':
                glTranslate(w*(1-arrow_w), 0., 0.)
            
            # draw at z_dist = 0.1 so head is in front of tail
            self.drawArrowHead(w*arrow_w, h, 0.1, 1., direction)

        elif direction == 'top' or direction == 'bottom':
            arrow_h = 0.4 # normalized height of the arrow
            with glSection(GL_LINES):
                glVertex3f(w*0.5, 0., 0.)
                glVertex3f(w*0.5, h, 0.)

            if direction == 'top':
                glTranslatef(0., h*0.8, 0.)

            # draw at z_dist = 0.1 so head is in front of tail
            self.drawArrowHead(w, h*arrow_h, 0.1, 1., direction)

    def drawBorderPrecise(self, w, h, border_width, z_dist):
        ''' Draws a perfect border of width border_width on the inside of the 
        rectangle edge with width w and height h.
        '''
        glLineWidth(border_width)
        with glSection(GL_LINES):
                glVertex3f(0., border_width/2., z_dist)
                glVertex3f(w, border_width/2., z_dist)

                glVertex3f(w-(border_width/2.), 0., z_dist)
                glVertex3f(w-(border_width/2.), h, z_dist)

                glVertex3f(w, h-(border_width/2.), z_dist)
                glVertex3f(0., h-(border_width/2.), z_dist)

                glVertex3f(border_width/2., h, z_dist)
                glVertex3f(border_width/2., 0., z_dist)

    def drawBorderRegular(self, w, h, line_width, z_dist):
        glLineWidth(line_width)
        with glSection(GL_LINES):
                glVertex3f(0., 0., z_dist)
                glVertex3f(w, 0., z_dist)

                glVertex3f(w, 0., z_dist)
                glVertex3f(w, h, z_dist)

                glVertex3f(w, h, z_dist)
                glVertex3f(0., h, z_dist)

                glVertex3f(0., h, z_dist)
                glVertex3f(0., 0., z_dist)        

    def drawLinkCylinder(self, start, end):
        # calculate a vector in direction start -> end
        v = end - start

        # interpolate cylinder points
        cyl_points = [tuple(p) for p in [start - v, start, end, end + v]]
        
        # Draw link
        glePolyCylinder(cyl_points, None, self.link_width / 50.0)

    def drawLinkLine(self, start, end):
        """Surprise! Actually draws a line."""
        glBegin(GL_LINES)
        glVertex3fv(start)
        glVertex3fv(end)
        glEnd()

    def drawRect(self, w, h, z_dist, color):
        glColor4f(*color)
        with glSection(GL_QUADS):
            glVertex3f(0., 0., z_dist)
            glVertex3f(w, 0., z_dist)
            glVertex3f(w, h, z_dist)
            glVertex3f(0., h, z_dist)

    def drawRectSplit(self, w, h, border_width, line_color, fill_color):

        # first draw a border
        self.drawRect(w, h, -0.2, line_color) # border

        # next draw a vertical line separating the two halves
        glColor4f(*line_color)
        glLineWidth(border_width)
        with glSection(GL_LINES):
            glVertex3f(w/2., 0., 0.)
            glVertex3f(w/2., h, 0.)

        # next draw the background using two filled rectangles
        with glMatrix():
            glTranslatef(border_width, border_width, 0.)
            w -= 2*border_width
            h -= 2*border_width
            self.drawRect(w, h, -0.1, fill_color) # background            

    # ------------------------    Render, Level 5    ---------------------------

    def drawArrowHead(self, w, h, z_dist, size, direction):
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

    def changeBounds(self, lower = True, inc = True):
        ''' Raises or lowers the minimum value on the colormap.'''
        if lower and inc: #inc lower bound
            self.lowerBound = min(self.lowerBound+self.delta,1)
        elif lower: # dec lower bound
            self.lowerBound = max(self.lowerBound-self.delta,0)
        elif not lower and inc: # inc upper bound
            self.upperBound = min(self.upperBound+self.delta,1)
        elif not lower and not inc: # dec upper bound
            self.upperBound = max(self.upperBound-self.delta,0)
        self.update(colors = True, links = True, nodes = False, reset = False)
        #print "New colormap showing links between [%.1f%%,%.1f%%] of the range" % (self.lowerBound*100,self.upperBound*100)

    def changeDLinkView(self):
        if self.drawDepthLinks and not self.drawOnlyDepthLinks and not self.drawOnlyELinks:
            self.drawOnlyDepthLinks = True
        elif self.drawDepthLinks:
            self.drawDepthLinks = False
            self.drawOnlyDepthLinks = False
        else: 
            self.drawDepthLinks = True

        #print 'drawDepthLinks =',self.drawDepthLinks,', drawOnlyDepthLinks =',self.drawOnlyDepthLinks

        self.updateDrawing()      

    def changeELinkOffset(self, centerX = False, centerY = False, diagonalX = False, diagonalY = False, inc = True):
        val = 0.05 if inc else -0.05
        if centerX:
            self.elink_offset_center_x += val
            if not inc: self.elink_offset_center_x = max(0.05, self.elink_offset_center_x)
            #print 'self.elink_offset_center_x = ' + str(self.elink_offset_center_x)
        if centerY:
            self.elink_offset_center_y += val
            if not inc: self.elink_offset_center_y = max(0.05, self.elink_offset_center_y)
            #print 'self.elink_offset_center_y = ' + str(self.elink_offset_center_y)
        if diagonalX:
            self.elink_offset_diagonal_x += val
            if not inc: self.elink_offset_diagonal_x = max(0.05, self.elink_offset_diagonal_x)
            #print 'self.elink_offset_diagonal_x = ' + str(self.elink_offset_diagonal_x)
        if diagonalY:
            self.elink_offset_diagonal_y += val
            if not inc: self.elink_offset_diagonal_y = max(0.05, self.elink_offset_diagonal_y)
            #print 'self.elink_offset_diagonal_y = ' + str(self.elink_offset_diagonal_y)
        self.updateDrawing()

    def changeGridStatus(self):
        if self.showGrid:
            self.showGrid = False
        else:
            self.showGrid = True

        self.updateDrawing()

    def changeToriView(self):
        if not self.drawELinks and self.insetEDim:
            self.insetEDim = False
        elif not self.drawELinks:
            self.insetEDim = True

        #print 'insetEDim =',self.insetEDim
        self.updateDrawing()

    def changeELinkView(self):
        ''' Consider using changeViewPlane() instead, but this works for now.'''

        # if the current plane is in the previous e-dim, switch it to new e-dim and mark it
        #   so when the user switches back, the current plane goes back to first e-dim
        # dont do this anymore since we have mouse clicking for I/O

        if not self.insetEDim and not self.drawELinks:
            self.oldInsetEDim = self.insetEDim
            self.insetEDim = True
            self.drawELinks = True

        elif self.drawELinks and not self.drawOnlyELinks and not self.drawOnlyDepthLinks:
            self.drawOnlyELinks = True
        elif self.drawELinks:
            self.drawELinks = False
            self.insetEDim = self.oldInsetEDim
            self.drawOnlyELinks = False
        elif not self.drawELinks and self.drawOnlyDepthLinks:
            self.drawELinks = True
            self.drawOnlyELinks = True
            self.oldInsetEDim = self.insetEDim
        else:
            self.drawELinks = True
            self.oldInsetEDim = self.insetEDim

        self.updateDrawing()

    def changeGapFactor(self, inc = True):
        val = 0.5 if inc else -0.5
        self.gap += val
        if not inc: self.gap = max(0.5, self.gap)
        self.updateDrawing()

    def changeLinkWidth(self, inc = True):
        val = 1 if inc else -1
        self.link_width += val
        if not inc: self.link_width = max(1,self.link_width)
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

    def changePackFactor(self, links = False, nodes = False, inc = True):
        val = 0.1 if inc else -0.1
        if links: 
            self.link_pack_factor += val
            if not inc: self.link_pack_factor = max(0.1, self.link_pack_factor)
            #print 'self.link_pack_factor = ' + str(self.link_pack_factor)
        if nodes: 
            self.node_pack_factor += val
            if not inc: self.node_pack_factor = max(0.1, self.node_pack_factor)
            #print 'self.node_pack_factor = ' + str(self.node_pack_factor)
            
        self.updateDrawing()

    def changePlaneSpacing(self, inc = True):
        if inc:
            if self.plane_spacing >= 1:  self.plane_spacing += 1
            else: self.plane_spacing += .2
        else:
            if self.plane_spacing <= 1:  self.plane_spacing -= .2
            else: self.plane_spacing -= 1
        self.updateDrawing()

    def keyPressEvent(self, event):

        key_map = { 
                    "e" : lambda :  self.changeELinkView(),
                    "d" : lambda :  self.changeDLinkView(),
                    "=" : lambda :  self.changePlaneSpacing(inc = True),
                    "+" : lambda :  self.changePlaneSpacing(inc = True),
                    "-" : lambda :  self.changePlaneSpacing(inc = False),
                    "_" : lambda :  self.changePlaneSpacing(inc = False),
                    "f" : lambda :  self.resetRotation(), 
                    "F" : lambda :  self.resetRotation(),
                    #"g" : lambda :  self.changeGridStatus(),
                    #"G" : lambda :  self.changeGridStatus(),
                    #"t" : lambda :  self.changeGapFactor(inc = True),
                    #"T" : lambda :  self.changeGapFactor(inc = False),
                    #"r" : lambda :  self.changePackFactor(links = True, inc = True),
                    #"R" : lambda :  self.changePackFactor(links = True, inc = False),
                    #"y" : lambda :  self.changePackFactor(nodes = True, inc = True),
                    #"Y" : lambda :  self.changePackFactor(nodes = True, inc = False),
                    "l" : lambda :  self.changeLinkWidth(inc = True),
                    "L" : lambda :  self.changeLinkWidth(inc = False),
                    "n" : lambda :  self.changeNodeSize(inc = True),
                    "N" : lambda :  self.changeNodeSize(inc = False),
                    #";" : lambda :  self.changeELinkOffset(centerX = True, inc = True),
                    #":" : lambda :  self.changeELinkOffset(centerX = True, inc = False),
                    #"'" : lambda :  self.changeELinkOffset(centerY = True, inc = True),
                    #'"' : lambda :  self.changeELinkOffset(centerY = True, inc = False),
                    #"o" : lambda :  self.changeELinkOffset(diagonalX = True, inc = True),
                    #"O" : lambda :  self.changeELinkOffset(diagonalX = True, inc = False),
                    #"p" : lambda :  self.changeELinkOffset(diagonalY = True, inc = True),
                    #"P" : lambda :  self.changeELinkOffset(diagonalY = True, inc = False),
                    "<" : lambda :  self.changeBounds(lower = True, inc = False),
                    ">" : lambda :  self.changeBounds(lower = True, inc = True),
                    "," : lambda :  self.changeBounds(upper = True, inc = False),
                    "." : lambda :  self.changeBounds(upper = True, inc = True)
                    }

        if event.text() in key_map:
            key_map[event.text()]()
        else:
            super(Torus5dViewSlice4d, self).keyPressEvent(event)
    
    def mousePressEvent(self, event):
        """We keep track of right-click drags for picking."""
        super(Torus5dViewSlice4d, self).mousePressEvent(event)

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
            for i in range(self.numIcons):
                #print 'x =',y,', y =',y,', iconHitBoxes['+str(i)+'] =',self.iconHitBoxes[i]
                if x >= self.iconHitBoxes[i][0][0] and x <= self.iconHitBoxes[i][0][1] \
                  and y >= self.iconHitBoxes[i][1][0] and y <= self.iconHitBoxes[i][1][1]:
                    found = True
                    if i == 0: # main icon (inset vs. offset)
                        self.changeToriView()
                    elif i == 1:
                        self.changePlaneSpacing(inc = False)
                    elif i == 2:
                        self.changePlaneSpacing(inc = True)
                    elif i == 3:
                        self.changeDLinkView()
                    elif i == 4:
                        self.changeELinkView()

            # next check if clicking outside an icon but inside the toolbar area
            if not found and x >= self.toolBarDims[self.toolBarPos][0][0] \
              and x <= self.toolBarDims[self.toolBarPos][0][1] \
              and y >= self.toolBarDims[self.toolBarPos][1][0] \
              and y <= self.toolBarDims[self.toolBarPos][1][1]:
                self.toolBarSelected = True
                self.updateDrawing(nodes = False, links = False, grid = False)

        elif event.button() == Qt.RightButton:
            self.right_drag = True

    def mouseReleaseEvent(self, event):
        """We keep track of whether a drag occurred with right-click."""
        super(Torus5dViewSlice4d, self).mouseReleaseEvent(event)

        # Return if haven't dragged module onto the data tree yet to prevent
        #   the error when mouse I/O fails to return, causing any keyboard
        #   modifier (shift, contrl..) to be mis-interpreted as mouseEvent
        if max(self.shape) == 0:
            return

        if self.toolBarSelected:
            self.toolBarSelected = False
            self.updateDrawing(nodes = False, links = False, grid = False)

        if self.right_drag:
            self.right_drag = False

    def mouseMoveEvent(self, event):

        if self.toolBarSelected:
            x = event.x()
            y = self.height()-event.y() # since x,y pos is from bottom left
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
                for pos in check_list:
                    if (x >= self.toolBarDims[pos][0][0] and x <=
                      self.toolBarDims[pos][0][1] and y >=
                      self.toolBarDims[pos][1][0] and y <=
                      self.toolBarDims[pos][1][1]):
                        self.toolBarPos = pos
                        self.updateDrawing(nodes = False, links = False, grid = False)
                        break
        else:
            super(Torus5dViewSlice4d, self).mouseMoveEvent(event)

    def resetRotation(self):
        self.rotation = np.identity(4)
        self.updateDrawing()



# ******************************************************************************

# Methods for changing axis with key press I/O
# To turn back on, also add the following to key_map in keyPressEvent()
    #"a" : lambda :  self.keyAxisChange(0),
    #"b" : lambda :  self.keyAxisChange(1),
    #"c" : lambda :  self.keyAxisChange(2),
    #"d" : lambda :  self.keyAxisChange(3),

"""
    def keyAxisChange(self, axis):
        if self.axis != axis: self.updateAxis(axis)
"""

# ******************************************************************************

# Methods for adding/removing planes with key press I/O
# To turn back on, add this signal below the properties after __init__
    #viewPlanesUpdateSignal = signal(dict)
# And also add the following to keyMap in keyPressEvent()
    #"[" : lambda :  self.changeViewPlane(-1),
    #"]" : lambda :  self.changeViewPlane(1),
    #"}" : lambda :  self.addViewPlane(1),
    #"{" : lambda :  self.addViewPlane(-1),

"""
    def changeViewPlane(self, direction, removeCurrent = True):
        '''Removes current viewing plane and adds the next.'''
        w, h, d = self.getSliceDims()
        #print '\nIn, CurrPlane = ' + str(self.current_planes[d])
        #print 'In, ViewPlanes = ' + str(self.view_planes[d])
        nextPlane = self.nextPlane(direction)
        if removeCurrent and (self.current_planes[d], self.current_planes[4]) in self.view_planes[d]:
            self.view_planes[d].remove((self.current_planes[d], self.current_planes[4]))
        self.current_planes[d] = nextPlane
        if (self.current_planes[d], self.current_planes[4]) not in self.view_planes[d]:
            self.view_planes[d].add((self.current_planes[d], self.current_planes[4]))
        #print 'Out, CurrPlane = ' + str(self.current_planes[d])
        #print 'Out, ViewPlanes = ' + str(self.view_planes[d])
        
        # COMMENT THIS BACK IN if allowing view_planes to be changed from here
        #self.viewPlanesUpdateSignal.emit(self.view_planes)
        self.updateDrawing()

    def addViewPlane(self, direction):
        ''' Adds a viewing plane and advances current to next plane.'''
        self.changeViewPlane(direction, False)

    def nextPlane(self, direction):
        w, h, d = self.getSliceDims()
        numIndicies = self.shape[d]
        if direction > 0:
            if self.current_planes[d] == numIndicies -1: 
                return 0
            else: return self.current_planes[d] + 1
        elif direction < 0:
            if self.current_planes[d] == 0:
                return numIndicies - 1
            else: return self.current_planes[d] - 1
        else: return self.current_planes[d]
"""




