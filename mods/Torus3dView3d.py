from PySide.QtCore import *
from BFModule import *
from GLWidget import GLWidget

class Torus3dView3d(BFModuleWindow):
    """This is a 3d rendering of a 3d torus.
    """
    display_name = "3D Torus View"
    in_use = True

    def __init__(self, parent, parent_view = None, title = None):
        super(Torus3dView3d, self).__init__(parent, parent_view, title)

    def createModule(self):
        return BFModule(self.parent_view.module, self.parent_view.module.model)

    def createView(self):
        view = QWidget()

        layout = QGridLayout()
        layout.addWidget(GLWidget(self), 0, 0, 1, 1)
        layout.setRowStretch(0, 10)
        layout.setContentsMargins(0, 0, 0, 0)
        view.setLayout(layout)
        return view


