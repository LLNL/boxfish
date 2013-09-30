import math
import numpy as np
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLE import *
from Torus5dModule import *

class Torus5dViewNodecentric(Torus5dGLWidget):
    ''' Draws a view showing all links and nodes extending outward from a
    center node.  Extends a maximum of three hops away from the center node.
    Needs to be modified so 10 links extend outward from the center node only,
    and all other nodes have 9 links extending outward (with the 10th being
    connected back to the center).  Each direction 0, 2pi*1/10, 2pi*2/10, etc,
    corresponds to dimensions a+, b+, c+, ..., e+, a-, b-, ...,e- 
    '''

    # ***************************    Initialize    *****************************
    
    def __init__(self, parent, dataModel):
        ''' Draw a 2d layout showing an egocentric view.'''
        super(Torus5dViewNodecentric, self).__init__(parent, dataModel, rotation = False)

        self.layoutList = DisplayList(self.drawLayout)
        self.labelList = DisplayList(self.drawLabels)
        self.resizeSignal.connect(self.updateDrawing)

        self.firstDraw = True
        self.systemMaxHops = 3
        self.widgetLists = []
        self.widget2dLists = []
        self.nodeObjectList=[]
        # TODO:  Uncomment this
        self.widgetLists.append(self.layoutList)
        self.widget2dLists.append(self.labelList)
        self.currentMaxHops = 0 # not needed here
        self.prevHopChange = 0
        self.prevOpacityChange = 0
        self.maxHopOpacity = 1
        self.opacitySteps = [1, 0.05, 0.1, 1]
        self.startNode = [0 for i in range(len(self.shape))]
        self.circleNumPts = 100
        self.avgLinkRadiusFactor = 1.7
        self.borderOffsetZ = 0.1
        self.nodeOffsetZ = 0.1
        self.linkRadiusFactor = 1.5
        self.nodeRadiusFactor = 1.6
        self.spanBuffer = 1.05
        self.changeOpacityRange = 20
        self.holdOpacityRange = 2 * self.changeOpacityRange
        self.redrawRange = 4
        self.holdCurrentMaxHops = False
        Qt.ShiftModifier = False # to fix the weird vertical translation bug
        
        self.initMaxHops = 2
        self.updateLayoutSizes()
        self.updateLayoutValues()

    shape = property(fget = lambda self: self.dataModel.shape)

    def initializeGL(self):
        """Turn up the ambient light for this view and enable simple
           transparency.  To keep views looking the same."""
        super(Torus5dViewNodecentric, self).initializeGL()
        glLightfv(GL_LIGHT0, GL_AMBIENT,  [1.0, 1.0, 1.0, 1.0])

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        #glLineWidth(self.link_width)

    # ***************************      Update      *****************************

    def orient_scene(self):
        # overloaded, calls super at the end

        if self.firstDraw:
            return
        elif not self.holdCurrentMaxHops:
            startTransparent = self.hopOpacityRange[self.currentMaxHops][0]
            startOpaque = self.hopOpacityRange[self.currentMaxHops][1]
            endOpaque = self.hopOpacityRange[self.currentMaxHops][2]
            zoomLevel = self.translation[2]

            if zoomLevel > endOpaque and self.currentMaxHops != self.systemMaxHops: # increase currentMaxHops
                self.maxHopOpacity = self.opacitySteps[self.currentMaxHops+1]
                self.currentMaxHops += 1
                self.updateDrawing()
            elif zoomLevel < startTransparent and self.currentMaxHops != 0: # decrease currentMaxHops
                self.maxHopOpacity = 1-self.opacitySteps[self.currentMaxHops-1]
                self.currentMaxHops -= 1
                self.updateDrawing()
            elif self.currentMaxHops != 0: # keep currentMaxHops the same, check the opacity
                if zoomLevel > startOpaque and self.maxHopOpacity != 1:
                    self.maxHopOpacity = 1
                    self.updateDrawing()
                elif zoomLevel > startTransparent and zoomLevel < startOpaque: # change opacity
                    zoomOpacity = (zoomLevel - startTransparent) / (startOpaque - startTransparent)
                    opacityDiff = zoomOpacity - self.maxHopOpacity
                    if opacityDiff > self.opacitySteps[self.currentMaxHops]: # make more opaque
                        self.maxHopOpacity += self.opacitySteps[self.currentMaxHops]
                        self.updateDrawing()
                    elif opacityDiff < -self.opacitySteps[self.currentMaxHops]: # make less opaque
                        self.maxHopOpacity -= self.opacitySteps[self.currentMaxHops]
                        self.updateDrawing()

        super(Torus5dViewNodecentric, self).orient_scene(

    def resetView(self):
        spans = self.getViewSpan()
        print 'spans = ' + str(spans)
        aspect = self.width() / float(self.height())

        # Check both distances instead of the one with the larger span
        # as we don't know how aspect ratio will come into play versus shape

        # Needed vertical distance
        fovy = float(self.fov) * math.pi / 360.
        disty = spans[1] / 2. / math.tan(fovy) #spans[1] = spans[height]

        # Needed horizontal distance
        fovx = fovy * aspect
        distx = spans[0] / 2. / math.tan(fovx) #spans[0] = spans[width]

        self.translation = [0, 0, -max(distx, disty)] # maybe adjust the 1.5

        start_zoom = self.translation[2]
        hops = range(self.systemMaxHops+1)
        self.hopOpacityRange = {i: [] for i in hops}

        # current max hop should be in the middle of holdOpacityRange
        # first_range[0] is zoom dist to start this hop, fully transparent
        # first_range[1] is zoom dist for this hop to be fully opaque
        # first_range[2] is zoom distance to start the next hop
        first_range = [start_zoom - self.holdOpacityRange/2. - self.changeOpacityRange, \
            start_zoom - self.holdOpacityRange/2., start_zoom + self.holdOpacityRange/2.]
        self.hopOpacityRange[self.currentMaxHops] = first_range

        hop_range = self.holdOpacityRange + self.changeOpacityRange
        print 'first_range = ' + str(first_range) + ', hop_range = ' + str(hop_range)
        prev_range = first_range
        for i in reversed(hops[:self.currentMaxHops]):
            current_range = [prev_range[0]-hop_range, prev_range[1]-hop_range, \
                prev_range[2]-hop_range]
            self.hopOpacityRange[i] = current_range
            prev_range = current_range
        prev_range = first_range
        for i in hops[self.currentMaxHops+1:]:
            current_range = [prev_range[0]+hop_range, prev_range[1]+hop_range, \
                prev_range[2]+hop_range]
            self.hopOpacityRange[i] = current_range
            prev_range = current_range

        print 'hopOpacityRange = ' + str(self.hopOpacityRange)






        self.prevOpacityChange = self.translation[2]
        self.prevHopChange = self.translation[2] + self.holdOpacityRange/2.

        # TODO: make array of zoom distances to initiate changes, indexed by currentMaxHop

    def update(self, colors = True, values = True, reset = True):
        '''Update colors, values, and drawing for this view.'''
        if colors: super(Torus5dViewNodecentric, self).update()
        if values: self.updateLayoutValues()
        if reset: self.resetView() # only do this for perspective projection
        self.updateDrawing()

    def updateDrawing(self, sizes = False):
        # call updateLayoutSizes if want radii recalculated each drawing, not just once
        if sizes: self.updateLayoutSizes() 
        self.layoutList.update()
        self.updateGL()

    def updateLayoutSizes(self):
        '''Calculate angles and radii for drawing nodes and links in layout.'''
        # store angles; index 0-4 is positive a-e, 5-9 for negative a-e
        if np.amax(self.shape) == 0: # dont call until after shape is loaded
            return

        angle = 2*np.pi/(len(self.shape)*2)
        self.linkAngles = [i*angle for i in range(len(self.shape*2))]

        max_hop_range = np.arange(self.systemMaxHops+1) # include maxHops value
        # to allow opacityRange to be changed and view still centered (since resetView
        #   is dependent on nodeRadii and linkRadii), use this factor below
        self.startNodeRadius = 1.0 * (self.changeOpacityRange/10) * self.nodeRadiusFactor     # use this for perspective projection
        self.nodeRadii = [0 for a in max_hop_range]
        current_radius = self.startNodeRadius
        for i in max_hop_range: 
            self.nodeRadii[i] = current_radius
            # 2+i makes center node slightly larger than its neighbors than 2 alone
            current_radius /= (2+i) # TODO: Maybe make this adjustable
        
        # figure out the link radius for each link away
        self.startLinkRadius = 13.0 * (self.changeOpacityRange/10) * self.linkRadiusFactor  # use this for perspective projection
        self.linkRadii = [0 for a in max_hop_range]
        current_radius = self.startLinkRadius
        for i in max_hop_range:
            self.linkRadii[i] = current_radius
            current_radius /= 4 # TODO: Maybe make this adjustable

        grey_value = (self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) /  3
        if grey_value >= 0.5:
            self.bright_bg_color = True

        #print 'self.nodeRadii = ' + str(self.nodeRadii)
        #print 'self.linkRadii = ' + str(self.linkRadii)
        
    def updateLayoutValues(self):
        '''Stores node and link information in tree-like list structure.  Each
        node has an index, a path (integer list), XY position, node color, and
        link colors (for 10 links leaving that node).

        Positions are initialized to (-1, -1) and updated in drawLayout. Resize
        events will call updateLayoutSizes and then updateDrawing, which calls
        drawLayout.  Values are only recalculated when a new center node is chosen,
        or when the dataModel has changed.  If torus dimensions are small and 
        memory is not a large concern, can modify this to store all nodes and links
        in one data structure and then not have to call this method again when
        a new center node is chosen (instead, only when dataModel changes).  

        Path indicies are 0-4 are positive a-e, starting at 0 degrees, increasing
        36 degrees each index.  5-9 are negative a-e, starting at 180 degrees,
        again 36 degrees each index. All paths start from widget window center.
        Radial distances are created in updateLayoutSizes based on window dimensions. 


        TODO:  Finish Description
        UPDATED: Removed node_color, can lookup during drawing phase.  Maybe
        should remove link_colors too.  Leave them for now.
        '''
        if max(self.shape) == 0: # with this is called before a dropEvent
            return
        
        # figure out number of hops, and the node radius for each hop away
        if self.firstDraw:
            torus_max_hops = 0 
            for i in range(len(self.shape)):
                torus_max_hops += self.shape[i]/2
            self.systemMaxHops = min(self.systemMaxHops, torus_max_hops)
            self.currentMaxHops = min(self.initMaxHops, torus_max_hops)
            self.firstDraw = False
            self.updateLayoutSizes()

        # first store the angles for the endpoints of the lines in a circle
        self.circleAngles = np.linspace(0, 2*np.pi, self.circleNumPts)

        # node number, path from start_node, opengl position, avg_link_color
        emptyNode = [tuple(), tuple(), tuple(), None]

        # nodeObjectList starts off with just the first center node
        #   explicitly calc the link colors for this node for cleaner code below
        total_link_val = 0
        for dim in range(len(self.startNode)):
            total_link_val += self.dataModel.pos_link_values[tuple(self.startNode)][dim][0]
            total_link_val += self.dataModel.neg_link_values[tuple(self.startNode)][dim][0]
        
        # ******** TODO:  Send in the preempt_range, see Torus5dModule.Torus5dGLWidget.updateLinkColors() ********
        avg_link_color = self.map_link_color(total_link_val/(2*len(self.startNode)), 1.0)
        nodeObjectList = [np.array([tuple(self.startNode), tuple(), (0, 0), tuple(avg_link_color)])]

        # pre-calculate avg's for systemMaxHops, not just currentMaxHops to allow
        #   zooming updates to call updateDrawing() instead of update()
        for hop in range(self.systemMaxHops):
            
            #print 'Hop = ' + str(hop)
            
            # append an an array for the nodes belonging to the next hop
            next_hop_shape = [2*len(self.startNode) for i in range(hop+1)]
            nodeObjectList.append(np.tile(emptyNode, next_hop_shape + [1]))

            # extra dim in current_shape to calc avg colors of leaf nodes
            current_shape = [2*len(self.startNode) for i in range(hop)]
            #print 'current_shape = ' + str(current_shape)
            for current_path in np.ndindex(tuple(current_shape)): 
                #print '\tcurrent_path = ' + str(current_path)
                nodeObject = nodeObjectList[hop][current_path]
                #for nodeObject in nodeObjectList[hop][current_path]:
                # calculate the link colors and new paths for 10 outward links
                node = nodeObject[0] # keep a tuple
                
                #print '\tCurrent_path = ' + str(current_path) + ', Node = ' + str(node) + ', Path = ' + str(nodeObject[1])
                
                path = list(nodeObject[1])
                total_link_val = 0
                #link_colors = np.array([[0, 0, 0, 1] for i in range(2*len(node))])
                for dim in range(len(node)):                     
                    # get new nodes for this dim, positive and negative
                    pos_dim_node = self.getNextNode(node, dim, 1)
                    neg_dim_node = self.getNextNode(node, dim, -1)

                    # calculate path for these two nodes, appending to current path
                    # path value 0-4 is positive a-e, 5-9 is negative a-e
                    pos_path = path + [dim] 
                    neg_path = path + [dim + len(node)] 

                    # calculate the avg link color for the new pos and neg dim nodes
                    total_link_val_pos = 0
                    total_link_val_neg = 0
                    for dim2 in range(len(node)):
                        total_link_val_pos += self.dataModel.pos_link_values[tuple(pos_dim_node)][dim2][0]
                        total_link_val_pos += self.dataModel.neg_link_values[tuple(pos_dim_node)][dim2][0]
                        total_link_val_neg += self.dataModel.pos_link_values[tuple(neg_dim_node)][dim2][0]
                        total_link_val_neg += self.dataModel.neg_link_values[tuple(neg_dim_node)][dim2][0]
                    # ******** TODO:  Send in the preempt_range, see Torus5dModule.Torus5dGLWidget.updateLinkColors() ********
                    avg_link_color_pos = self.map_link_color(total_link_val_pos/(2*len(node)), 1.0)
                    #print 'pos_node = ' + str(pos_dim_node) + ', color_val[0] = ' + str(total_link_val_pos/10) + ', color = ' + str(avg_link_color_pos)
                    
                    # ******** TODO:  Send in the preempt_range, see Torus5dModule.Torus5dGLWidget.updateLinkColors() ********
                    avg_link_color_neg = self.map_link_color(total_link_val_neg/(2*len(node)), 1.0)
                    #print 'neg_node = ' + str(neg_dim_node) + ', color_val[0] = ' + str(total_link_val_neg/10) + ', color = ' + str(avg_link_color_neg)
                    
                    #print '\t\tAdding pos: dim = ' + str(dim) + ', node = ' + str(pos_dim_node) + ', path = ' + str(pos_path)
                    #print '\t\tAdding neg: dim = ' + str(dim) + ', node = ' + str(neg_dim_node) + ', path = ' + str(neg_path)
                    
                    # insert positions as (-1, -1) so it will be an error if used before setting correctly
                    nodeObjectList[hop+1][tuple(pos_path)] = ([tuple(pos_dim_node), tuple(pos_path), (-1, -1), tuple(avg_link_color_pos)])
                    nodeObjectList[hop+1][tuple(neg_path)] = ([tuple(neg_dim_node), tuple(neg_path), (-1, -1), tuple(avg_link_color_neg)])
        self.nodeObjectList = nodeObjectList
        

    # ***************************    Calculate     *****************************

    def getNextNode(self, node, dim, offset):
        ''' Returns new node by offsetting current node in this dimension.
        '''
        max_num_nodes = self.shape[dim]
        new_node = list(node[:])
        index = node[dim] + offset
        #print '\t\t\tnew_node = ' + str(new_node) + ', dim = ' + str(dim) + ', offset = ' + str(offset) + ', index = ' + str(index)
        if index >= max_num_nodes: 
            index -= max_num_nodes 
        elif index < 0:
            index += max_num_nodes 
        new_node[dim] = index
        #print 'returning node = ' + str(new_node)
        return new_node

    def getNextPath(self, path):
        #print '\t\tincr path = ' + str(path) + ', len(path) = ' + str(len(path))
        while len(path) > 0 and path[len(path)-1] == 2*len(self.shape)-1:
            # reached max index, chop off 1 from end
            path = path[:len(path)-1]
            #print '\t\tchopping off, path = ' + str(path)
        if len(path) > 0:
            path[len(path)-1] += 1
            #print '\t\tdone chopping, inc path = ' + str(path)
        #print '\t\t\treturning ' + str(path)
        return path

    def getViewSpan(self, hops = None):
        if hops == None:
            hops = self.currentMaxHops
            print 'VIEW SPAN: currentMaxHops = ' + str(self.currentMaxHops)
        dist = 0
        # add all linkRadii - this over estimates because only currentMaxHops
        #   number of links are shown, but this provides a little extra room
        for i in range(self.currentMaxHops):
            dist += 2*self.linkRadii[i] # not i+1 because we're doubling
        # for the last hop, add 2*avgLinkRadii, which is 2*nodeRadii*avgLinkRadFactor
        dist += self.nodeRadii[self.currentMaxHops] * self.avgLinkRadiusFactor * 2
        dist *= self.spanBuffer
        return (dist, dist, self.nodeOffsetZ + self.borderOffsetZ)


    # ****************************     Render      *****************************

    # ------------------------    Render, Level 0    ---------------------------

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.orient_scene()
        self.draw()
        super(Torus5dViewNodecentric, self).paintGL()

    # ------------------------    Render, Level 1    ---------------------------
    
    def draw(self):
        ''' Draw color bars and minimaps.'''
        # remove this call to overlays2D for perspective projection
        #with overlays2D(self.width(), self.height(), self.bg_color):
        #    for func in self.widget2dLists:
        #        func()

        for func in self.widgetLists:
            func()
    
    # ------------------------    Render, Level 2    --------------------------- 

    def drawLayout(self):
        '''Calculate the position of each node and color link values.'''
        
        ''' To switch to perspective projection:
        1.  self.update() -> set reset = True to be default, so self.resetView()
                is called to translate scene into the -z direction
        2.  self.drawWidgets() -> remove call with overlays2D(), just call functions
                in widgetList directly
        3.  self.updateLayoutSizes() -> change startNodeRadius and startLinkRadius
                to be independent of window width/height, with a 1:13 ratio
        4.  self.drawLayout() -> remove call to setup_overlay2D, remove
                with glMatrix() and remove glTranslate to center 2D view
        5.  self.orient_scene() -> remove entirely, or simply have the body call
                super.orient_scene() to let GLWidget handle rotation and translation
                instead of doing it in this view
        '''
        # remove this call if doing a perspective projection
        # setup_overlay2D(0, 0, self.width(), self.height()) 

        #self.drawLabels()

        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        if max(self.shape) == 0: # with this is called before a dropEvent
            return
        #elif self.currentMaxHops == 0: # when this is called from a dropEvent
        #    self.updateLayoutValues()

        #glLineWidth(self.lineWidth)

        # put axis at center
        #with glMatrix(): # remove this if doing perspective projection
            #glLoadIdentity() # remove this if doing perspective projection
            #glTranslatef(self.width()/2, self.height()/2, 0)

        self.drawNodeCircle(self.nodeObjectList[0][()])
        self.drawLinkLines(self.nodeObjectList[0][()])

        #print 'drawing n/l at path = []'

        if self.currentMaxHops > 0:
            #print 'Drawing with maxHopOpacity = ' + str(self.maxHopOpacity) + ', zoomLevel = ' + str(self.translation[2])
            for angle in range(2*len(self.shape)):
                path = [angle]
                self.drawLocalRegion(path)
                    
    def drawLabels(self):
        w = self.width()*0.2
        h = self.height()*0.2
        
        setup_overlay2D(0, 0, int(w), int(h))

        bg_color_avg = (self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) / 3
        if bg_color_avg >= 0.5:
            self.bright_bg_color = True
        else:
            self.bright_bg_color = False

        if self.bright_bg_color:
            glColor3f(0, 0, 0)
        else:
            glColor3f(1, 1, 1)

        # draw a border
        with glMatrix():
            glLineWidth(1.0)
            with glSection(GL_LINES):
                glVertex3f(1, 1, 0.01)
                glVertex3f(w, 1, 0.01)
                glVertex3f(w, 1, 0.01)
                glVertex3f(w, h, 0.01)
                glVertex3f(w, h, 0.01)
                glVertex3f(1, h, 0.01)
                glVertex3f(1, h, 0.01)
                glVertex3f(1, 1, 0.01)
        with glMatrix():
            glTranslatef(w/2, h/2, 0)
            with glSection(GL_TRIANGLES):
                glVertex3f(0, 5, 0)
                glVertex3f(5, 0, 0)
                glVertex3f(-5, 0, 0)

        '''
        if self.currentMaxHops > 0:
            # draw labels for first hop
            bg_color_avg = (self.bg_color[0] + self.bg_color[1] + self.bg_color[2]) / 3
            if bg_color_avg >= 0.5:
                glColor3f(0, 0, 0)
            else:
                glColor3f(1, 1, 1)

            chars = {0: ['+', 'a'], 1: ['+', 'b'], 2: ['+', 'c'], 3: ['+', 'd'], 4: ['+', 'e'],
                5: ['-', 'a'], 6: ['-', 'b'], 7: ['-', 'c'], 8: ['-', 'd'], 9: ['-', 'e']}
            
            for labelDim in range(len(chars)):
                theta = self.linkAngles[labelDim]
                r1 = self.linkRadii[0]*0.75
                r2 = self.linkRadii[0]*0.9
                with glMatrix():
                    #glTranslatef(r1*np.cos(theta), r1*np.sin(theta), 0)
                    glScalef(0.001, 0.001, 0.001)
                    glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(chars[labelDim][0]))
                with glMatrix():
                    #glTranslatef(r2*np.cos(theta), r2*np.sin(theta), 0)
                    glScalef(0.001, 0.001, 0.001)
                    glutStrokeCharacter(GLUT_STROKE_ROMAN, ord(chars[labelDim][1]))
                    glPopMatrix()
        '''

    # ------------------------    Render, Level 3    ---------------------------    
    
    def drawLinkLines(self, nodeObject):
        '''Remember, len(path) == hop level.'''
        path = nodeObject[1]
        for dim in range(2*len(self.shape)):
            theta = self.linkAngles[dim]
            theta += len(path) * self.linkAngles[1]/2.
            '''
            if len(path) % 2 != 0: # odd hop
                offset_x = self.nodeRadii[len(path)] * 0.2 * np.cos(theta + np.pi/2)
                offset_y = self.nodeRadii[len(path)] * 0.2 * np.sin(theta + np.pi/2)
            else:
                offset_x = 0
                offset_y = 0'''

            if dim < 5: # offset positive lines by 90 degrees, r * 0.2
                color_val = list(self.dataModel.pos_link_values[tuple(nodeObject[0])][dim]) # index with node id
            else:
                color_val = list(self.dataModel.neg_link_values[tuple(nodeObject[0])][dim-5]) # index with node id

            # Note:  if changing the way end_x, end_y are drawn, MUST also modify getViewSpan()
            end_x = (self.linkRadii[len(path)]-self.nodeRadii[len(path)+1]) * np.cos(theta)
            end_y = (self.linkRadii[len(path)]-self.nodeRadii[len(path)+1]) * np.sin(theta)
            
            # ******** TODO:  Send in the preempt_range, see Torus5dModule.Torus5dGLWidget.updateLinkColors() ********
            color = list(self.map_link_color(*color_val))
            #print 'node = ' + str(nodeObject[0]) + ', color_val[0] = ' + str(color_val[0]) + ', color = ' + str(color)
            if len(nodeObject[1]) >= self.currentMaxHops-1: # leafNode avgLinks and links connecting leafNode
                color[3] = self.maxHopOpacity
                #print 'drawing outer n/l with maxHopOpacity = ' + str(self.maxHopOpacity)
            else:
                color[3] = 0.9
            glLineWidth(2.)
            glColor4f(*(tuple(color)))
            #print '\tdrawing link: end_x, end_y = ' + str(end_x) + ', ' + str(end_y)
            with glSection(GL_LINES):
                glVertex3f(0, 0, 0)
                glVertex3f(end_x, end_y, 0)

    def drawLocalRegion(self, path):
        # len(path) should NEVER be 0!  always called for a hop >= 1 away from startNode

        done = False
        push = 0
        while not done: # there's more to do
            #print 'new path = ' + str(path)
            if len(path) != self.currentMaxHops: #depth first
                # called from path = [0] for example, but before drawing, need
                #   to translate by linkRadii[0], so linkRadii[len(path)-1]
                r = self.linkRadii[len(path)-1] # radius is based on hop #
                #print '*** Translating by linkRadii[' + str(len(path)-1) + '] == r = ' + str(r) + ' ***'
                # translate by the direction in the last path value
                theta = self.linkAngles[path[len(path)-1]]
                theta += (len(path)-1) * self.linkAngles[1]/2.

                glPushMatrix()
                push += 1
                #print 'pushing matrix, path = ' + str(path) + ', push = ' + str(push)

                glTranslatef(r*np.cos(theta), r*np.sin(theta), 0)
                #if (path[0] == 0):
                #print 'drawing n/l at path = ' + str(path)
                self.drawNodeCircle(self.nodeObjectList[len(path)][tuple(path)])
                self.drawLinkLines(self.nodeObjectList[len(path)][tuple(path)])
                path += [0]
                continue
            else:
                # called from path = [0,0] for example (if maxHops == 2) and
                #   currently at center of path = [0], so need to draw using
                #   linkRadii[1], or linkRadii[len(path)-1]
                for i in range(len(2*self.shape)):
                    path[self.currentMaxHops-1] = i
                    r = self.linkRadii[len(path)-1] # radius is based on hop #
                    theta = self.linkAngles[path[len(path)-1]]
                    theta += (len(path)-1) * self.linkAngles[1]/2.
                    center = [r*np.cos(theta), r*np.sin(theta), 0]
                    #print 'drawing n/l avg at path = ' + str(path)
                    self.drawNodeCircle(self.nodeObjectList[len(path)][tuple(path)], center)
                # how ever many values we chopped off the path, pop modelview matrix
                #   when we chop off from path, we're moving back inward - erase translation
                new_path = self.getNextPath(path)
                # when new_path = [] we pop 1 too many, so take max of len(new_path) and 1
                num_pop_matricies = len(path) - max(1, len(new_path))
                for i in range(num_pop_matricies):
                    push -= 1
                    #print 'popping matrix, path = ' + str(path) + ', new_path = ' + str(new_path) + ', push = ' + str(push)
                    glPopMatrix()
                path = new_path

            if len(path) <= 1:
                done = True

    def drawNodeCircle(self, nodeObject, center = [0, 0, 0], avgLinks = True):
        ''' Draw all 1 node as a circle.  Always called from len(path) >= 0.'''

        r = self.nodeRadii[len(nodeObject[1])] # len(nodeObject[1]) == len(path) == hop #
        if avgLinks:
            r2 = r * self.avgLinkRadiusFactor
        else:
            r2 = r*1.1
        
        if avgLinks:
            colors = list(nodeObject[3])
            if len(nodeObject[1]) == self.currentMaxHops and self.currentMaxHops != 0: # leafNode
                colors[3] = self.maxHopOpacity
            else:
                colors[3] = 0.9
            #print '\tleafNode = ' + str(nodeObject[0]) + ', color = ' + str(colors)
            glColor4f(*(tuple(colors)))
            glBegin(GL_TRIANGLE_FAN)
            glVertex3f(center[0], center[1], center[2]-self.borderOffsetZ)
            for theta in self.circleAngles:
                glVertex3f(center[0] + r2 * np.cos(theta), center[1] + r2 * np.sin(theta), center[2]-self.borderOffsetZ)
            glEnd()

        colors = list(self.node_colors[nodeObject[0]])
        if len(nodeObject[1]) == self.currentMaxHops and self.currentMaxHops != 0: # leafNode
            colors[3] = self.maxHopOpacity
        else:
            colors[3] = 0.9
        glColor4f(*(tuple(colors)))
        glBegin(GL_TRIANGLE_FAN)
        glVertex3f(center[0], center[1], center[2]+self.nodeOffsetZ)
        for theta in self.circleAngles:
            glVertex3f(center[0] + r * np.cos(theta), center[1] + r * np.sin(theta), center[2]+self.nodeOffsetZ)
        glEnd()     


    # **************************        I/O       ******************************

    def changeHoldView(self):
        if self.holdCurrentMaxHops:
            self.holdCurrentMaxHops = False
        else:
            self.holdCurrentMaxHops = True
        self.updateDrawing()

    def changeLinkRadii(self, key):
        if key == 'l' or key == 'L':
            if key == 'l':
                self.linkRadiusFactor += 0.1
                print 'linkRadiusFactor = ' + str(self.linkRadiusFactor)
            elif key == 'L':
                self.linkRadiusFactor -= 0.1
                self.linkRadiusFactor = max(0.1, self.linkRadiusFactor)
                print 'startLinkRadius = ' + str(self.linkRadiusFactor)
            self.updateDrawing(sizes = True)   
        else:
            if key == '0':
                self.linkRadii[0] += 1
                print 'linkRadii[0] = ' + str(self.linkRadii[0])
            elif key == ')':
                self.linkRadii[0] -= 1
                self.linkRadii[0] = max(1, self.linkRadii[0])
                print 'linkRadii[0] = ' + str(self.linkRadii[0])
            elif key == '1':
                self.linkRadii[1] += 0.5
                print 'linkRadii[1] = ' + str(self.linkRadii[1])
            elif key == '!':
                self.linkRadii[1] -= 0.5
                self.linkRadii[1] = max(0.5, self.linkRadii[1])
                print 'linkRadii[1] = ' + str(self.linkRadii[1])
            elif key == '2':
                self.linkRadii[2] += 0.25
                print 'linkRadii[2] = ' + str(self.linkRadii[2])
            elif key == '@':
                self.linkRadii[2] -= 0.25
                self.linkRadii[2] = max(0.25, self.linkRadii[2])
                print 'linkRadii[2] = ' + str(self.linkRadii[2])
            elif key == '3':
                self.linkRadii[3] += 0.125
                print 'linkRadii[3] = ' + str(self.linkRadii[3])
            elif key == '#':
                self.linkRadii[3] -= 0.125
                self.linkRadii[3] = max(0.125, self.linkRadii[3])
                print 'linkRadii[3] = ' + str(self.linkRadii[3])
            elif key == '4':
                self.linkRadii[4] += 0.0625
                print 'linkRadii[4] = ' + str(self.linkRadii[4])
            elif key == '$':
                self.linkRadii[4] -= 0.0625
                self.linkRadii[4] = max(0.0625, self.linkRadii[4])
                print 'linkRadii[4] = ' + str(self.linkRadii[4])
            self.updateDrawing()

    def changeNodeRadii(self, key):
        if key == 'n':
            self.nodeRadiusFactor += 0.1
            print 'nodeRadiusFactor = ' + str(self.nodeRadiusFactor)
        elif key == 'N':
            self.nodeRadiusFactor -= 0.1
            self.nodeRadiusFactor = max(0.1, self.nodeRadiusFactor)
            print 'nodeRadiusFactor = ' + str(self.nodeRadiusFactor)
        self.updateDrawing(sizes = True)

    def keyPressEvent(self, event):
        key_map = { "l" : lambda : self.changeLinkRadii('l'),
                    "L" : lambda : self.changeLinkRadii('L'),
                    "n" : lambda : self.changeNodeRadii('n'),
                    "N" : lambda : self.changeNodeRadii('N'),
                    "0" : lambda : self.changeLinkRadii('0'),
                    ")" : lambda : self.changeLinkRadii(')'),
                    "1" : lambda : self.changeLinkRadii('1'),
                    "!" : lambda : self.changeLinkRadii('!'),
                    "2" : lambda : self.changeLinkRadii('2'),
                    "@" : lambda : self.changeLinkRadii('@'),
                    "3" : lambda : self.changeLinkRadii('3'),
                    "#" : lambda : self.changeLinkRadii('#'),
                    "4" : lambda : self.changeLinkRadii('4'),
                    "$" : lambda : self.changeLinkRadii('$'),
                    "h" : lambda : self.changeHoldView()
        }

        print '\tReceived event.text() = ' + str(event.text())
        if event.text() in key_map:
            key_map[event.text()]()
        else:
            GLWidget.keyPressEvent(self, event)

    def mousePressEvent(self, event):
        super(Torus5dViewNodecentric, self).mousePressEvent(event)
        
        # Return if haven't dragged module onto the data tree yet to prevent
        #   the error when mouse I/O fails to return, causing any keyboard
        #   modifier (shift, contrl..) to be mis-interpreted as mouseEvent
        if max(self.shape) == 0:
            return

        print 'zoomLevel = ' + str(self.translation[2])







