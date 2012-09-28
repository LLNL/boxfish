from SceneInfo import *

class GLModuleScene(ModuleScene):
    """Contains scene information for propagation between GL-based
       modules."""

    def __init__(self, agent_type, module_type, rotation = None,
        translation = None):
        super(GLModuleScene, self).__init__(agent_type, module_type)

        self.rotation = rotation
        self.translation = translation

    def __equals__(self, other):
        if self.rotation == other.rotation \
                and self.translation == other.translation:
            return True
        return False

    def copy(self):
        if self.rotation is not None and self.translation is not None:
            return GLModuleScene(self.agent_type, self.module_name,
                self.rotation.copy(), self.translation.copy())
        elif self.rotation is not None:
            return GLModuleScene(self.agent_type, self.module_name,
                self.rotation.copy(), None)
        elif self.translation is not None:
            return GLModuleScene(self.agent_type, self.module_name,
                None, self.translation.copy())
        else:
            return GLModuleScene(self.agent_type, self.module_name)
