"""
Support for nicely indented GL sections in python using Python's with
statement.

Author:
    Todd Gamblin, tgamblin@llnl.gov
"""
from contextlib import contextmanager
from OpenGL.GL import *
from glefix import *

@contextmanager
def glSection(type):
    glBegin(type)
    yield
    glEnd()

@contextmanager
def glMatrix():
    glPushMatrix()
    yield
    glPopMatrix()

@contextmanager
def glModeMatrix(type):
    glMatrixMode(type)
    glPushMatrix()
    yield
    glMatrixMode(type)
    glPopMatrix()

@contextmanager
def attributes(*glBits):
    for bit in glBits:
        glPushAttrib(bit)
    yield
    for bit in glBits:
        glPopAttrib()

@contextmanager
def enabled(*glBits):
    for bit in glBits:
        glEnable(bit)
    yield
    for bit in glBits:
        glDisable(bit)

@contextmanager
def disabled(*glBits):
    for bit in glBits:
        glDisable(bit)
    yield
    for bit in glBits:
        glEnable(bit)

@contextmanager
def overlays2D(width, height, background_color):
    """The before and after gl calls necessary to setup 2D overlays to the
       main gl drawing. This should be encase all methods which have a call to
       setup_overlay2D.
    """
    # Prepare to change modes
    glDisable(GL_LIGHTING)
    glDisable(GL_LIGHT0)
    glDisable(GL_BLEND)
    glEnable(GL_SCISSOR_TEST)
    with glModeMatrix(GL_PROJECTION):
        yield
    # Change mode back
    glViewport(0, 0, width, height)
    glDisable(GL_SCISSOR_TEST)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glEnable(GL_BLEND)
    glClearColor(*background_color)

def setup_overlay2D(x, y, width, height):
    """Sets up the small 2D overlay area. The background is clear.
    """
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    glScissor(x, y, width, height)
    glViewport(x, y, width, height)
    glOrtho(x, x + width, y, y + height, -1, 1)
    glMatrixMode(GL_MODELVIEW)


class DisplayList(object):
    """Use this to turn some rendering function of yours into a DisplayList,
       without all the tedious setup.

       Suppose you have a rendering function that looks like this:
           def myRenderFunction():
               # ... Do rendering stuff ...

       And you want to use it to build a displayList:
           myList = DisplayList(myRenderFunction)

       Now to call the list, just do this:
           myList()

       If you want the render function to get called again the next time your
       display list is called, you call "update()" on the display list:
           myList.update()

       Now the next call to myList() will generate you a new display list by
       running your render function again.  After that, it just calls the
       new list.

       Note that your render function *can* take args, and you can pass them
       when you call the display list, but they're only really passed along
       when an update is needed, so it's probably best to just not make
       render functions with arguments.

       TODO: this should probably have ways to keep around active list ids so
       TODO: that they can be freed up at the end of execution.
    """
    def __init__(self, renderFunction):
        self.renderFunction = renderFunction
        self.needsUpdate = True
        self.listId = None

    def update(self):
        self.needsUpdate = True

    def __call__(self, *args):
        if self.needsUpdate:
            if self.listId:
                glDeleteLists(self.listId, 1)
            self.listId = glGenLists(1)

            glNewList(self.listId, GL_COMPILE_AND_EXECUTE)
            self.renderFunction(*args)
            glEndList()
            self.needsUpdate = False
        else:
            glCallList(self.listId)
