import math
import numpy as np
from OpenGL.GL import *
from Torus5dModule import *
from boxfish.gl.GLWidget import set_perspective
from boxfish.gl.glutils import *
from OpenGL.GLUT import *

class Torus5dViewMinimaps(Torus5dGLWidget):
    ''' Draws a view which shows the average link values bundled together. Every
    3d slice has three of the five dimensions (a, b, c, d, e) mapped to OpenGL
    x, y, and z.  By default, half of the horizontal links (first dimension,
    mapped to OpenGL x) and half of the vertical links (second dimension, mapped
    to OpenGL y) are shown, with a color value calculated by averaging these 
    links for all possible values in the third dimension.  This is 
    sufficient to show patterns in the data. For more detail consult the 
    Torus3dView2d module or the Torus 5d User Guide.
    '''

    # ***************************    Initialize    *****************************

    axisUpdateSignal = Signal(int, int)
    viewPlanesUpdateSignal = Signal(dict)

    def __init__(self, parent, dataModel):
        ''' Draw the overview of the main window - including minimaps and
        any other overviews.'''
        super(Torus5dViewMinimaps, self).__init__(parent, dataModel, rotation = False)

        self.show_axis = {0: [0, 1, 2], 1: [0, 1, 2], 2: [0, 1, 2], 3: [0, 1, 2], 4: []}
        self.showTotalVariance = True
        self.valuesInitialized = False
        self.reverseDrag = True
        self.left_drag = False
        self.left_press = False
        self.right_drag = False
        self.right_press = False
        self.showVariance = False
        self.scaleFactor = 0.5
        self.firstDraw = True
        self.cylinder_width = 2
        self.cylinder_width_offset = 0
        self.vertical_offset = 0
        self.max_vertical_offset = 0
        self.clicked_axis = -1
        self.clicked_axis_index = -1
        self.num_minimaps_total = 12 # TODO:  Allow this to be changed w/ toolbar
        self.num_minimaps_x = 3
        self.num_minimaps_y = self.num_minimaps_total / self.num_minimaps_x
        self.scaleVarianceLinks = False
        self.miniBorder = 0.01
        self.labelWidth = 0.21 + self.miniBorder
        self.labelHeight = 0.2 + self.miniBorder
        self.legendHeight = 0.2 + self.miniBorder
        self.borderInset = 0.0112
        Qt.ShiftModifier = False # to fix the weird vertical translation bug

        self.miniMapList = DisplayList(self.drawAllMiniMaps) # see glutils.py
        self.resizeSignal.connect(self.updateDrawing)

        self.widgetLists = []
        self.widgetLists.append(self.miniMapList)

        #self.updateMiniMapSizes()
        #self.updateMiniMapValues() #TODO: see what happens if this isn't here

    shape = property(fget = lambda self: self.dataModel.shape)
    view_planes = property(fget = lambda self: self.dataModel.view_planes)
    current_planes = property(fget = lambda self: self.dataModel.current_planes)

    def initializeGL(self):
        """Turn up the ambient light for this view and enable simple
           transparency.  To keep views looking the same."""
        super(Torus5dViewMinimaps, self).initializeGL()
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [1.0, 1.0, 1.0, 1.0])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        glLineWidth(self.link_width)


    # ***************************      Update      *****************************

    def update(self, colors = True, values = True):
        ''' Updates minimap values and colors by default.  Connected to node/link
        updates from the datamodel.
        '''
        if colors: super(Torus5dViewMinimaps, self).update()
        if values: self.updateMiniMapValues()
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
            self.updateMiniMapLayout()
            self.updateDrawing()
    
    def updateDrawing(self):
        ''' Does not update the values, only re-draws.  For resizing events.'''

        # for debugging
        self.reDrawing = True

        self.updateMiniMapSizes()
        self.miniMapList.update()
        #self.updateGL()
        self.paintEvent(None)

    def updateMiniMapBoxPos(self, bl_x, bl_y, tr_x, tr_y, row, col, d_list, 
        e_list):

        for d_val in d_list:
            for e_val in e_list:
                [[curr_bl_x, curr_bl_y], [curr_tr_x, curr_tr_y]] = self.minimaps_box_pos[row][col][d_val][e_val] 
                self.minimaps_box_pos[row][col][d_val][e_val] = [[curr_bl_x + bl_x, curr_bl_y + bl_y],
                  [curr_tr_x + tr_x, curr_tr_y + tr_y]]

    def updateMiniMapLayout(self):
        ''' Calculates the number of 4th and 5th dimension planes to show variance for.
        Also calculates the maps to go between axis, axis_index and row, col. '''
        # calculate minimap width
        border = 5
        self.minimap_size_x = int((self.width() - (self.num_minimaps_x + 1) * border) \
            / self.num_minimaps_x)

        # find the minimum gap between cylinders and that is the max variance circle radius
        #   to keep max radius consistent between minimaps
        # also, calculate numVarianceCircles and minimap_size_y for each minimap separately
        min_scale = 10000
        row = 0
        col = 0
        high_dim_planes = [[0 for i in range(self.num_minimaps_x)] for j in range(self.num_minimaps_y)]
        self.rowColToAxis = [[[] for i in range(self.num_minimaps_x)] for j in range(self.num_minimaps_y)]
        self.axisToRowCol = [[[] for j in self.show_axis[axis]] for axis in range(len(self.show_axis))]

        for axis in range(len(self.show_axis)):
            for axis_index in self.show_axis[axis]:
                width, height, depth = self.axis_map[axis][axis_index]
                scale = min(float(self.minimap_size_x) / self.shape[width] / 2.,
                        float(self.minimap_size_x) / self.shape[height] / 2.)
                min_scale = min(scale, min_scale)
                col += 1
                if col >= self.num_minimaps_x:
                    col = 0
                    row += 1
        
        self.maxVarianceRadius = min_scale * self.gap/2 * self.scaleFactor
        # calculate the number of extra rows for showing 4th/5th dimension plane variance
        self.varianceCircleGap = self.maxVarianceRadius/1.5 # TODO:  Tweak this to find proper spacing?
        self.numVarianceCircles = [[[0] for axis_index in self.show_axis[axis]] for axis in range(len(self.show_axis))]

        self.maxVarianceRows = 0
        d, axis, axis_index = self.getFirstMiniMap() # what d-value to start with and what axis
        minimap_count = 0
        for i in range(self.num_minimaps_y): # row
            for j in range(self.num_minimaps_x): # column
                if minimap_count < self.num_minimaps_total:
                    self.rowColToAxis[i][j] = (axis, axis_index)
                    self.axisToRowCol[axis][axis_index] = (i, j)
                    high_dim_planes[i][j] = self.shape[d] * self.shape[4]
                    self.numVarianceCircles[axis][axis_index][0] = int(
                        (self.minimap_size_x * (1 - self.labelWidth)) / \
                        (self.maxVarianceRadius*2 + self.varianceCircleGap*2))
                    total_circles = self.numVarianceCircles[axis][axis_index][0]
                    count = 1
                    while total_circles < high_dim_planes[i][j]:
                        self.numVarianceCircles[axis][axis_index].append(int(self.minimap_size_x/(2 * (self.maxVarianceRadius + self.varianceCircleGap))))
                        total_circles += self.numVarianceCircles[axis][axis_index][count]
                        count += 1
                    diff = total_circles - high_dim_planes[i][j]
                    # Make sure numVarianceCircles adds up to the total
                    self.numVarianceCircles[axis][axis_index][count-1] -= diff 
                    self.maxVarianceRows = max(len(self.numVarianceCircles[axis][axis_index]), self.maxVarianceRows)
                    d, axis, axis_index = self.getNextMiniMap(d, axis)
                    minimap_count += 1                    
                
    def updateMiniMapSizes(self):
        """Determines the size and placement of the minimaps based on the the
           size of the gl window.  12 minimaps arranged in 6x2 (row x col) default.
           Also determines the maximum circle size based on smallest gap between cylinders.
        """
        if max(self.shape) == 0:
            return
        elif self.firstDraw:
            self.updateMiniMapLayout()
            self.firstDraw = False

        # calculate minimap width and height - note all minimaps have the same height to make layout look nicer
        border = 5
        self.minimap_size_x = int((self.width() - (self.num_minimaps_x + 1) * border) \
            / self.num_minimaps_x) 
        self.minimap_size_y = int(self.minimap_size_x * (1 + (self.labelHeight * self.maxVarianceRows) + self.legendHeight))    

        # store the xy positions of each plane variance box
        self.minimaps_box_pos = [[[] for j in range(self.num_minimaps_x)] for i in range(self.num_minimaps_y)]
        self.minimaps_var_rowcol = [[[] for j in range(self.num_minimaps_x)] for i in range(self.num_minimaps_y)]
        self.minimaps_var_vals = [[[] for j in range(self.num_minimaps_x)] for i in range(self.num_minimaps_y)]

        # find the minimum gap between cylinders and that is the max variance circle radius
        #   to keep max radius consistent between minimaps
        # also, calculate numVarianceCircles and minimap_size_y for each minimap separately
        min_scale = 10000
        for axis in range(len(self.show_axis)):
            for axis_index in self.show_axis[axis]:
                width, height, depth = self.axis_map[axis][axis_index]
                scale = min(float(self.minimap_size_x) / self.shape[width] / 2.,
                        float(self.minimap_size_x) / self.shape[height] / 2.)
                min_scale = min(scale, min_scale)

        self.maxVarianceRadius = min_scale * self.gap/2 * self.scaleFactor
        self.varianceCircleGap = self.maxVarianceRadius/1.5 # TODO:  Tweak this to find proper spacing?   

        # could improve efficiency by only re-creating the list when necessary
        self.minimaps_x = list()

        for i in range(self.num_minimaps_x):
            self.minimaps_x.append((i+1)*border + i*self.minimap_size_x)

        self.minimaps_y = list()
        for i in range(self.num_minimaps_y):
            self.minimaps_y.append(self.height() - (i+1)*(border + self.minimap_size_y) + self.vertical_offset)

        self.max_vertical_offset = (border + self.num_minimaps_y * (border +  \
            self.minimap_size_y)) - self.height()

        self.cylinder_width = self.minimap_size_x/40. + self.cylinder_width_offset
        while self.cylinder_width < 0: # do this to find minimum cylinder_width_offset
            self.cylinder_width_offset += 1
            self.cylinder_width = self.minimap_size_x/40. + self.cylinder_width_offset

    def updateMiniMapValues(self):
        """Determines link colors for the minimaps by averaging.

        Currently averaging 'd' and 'e' dimensions just like the axis we're looking
         down. Also only works for 5D torus since assumes len(non_slice_indicies) = 2.
        """

        self.miniColors = list()
        self.miniVariance = list()
        # plane variance based on the average link bundle variance in the plane
        self.planeAvgVariance = list()
        self.planeMaxVariance = list()
        # plane variance based on the average link value in the whole plane
        self.planeTotalVariance = list() 

        # stuff for drawing the box-and-whisker style plots
        self.planeAvgLinkValue = list()
        self.planeStdDevLinkValue = list()
        self.planeLinkSpread = list()
        self.planeMeanLinkValue = list()
        self.globalMinLinkValue = sys.maxint
        self.globalMaxLinkValue = -sys.maxint-1
        min_variance = min_plane_variance = sys.maxint
        max_variance = max_plane_variance = -sys.maxint - 1

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
                link_colors = np.tile(self.default_link_color, 
                  [shape[w], shape[h], 1] + [3,1]) #uses slice dims
                #store link variance by slice
                link_variance = np.tile(0., [shape[w], shape[h], 1] + [3]) 
                plane_link_variance = np.tile(0., [shape[d], shape[4], shape[w], shape[h], 1, 3])
                # average the link bundles leaving every node in the slice, storing by 4th/5th dimension
                plane_link_values = np.tile([0. for i in range(self.shape[axis])],
                  [shape[d], shape[4]] + [shape[w], shape[h], 1] +  [3, 1])
                #print 'plane_link_values.shape = ' + str(plane_link_values.shape)
                #print '\nMAX PLANE_TOT_INDEX = ' + str(3*np.product(slice_shape)-1) \
                #  + ', MAX PLANE_AVG_INDEX = ' + str(3*self.shape[axis]-1)
                plane_total_variance = np.tile(0., [shape[d], shape[4]])
                plane_link_spread = np.tile([sys.float_info.max, sys.float_info.min], [shape[d], shape[4], 1])
                plane_mean_value = np.tile(0., [shape[d], shape[4]])
                plane_avg_variance = np.tile(0., [shape[d], shape[4]])
                plane_max_variance = np.tile(0., [shape[d], shape[4]])
                #print '\tplane_tot_index = ' + str(plane_tot_index)
                plane_tot_index = 0 # resets for each new 4th and 5th dimension plane
                for node in np.ndindex(*mini_shape): # 5D node, but non-slice dims (plus axis) are 1
                    dim_count = 0
                    #print '\tplane_avg_index = ' + str(plane_avg_index)
                    for dim in slice_indicies:
                        val = 0.0
                        count = 0
                        subNode = list(node)
                        link_values = list()

                        val_added_count = 0
                        for i in range(self.shape[axis]):
                            for j in range(self.shape[d]):
                                higher_dims = [t for t in non_slice_indicies if t != d] # == [4] for 5 dim
                                for k in range(self.shape[higher_dims[0]]):
                                    subNode[axis] = i
                                    subNode[non_slice_indicies[0]] = j
                                    subNode[non_slice_indicies[1]] = k
                                    current = self.dataModel.link_values[
                                            tuple(subNode)][dim][0]
                                    if current > self.globalMaxLinkValue:
                                        self.globalMaxLinkValue = current
                                    elif current < self.globalMinLinkValue:
                                        self.globalMinLinkValue = current

                                    if current < plane_link_spread[j][k][0]:
                                        plane_link_spread[j][k][0] = current
                                    elif current > plane_link_spread[j][k][1]:
                                        plane_link_spread[j][k][1] = current

                                    # TODO:  Check what happens if this is +=current instead of =current
                                    plane_link_values[j][k][tuple([node[w], node[h], 0])][dim_count][i] = current
                                    #print '\ncurrent = ' + str(current) + ', plane_link_value = ' + str(plane_link_values[j][k][tuple([node[w], node[h], 0])][dim_count][i])
                                    if (j, k) in self.view_planes[d]:
                                        link_values.append(current)
                                        #print 'link_value = ' + str(link_values[len(link_values)-1])
                                        val += current
                                        val_added_count += 1
                                        count += self.dataModel.link_values[
                                            tuple(subNode)][dim][1] # TODO : Ask Kate why this is necessary / when it's used?   

                        if shape[axis] != 0:
                            if count == 0:
                                mean = 0
                                variance = 0
                            else:
                                mean = val / count
                                variance = (np.sum(np.square(link_values))/count) - (mean*mean)
                                link_variance[(node[w], node[h], 0)][dim_count] = variance
                                #print '\nlink_variance[node()][dim] = ' + str(link_variance[(node[w], node[h], 0)][dim_count])
                                #print '\nlink_values[node] = ' + str(link_values)
                                for j in range(self.shape[d]):
                                    for k in range(self.shape[higher_dims[0]]):
                                        #print 'plane_link_values[d][e][node][dim] = ' + str(plane_link_values[j][k][(node[w], node[h], 0)][dim_count])
                                        mean = np.sum(plane_link_values[j][k][(node[w], node[h], 0)][dim_count]) / self.shape[axis]
                                        #print '\tmean = ' + str(mean)
                                        variance_plane = (np.sum(np.square(plane_link_values[j][k][(node[w], node[h], 0)][dim_count]))/(self.shape[axis])) - mean*mean
                                        plane_link_variance[j][k][(node[w], node[h], 0)][dim_count] = variance_plane
                                        #print 'plane_link_variance[j][k][node()][dim] = ' + str(plane_link_variance[j][k][(node[w], node[h], 0)][dim_count])
                                        #if variance_plane > 2*variance or variance_plane < 0.5*variance:
                                            #print 'wrong, axis = ' + str(axis) + ', axis_index = ' + str(aindex) + ', j = ' + str(j) + ', k = ' + str(k) + ', dim = ' + str(dim) + ', dim_count = ' + str(dim_count)
                            if variance > max_variance: max_variance = variance
                            if variance < min_variance: min_variance = variance
                            #print 'val = ' + str(val) + ', count = ' + str(count) + ', val_added_count = ' + str(val_added_count)
                            #print '\tcalling map_link_color(' + str(val/float(val_added_count)) +', 1.)'
                            temp = self.map_link_color(
                                val / float(val_added_count), 1.0) \
                                if count / float(self.shape[axis]) \
                                >= 1 else self.default_link_color
                            if temp[3] != 1.:
                                pass
                                #print 'BAD, link_color = ' + str(temp)
                            link_colors[(node[w], node[h], 0)][dim_count] = self.map_link_color(
                                val / float(val_added_count), 1.0) \
                                if count / float(self.shape[axis]) \
                                >= 1 else self.default_link_color

                        dim_count += 1

                #print 'self.shape = ' + str(self.shape) + ', plane_link_variance[j][k].shape = ' + str(plane_link_variance[j][k].shape)
                for j in range(self.shape[d]):
                    for k in range(self.shape[higher_dims[0]]):
                        total_count = np.product(slice_shape) * 3
                        avg_count = shape[w] * shape[h] * 3
                        # TODO:  Check to see when variance dim is used in drawLinkVariance (print out in place)
                        #   to make sure we want to include dim = axis in this summation
                        total_mean = np.sum(plane_link_values[j][k])/total_count
                        plane_mean_value[j][k] = total_mean
                        plane_total_variance[j][k] = (np.sum(np.square(plane_link_values[j][k]))/total_count) - (total_mean*total_mean)
                        plane_avg_variance[j][k] = np.sum(plane_link_variance[j][k])/avg_count
                        if plane_total_variance[j][k] > max_plane_variance: max_plane_variance = plane_total_variance[j][k]
                        if plane_total_variance[j][k] < min_plane_variance: min_plane_variance = plane_total_variance[j][k]

                #print 'axis = ' + str(axis) + ', map = ' + str(self.axis_map[axis]) + ', plane_total_variance = ' + str(plane_total_variance) + ', link_variance = ' + str(link_variance)

                #print 'plane_avg_variance[j][k] = ' + str(plane_avg_variance[j][k])
                
                self.planeMeanLinkValue.append(plane_mean_value.copy())
                self.planeLinkSpread.append(plane_link_spread.copy())
                self.planeAvgVariance.append(plane_avg_variance.copy())
                self.planeTotalVariance.append(plane_total_variance.copy())
                #print 'planeAvgVariance[axis][aindex] = ' + str(self.planeAvgVariance[axis][aindex]) 
                self.miniColors.append(link_colors.copy())
                self.miniVariance.append(link_variance.copy())
                aindex += 1

        self.min_variance = min_variance
        self.max_variance = max_variance
        self.min_plane_variance = min_plane_variance
        self.max_plane_variance = max_plane_variance
        self.valuesInitialized = True
        #print '**************** UPDATED MINIMAP VALUES ********************'


    # ***************************    Calculate     *****************************

    def getAxisLabelColor(self, val):
        # since lines and cylinders don't look alike, we need to turn
        #   up the ambient light in this view - but then the colors
        #   look too bright, so dull them out slightly
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
        
        return tuple(list(np.subtract(color[:3], 0.1)) + [1.])

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
            return (0., 0., 0., 0.35)
            #return (0.6, 0.6, 0.6, 0.8) # prev (0.2, 0.2, 0.2, 0.7)
        else:
            return (1., 1., 1., 0.35)
            #return (0.4, 0.4, 0.4, 0.8) # prev (0.6, 0.6, 0.6, 0.6)

    def getClickMiniMap(self, x, y, variance = True):
        """Checks if the given (x,y) value falls within a minimap.  If it is
        in plane variance boxes, toggle that plane.  Otherwise if it's inside
        the minimap, return (axis, axis_index) of the minimap."""
        if max(self.shape) == 0:
            return

        axis, axis_index, row, col, d_val, e_val = -1, -1, -1, -1, -1, -1
        done = False
        for j in range(self.num_minimaps_x): #col
            if done: # to escape this for loop if done
                break
            for i in range(self.num_minimaps_y): #row
                if i * self.num_minimaps_x + j < self.num_minimaps_total:
                    if x > self.minimaps_x[j] and x < self.minimaps_x[j] +  \
                    self.minimap_size_x and y > self.minimaps_y[i] and \
                    y < self.minimaps_y[i] + self.minimap_size_y:
                        axis, axis_index = self.rowColToAxis[i][j]
                        if variance and y < self.minimaps_box_pos[i][j][0][0][1][1]:
                            d_val, e_val = self.getClickPlaneVariance(axis, axis_index, i, j, x, y)
                            row = i
                            col = j
                            done = True
                            break

        return (axis, axis_index, d_val, e_val) #already done checking all possible maps        

    def getClickPlaneVariance(self, axis, axis_index, row, col, x, y):
        w, h, d = self.axis_map[axis][axis_index]
        done = False
        d_val, e_val, = -1, -1
        for i in range(self.shape[d]):
            if done:
                break
            for j in range(self.shape[4]):
                # get bottom left (bl) and top right (tr) x and y
                (bl_x, bl_y), (tr_x, tr_y) = self.minimaps_box_pos[row][col][i][j]
                #print '\tchecking: x = ' + str(x) + ', y = ' + str(y) + ', bl = ' + str((bl_x, bl_y)) + ', tr = ' + str((tr_x, tr_y))
                if x > bl_x and x <= tr_x:
                    if y > bl_y and y <= tr_y:
                        d_val = i
                        e_val = j
                        done = True
                        break
        # if x, y is to the right of the last plane variance, return -2, -2 to signal
        #   the leftDrag to treat that position as the last d,e values
        if not done:
            (first_bl_x, first_bl_y), (first_tr_x, first_tr_y) = self.minimaps_box_pos[row][col][0][0]
            (last_bl_x, last_bl_y), (last_tr_x, last_tr_y) = self.minimaps_box_pos[row][col][self.shape[d]-1][self.shape[4]-1]
            if y >= bl_y and y <= tr_y and x >= tr_x and x <= first_bl_x + self.minimap_size_x:
                d_val, e_val = -2, -2

        #print '\tvariancePlane: d_val = ' + str(d_val) + ', e_val = ' + str(e_val)
        return (d_val, e_val)        

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

    def getFirstMiniMap(self):
        w, h, d = self.getSliceDims() # first draw the current d-val
        if d == 0:
            axis = 1 # since d, axis can never be the same
        else:
            axis = 0 # simple starting point

        return (d, axis, self.getAxisIndex(d, axis))

    def getAxisIndex(self, d_val, axis):
        ''' Return the axis and axis_index of next minimap to draw.'''
        # find the first axis_index with d == d-val
        
        for axis_index in self.show_axis[axis]:
            w, h, d = self.axis_map[axis][axis_index]
            if d_val == d:
                break

        return axis_index
    
    def getNextMiniMap(self, d_val, axis):
        done = False
        while not done:
            if axis < len(self.shape)-2: # if axis < 3
                axis += 1
            else:
                axis = 0
                if d_val < len(self.shape)-2: # if d < 3
                    d_val += 1
                else: 
                    d_val = 0
            if d_val != axis:  
                # valid minimap, see Torus5dGLWidget.axis_map in Torus5dModule.py
                done = True

        return (d_val, axis, self.getAxisIndex(d_val, axis))

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

        return node2d

    def getSliceDims(self):
        """Get the dimensions that span width, height, depth of screen"""
        return self.axis_map[self.axis][self.axis_index]
    
    def getSliceSpan(self, shape, axis = 2):
        """Span in OpenGL 2D space of each dimension of the 2D view"""
        b = self.node_size * self.node_pack_factor
        h = shape[axis] * b + self.gap
        def span(d):
            if d % 2 == 0:
                return d * h + b
            else:
                return (d-1) * h + b
            #return d * b * shape[axis] + (d-1) * self.gap
            #return b * (shape[axis] + self.gap) * (d+2)
        return [span(d) for d in shape]


    # ****************************     Render      *****************************

    # ------------------------    Render, Level 0    ---------------------------

    #def paintGL(self):
    #    ''' How the QGLWidget is supposed to render the scene.'''
    #    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    #    glGetError()
    #    self.orient_scene()
    #    self.draw()
    #    super(Torus5dViewMinimaps, self).paintGL()

    def paintEvent(self, event):
        ''' How the QGLWidget is supposed to render the scene.'''
        with setupPaintEvent(self):
            glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
            glGetError()
            self.orient_scene()
            self.draw()
            super(Torus5dViewMinimaps, self).paintEvent(event)

    # ------------------------    Render, Level 1    ---------------------------  

    def draw(self):
        ''' Draw color bars and minimaps.'''
        with overlays2D(self.width(), self.height(), self.bg_color):
            for func in self.widgetLists:
                func()

    # ------------------------    Render, Level 2    ---------------------------  

    def drawAllMiniMaps(self):
        """Draws all 12 minimaps."""

        if max(self.shape) == 0:
            return
        elif not self.valuesInitialized:
            return

        glEnable(GL_LIGHTING) # to keep things looking the same
        glEnable(GL_LIGHT0)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        grey_value = (self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) /  3
        if grey_value >= 0.5:
            self.bright_bg_color = True
        else:
            self.bright_bg_color = False

        self.updateMiniMapSizes()

        d, axis, axis_index = self.getFirstMiniMap()
        count = 0
        for i in range(self.num_minimaps_y): #row
            for j in range(self.num_minimaps_x): #column
                if count < self.num_minimaps_total: # when last row isn't full
                    self.drawMiniMap(axis, axis_index, self.minimaps_x[j],
                    self.minimaps_y[i], self.minimap_size_x, self.minimap_size_y)
                    d, axis, axis_index = self.getNextMiniMap(d, axis)
                    count += 1

    # ------------------------    Render, Level 3    ---------------------------  

    def drawMiniMap(self, axis, axis_index, x, y, w, h):
        """Draws the minimap for the given axis.  After fixing anti-aliasing,
        go back to line widths proportional to window width."""
        setup_overlay2D(x, y, w, h)   

        #glEnable(GL_BLEND)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        border_width = 2.
        with glMatrix():
            # Calculate border size and line color
            if axis == self.axis and axis_index == self.axis_index:
                alpha = 0.9 # has no effect if not enabling GL_BLEND above
                color_offset = 1
            else:
                alpha = 0.8
                if self.bright_bg_color:
                    color_offset = 0.45
                else:
                    color_offset = 0.3
                
            # Set line color for border and labels
            if self.bright_bg_color:
                line_color = (1. - color_offset, 1. - color_offset, 1. - color_offset, alpha)
            else:
                line_color = (0. + color_offset, 0. + color_offset, 0. + color_offset, alpha)
            border_offset = border_width
            box_border_width = 1.
            z_dist = -0.9

            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glTranslatef(x, y, 0)

            self.drawMiniMapLinks(axis, axis_index, x, y, w, h)
            # outer border is offset by half so line doesn't extend beyond border_offset
            self.drawRectBorder(w, h, line_color, border_width, math.ceil(border_offset/2.), -0.9)
            self.drawAxisLegend(axis, axis_index, w, h, line_color, border_offset)
            self.drawPlaneVarianceLegend(axis, axis_index, w, h, line_color, border_offset, box_border_width)
            self.drawPlaneVarianceBoxes(x, y, axis, axis_index, w, h, line_color, color_offset, border_offset, box_border_width)

        #glDisable(GL_BLEND)
        glLineWidth(self.link_width)

    # ------------------------    Render, Level 4    ---------------------------  

    def drawAxisLegend(self, axis, axis_index, w, h, line_color, border_offset):
        '''Draw axis labels and arrows for a minimap.'''
         # Draw Label based on run coords - also draw horizontal and vert.
        coords = self.parent.agent.coords # coord names from user
        horiz, vert, depth = self.axis_map[axis][axis_index]
        # h-w is the total height of variance labels and legend; will draw
        #   based on w and legendHeight, and offset by this amount vertically
        vert_offset = h-w

        # Note:  legend width is really w-2*border_offset, so just using w here
        #   instead of calculating legend width
        # If re-doing this, make all this relative to legendHeight and legendWidth,
        #   and just translate to the position it needs to be in taking into account
        #   the border offset

        # first draw the line to give a border to the legend
        #glLineWidth(w/400.)
        glLineWidth(1.)
        glColor4f(*line_color)
        with glMatrix():
            with glSection(GL_LINES):
                glVertex3f(border_offset, w*(1-self.legendHeight) + (h-w) - border_offset, 0.01) # top section is 15% of w
                glVertex3f(w-border_offset, w*(1-self.legendHeight) + (h-w) - border_offset, 0.01)

        # now draw the axis dimension's label (axis we're looking down)
        #glLineWidth(w/200.)
        glLineWidth(1.)
        with glMatrix(): 
            #color = self.getAxisLabelColor('a')
            color = self.getAxisLabelColor(coords[axis])
            glColor4f(*color) #color[0], color[1], color[2], color[3]
            # first draw the arrow
            startX = 0.18
            endX = startX + (0.5*self.legendHeight)
            startY = 1-(0.75*self.legendHeight)
            endY = startY + (0.5*self.legendHeight)

            leftX = endX + 0.25*self.legendHeight*np.cos(180*np.pi/180.)
            leftY = endY + 0.25*self.legendHeight*np.sin(180*np.pi/180.)
            rightX = endX + 0.25*self.legendHeight*np.cos(270*np.pi/180.)
            rightY = endY + 0.25*self.legendHeight*np.sin(270*np.pi/180.)

            # to compensate for border which extends into the legend, push
            #   leftmost label down and to the right by border_offset
            with glSection(GL_LINES):
                glVertex3f(border_offset*1.5 + w*startX, w*startY + vert_offset - border_offset, 0)
                glVertex3f(border_offset*1.5 + w*endX, w*endY + vert_offset - border_offset, 0)
            with glSection(GL_TRIANGLES):
                glVertex3f(border_offset*1.5 + w*endX, w*endY + vert_offset - border_offset, 0.05) 
                glVertex3f(border_offset*1.5 + w*leftX, w*leftY + vert_offset - border_offset, 0.05)
                glVertex3f(border_offset*1.5 + w*rightX, w*rightY + vert_offset - border_offset, 0.05)
            glTranslatef(border_offset*1.5 + w*0.05, w*(1-(0.75*self.legendHeight)) + vert_offset - border_offset, 0)
            glScalef(w*0.001, w*0.001, w*0.001)
            
            for c in coords[axis]:
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(c))
        
        # draw the horizontal dimension's label
        # border is only above, so subtract border_offset from y verticies
        with glMatrix():
            color = self.getAxisLabelColor(coords[horiz])
            glColor4f(*color)
            offset = 0.0315
            # draw arrow
            with glSection(GL_LINES):
                glVertex3f(w*(0.483+offset), w*(1-(0.5*self.legendHeight)) + vert_offset - border_offset, 0) #line length = 0.15
                glVertex3f(w*(0.633+offset), w*(1-(0.5*self.legendHeight)) + vert_offset - border_offset, 0) # height between 0.875 and 0.95
            with glSection(GL_TRIANGLES):
                glVertex3f(w*(0.633+offset), w*(1-(0.5*self.legendHeight)) + vert_offset - border_offset, 0.05)
                glVertex3f(w*(0.603+offset), w*(1-(0.3*self.legendHeight)) + vert_offset - border_offset, 0.05)
                glVertex3f(w*(0.603+offset), w*(1-(0.7*self.legendHeight)) + vert_offset - border_offset, 0.05)
            glTranslatef(w*(0.367+offset), w*(1-(0.75*self.legendHeight)) + vert_offset - border_offset, 0)
            glScalef(w*0.001, w*0.001, w*0.001)
            for c in coords[horiz]:
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(c))
        
        # draw vertical dimension's label
        # border is on right and above, so subtract border_offset from x and y verticies
        with glMatrix():
            color = self.getAxisLabelColor(coords[vert])
            glColor4f(*color)
            offset = 0.1
            # draw arrow
            with glSection(GL_LINES):
                glVertex3f(w*(0.816+offset) - border_offset, w*(1-(0.75*self.legendHeight)) + vert_offset - border_offset, 0) # width between 0.683 and 0.95
                glVertex3f(w*(0.816+offset) - border_offset, w*(1-(0.2*self.legendHeight)) + vert_offset - border_offset, 0)
            with glSection(GL_TRIANGLES):
                glVertex3f(w*(0.816+offset) - border_offset, w*(1-(0.75*self.legendHeight)) + vert_offset - border_offset, 0.05) #was h*.975
                glVertex3f(w*(0.786+offset) - border_offset, w*(1-(0.575*self.legendHeight)) + vert_offset - border_offset, 0.05) #was h*.945
                glVertex3f(w*(0.846+offset) - border_offset, w*(1-(0.575*self.legendHeight)) + vert_offset - border_offset, 0.05)
            glTranslatef(w*(0.683+offset) - border_offset, w*(1-(0.75*self.legendHeight)) + vert_offset - border_offset, 0)
            glScalef(w*0.001, w*0.001, w*0.001)
            for c in coords[vert]:
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(c))  

    def drawMiniMapLinks(self, axis, axis_index, x, y, w, h):

        # setup a perspective projection for the links only
        #viewport_params = glGetIntegerv(GL_VIEWPORT)
        #glViewport(x, y, w, h)
        #glDisable(GL_SCISSOR_TEST)
        #glMatrixMode(GL_PROJECTION)
        #glPushMatrix()
        #glLoadIdentity()
        #glScissor(x, y, w, h)
        #glViewport(x, y, w, h)
        #set_perspective(self.fov, float(w)/h, self.near_plane, self.far_plane)
        #glMatrixMode(GL_MODELVIEW)

        with glMatrix():
            #glLoadIdentity()
            #glTranslatef(x, y, 0) # push back for perspective projection
            #glColor4f(1., 0., 0., 1.)
            #with glSection(GL_QUADS):
            #    glVertex3f(0, 0, 0)
            #    glVertex3f(w, 0, 0)
            #    glVertex3f(w, h, 0)
            #    glVertex3f(0, h, 0)

            # Background color stays the same but we set this clear
            # information because otherwise it will be transparent.
            glClearColor(*self.bg_color)
            glClear(GL_COLOR_BUFFER_BIT)
            glClear(GL_DEPTH_BUFFER_BIT)

            # Draw Links by setting the axis we're looking down to a shape
            # of 1, thus compressing it to a single line.
            glLineWidth(2.)
            #glLineWidth(w/100.)
            mini_shape = list(self.shape[:])
            if mini_shape[axis] != 0:
                mini_shape[axis] = 1
            width, height, depth = self.axis_map[axis][axis_index]
            if self.shape[width] != 0 and self.shape[height] != 0:
                with glMatrix():
                    trans_height = w/2. + w * (len(self.numVarianceCircles[axis][axis_index]) * self.labelHeight)
                    glTranslatef(w/2., trans_height, 0)
                    scale = min(float(w) / self.shape[width] / 2.,
                        float(w) / self.shape[height] / 2.) # use w both times because minimap area is w*w
                    # axis should be 2, shape should be slice_shape being viewed here
                    effective_shape = (mini_shape[width], mini_shape[height], 1)
                    #print 'laying out links, effective_shape = ' + str(effective_shape)
                    self.drawLinks(effective_shape, 2,
                        self.miniColors[axis*3 + axis_index], 
                        self.miniVariance[axis*3 + axis_index], scale*self.scaleFactor) #TODO Make this 1 by fixing the window    


        #glMatrixMode(GL_PROJECTION)
        #glPopMatrix()
        #glViewport(*viewport_params)
        #glEnable(GL_SCISSOR_TEST)
        #glScissor(x, y, width, height)
        #glMatrixMode(GL_MODELVIEW)
        
    def drawPlaneVarianceBoxes(self, x, y, axis, axis_index, w, h, line_color, 
        color_offset, border_offset, box_border_width):
        ''' Draw all variance circles for the minimap with this
        axis and axis_index.  Also draws vertical lines separating each plane.
        '''
        #an array of number of 4th dim planes per row
        num_circles = self.numVarianceCircles[axis][axis_index] 
        num_rows = len(num_circles)
        # so num_rows is the number of rows of plane variance circles at the bottom
        horiz, vert, depth = self.axis_map[axis][axis_index]

        # to maximize responsiveness with mouse selection, store bottom left, top right x,y for each box
        row, col = self.axisToRowCol[axis][axis_index]

        self.minimaps_box_pos[row][col] = [[[[x, y], [x, y]] for e in range(self.shape[4])] 
            for d in range(self.shape[depth])]
        self.minimaps_var_rowcol[row][col] = [[[-1, -1] for e in range(self.shape[4])] 
          for d in range(self.shape[depth])]
        # need to save the row, col positions of each box, given their 4th and 5th dim values
        self.minimaps_var_vals[row][col] = [[[-1, -1] for j in range(num_circles[i])] 
          for i in range(num_rows)]       

        # Draw circles for 4th and 5th dim planes
        d_val = 0
        e_val = 0
        changed_circle_gap = False

        for i in range(num_rows): # how many rows we're doing
            glPushMatrix()
            # the actual gap should be calculated by evenly spacing the columns on this row
            total_variance_width = 2*self.maxVarianceRadius * num_circles[i]
            if i == 0:
                offset_x = w*self.labelWidth + border_offset + box_border_width
                offset_y = w*self.labelHeight*(num_rows-1) + \
                  (num_rows-1)*3*box_border_width + border_offset
                start_x = self.minimaps_x[col] + offset_x
                start_y = self.minimaps_y[row] + offset_y
                space = w*(1-self.labelWidth)-2* border_offset - 2*box_border_width * num_circles[i]
                # translate to first box, at bottom left corner;  first row move over label
                glTranslatef(offset_x, offset_y, 0)
                
            else:
                offset_x = border_offset + box_border_width
                offset_y = w*self.labelHeight*(num_rows-(i+1)) + \
                  box_border_width*(3*(num_rows-(i+1))+1) + border_offset
                start_x = self.minimaps_x[col] + offset_x
                start_y = self.minimaps_y[row] + offset_y
                # here account for both border offsets
                space = w - 2*border_offset - 2*box_border_width * num_circles[i]
                # translate to first box, bottom left corner; move over border_offset to account for width of the line
                glTranslatef(offset_x, offset_y, 0)

            # **** TODO:  Test this behavior with a dataset that gives rows like [5, 7, 6] or so ****
            # Use first row circle gap unless the number of circles is greater than the first row
            if i == 0 or (changed_circle_gap and num_circles[i] <= num_circles[0]):
                 # circle_gap is space between circle edge and lines on either side
                circle_gap = (space-total_variance_width)/float((2*num_circles[0]))
                changed_circle_gap = False
            elif i > 0 and num_circles[i] > num_circles[0]:
                circle_gap = (space-total_variance_width)/float((2*num_circles[i])) 
                changed_circle_gap = True

            box_width = 2*(circle_gap + self.maxVarianceRadius)
            effective_box_width = box_width + 2*box_border_width
            row_trans_x = 0.

            for j in range(num_circles[i]):
                # store the position for mouse clicks
                #bottom_left_x = int(start_x + j*(effective_box_width + box_border_width))
                bottom_left_x = int(start_x + j*(effective_box_width + box_border_width))
                bottom_left_y = int(start_y)
                top_right_x = int(bottom_left_x + effective_box_width)
                top_right_y = int(start_y + w*self.labelHeight - box_border_width)
                #self.minimaps_box_pos[row][col][d_val][e_val] = [(bottom_left_x, bottom_left_y), (top_right_x, top_right_y)]
                self.updateMiniMapBoxPos(offset_x, offset_y, offset_x, offset_y, row, col, [d_val], [e_val])
                self.minimaps_var_rowcol[row][col][d_val][e_val] = [i, j]
                self.minimaps_var_vals[row][col][i][j] = [d_val, e_val]

                glLineWidth(1.)
                #glLineWidth(w/250.)
                border_color = self.getBorderColor(axis, axis_index, d_val, e_val)
                glPushMatrix()
                # draw the label at the top with a line underneath
                glColor4f(*line_color)
                glTranslatef(0., w*self.labelHeight*0.82 - box_border_width, -0.2)
                eff_height = w*self.labelHeight*0.77 - box_border_width # where the line is drawn
                with glSection(GL_LINES):
                    glVertex3f(box_border_width, -w*self.labelHeight*0.05, 0.)
                    glVertex3f(box_width - box_border_width, -w*self.labelHeight*0.05, 0.)
                glTranslatef(circle_gap + box_border_width, 0, 0)
                # now for the label
                glColor4f(*border_color)
                with glMatrix():
                    glScalef(w*0.00025, w*0.00025, 1) # should be based on box_width, but leave as is
                    if d_val > 9:
                        glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(str(1)))
                        glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(str(d_val - 10)))
                    else:
                        glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(str(d_val)))
                glTranslatef(circle_gap, 0, 0)
                with glMatrix():
                    glTranslatef(0, w*0.00001, 0)
                    glScalef(w*0.000225, w*0.000225, 1)
                    glutStrokeCharacter(GLUT_STROKE_ROMAN, ord('/'))
                glTranslatef(circle_gap, 0, 0)
                with glMatrix():
                    glScalef(w*0.00025, w*0.00025, 1)
                    glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(str(e_val)))
                glPopMatrix()

                glLineWidth(box_border_width)
                #glLineWidth(w/200.)
                border_color = self.getBorderColor(axis, axis_index, d_val, e_val)
                glColor4f(*border_color)
                # draw the inner line, top line, & bottom line around this box
                #   already took into account border_offset in translation of the row
                self.updateMiniMapBoxPos(0, 0, box_width + 2*box_border_width, 
                    w*self.labelHeight + 2*box_border_width, row, col, [d_val], [e_val])
                with glSection(GL_LINES):
                    #left line
                    glVertex3f(box_border_width, w*self.labelHeight, -0.1)
                    glVertex3f(box_border_width, 0, 0.1)
                    #top line
                    glVertex3f(0, w*self.labelHeight - box_border_width, -0.1)
                    glVertex3f(box_width, w*self.labelHeight - box_border_width, -0.1)
                    #bottom line
                    glVertex3f(0, box_border_width, -0.1)
                    glVertex3f(box_width, box_border_width, -0.1)
                    #right line
                    glVertex3f(box_width-box_border_width, w*self.labelHeight, -0.1)
                    glVertex3f(box_width-box_border_width, 0, -0.1)
                    
                
                #print 'axis = ' + str(axis) + ', axis_index = ' + str(axis_index) + ', d_val = ' + str(d_val) + ', e_val = ' + str(e_val)
                
                if self.showTotalVariance:
                    plane = self.planeTotalVariance[axis*3 + axis_index]
                    max_variance = self.max_plane_variance
                    #print '********* Showing TOTAL Variance **********'
                else:
                    plane = self.planeAvgVariance[axis*3 + axis_index] 
                    max_variance = self.max_variance
                    #print '********* Showing AVG Variance **********'

                
                #print 'plane.shape = ' + str(plane.shape) + ', plane = ' + str(plane) 
                # draw circle 6/10 way down this box (already at -0.5, subtract 0.1to get to -0.6)
                
                #center = (circle_gap + self.maxVarianceRadius, circle_gap + self.maxVarianceRadius, 0)
                #self.drawCircle(plane[d_val][e_val], 0, max_variance, 0, self.maxVarianceRadius, center, border = True)
                
                #print '\n\taxis =',axis,', axis_index =',axis_index,', d_val =',d_val,', e_val =',e_val
                #print '\tglobal_spread = (',self.globalMinLinkValue,',',self.globalMaxLinkValue,')'
                #print '\tplane_spread = (',self.planeLinkSpread[axis*3+axis_index][d_val][e_val][0],',',self.planeLinkSpread[axis*3+axis_index][d_val][e_val][1],')'
                #print '\tplane_variance =',math.sqrt(self.planeTotalVariance[axis*3+axis_index][d_val][e_val])
                #print '\tplane_mean =',self.planeMeanLinkValue[axis*3+axis_index][d_val][e_val]     

                # draw a rectangle for the box-whisker plot, this will represent
                #   the global spread of link data
                #box_whisker_color = (line_color[0], line_color[1], line_color[2], 1.)
                with glMatrix():
                    #glColor4f(*box_whisker_color)
                    box_space = eff_height*0.1 + box_border_width
                    #with glSection(GL_LINE_LOOP):
                    #    glVertex3f(box_space, box_space, -0.2)
                    #    glVertex3f(box_width-box_space, box_space, -0.2)
                    #    glVertex3f(box_width-box_space, eff_height-box_space, -0.2)
                    #    glVertex3f(box_space, eff_height-box_space, -0.2)
                    glTranslatef(box_space, box_space, -0.2)
                    self.drawBoxPlot(box_width-2*box_space, eff_height-2*box_space, axis, axis_index, d_val, e_val, line_color, color_offset)
                
                
                #glLineWidth(0.8)
                #with glSection(GL_LINES):
                #    glVertex3f(box_border_width, box_width-box_border_width, -0.15)
                #    glVertex3f(box_width-box_border_width, box_width-box_border_width, -0.15)
                
                # draw vertical line separating circles, move view over to the starting point of next square
                glColor4f(*line_color)
                glLineWidth(box_border_width)

                # first update the remaining d values for this e_val
                self.updateMiniMapBoxPos(row_trans_x, 0, 
                    row_trans_x, 0, row, col,
                    [d_val], [e_val])

                row_trans_x += box_width + 2*box_border_width
                glTranslatef(box_width + 2*box_border_width, 0, 0) # translate to the next box
                with glSection(GL_LINES): 
                    glVertex3f(-box_border_width, w*self.labelHeight, 0) #-box_border_width b/c drawing to left of new pos
                    glVertex3f(-box_border_width, 0, 0)

                d_val += 1
                if d_val >= self.shape[depth]:
                    d_val = 0
                    e_val += 1
            glPopMatrix()
            #glTranslatef(0, -h*self.labelHeight, 0) # move down to the next row
        #if axis == 1 and axis_index == 2:
        #    print 'end: minimaps_box_pos =',self.minimaps_box_pos[row][col]

    def drawPlaneVarianceLegend(self, axis, axis_index, w, h, line_color, 
        border_offset, box_border_width):
        '''Draw the bottom rows on the minimaps, for showing the 4th and 5th
        dimension plane variances as circles.'''
        num_circles = self.numVarianceCircles[axis][axis_index]
        num_rows = len(num_circles)
        horiz, vert, depth = self.axis_map[axis][axis_index]
        coords = self.parent.agent.coords # coord names from user

        # first draw horiz lines to hold plane variance rows
        glLineWidth(box_border_width)
        glColor4f(*line_color)
        with glMatrix():
            with glSection(GL_LINES):
                for i in range(num_rows):
                    # offset vertically by the border_offset since these rows are directly
                    #   above the bottom border.  Also take into account the border of the 
                    #   box inset, two borders per row b/c its a rectangle 
                    glVertex3f(border_offset, w*self.labelHeight*(i+1) + 
                        box_border_width*2*(i+1) + border_offset, 0.01)
                    glVertex3f(w-border_offset, w*self.labelHeight*(i+1) + 
                        box_border_width*2*(i+1) + border_offset, 0.01)

        # second draw 4th/5th dim label and a vertical line just to the right
        # use border offset to push characters to right slightly, and account
        #   for box_border_width, 2 per rectangle per row
        with glMatrix():
            with glSection(GL_LINES): 
                glVertex3f(border_offset + w*self.labelWidth, w*num_rows*self.labelHeight + num_rows*2*box_border_width + border_offset, 0) #grid for label
                glVertex3f(border_offset + w*self.labelWidth, w*(num_rows-1)*self.labelHeight + (num_rows-1)*2*box_border_width + border_offset, 0)
            color = self.getAxisLabelColor(coords[depth])
            #print 'd/e color =',color
            glColor4f(*color)
            with glMatrix():
                glTranslatef(border_offset + w*0.025, w*(num_rows-0.67)*self.labelHeight + (num_rows-1)*2*box_border_width + border_offset, 0)
                glScalef(w*0.0008, w*0.0008, 1)
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(coords[depth]))
            with glMatrix():
                glTranslatef(border_offset + w*0.085, w*(num_rows-0.665)*self.labelHeight + (num_rows-1)*2*box_border_width + border_offset, 0)
                glScalef(w*0.0007, w*0.0007, 1)
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord('/'))
            with glMatrix():
                glTranslatef(border_offset + w*0.135, w*(num_rows-0.67)*self.labelHeight + (num_rows-1)*2*box_border_width + border_offset, 0)
                glScalef(w*0.0008, w*0.0008, 1)
                glutStrokeCharacter(GLUT_STROKE_ROMAN, ord('e'))    

    def drawRectBorder(self, w, h, line_color, border_width, border_offset, 
        z_dist):
        '''Draw a colored rectangular border with dimensions w, h.'''
        glLineWidth(border_width)
        glColor4f(*line_color)
        #print 'RECT_BORDER: line_color =',line_color
        #extend = border_offset/2.
        with glMatrix():
            with glSection(GL_LINES):
                glVertex3f(0, border_offset, z_dist)
                glVertex3f(w, border_offset, z_dist)
                glVertex3f(w-border_offset, 0, z_dist)
                glVertex3f(w-border_offset, h, z_dist)
                glVertex3f(w, h-border_offset, z_dist)
                glVertex3f(0, h-border_offset, z_dist)
                glVertex3f(border_offset, h, z_dist)
                glVertex3f(border_offset, 0, z_dist)

    # ------------------------    Render, Level 5    ---------------------------

    def drawBoxPlot(self, w, h, axis, axis_index, d_val, e_val, spread_color, 
        color_offset):
        # already drew the outer border, so draw the rect for the plane spread
        #   based on the global min and max values (drawn at y = 0, y = h)

        # how much to change grey value going from global spread to plane spread
        if self.bright_bg_color:
            border_color = (0., 0., 0., spread_color[3])
            plane_spread_color = (spread_color[0]/2., spread_color[1]/2., spread_color[2]/2.,
                spread_color[3])
        else:
            border_color = (0.8, 0.8, 0.8, 0.6)
            #plane_spread_color = ((spread_color[0]+1)/2., (spread_color[1]+1)/2., (spread_color[2]+1)/2.,
            #    spread_color[3])
            #plane_spread_color = spread_color
        plane_spread_color = (spread_color[0]/2., spread_color[1]/2., spread_color[2]/2.,
                spread_color[3])
        variance_color = (border_color[0], border_color[1], border_color[2],
            border_color[3]-0.2)

        #plane_spread_color = (spread_color[0]+color_change, spread_color[1]+color_change,
        #        spread_color[2]+color_change, 0.9)
        #variance_color = (spread_color[0]+2*color_change, spread_color[1]+2*color_change,
        #        spread_color[2]+2*color_change, 0.9)

        # TODO:  Use the color offset to draw rectangles based on these heights
        #   also draw the mean value

        min_spread = self.planeLinkSpread[axis*3+axis_index][d_val][e_val][0]
        max_spread = self.planeLinkSpread[axis*3+axis_index][d_val][e_val][1]
        std_dev = math.sqrt(self.planeTotalVariance[axis*3+axis_index][d_val][e_val])
        mean = self.planeMeanLinkValue[axis*3+axis_index][d_val][e_val]
        global_spread = (self.globalMaxLinkValue - self.globalMinLinkValue)

        border = 1.
        with glMatrix():
            glLineWidth(border)
            glColor4f(*border_color)
            # draw border as a quad to fix problems with the lines scaling right
            with glSection(GL_QUADS):
                glVertex3f(0., 0., 0.) # border is in back
                glVertex3f(w, 0., 0.)
                glVertex3f(w, h, 0.)
                glVertex3f(0., h, 0.)

            w -= 2*border
            h -= 2*border
            min_spread_h = h * ((min_spread - self.globalMinLinkValue) / global_spread)
            max_spread_h = h * ((max_spread - self.globalMinLinkValue) / global_spread)
            std_dev_above_h = h * (min(1, (std_dev + mean - self.globalMinLinkValue) /
                global_spread))
            std_dev_below_h = h * (max(0, (mean - std_dev - self.globalMinLinkValue) /
                global_spread))
            mean_h = h * ((mean - self.globalMinLinkValue) / global_spread)
            #print '\t\th =',h,', spread_h = (',min_spread_h,',',max_spread_h,')'
            #print '\t\tstd_dev_h = (',std_dev_below_h,',',std_dev_above_h,')'
            #print '\t\tmean_h =',mean_h
            glTranslatef(border, border, 0.)

            # first fill in the border area to be the bg color
            glColor4f(*self.bg_color)
            with glSection(GL_QUADS):
                glVertex3f(0., 0., .01) # filled section in front of border
                glVertex3f(w, 0., .01)
                glVertex3f(w, h, .01)
                glVertex3f(0., h, .01)

            glColor4f(*plane_spread_color)
            with glSection(GL_QUADS):
                glVertex3f(0, min_spread_h, 0.05) # plane spread is next
                glVertex3f(w, min_spread_h, 0.05)
                glVertex3f(w, max_spread_h, 0.05)
                glVertex3f(0., max_spread_h, 0.05)

            glColor4f(*variance_color)
            with glSection(GL_QUADS):
                glVertex3f(0., std_dev_below_h, 0.1) # variance is next
                glVertex3f(w, std_dev_below_h, 0.1)
                glVertex3f(w, std_dev_above_h, 0.1)
                glVertex3f(0., std_dev_above_h, 0.1)

            glColor4f(1., .2, .2, 0.9)
            with glSection(GL_LINES): # line is last
                glVertex3f(0., mean_h, .15)
                glVertex3f(w+0.5, mean_h, .15)
    
    def drawLinks(self, shape, axis, link_colors, link_variance, scale = 1):
        glMaterialfv(GL_FRONT_AND_BACK,GL_DIFFUSE,[1.0, 1.0, 1.0, 1.0])
        glPushMatrix()

        #glEnable(GL_BLEND)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        #print 'New Minimap:'
        self.centerView(shape, axis, scale)
        w, h, d = self.getSliceDims()

        # take care of d and e dimensions by adjusting shape
        shape = tuple(shape)

        for start_node in np.ndindex(*shape):
            colors = link_colors[start_node]
            variance = link_variance[start_node]

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
                    #print '\t\tColors = ' + str(colors[dim])
                    #if self.axis == 0 and self.axis_index == 0:
                    #    print 'Nodes: ' + str(start_node) + ' to ' + str(end_node) + '; Drawing: ' + str(start) + ' to ' + str(end)
                    #self.drawLinkVariance(start, end, variance[dim], self.gap*scale)
                    if self.showVariance: 
                        #print 'DRAWING LINK VARIANCE FOR dim = ' + str(dim)
                        center = start + ((end-start)/2)
                        minRadius = self.cylinder_width/2
                        self.drawCircle(variance[dim], self.min_variance, 
                            self.max_variance, minRadius, self.maxVarianceRadius, center)
                    #print 'link colors = ' + str(colors[dim])
                    glColor4f(*colors[dim])
                    self.drawLinkLine(start, end) 
                    #self.drawLinkCylinder(start, end) # doesn't work with minimaps due to projection

        glPopMatrix()       
        #glDisable(GL_BLEND)           

    def drawCircle(self, value, min_val, max_val, min_radius, max_radius, 
        center = (0, 0, 0), numPts = 50, fill = True, border = False):

        #print '\tbg_color = ' + str(self.bg_color)
        #glEnable(GL_BLEND)
        #glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        #print 'value =',value,', min_val=',min_val,', max_val=',max_val,', min_radius=',min_radius,', max_radius=',max_radius,', fill=',fill,', border=',border

        if value < min_val:
            normalized_val = 0
        else:
            normalized_val = (value - min_val) / (max_val - min_val)

        radius = min_radius + (max_radius - min_radius) * normalized_val
        if self.bright_bg_color == True: 
            max_color = 0
            min_color = 1
            variance_color = 1 - (min_color * normalized_val) # this way b/c max == 0
        else:
            max_color = 1
            variance_color = max_color * normalized_val
        max_angle = 2*np.pi
        thetaVals = np.linspace(0, max_angle, numPts)

        if border:
            glColor4f(0.5, 0.5, 0.5, 0.8)
            glLineWidth(1.)
            glBegin(GL_LINE_STRIP)
            for theta in thetaVals:
                glVertex3f(center[0] + max_radius * np.cos(theta), center[1] + max_radius * np.sin(theta), center[2]-0.5)
            glEnd()

        glColor4f(max_color, max_color, max_color, 0.8)
        if fill:
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(center[0], center[1], -0.5)
        else:
            glLineWidth(1.)
            glBegin(GL_LINE_STRIP)
        
        for theta in thetaVals:
            glVertex3f(center[0] + radius * np.cos(theta), center[1] + radius * np.sin(theta), center[2]-0.5)
        glEnd()
        #glDisable(GL_BLEND)

    # ------------------------    Render, Level 6    ---------------------------

    def centerView(self, slice_shape, axis = 2, scale = 1):
        half_spans = np.array(self.getSliceSpan(slice_shape), np.float) / -2.
        half_spans[axis] = 0
        half_spans *= self.axis_directions
        half_spans *= scale
        glTranslatef(*half_spans)
    
    def drawLinkLine(self, start, end):
        """Surprise! Actually draws a line."""
        glLineWidth(self.cylinder_width)
        glBegin(GL_LINES)
        glVertex3fv(start)
        glVertex3fv(end)
        glEnd()

    def drawLinkCylinder(self, start, end):
        # calculate a vector in direction start -> end
        v = end - start

        # interpolate cylinder points
        cyl_points = [tuple(p) for p in [start - v, start, end, end + v]]

        # Draw link
        #print 'Drawing cylinder of width = ' + str(self.cylinder_width)
        notGlePolyCylinder(cyl_points, None, self.cylinder_width )    


    # **************************        I/O       ******************************

    def changeBorderInset(self, inc = True):
        if inc:
            self.borderInset *= 1.1
            #print 'borderInset = ' + str(self.borderInset)
        else:
            self.borderInset *= 0.9
            #print 'borderInset = ' + str(self.borderInset)
        self.updateDrawing()

    def changeLinkWidth(self, inc = True):
        if inc:
            self.cylinder_width_offset += 1
        else:
            self.cylinder_width_offset -= 1
        self.updateDrawing()

    def changeMinimapLayout(self, numWide):
        '''Allow the user to change how many minimaps there are across.'''
        #TODO: Allow user to change which minimaps are shown and which are not
        #   then need to calculate num_minimaps_total based on the dictionary
        self.vertical_offset = 0
        self.num_minimaps_x = numWide
        self.num_minimaps_y = int(math.ceil(self.num_minimaps_total / float(numWide)))
        self.updateMiniMapLayout()
        self.updateDrawing()         

    def changeMouseDrag(self):
        ''' Change the way click and drag works to be the opposite.'''
        if self.reverseDrag: self.reverseDrag = False
        else: self.reverseDrag = True        

    def changeNodeLinkBounds(self, lower, upper, links = True):
        if links:
            self.lowerBoundLinks = lower
            self.upperBoundLinks = upper
        else: 
            self.lowerBoundNodes = lower
            self.upperBoundNodes = upper

    def changePlaneVarianceType(self):
        if self.showTotalVariance:
            self.showTotalVariance = False
        else:
            self.showTotalVariance = True
        self.updateDrawing()

    def changeShowVariance(self):
        if self.showVariance:
            self.showVariance = False
        else:
            self.showVariance = True
        self.updateDrawing()

    def changeViewPlane(self, dim_d, dim_e, d_val = None, e_val = None, 
        axis = None, axis_index = None, leftClick = False, leftDrag = False, 
        rightClick = False, rightDrag = False):

        if d_val == None:
            d_val = self.clicked_dval
        if e_val == None:
            e_val = self.clicked_eval

        if leftClick: # set this to the current plane, add if necessary
            self.current_planes[dim_d] = d_val
            self.current_planes[dim_e] = e_val
            if (d_val, e_val) not in self.view_planes[dim_d]:
                self.view_planes[dim_d].add((d_val, e_val))

        elif rightClick: # toggle this plane on/off
            if (d_val, e_val) not in self.view_planes[dim_d]:
                self.view_planes[dim_d].add((d_val, e_val))
            else:
                if len(self.view_planes[dim_d]) > 1:              
                    self.view_planes[dim_d].remove((d_val, e_val))
                    if self.current_planes[dim_d] == d_val and self.current_planes[dim_e] == e_val:
                        sorted_planes = sorted(self.view_planes[dim_d],
                            key = lambda val: val[1]*self.shape[dim_d] + val[0])
                        self.current_planes[dim_d] = sorted_planes[0][0]
                        self.current_planes[dim_e] = sorted_planes[0][1]

        elif leftDrag or rightDrag: 
            # TODO:  Test this with larger dataset needing 3 rows
            row, col = self.axisToRowCol[axis][axis_index]
            var_row, var_col = self.minimaps_var_rowcol[row][col][d_val][e_val]
            clk_var_row, clk_var_col = self.minimaps_var_rowcol[row][col][self.clicked_dval][self.clicked_eval]
            if clk_var_row > var_row:
                row_range = np.arange(var_row, clk_var_row)
            else:
                row_range = np.arange(clk_var_row+1, var_row+1)
            if clk_var_col > var_col:
                col_range = np.arange(var_col, clk_var_col+1)
            else:
                col_range = np.arange(clk_var_col, var_col+1)

            if len(row_range) > 1: #add all the columns from the middle rows
                for i in row_range[1:len(row_range)-1]: #the middle rows should add all columns
                    for j in range(self.numVarianceCircles[axis][axis_index][i]):
                        d_value, e_value = self.minimaps_var_vals[row][col][i][j]
                        if leftDrag:
                            self.view_planes[dim_d].add((d_value, e_value))
                        else: # rightDrag
                            self.removePlaneSafely(d_value, e_value, dim_d, dim_e)

            if len(row_range) > 0: # add the remainder of boxes left in the first row
                for j in np.arange(clk_var_col, self.numVarianceCircles[axis][axis_index][clk_var_row]):
                    d_value, e_value = self.minimaps_var_vals[row][col][clk_var_row][j]
                    if leftDrag:
                        self.view_planes[dim_d].add((d_value, e_value))
                    else: # rightDrag
                        self.removePlaneSafely(d_value, e_value, dim_d, dim_e)
                #the last row should add all values up to the current mouse dval, eval
                for j in range(var_col+1):
                    if self.numVarianceCircles[axis][axis_index][var_row] > j:
                        d_value, e_value = self.minimaps_var_vals[row][col][var_row][j]
                        if leftDrag:
                            self.view_planes[dim_d].add((d_value, e_value))
                        else: # rightDrag
                            self.removePlaneSafely(d_value, e_value, dim_d, dim_e)

            elif len(row_range) == 0:
                for j in col_range:
                    d_value, e_value = self.minimaps_var_vals[row][col][var_row][j]
                    if leftDrag:
                        self.view_planes[dim_d].add((d_value, e_value))
                    else: # rightDrag
                        self.removePlaneSafely(d_value, e_value, dim_d, dim_e)

            self.last_dval = d_val
            self.last_eval = e_val
        else:
            return

        #if any of the clicks above, update the view planes for the datamodel
        self.viewPlanesUpdateSignal.emit(self.view_planes)
        self.updateDrawing()

    def removePlaneSafely(self, d_val, e_val, dim_d, dim_e):
        # remove if it's currently in view_planes and there is at least one other
        if (d_val, e_val) in self.view_planes[dim_d] and len(self.view_planes[dim_d]) > 1:
            self.view_planes[dim_d].remove((d_val, e_val))
            # after removing, check if it's the current plane, and if so find
            #   the next sorted plane to be the new current plane
            if self.current_planes[dim_d] == d_val and self.current_planes[dim_e] == e_val:
                sorted_planes = sorted(self.view_planes[dim_d],
                    key = lambda val: val[1]*self.shape[dim_d] + val[0])
                self.current_planes[dim_d] = sorted_planes[0][0]
                self.current_planes[dim_e] = sorted_planes[0][1]

    def keyPressEvent(self, event):
        # Add 'e', axis after deciding what to do with them.
        key_map = { "a" : lambda :  self.keyAxisChange(0),
                    "b" : lambda :  self.keyAxisChange(1),
                    "c" : lambda :  self.keyAxisChange(2),
                    "d" : lambda :  self.keyAxisChange(3),
                    "[" : lambda :  self.changeViewPlane(-1),
                    "]" : lambda :  self.changeViewPlane(1),
                    "}" : lambda :  self.addViewPlane(1),
                    "{" : lambda :  self.addViewPlane(-1),
                    "/" : lambda :  self.toggleDepthLinks(),
                    "=" : lambda :  self.increasePlaneSpacing(),
                    "-" : lambda :  self.decreasePlaneSpacing(),
                    "p" : lambda :  self.resetRotation(),
                    "+" : lambda :  self.changeLinkWidth(inc = True),
                    "_" : lambda :  self.changeLinkWidth(inc = False),
                    "<" : lambda :  self.lowerLowerBound(),
                    ">" : lambda :  self.raiseLowerBound(),
                    "," : lambda :  self.lowerUpperBound(),
                    "." : lambda :  self.raiseUpperBound(),
                    #"1" : lambda :  self.changeMinimapLayout(1),
                    #"2" : lambda :  self.changeMinimapLayout(2),
                    #"3" : lambda :  self.changeMinimapLayout(3),
                    #"4" : lambda :  self.changeMinimapLayout(4),
                    #"5" : lambda :  self.changeMinimapLayout(5),
                    "r" : lambda :  self.changeMouseDrag(),
                    "R" : lambda :  self.changeMouseDrag(),
                    "v" : lambda :  self.changeShowVariance(),
                    ";" : lambda :  self.changeBorderInset(inc = False),
                    "'" : lambda :  self.changeBorderInset(inc = True),
                    "V" : lambda :  self.changePlaneVarianceType()
                    }

        #print 'received key == ' + str(event.key())

        if event.text() in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
            self.changeMinimapLayout(int(event.text()))

        if event.text() in key_map:
            key_map[event.text()]()
        else:
            super(Torus5dViewMinimaps, self).keyPressEvent(event)

    def mouseMoveEvent(self, event):
        '''Keep track of drags for offsetting the minimaps to create a scrollable
        window.
        '''
        if self.left_press or self.left_drag or self.right_press or self.right_drag:
            if self.left_press:
                self.left_drag = True
                self.left_press = False
            elif self.right_press:
                self.right_drag = True
                self.right_press = False

            axis, axis_index, d_val, e_val = self.getClickMiniMap(event.x(), self.height() - event.y())
            # since we're handling the case for left drag when in space to right of last variance plane
            #    change d_val, e_val to the last if they're currently -2, -2
            if axis >= 0:
                w, h, d = self.axis_map[axis][axis_index]
                #when mouse is to the right of the last box in the last row, (dval, eval) == (-2, -2)
                #   and for leftDrag's treat this like the last dval & eval's
                if d_val == -2:
                    d_val = self.shape[d]-1
                    e_val = self.shape[4]-1
                # here, check for d_val != -1, which means no variance plane found, so d_val == -2
                #   is allowed, which means the area to the right of the last variance plane
                if axis == self.clicked_axis and axis_index == self.clicked_axis_index and \
                    d_val >= 0 and (d_val != self.last_dval or e_val != self.last_eval):
                    # add the new the minimaps between first click and this drag position
                    if self.left_drag:
                        self.changeViewPlane(d, 4, d_val, e_val, axis, axis_index, leftDrag = True)
                    elif self.right_drag:
                        self.changeViewPlane(d, 4, d_val, e_val, axis, axis_index, rightDrag = True)
  
    def mousePressEvent(self, event):
        """We keep track of right-click drags for picking."""
        super(Torus5dViewMinimaps, self).mousePressEvent(event)
        
        # Return if haven't dragged module onto the data tree yet to prevent
        #   the error when mouse I/O fails to return, causing any keyboard
        #   modifier (shift, contrl..) to be mis-interpreted as mouseEvent
        if max(self.shape) == 0:
            return

        if event.button() == Qt.LeftButton: # handled when released
            self.left_press = True
            self.left_press_start_y = self.height() - event.y()
            self.left_press_start_x = event.x()
        elif event.button() == Qt.RightButton: # handled when released
            self.right_press = True
            self.right_press_start_y = self.height() - event.y()
            self.right_press_start_x = event.x()

        self.clicked_axis, self.clicked_axis_index, \
                self.clicked_dval, self.clicked_eval =  \
                self.getClickMiniMap(event.x(), self.height() - event.y())
        if self.clicked_dval != -1:
            self.last_dval = self.clicked_dval
        if self.clicked_eval != -1:
            self.last_eval = self.clicked_eval

    def mouseReleaseEvent(self, event):
        '''Keep track of drags for offsetting the minimaps to create a scrollable
        window.
        '''
        
        # Return if haven't dragged module onto the data tree yet to prevent
        #   the error when mouse I/O fails to return, causing any keyboard
        #   modifier (shift, contrl..) to be mis-interpreted as mouseEvent
        if max(self.shape) == 0:
            return

        axis, axis_index, d_val, e_val = self.getClickMiniMap(event.x(), 
            self.height() - event.y())
        
        if self.left_press and axis >= 0 and self.clicked_axis == axis and \
          self.clicked_axis_index == axis_index:
            # ignoring clicks that press in one minimap and release in another
            self.left_press = False
            if axis != self.axis or axis_index != self.axis_index:
                self.vertical_offset = 0
                self.axisUpdateSignal.emit(axis, axis_index)
            elif d_val >= 0:
                # check if d_val/eval is different than the current
                # left click changes the current plane to be the clicked plane
                w, h, d = self.axis_map[axis][axis_index]
                if self.current_planes[d] != d_val or \
                  self.current_planes[4] != e_val: 
                    # if not already the current plane, select it to be
                    self.changeViewPlane(d, 4, d_val, e_val, leftClick = True)

        elif self.right_press and axis >= 0 and self.clicked_axis == axis \
          and self.clicked_axis_index == axis_index:
            # ignoring clicks that press in one minimap and release in another
            self.right_press = False
            w, h, d = self.axis_map[axis][axis_index]
            # toggle this plane on/off
            self.changeViewPlane(d, 4, d_val, e_val, rightClick = True)

        self.left_drag = False
        self.right_drag = False

    def wheelEvent(self, event):
        #print 'Received wheel event.'
        if event.orientation() == Qt.Orientation.Vertical: # allow translation
                #print 'Orientation vertical.'
                if int(Qt.Key_Shift) in self.pressed_keys and self.max_vertical_offset > 0:
                    #print 'Shift pressed.'

                    if self.reverseDrag: factor = -1
                    else: factor = 1
                    
                    self.vertical_offset += int(.001 * event.delta() * factor * self.height())
                    self.vertical_offset = max(0, self.vertical_offset)
                    self.vertical_offset = min(self.max_vertical_offset, self.vertical_offset)
                    #print '\tVertical Offset = ' + str(self.vertical_offset)
                    
                    #self.translation[1] += int(.001 * event.delta() * factor * self.height())
                    #self.translation[1] = max(0, self.translation[1])
                    #self.translation[1] = min(self.max_vertical_offset, self.translation[1])

                    #print '\tDelta = ' + str(event.delta()) + ', change =',str(.001 * event.delta() * factor * self.height()),', translation[1] =',self.translation[1]                    

                    self.updateDrawing()




