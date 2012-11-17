from PySide.QtCore import *
from OpenGL.GL import *
from OpenGL.GLUT import *

from GLModule import *
from boxfish.gl.GLWidget import GLWidget


class Patch3dAgent(GLAgent):
    """ This is an agent for modules that deal with application patches. """

    patchUpdateSignal = Signal(list, list)

    def __init__(self, parent, datatree):
        super(Patch3dAgent, self).__init__(parent, datatree)

        self.addRequest("patches")

	self.patchid = None
	self.values = None
        self.patch_table = None
	self.patch_coords_dict = dict()
	self.coords_patch_dict = dict()
	self.run = None


    def registerPatchAttributes(self, indices):
        self.registerRun(self.datatree.getItem(indices[0]).getRun())
        self.requestAddIndices("patches", indices)

    def registerRun(self, run):
	if run is not self.run:
	    self.run = run
	    application = run["application"]
	    centers = application["centers"]
	    sizes = application["sizes"]
	    self.patch_table = run.getTable(application["patch_table"])

	    self.patch_coords_dict, self.coords_patch_dict = \
		self.patch_table.createIdAttributeMaps(centers + sizes)

    def requestUpdated(self, name):
        if name == "patches":
            self.updatePatchValues()

    def updatePatchValues(self):
        self.patchid, self.values = self.requestOnDomain("patches",
            domain_table = self.patch_table,
            row_aggregator = "mean", attribute_aggregator = "mean")
        self.patchUpdateSignal.emit(self.patchid, self.values)


@Module("3D Patch View", Patch3dAgent, GLModuleScene)
class Patch3dFrame(GLFrame):

    def __init__(self, parent, parent_frame = None, title = None):
        super(Patch3dFrame, self).__init__(parent, parent_frame, title)

	self.agent.patchUpdateSignal.connect(self.updatePatchData)

    def createView(self):
        return Patch3dGLWidget(self)

    def droppedData(self, indexList):
	self.agent.registerPatchAttributes(indexList)

    @Slot(list, list)
    def updatePatchData(self, patchid, values):
        self.view.patchid = patchid
        self.view.values = values

	self.view.updateGL()


class Patch3dGLWidget(GLWidget):

    def __init__(self, parent):
        super(Patch3dGLWidget, self).__init__(parent)
        self.parent = parent

        # color for when we have no data
        self.default_color = [0.9, 0.9, 0.9, 0.5]

	self.values = None

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.orient_scene()
        self.drawPatches()

        super(Patch3dGLWidget, self).paintGL()

    def drawPatches(self):
	if self.values is None:
	    return

        glPushMatrix()

        glColor4f(*self.default_color)

	cmap = self.parent.agent.requestScene("patches").color_map
	minval = min(self.values)
	maxval = max(self.values)

        for patch, value in zip(self.patchid, self.values):
            glPushMatrix()

	    cx, cy, cz, sx, sy, sz = self.parent.agent.patch_coords_dict[patch]
            glTranslatef(-cx, -cy, -cz)
            glScalef(-sx, -sy, -sz)

	    glColor4f(*cmap.getColor((value-minval) / (maxval - minval)))

            # glut will draw a cube with its center at (0, 0, 0)
            glutSolidCube(1)
            glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()


