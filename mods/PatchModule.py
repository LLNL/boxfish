from PySide.QtCore import *
from OpenGL.GLUT import *
from GLWidget import GLWidget
from GLModuleScene import GLModuleScene
from ModuleAgent import *
from ModuleView import *

import sys
import numpy as np
import matplotlib.cm as cm

class PatchAgent(ModuleAgent):
    patchUpdateSignal = Signal(list,list)
    transformUpdateSignal = Signal(np.ndarray, np.ndarray)

    def __init__(self, parent, datatree):
        super(PatchAgent, self).__init__(parent, datatree)

        self.addRequest("patches")

        self.centers = None
        self.sizes = None
        self.table = None

        self.receiveModuleSceneSignal.connect(self.processModuleScene)

    def registerPatchAttributes(self, indices):
        # Determine Torus info from first index
        self.registerRun(self.datatree.getItem(indices[0]).getRun())
        self.requestAddIndices("patches", indices)
        self.updatePatchValues()

    def registerRun(self, run):
        application = run["application"]
        self.sizes = application["size"]
        self.centers = application["center"]
        self.table = application["patch_table"]
        
    def requestUpdated(self, name):
        if name == "patches":
            self.updatePatchValues()

    def updatePatchValues(self):
        if not self.table:
            return
        
        table_item = self.datatree.getTable(self.table)        
        patch_info, attribute_values = self.requestGroupBy("patches",
            [table_item["field"],self.centers,self.sizes], table_item,
            "mean", "mean")
        
        if attribute_values is not None:
            self.patchUpdateSignal.emit(patch_info, attribute_values[0])

    @Slot(ModuleScene)
    def processModuleScene(self, module_scene):
        if self.module_scene.module_name == module_scene.module_name:
            self.module_scene = module_scene.copy()
            self.transformUpdateSignal.emit(self.module_scene.rotation,
                self.module_scene.translation)
    
@Module("3D Patch View", PatchAgent, GLModuleScene)
class PatchView3d(ModuleView):

    def __init__(self, parent, parent_view = None, title = None):
        super(PatchView3d, self).__init__(parent, parent_view, title)

    def createView(self):
        return GLPatchView3d(self)

    @Slot(list, list)
    def updatePatchData(self, patch_info, vals):

        self.view.patch_info = patch_info
        self.view.vals = vals
            


class GLPatchView3d(GLWidget):

    def __init__(self,parent):

        super(GLPatchView3d, self).__init__(parent)
        self.parent = parent

        # color for when we have no data
        self.default_color = [0.5, 0.5, 0.5, 0.5]


    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        self.orient_scene()
        self.drawPatches()

        super(GLTorus3dView, self).paintGL()

    def drawPatches(self):
        glPushMatrix()
        self.centerView()

        glColor4f(*self.default_color)
        
        for patch in self.patch_info:
            glPushMatrix()

            glTranslatef(-patch[1][0],-patch[1][1],-patch[1][2])
            glScalef(-patch[2][0],-patch[2][1],-patch[2][2])

            # glut will draw a cube with its center at (0,0,0)
            glutSolidCube(1)
            glPopMatrix()

        # Get rid of the grid_span translation
        glPopMatrix()

        
