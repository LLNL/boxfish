from PySide.QtCore import *
from BFModule import *
from GLWidget import GLWidget
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLE import *
import numpy as np

from BFColumn import BFColumn
import matplotlib
import matplotlib.cm as cm

# TODO: this is a hack.  we should change our yaml format so that hardware
# is a dict and not a list of single-item dicts.
def get_from_list(dict_list, key):
    for dict in dict_list:
        if key in dict:
            return dict[key]

class Torus3dView3dModule(BFModule):
    columnSignal = Signal(list, list)

    def __init__(self, parent, model):
        super(Torus3dView3dModule, self).__init__(parent, model)

    # TODO: the module probably shouldn't have to know about
    # BFColumn -- it can just specify which attributes it wants
    # to be notified about
    def registerColumn(self, index):
        item = self.model.getItem(index)
        # BFColumn is really a requirement set plus information
        # about who to notify.  BFModule knows most of this, though
        # so maybe just pass the item
        col = BFColumn(item.parent(), [item.name], self)

        # e.g., how about self.addRequirement([item ...])?
        self.addRequirement([col])

    @Slot(BFColumn)
    def requiredColumnChanged(self, col):
        identifiers = col.table._table.identifiers()
        for filt in col.modifier_chain:
            identifiers = filt.process(col, identifiers)

        coords, attrVals = col.table._table.attributes_by_attributes(
            identifiers, self.coords, col.attributes, "mean")
        self.columnSignal.emit(coords, attrVals)

class Torus3dView3d(BFModuleWindow):
    """This is a 3d rendering of a 3d torus.
    """
    display_name = "3D Torus View"
    in_use = True

    def __init__(self, parent, parent_view = None, title = None):
        super(Torus3dView3d, self).__init__(parent, parent_view, title)
        if self.module:
            self.module.columnSignal.connect(self.updateNodeData)

    def createModule(self):
        self.module = Torus3dView3dModule(self.parent_view.module, self.parent_view.module.model)
        return self.module

    def createView(self):
        self.view = GLTorus3dView(self)
        return self.view

    @Slot(list, list)
    def updateNodeData(self, coords, vals):
        vals = vals[0]  # TODO: why is this a list nested in a list
        min_val = min(vals)
        max_val = max(vals)
        range = max_val - min_val

        cmap = cm.get_cmap("gist_earth_r")
        for coord, val in zip(coords, vals):
            x, y, z = coord
            self.view.node_colors[x, y, z] = cmap((val - min_val) / range)
        self.view.updateGL()

    def findRunAndGetHardware(self,item):
        if item.typeInfo() == "RUN":
            if "hardware" in item:
                hardware = item["hardware"]

                coords = get_from_list(hardware, "coords")
                shape = [get_from_list(hardware, "dim")[coord] for coord in coords]
                self.module.coords = coords
                self.view.setShape(shape)
            else:
                pass
        else:
            if item.parent():
                self.findRunAndGetHardware(item.parent())

    def droppedData(self, index_list):
        if len(index_list) != 1:
            return

        index = index_list[0]
        item = self.module.model.getItem(index)

        self.findRunAndGetHardware(item)
        
        if item.typeInfo() == "ATTRIBUTE":
            self.module.registerColumn(index)
 

class GLTorus3dView(GLWidget):
    def __init__(self, parent):
        super(GLTorus3dView, self).__init__(parent)

        self.default_color = [0.5, 0.5, 0.5, 1.0] # color for when we have no data
        self.setShape([0, 0, 0])                  # Set shape and set up color matrix
        self.seam = [0, 0, 0]                     # Offsets representing seam of the torus
        self.box_size = 0.2                       # Size of one edge of each cube representing a node
        self.link_radius = self.box_size * .1     # Radius of link cylinders

    def getBoxSize(self):
        return self.box_size

    def setBoxSize(self, box_size):
        self.box_size = box_size
        self.updateGL()

    def getShape(self):
        return self.shape

    def setShape(self, shape):
        self.shape = shape
        self.node_colors = np.empty(self.shape + [4])
        self.node_colors.fill(0.5)  # TODO: make this fill with self.default_color
        self.updateGL()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        self.orient_scene()
        self.drawCubes()
        self.drawLinks()
        glFlush()

    def centerView(self):
        """ First we move the coordinate system by half the size of the total
            grid. This will allow us to draw boxes and links at (0,0,0),
            (1,0,0),... etc. but they will appear centered around the global
            origin.
        """
        x_span, y_span, z_span = self.shape
        glTranslatef(-(x_span-1)/2.0,-(y_span-1)/2.0,(z_span-1)/2.)

    def drawCubes(self):
        glPushMatrix()
        self.centerView()

        x_span, y_span, z_span = self.shape
        for x, y, z in np.ndindex(*self.shape):
            glPushMatrix()

            glColor4f(*self.node_colors[x,y,z])
            glTranslatef((x + self.seam[0]) % x_span,
                         (y + self.seam[1]) % y_span,
                         -((z + self.seam[2]) % z_span))

            # glut will draw a cube with its center at (0,0,0)
            glutSolidCube(self.box_size)
            glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()


    def drawLinks(self):
        glMaterialfv(GL_FRONT_AND_BACK,GL_DIFFUSE,[1.0,1.0,1.0,1.0])

        glPushMatrix()
        self.centerView()

        x_span, y_span, z_span = self.shape
        for x, y, z in np.ndindex(*self.shape):
            glPushMatrix()

            glColor4f(0.5, 0.5, 0.5, 1.0)
            glTranslatef((x + self.seam[0]) % x_span,
                         (y + self.seam[1]) % y_span,
                         -((z + self.seam[2]) % z_span))

            glePolyCylinder([(-1, 0, 0), (0, 0, 0), (1, 0, 0), (2, 0, 0)], None, self.link_radius)
            glePolyCylinder([(0, -1, 0), (0, 0, 0), (0, 1, 0), (0, 2, 0)], None, self.link_radius)
            glePolyCylinder([(0, 0, -1), (0, 0, 0), (0, 0, 1), (0, 0, 2)], None, self.link_radius)
            glPopMatrix()
        glPopMatrix()


