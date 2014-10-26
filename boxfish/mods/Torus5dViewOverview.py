import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from boxfish.gl.glutils import *
from Torus5dModule import *
from OpenGL.GLE import glePolyCylinder

class Torus5dViewOverview(Torus5dGLWidget):
    ''' Draws an overview which shows all the planes for a selected axis and
    axis index.  The planes are laid out as slices in OpenGL-z direction.
    Selected planes are opaque, de-selected are transparent.  Each plane is
    drawn as a minimap to show the average data therein.
    '''

    # ***************************    Initialize    *****************************

    viewPlanesUpdateSignal = Signal(dict)
    axisUpdateSignal = Signal(int, int)

    def __init__(self, parent, dataModel):
        ''' Draw the overview of the main window - including minimaps and
        any other overviews.'''
        super(Torus5dViewOverview, self).__init__(parent, dataModel, rotation = False)

        self.showVariance = False

        self.overviewList = DisplayList(self.drawOverview)
        self.overviewToolBarList = DisplayList(self.drawOverviewToolBar)
        self.resizeSignal.connect(self.updateDrawing)

        self.widget3dLists = []
        self.widget3dLists.append(self.overviewList)

        self.widget2dLists = []
        self.widget2dLists.append(self.overviewToolBarList)
        self.valuesInitialized = False
        Qt.ShiftModifier = False # to fix the weird vertical translation bug

    shape = property(fget = lambda self: self.dataModel.shape)
    view_planes = property(fget = lambda self: self.dataModel.view_planes)
    current_planes = property(fget = lambda self: self.dataModel.current_planes)

    def initializeGL(self):
        """Turn up the ambient light for this view and enable simple
           transparency.  To keep views looking the same."""
        super(Torus5dViewOverview, self).initializeGL()
       # glLightfv(GL_LIGHT0, GL_AMBIENT,  [1.0, 1.0, 1.0, 1.0])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)


    # ***************************      Update      *****************************

    def resetView(self):
        # Do not rotate the view - instead draw it in OpenGL XY space to begin with
        # Set initial position based on the size and axis of the model

        slice_shape = self.getSliceShape()
        w_span, h_span = slice_shape[0], slice_shape[1]
        if w_span != 0 and h_span != 0:
            single_span = self.getSliceSpan(slice_shape)
            #print 'single_span = ' + str(single_span)
            self.miniGap = single_span[0]/2.
            self.miniSpanX = single_span[0]
            self.miniSpanY = single_span[1]
            spans = single_span
            spans[0] = (self.miniGap + single_span[0]) * self.shape[4] + self.miniGap
            self.totalSpanX = spans[0]
            #print 'miniGap = ' + str(self.miniGap) + ', miniSpanX = ' + str(self.miniSpanX) + ', miniSpanY = ' + str(self.miniSpanY)
            #print '\ttotalSpanX = ' + str(self.totalSpanX)
            
            #spans = self.getSliceSpan(slice_shape)
            aspect = self.width() / float(self.height())

            # Check both distances instead of the one with the larger span
            # as we don't know how aspect ratio will come into play versus shape

            # Needed vertical distance
            fovy = float(self.fov) * math.pi / 360.
            disty = spans[1] / 2. / math.tan(fovy) #spans[1] = spans[height]

            # Needed horizontal distance
            fovx = fovy * aspect
            distx = spans[0] / 2. / math.tan(fovx) #spans[0] = spans[width]

            #self.translation = [0, 0, -max(distx, disty)]
            #pre-do the translation, values are from using line above and
            #   modifying from there, printing out transl. matrix
            self.translation = [  8.48,       -12.3,        -85.01096]

            # also pre-do the rotation so it looks clean; matrix values
            #   from printing out self.rotation while testing
            self.rotation = [[ 0.93936801,  0.21609111, -0.26625699,  0.        ],
            [ 0.07260955,  0.63351005,  0.77032316,  0.        ],
            [ 0.33513576, -0.74294877,  0.57940996,  0.        ],
            [ 0.,          0.,          0.,          1.        ]]

            #self.far_plane = 150. # default 1000 in GLWidget
            #self.resizeGL(self.width(), self.height())

    def update(self, colors = True, values = True, reset = True):
        if colors: super(Torus5dViewOverview, self).update()
        if values: self.updateMiniMapValues()
        if reset: self.resetView()
        self.updateDrawing()

    def updateAxis(self, axis, axis_index = -1):
        ''' Slot for agent.axisUpdateSignal.  Also called from mousePress and
        keyPress events.
        '''
        if self.axis != axis or self.axis_index != axis_index:
            if axis_index == -1: #keyboard change axis command
                if self.axis == axis: #increment axis_index
                    self.axis_index = self.nextAxisIndex()
                else:
                    self.axis_index = 0
                    self.axis = axis
            else: #mouse click i/o
                self.axis = axis
                self.axis_index = axis_index
            #print 'Axis = ' + str(self.axis) + ', Index = ' + str(self.axis_index)
        #print '************** OVERVIEW, updateAxis() ************'
        self.resetView()
        self.updateDrawing()                          

    def updateDrawing(self):
        for disp_list in self.widget3dLists:
            disp_list.update()

        for disp_list in self.widget2dLists:
            disp_list.update()

        #self.updateGL()
        self.paintEvent(None)

    def updateMiniMapValues(self):
        '''Same as updateMiniMapValues, but does all planes.  Not currently doing anything
        with variance data, but calculating it - so remove this if final decision is not 
        to include it.
        '''
        #self.miniColors = list()
        #self.miniVariance = list()
        #self.planeAvgVariance = list()
        #self.planeMaxVariance = list()
        #self.planeTotalVariance = list()
        self.planeLinkColors = list()
        #min_variance = sys.maxint
        #max_variance = -sys.maxint - 1
        plane_tot_index = 0 # REMOVE AFTER DEBUGGING
        plane_avg_index = 0
        for axis in range(4):
            aindex = 0
            for w, h, d in self.axis_map[axis]:
                shape = self.shape[:]
                slice_shape = [shape[w], shape[h], shape[axis]]
                slice_indicies = [w, h, axis]
                non_slice_indicies = [i for i in range(len(shape)) if i not in slice_indicies] # length 2
                #d_values = [i for i in range(self.shape[d])]
                d_values = [0]
                mini_shape = list()
                if shape[axis] != 0:
                    shape = list(shape)
                    # only shape[w] and shape[h] remain in mini_shape; the rest become 1
                    mini_shape = [shape[i] if i in slice_indicies[:2] else 1 for i in range(len(shape))]
                    mini_shape = tuple(mini_shape)
                #link_colors = np.tile(self.default_link_color, [shape[w], shape[h], 1] + [3,1]) #uses slice dims
                #link_variance = np.tile(0., [shape[w], shape[h], 1] + [3]) #store link variance by slice
                plane_link_colors = np.tile(self.default_link_color, [shape[d], shape[4], shape[w], shape[h], 1] + [3,1]) #uses slice dims
                #plane_link_variance = np.tile(0., [shape[d], shape[4], shape[w], shape[h], 1, 3])
                # average the link bundles leaving every node in the slice, storing by 4th/5th dimension
                plane_link_values = np.tile([0. for i in range(self.shape[axis])], [shape[d], shape[4]] + [shape[w], shape[h], 1] +  [3, 1])
                #plane_total_variance = np.tile(0., [shape[d], shape[4]])
                #plane_avg_variance = np.tile(0., [shape[d], shape[4]])
                #plane_max_variance = np.tile(0., [shape[d], shape[4]])
                #print '\tplane_tot_index = ' + str(plane_tot_index)
                plane_tot_index = 0 # resets for each new 4th and 5th dimension plane
                for node in np.ndindex(*mini_shape): # 5D node, but non-slice dims (plus axis) are 1
                    dim_count = 0
                    #print '\tplane_avg_index = ' + str(plane_avg_index)
                    for dim in slice_indicies:
                        val = [[0.0 for k in range(self.shape[4])] for j in range(self.shape[d])]
                        count = [[0 for k in range(self.shape[4])] for j in range(self.shape[d])]
                        subNode = list(node)
                        link_values = [[[] for k in range(self.shape[4])] for j in range(self.shape[d])]

                        #val_added_count = [[0 for k in range(self.shape[4])] for j in range(self.shape[d])]
                        for i in range(self.shape[axis]):
                            for j in range(self.shape[d]):
                                higher_dims = [t for t in non_slice_indicies if t != d] # == [4] for 5 dim
                                for k in range(self.shape[higher_dims[0]]):
                                    subNode[axis] = i
                                    subNode[non_slice_indicies[0]] = j
                                    subNode[non_slice_indicies[1]] = k
                                    current = self.dataModel.link_values[
                                            tuple(subNode)][dim][0]
                                    
                                    # TODO:  Check what happens if this is +=current instead of =current
                                    plane_link_values[j][k][tuple([node[w], node[h], 0])][dim_count][i] = current
                                    val[j][k] += current
                                    #val_added_count[j][k] += 1 
                                    count[j][k] += self.dataModel.link_values[
                                        tuple(subNode)][dim][1] # TODO : Ask Kate why this is necessary / when it's used?   

                        if shape[axis] != 0:
                            for j in range(self.shape[d]):
                                for k in range(self.shape[higher_dims[0]]):
                                    #if count[j][k] == 0:
                                    #    mean = 0
                                    #    variance_plane = 0
                                    #else:
                                    #    mean = np.sum(plane_link_values[j][k][(node[w], node[h], 0)][dim_count]) / self.shape[axis]
                                    #   variance_plane = (np.sum(np.square(plane_link_values[j][k][(node[w], node[h], 0)][dim_count]))/(self.shape[axis])) - mean*mean
                                    #plane_link_variance[j][k][(node[w], node[h], 0)][dim_count] = variance_plane
                                    plane_link_colors[j][k][(node[w], node[h], 0)][dim_count] = self.map_link_color(
                                        val[j][k] / float(self.shape[axis]), 1.0) \
                                        if count[j][k] / float(self.shape[axis]) \
                                        >= 1 else self.default_link_color
                            
                            # if including variance, comment back in and see GLMiniMaps.updateMiniMapValues
                            #if variance > max_variance: max_variance = variance
                            #if variance < min_variance: min_variance = variance

                        dim_count += 1

                '''
                for j in range(self.shape[d]):
                    for k in range(self.shape[higher_dims[0]]):
                        total_count = np.product(slice_shape) * 3
                        avg_count = shape[w] * shape[h] * 3
                        # TODO:  Check to see when variance dim is used in drawLinkVariance (print out in place)
                        #   to make sure we want to include dim = axis in this summation
                        total_mean = np.sum(plane_link_values[j][k])/total_count
                        plane_total_variance[j][k] = (np.sum(np.square(plane_link_values[j][k]))/total_count) - (total_mean*total_mean)
                        plane_avg_variance[j][k] = np.sum(plane_link_variance[j][k])/avg_count
                '''

                #print 'axis = ' + str(axis) + ', map = ' + str(self.axis_map[axis]) + ', plane_total_variance = ' + str(plane_total_variance) + ', link_variance = ' + str(link_variance)

                #print 'plane_avg_variance[j][k] = ' + str(plane_avg_variance[j][k])
                
                #self.planeAvgVariance.append(plane_avg_variance.copy())
                #self.planeTotalVariance.append(plane_total_variance.copy())
                self.planeLinkColors.append(plane_link_colors.copy())
                #self.miniColors.append(link_colors.copy())
                #self.miniVariance.append(link_variance.copy())
                aindex += 1

        #self.min_variance = min_variance
        #self.max_variance = max_variance
        self.valuesInitialized = True


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

    def getBorderColor(self, axis, axis_index, d_val, e_val, d_color = True):
        ''' Get the current border color of a 4th/5th dimension plane for a minimap.'''
        w, h, d = self.axis_map[axis][axis_index]
        coords = self.parent.agent.coords

        if axis == self.axis and axis_index == self.axis_index and \
            d_val == self.current_planes[d] and e_val == self.current_planes[4]:
            return self.getAxisLabelColor(0)
        elif (d_val, e_val) in self.view_planes[d]:
            if d_color:
                return self.getAxisLabelColor(coords[d])
            else:
                return self.getAxisLabelColor(coords[4])
        elif self.bright_bg_color:
            return (0.6, 0.6, 0.6, 0.8)
        else:
            return (0.4, 0.4, 0.4, 0.8)

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

    def getMousePress(self, x, y):
        for i in range(4):
            x_start = self.arrowPos[i][0][0]
            x_end = self.arrowPos[i][0][1]
            y_start = self.arrowPos[i][1][0]
            y_end = self.arrowPos[i][1][1]
            if x >= x_start and x <= x_end and y >= y_start and y <= y_end:
                if i == 0: #left button clicked
                    self.changeView(inc = False)
                elif i == 1: #right
                    self.changeView(inc = True)
                elif i == 2: #top
                    self.changeViewPlane(inc = True)
                else: #bottom
                    self.changeViewPlane(inc = False)

                #print 'x_range =',x_start,x_end,', y_range =',y_start,y_end
                #print 'HIT',i, ' at x, y =',x,', ',y

    def getNextNode(self, point, axis, amount):
        """Increments the <axis> dimension in the point by <amount>"""
        p = list(point)
        p[axis] += amount
        return tuple(p)                

    def getNodePos2d(self, node, shape, axis = 2, scale = 1):
        ''' Maps from (x, y, z), looking down z axis, to (new_x, new_y, 0).
        Parameters 'node' and 'shape' must be 3D vectors (list of length 3).
        '''
        # b = effective box size - increasing this effectively increases length
        #   of diagonal links, or equivalently, the spacing between two parallel
        #   lines of the same cylinder (rem. number of lines = shape[axis])
        b = self.node_size * self.node_pack_factor   # box plus spacing, maybe replace link_width with node_size
        # h = effective cylinder size - number of lines * b + gap between any
        #   two neighboring cylinders (space between closest lines)
        h = (shape[axis] * b) + self.gap  # grid spacing

        def coord(n, d):
            # center = node coord span / 2, so if shape[d] = 4, node[d] = 0,1,2,3
            #   so center would be 3/2 = 1.5
            center = float(shape[d] - 1) / 2
            # inset = offset to create "diagonal" lines of nodes; if node[d] is
            #   left of center, add to create diagonal lines going right towards
            #   center;  if node[d] is right of center, subtract offset to 
            #   create diagonal lines going left towards center
            inset = node[axis] * b * np.sign(center - n)
            even = (shape[d] % 2 == 0)
            # need to add extra space when shape[d] is even; ex: if shape[d] = 4
            #   then n = 1 and n = 2 will be on diagonal lines going right and
            #   left respectively - need to space these out by adding an extra
            #   factor of h -> thus if even and node[d] > center, add one more
            #   factor of h when calculating the 2d position
            return h * (n + int(even and n > center)) + inset

        dim = range(3)
        dim.remove(axis)

        node2d = np.zeros(3)
        for d in dim:
            node2d[d] = scale * coord(node[d], d)
        node2d *= self.axis_directions

        #if node == (4, 0, 0):
        #    print 'MAP2D: shape = ' + str(shape) + ', axis = ' + str(axis) + ', scale = ' + str(scale) + ', node = (4, 0, 0): returning ' + str(node2d)
        return node2d

    def getPlaneSpacing(self):
        slice_w, slice_h, slice_d = self.getSliceDims()
        spacing = self.getSliceSpan(self.getSliceShape())[1]
        #print '\tinit spacing =',spacing
        for axis in range(len(self.shape)-1):
            for axis_index in range(len(self.axis_map[axis])):
                w, h, d = self.axis_map[axis][axis_index]
                if d == slice_d:
                    #print '\t\tfound: d =',d,', axis =',axis,', axis_index =',axis_index
                    new_spacing = self.getSliceSpan([self.shape[w], self.shape[h], self.shape[d]])[1]
                    #print '\ttesting new_spacing =',new_spacing
                    spacing = max(spacing, new_spacing)
                    #print '\tnew spacing =',spacing

        return spacing        

    def getSliceDims(self):
        """Get the dimensions that span width, height, depth of screen"""
        return self.axis_map[self.axis][self.axis_index]

    def getSliceShape(self):
        ''' Slice is a selection of 3 dimensions for a 4D projection.  The
        dimensions are {a, b, c, d, e} = {0, 1, 2, 3, 4}.
        '''
        w, h, d = self.getSliceDims()
        return [self.shape[w], self.shape[h], self.shape[self.axis]]
        
    def getSliceSpan(self, shape, axis = 2):
        """Span in OpenGL 2D space of each dimension of the 2D view"""
        if len(shape) != 3:
            #print 'ERROR:  Called getSliceSpan with shape != 3'
            return 

        shape[axis] = 1 
        x_span = abs(self.getNodePos2d([0, 0, 0], shape, axis) - 
            self.getNodePos2d([shape[0]-1, 0, 0], shape, axis))
        y_span = abs(self.getNodePos2d([0, 0, 0], shape, axis) - 
            self.getNodePos2d([0, shape[1]-1, 0], shape, axis))
        z_span = abs(self.getNodePos2d([0, 0, 0], shape, axis) - 
            self.getNodePos2d([0, 0, shape[2]-1], shape, axis))
        #print 'shape = ' + str(shape) + ', x_span = ' + str(x_span) + ', y_span = ' + str(y_span) + ', z_span = ' + str(z_span)

        return [x_span[0], y_span[1], z_span[2]]

    # ****************************     Render      *****************************

    # ------------------------    Render, Level 0    ---------------------------

    #def paintGL(self):
    #    ''' How the QGLWidget is supposed to render the scene.'''
    #    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    #    glGetError()
    #    self.orient_scene() # push the view back to get behind front clip plane
    #    self.draw()
    #    super(Torus5dViewOverview, self).paintGL()

    def paintEvent(self, event):
        ''' How the QGLWidget is supposed to render the scene.'''
        with setupPaintEvent(self):
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glGetError()
            self.orient_scene() # push the view back to get behind front clip plane
            self.draw()
            super(Torus5dViewOverview, self).paintEvent(event)

    # ------------------------    Render, Level 1    ---------------------------

    def draw(self, toolbar = True):
        ''' Draw overview window.'''
        for func in self.widget3dLists:
            func()

        if toolbar:
            with overlays2D(self.width(), self.height(), self.bg_color):
                for func in self.widget2dLists:
                    func()        

    # ------------------------    Render, Level 2    ---------------------------
    
    def drawOverview(self):
        if max(self.shape) == 0:
            return
        elif not self.valuesInitialized:
            return

        #print '*********** OVERVIEW ***********\nlower_bound =',self.lowerBound,', upper_bound =',self.upperBound

        grey_value = (self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) /  3
        #print 'grey_value = ' + str(grey_value)
        if grey_value >= 0.5:
            self.bright_bg_color = True
        else:
            self.bright_bg_color = False

        if grey_value >= 0.35:
            line_color = (0.3, 0.3, 0.3, 0.3)
        else:
            line_color = (0.6, 0.6, 0.6, 0.3)

        prev_blend_on = glGetBoolean(GL_BLEND)
        glEnable(GL_BLEND) 
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(*self.bg_color) 
        glClear(GL_COLOR_BUFFER_BIT)
        glClear(GL_DEPTH_BUFFER_BIT)
        self.cylinder_width = 0.5
        #print 'old z_translate == miniSpanY = ',self.miniSpanY
        #z_translate = self.miniSpanY*3/2.
        w, h, d = self.axis_map[self.axis][self.axis_index]
        z_translate = self.getPlaneSpacing() # change this to modify spacing between planes
        
        glLineWidth(1.)
        with glMatrix():
            # setup grid - position never changes, only how wide and deep
            grid_y = -z_translate*10/9. # how far down to push the grid
            max_grid_z = z_translate*(self.shape[d]-1) # how deep the grid is
            max_grid_x = self.totalSpanX-2*self.miniGap # how wide the grid is
            offset_grid = self.miniGap/10.
            
            glTranslatef(-self.totalSpanX/2. + self.miniGap, 0, 0) # translate to left edge
            glColor4f(*line_color) # prev 0.5, 0.5, 0.5, 0.4
            with glSection(GL_LINES):
                for grid_x in np.arange(int(0), int(max_grid_x+2*offset_grid+0.5)+2, 2):
                    for grid_z in np.arange(int(0), int(max_grid_z+2*offset_grid+0.5)+2, 2):
                        glVertex3f(grid_x-2-offset_grid, grid_y, -grid_z+2+offset_grid)
                        glVertex3f(grid_x-offset_grid, grid_y, -grid_z+2+offset_grid) #horizontal line
                        glVertex3f(grid_x-2-offset_grid, grid_y, -grid_z+offset_grid) 
                        glVertex3f(grid_x-2-offset_grid, grid_y, -grid_z+2+offset_grid) #vertical

            glLineWidth(2.)
            #print '\n\tview_planes[d] =',self.view_planes[d]
            # currently OpenGL center is widget center    
            for j in range(self.shape[4]):
                with glMatrix():
                    # offset in the y-dir by the difference between the maximum
                    #   spanY (i.e. z_translate), and the current spanY.  this
                    #   ensures spacing between grid and bottom of minimap stays
                    #   constant 
                    glTranslatef(0, self.miniSpanY-z_translate, 0)
                    for i in range(self.shape[d]):
                        self.drawMiniMapPlane(i, j)
                        with glMatrix():
                            self.drawPlaneLabel(i, j)
                        glTranslatef(0, 0, -z_translate)
                glTranslatef(self.miniSpanX + self.miniGap, 0, 0)                    

        if not prev_blend_on:
            glDisable(GL_BLEND)

    def drawOverviewToolBar(self):

        prev_blend_on = glGetBoolean(GL_BLEND)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        if max(self.shape) == 0:
            return

        grey_value = (self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) /  3
        if grey_value >= 0.5:
            self.bright_bg_color = True
        else:
            self.bright_bg_color = False

        # setup the sub-window viewport, perspective, and clipping planes
        eff_size = min(self.width(), self.height())
        w = max(int(eff_size*0.21), 66) # by experimenting
        w = min(w, 150)
        h = w
        #print 'drawOverviewToolBar:  w =',w,'h =',h
        x = int(self.width() - w)
        y = int(self.height() - h)
        setup_overlay2D(x, y, w, h)

        with glMatrix():
            glLoadIdentity()
            glTranslatef(x, y, 0.) #lower left corner of toolbar
            # draw boxes for arrows and center label/icon
            glTranslatef(w*0.05, h*0.05, 0.)
            # save hit boxes, [(x_start, x_end), (y_start, y_end)] as lists for now
            self.arrowPos = [[[x+w*0.05, x+w*0.05], [y+h*0.05, y+h*0.05]] for i in range(4)]
            self.drawOverviewControls(w*0.9, h*0.9)

        if not prev_blend_on:
            glDisable(GL_BLEND)

    # ------------------------    Render, Level 2    ---------------------------    

    def drawMiniMapPlane(self, d_val, e_val):
        """Draws the minimap for the given axis.  After fixing anti-aliasing,
        go back to line widths proportional to window width."""
        #print 'drawing minimap plane, d_val = ' + str(d_val) + ', e_val = ' + str(e_val)

        w, h, d = self.axis_map[self.axis][self.axis_index]
        effective_shape = (self.shape[w], self.shape[h], 1)
        #print 'DrawMiniMapPlane: planeLinkColors.shape = ' + str(self.planeLinkColors[d_val][e_val].shape)
        # set all the alpha values according to whether this plane is selected
        #print 'planeLinkColors[][d][e].shape = ' + str(self.planeLinkColors[self.axis*3 + self.axis_index][d_val][e_val].shape)
        if (d_val, e_val) in self.view_planes[d]:
            selected = True
        else:
            selected = False
        #print '\t\t(d, e) = ' + str((d_val, e_val)) + ', selected = ' + str(selected)
        self.drawLinks(effective_shape, 2, self.planeLinkColors[self.axis*3 + self.axis_index][d_val][e_val], None, 1, selected = selected)

    def drawOverviewControls(self, w, h):
        if self.bright_bg_color:
            fill_color = (0.7, 0.7, 0.7, 0.9)
            line_color = (0.2, 0.2, 0.2, 0.9)
            tri_color = (0.4, 0.4, 0.4, 0.9)
        else:
            fill_color = (0.3, 0.3, 0.3, 0.9)
            line_color = (0.8, 0.8, 0.8, 0.9)
            tri_color = (0.6, 0.6, 0.6, 0.9)

        # fill in hit boxes for mouse i/o
        with glMatrix():
            x = 0
            y = h*0.333
            arrow_w = w*0.333-1 # -1 for the border, to keep centered
            arrow_h = h*0.333
            #print 'drawOverviewControls:  arrow_w =',arrow_w,', arrow_h =',arrow_h
            glTranslatef(x, y, 0.)
            self.drawArrow(arrow_w, arrow_h, 0.09, 'left', fill_color, line_color, tri_color)
            self.arrowPos[0][0][0] += x
            self.arrowPos[0][0][1] += x + arrow_w
            self.arrowPos[0][1][0] += y
            self.arrowPos[0][1][1] += y+ arrow_h

        with glMatrix():
            x = w*0.667+1
            y = h*0.333
            arrow_w = w*0.333-1
            arrow_h = h*0.333
            glTranslatef(x, y, 0.)
            self.drawArrow(arrow_w, arrow_h, 0.09, 'right', fill_color, line_color, tri_color)
            self.arrowPos[1][0][0] += x
            self.arrowPos[1][0][1] += x + arrow_w
            self.arrowPos[1][1][0] += y
            self.arrowPos[1][1][1] += y+ arrow_h

        with glMatrix():
            x = w*0.333
            y = h*0.667+1
            arrow_w = w*0.333
            arrow_h = h*0.333-1
            glTranslatef(x, y, 0.)
            self.drawArrow(arrow_w, arrow_h, 0.09, 'up', fill_color, line_color, tri_color)
            self.arrowPos[2][0][0] += x
            self.arrowPos[2][0][1] += x + arrow_w
            self.arrowPos[2][1][0] += y
            self.arrowPos[2][1][1] += y+ arrow_h    

        with glMatrix():
            x = w*0.333
            y = 0.
            arrow_w = w*0.333
            arrow_h = h*0.333-1
            glTranslatef(x, y, 0.)
            self.drawArrow(arrow_w, arrow_h, 0.09, 'down', fill_color, line_color, tri_color)
            self.arrowPos[3][0][0] += x
            self.arrowPos[3][0][1] += x + arrow_w
            self.arrowPos[3][1][0] += y
            self.arrowPos[3][1][1] += y+ arrow_h

        with glMatrix():
            # TODO:  Maybe add a hitbox for this to turn on/off the minimaps
            glTranslatef(w*0.333, h*0.333, 0.)
            self.drawIcon(w*0.333, h*0.333, 0.11, fill_color, line_color)        

    def drawPlaneLabel(self, d_val, e_val):
        #label_width = self.miniSpanX
        label_width = 11.
        #label_height = self.miniSpanY*2/3.
        label_height = 5.
        #print 'label_width =',label_width
        if e_val == 0: #translate left
            offset_x = -self.miniSpanX*6/4
            offset_z = self.miniSpanY
        elif e_val == 1: #translate right
            offset_x = self.miniSpanX*5/4. # add one miniSpanX extra to far enough right
            offset_z = self.miniSpanY

        glLineWidth(4.)
        glRotate(90, -1, 0, 0)
        # after rotating, x stays same, +y -> -z, +z -> +y

        # first draw the labels at the front (5th dim) if d_val = 0
        if d_val == 0:
            with glMatrix():
                dist_x = (self.miniSpanX-label_width*0.8)/2.
                glTranslatef(dist_x, -2*label_height, -self.miniSpanY)
                self.drawLabel(label_height*0.8, self.miniSpanX*.75, d_val, e_val, draw_dim_d = False)
                #self.drawLabel(label_height*0.8, label_width*0.8, d_val, e_val, draw_dim_d = False)

        # second draw the labels on the sides (4th dim)
        glTranslatef(offset_x, -label_height/2., -self.miniSpanY) # move to the side of minimap
        self.drawLabel(label_height, self.miniSpanX, d_val, e_val, draw_dim_d = True)    
        #self.drawLabel(label_height, label_width, d_val, e_val, draw_dim_d = True)    

    # ------------------------    Render, Level 3    ---------------------------  

    def drawArrow(self, w, h, z_dist, direction, fill_color, line_color, tri_color):
        glColor4f(*fill_color)
        self.drawRect(w, h, z_dist)

        glColor4f(*line_color)
        self.drawBorder(w, h, 1., z_dist+ 0.1)

        with glMatrix():
            glTranslatef(w*0.15+1, h*0.15+1, 0.) # +1 for the border
            glColor4f(*tri_color)
            self.drawArrowHead(w*0.7-2, h*0.7-2, z_dist+0.1, 1, direction) #-2 for border

    def drawIcon(self, w, h, z_dist, fill_color, line_color):
        ''' Draws a label 'a', 'b', ..., 'e' for which overview is being shown.
        '''
        width, height, depth = self.getSliceDims()
        # draw a filled rect for background of the icon
        glColor4f(*fill_color)
        self.drawRect(w, h, z_dist)

        # draw the character (label) for the icon
        dim_char = self.parent.agent.coords[depth]
        eff_size = min(w, h)
        scale_factor = eff_size*0.007 # by experiment
        glColor4f(*line_color)
        with glMatrix():
            glTranslatef(w*0.25, h*0.165, z_dist+0.01) # by experiment
            glScalef(scale_factor, scale_factor, 1.)
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(dim_char))

        # draw the colored border for the icon
        glColor4f(*self.getAxisLabelColor(dim_char))
        self.drawBorder(w, h, 1., z_dist + 0.01)            

    def drawLabel(self, label_height, label_width, d_val, e_val, draw_dim_d):
        coords = self.parent.agent.coords
        w, h, d = self.axis_map[self.axis][self.axis_index]

        if self.bright_bg_color:
            border_color = (0., 0., 0., 0.35)
            text_color = border_color
            fill_color = (0., 0., 0., 0.1)
        else:
            border_color = (1., 1., 1., 0.35)
            text_color = border_color
            fill_color = (1., 1., 1., 0.1)
        
        if draw_dim_d: # set border to the selected view planes
            border_color = self.getBorderColor(self.axis, self.axis_index, d_val, e_val) 
            #print 'd_val = ' + str(d_val) + ', e_val = ' + str(e_val) + ', border_color = ' + str(border_color)
            dim_char = coords[d]
            dim_val = d_val
            #scale_factor = 0.025
            scale_factor = 0.03
        else:
            dim_char = coords[4]
            dim_val = e_val
            #scale_factor = 0.02
            scale_factor = 0.025
        
        
        if len(str(dim_val)) > 1: # 2 digit dimension value
            if draw_dim_d:
                offset_x = self.miniSpanX/10.
            else:
                offset_x = self.miniSpanX/40.
            two_digit_val = True
            scale_factor -= 0.005
        else:
            if draw_dim_d:
                offset_x = self.miniSpanX/6.
            else:
                offset_x = self.miniSpanX/20.
            two_digit_val = False

        
        # draw a border and filled in box to hold label
        # 0 for no border, just rectangle, and 0.5 for slightly larger rectangle,
        #   creating a border of 0.5
        for border in [0, 0.5]:
            if border > 0 and draw_dim_d:
                glColor4f(*border_color)
                offset_z = -0.1 # how far down to push the border-colored rect
            elif border > 0:
                offset_z = -0.1
            else:
                glColor4f(*fill_color)
                offset_z = 0

            if draw_dim_d and border == 0: # draw the selection
                glLoadName(e_val*self.shape[d] + d_val)
                glPushMatrix()

            #with glSection(GL_TRIANGLES):
            #    glVertex3f(-border, -border, offset_z)
            #    glVertex3f(label_width+border, -border, offset_z)
            #    glVertex3f(label_width+border, label_height+border, offset_z)
            #    glVertex3f(label_width+border, label_height+border, offset_z)
            #    glVertex3f(-border, label_height+border, offset_z)
            #    glVertex3f(-border, -border, offset_z)
            with glSection(GL_TRIANGLES):
                glVertex3f(-border, -border, offset_z)
                glVertex3f(label_width+border, -border, offset_z)
                glVertex3f(label_width+border, label_height+border, offset_z)
                glVertex3f(label_width+border, label_height+border, offset_z)
                glVertex3f(-border, label_height+border, offset_z)
                glVertex3f(-border, -border, offset_z)

            if draw_dim_d and border == 0:
                glPopMatrix()

        glColor4f(*text_color)
        glLineWidth(2.)
        #glTranslatef(offset_x, self.miniSpanY/8., 0)
        glTranslatef(offset_x, label_height/4., 0.)
        with glMatrix():
            glScalef(scale_factor, scale_factor, 1)
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(dim_char))
        glTranslatef(self.miniSpanX/4., 0, 0)
        with glMatrix():
            glScalef(scale_factor, scale_factor, 1)
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord('='))
        glTranslatef(self.miniSpanX/4., 0, 0)
        with glMatrix():
            glScalef(scale_factor, scale_factor, 1)
            glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(str(dim_val)[0]))
        if two_digit_val:
            glTranslatef(self.miniSpanX/4., 0, 0)
            with glMatrix():
                glScalef(scale_factor, scale_factor, 1)
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(str(dim_val)[1]))        

    def drawLinks(self, shape, axis, link_colors, link_variance, scale = 1, selected = True):
        glMaterialfv(GL_FRONT_AND_BACK,GL_DIFFUSE,[1.0, 1.0, 1.0, 1.0])
        glPushMatrix()

        # take care of d and e dimensions by adjusting shape
        shape = tuple(shape)

        for start_node in np.ndindex(*shape):
            colors = link_colors[start_node]
            
            start_cyl = self.getCylinderIndex(start_node, shape, axis) 

            start = np.array(self.getNodePos2d(start_node, shape, axis, scale))


            # iterate over dimensions.
            for dim in range(3):
                end_node = self.getNextNode(start_node, dim, 1)
                # Skip torus wraparound links
                if end_node[dim] >= shape[dim]:
                    continue

                # Only render lines that connect points within the same cylinder
                end_cyl = self.getCylinderIndex(end_node, shape, axis) # uses all 5 dim's
                if start_cyl == end_cyl:
                    # Prevents occluding links on the innermost cylinder by not
                    # rendering links that would make T-junctions
                    if start_cyl == 0:
                        # find transverse dimension
                        for t in range(3):
                            if t != axis and t != dim: break
                        left_cyl = self.getCylinderIndex(self.getNextNode(start_node, t, -1), shape, axis)
                        right_cyl = self.getCylinderIndex(self.getNextNode(start_node, t, 1), shape, axis)
                        if end_cyl == right_cyl and end_cyl == left_cyl:
                            continue

                    end = np.array(self.getNodePos2d(end_node, shape, axis, scale))
                    #print 'scale = ' + str(scale) + ', axis = ' + str(axis) + ', start_node = '  + str(start_node) + ', start = ' + str(start) + ', end_node = ' + str(end_node) + ', end = ' + str(end)
                    #print '\t\tColors = ' + str(colors[dim])
                    #if self.axis == 0 and self.axis_index == 0:
                    #    print 'Nodes: ' + str(start_node) + ' to ' + str(end_node) + '; Drawing: ' + str(start) + ' to ' + str(end)
                    #self.drawLinkVariance(start, end, variance[dim], self.gap*scale)
                    if self.showVariance: 
                        variance = link_variance[start_node]
                        #print 'DRAWING LINK VARIANCE FOR dim = ' + str(dim)
                        center = start + ((end-start)/2)
                        minRadius = self.cylinder_width/2
                        self.drawCircle(variance[dim], self.min_variance, self.max_variance, minRadius, self.maxVarianceRadius, center)
                    #print 'link colors = ' + str(colors[dim])
                    link_color_values = list(colors[dim])
                    #print 'self.outOfRangeOpacity =',self.outOfRangeOpacity,', link_color_values[3] =',link_color_values[3]
                    
                    if not selected and link_color_values[3] != self.outOfRangeOpacity:
                        link_color_values[3] = 0.4
                    #print '\t\t\tlink_color_values =',link_color_values,', opacity =',link_color_values[3]
                    glColor4f(*link_color_values)
                    #self.drawLinkLine(start, end) 
                    self.drawLinkCylinder(start, end) # doesn't work with minimaps due to projection

        glPopMatrix()    

    # ------------------------    Render, Level 4    ---------------------------  
    
    def drawArrowHead(self, w, h, z_dist, size, direction):
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

    def drawBorder(self, w, h, border_width, z_dist):
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

    def drawLinkCylinder(self, start, end):
        # calculate a vector in direction start -> end
        v = end - start

        # interpolate cylinder points
        cyl_points = [tuple(p) for p in [start - v, start, end, end + v]]

        # Draw link
        #print 'Drawing cylinder of width = ' + str(self.cylinder_width)
        glePolyCylinder(cyl_points, None, self.cylinder_width )

    def drawRect(self, w, h, z_dist):
        with glSection(GL_QUADS):
            glVertex3f(0., 0., z_dist)
            glVertex3f(w, 0., z_dist)
            glVertex3f(w, h, z_dist)
            glVertex3f(0., h, z_dist)                


    # **************************        I/O       ******************************

    def changeNodeLinkBounds(self, lower, upper, links = True):
        if links:
            self.lowerBoundLinks = lower
            self.upperBoundLinks = upper
        else: 
            self.lowerBoundNodes = lower
            self.upperBoundNodes = upper

    def changeView(self, inc = True):
        '''Changes the 4th dimension value, keeping axis the same when possible.
        '''
        # first calculate the new 4th dimension
        w, h, d = self.getSliceDims()
        #print '\told axis =',self.axis,', axis_index =',self.axis_index,', w =',w,', h =',h,', d =',d
        if inc and d < len(self.shape)-2: # len shape = 5, so d < 3
            d += 1
        elif inc:
            d = 0
        elif not inc and d > 0:
            d -= 1
        elif not inc:
            d = len(self.shape)-2 # d = 3

        # if the new d-value is the current axis, inc axis since w, h, d tuple
        #   doesn't exist for axis == d (see self.axis_map)
        if d == self.axis:
            if self.axis < len(self.shape)-2:
                self.axis += 1
            else: # self.axis == 3
                self.axis = 0
        #print '\t\tcalling setNewView, axis =',self.axis,', axis_index =',self.axis_index,', w =',w,', h =',h,', d =',d
        self.setNewView(d)
        self.axisUpdateSignal.emit(self.axis, self.axis_index)
        self.updateAxis(self.axis, self.axis_index)

    def changeViewPlane(self, inc = True):
        # first calculate new axis
        w, h, d = self.getSliceDims()
        done = False
        while not done:
            if inc and self.axis < len(self.shape)-2:
                self.axis += 1
            elif inc:
                self.axis = 0
            elif not inc and self.axis > 0:
                self.axis -= 1
            elif not inc:
                self.axis = len(self.shape)-2

            # if the new axis is the current d-val, inc/dec again since (w, h, d)
            #    tuple doesn't exist for axis == d (see self.axis_map)
            if self.axis != d:
                done = True

        self.setNewView(d)
        self.axisUpdateSignal.emit(self.axis, self.axis_index)
        self.updateAxis(self.axis, self.axis_index)

    def mousePressEvent(self, event):

        # Return if haven't dragged module onto the data tree yet to prevent
        #   the error when mouse I/O fails to return, causing any keyboard
        #   modifier (shift, contrl..) to be mis-interpreted as mouseEvent
        if max(self.shape) == 0:
            return

        if event.button() == Qt.LeftButton:
            self.getMousePress(event.x(), self.height()-event.y())

    def mouseReleaseEvent(self, event):
        
        # Return if haven't dragged module onto the data tree yet to prevent
        #   the error when mouse I/O fails to return, causing any keyboard
        #   modifier (shift, contrl..) to be mis-interpreted as mouseEvent
        if max(self.shape) == 0:
            return

        if event.button() == Qt.RightButton:
            self.processPlaneHighlights(self.selectionPick(event), right_click = True)
        elif event.button() == Qt.LeftButton:
            self.processPlaneHighlights(self.selectionPick(event), right_click = False)

    def processPlaneHighlights(self, hitlist, right_click):
        w, h, d = self.getSliceDims()
        for i in hitlist:
            e_val = i/self.shape[d]
            d_val = i-e_val*self.shape[d]
            #print 'd_val = ' + str(d_val) + ', e_val = ' + str(e_val)
            if right_click: # toggle plane on and off
                if (d_val, e_val) not in self.view_planes[d]:
                    self.view_planes[d].add((d_val, e_val))
                else:
                    if len(self.view_planes[d]) > 1:
                        self.view_planes[d].remove((d_val, e_val))
                        if self.current_planes[d] == d_val and self.current_planes[4] == e_val:
                            sorted_planes = sorted(self.view_planes[d],
                              key = lambda val: val[1]*self.shape[d] + val[0])
                            #print 'sorted_planes = ' + str(sorted_planes)
                            self.current_planes[d] = sorted_planes[0][0]
                            self.current_planes[4] = sorted_planes[0][1]
            else: # left click, set this to be the new current plane
                if (d_val, e_val) not in self.view_planes[d]:
                    self.view_planes[d].add((d_val, e_val))
                self.current_planes[d] = d_val
                self.current_planes[4] = e_val
            self.viewPlanesUpdateSignal.emit(self.view_planes)

    def selectionPick(self, event):
        """Allow the user to pick nodes."""
        # Adapted from Josh Levine's version in Boxfish 0.1
        #steps:
        #render the scene with labeled nodes
        #find the color of the pixel @self.x, self.y
        #map color back to id and return
        #self.updateGL()
        self.paintEvent(event)

        #disable unneded
        glDisable(GL_LIGHTING)
        glDisable(GL_LIGHT0)
        prev_blend_on = glGetBoolean(GL_BLEND)
        glDisable(GL_BLEND)

        #set up the selection buffer
        w, h, d = self.getSliceDims()
        select_buf_size = self.dataModel.shape[d] * self.dataModel.shape[4] + 10
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
        #glLoadIdentity()
        #glTranslatef(*self.translation[:3])
        #glMultMatrixd(self.rotation)

        #self.orient_scene()
        # Redo the drawing
        glPushMatrix()
        # don't need resetView because it's called once, changing translation/rotation
        #   and paintGL calls orient_scene which takes this translation/rotation into account
        #self.resetView()  
        #print 'translation = ' + str(self.translation) + ', rotation = ' + str(self.rotation)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.orient_scene() # push the view back to get behind front clip plane
        self.draw(toolbar = False)
        super(Torus5dViewOverview, self).paintGL()
        #super(Torus5dViewOverview, self).updateGL()
        #self.updateGL()
        
        #self.drawOverview()
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
        for hit in pick_buffer:

            if hit[0] < nearest :
              nearest = hit[0]
              hitlist = [hit[2][0]]

        #go back to normal rendering
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glPolygonMode(GL_FRONT_AND_BACK,GL_FILL)
        if prev_blend_on:
            glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        #print hitlist
        return hitlist

    def setNewView(self, d):
        for i in range(len(self.axis_map[self.axis])):
            temp_w, temp_h, temp_d = self.axis_map[self.axis][i]
            if d == temp_d:
                self.axis_index = i
                break
        #print '\tnew axis =',self.axis,', axis_index =',self.axis_index







# Possibly still relevant old method
'''
    def drawDimensionSelector(self, w, h):
        border_width = max(1., self.height()/200.)
        num_icons = len(self.shape)+1
        icon_width = (w-(2*border_width))/float(num_icons)
        icon_height = h-2*border_width
        w, h, depth = self.getSliceDims()

        with glMatrix():
            glLineWidth(border_width)

            # first set color and draw the inner border of this sub-window
            if self.bright_bg_color:
                glColor4f(0.35, 0.35, 0.35, 1.)
            else:
                glColor4f(0.65, 0.65, 0.65, 1.)
            self.drawBorder(w-border_width, h-border_width, border_width, 0.15)
            glTranslatef(border_width, border_width, 0.)

            # next draw the icon border and image
            icon_border_width = max(1., self.height()/400.)
            glColor4f(0.5, 0.5, 0.5, 1.)
            #self.drawBorder(icon_width, icon_height, icon_border_width, 0.2)

            for i in range(len(self.shape)):
                glTranslatef(icon_width, 0., 0.)
                if i == depth:
                    glColor4f(*self.getAxisLabelColor(self.parent.agent.coords[i]))
                else:
                    glColor4f(0.5, 0.5, 0.5, 1.)                    

                # draw a box and label for each coordinate
                #self.drawBorder(icon_width, icon_height, icon_border_width, 0.2)
'''
