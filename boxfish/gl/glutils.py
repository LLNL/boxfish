"""
Support for nicely indented GL sections in python using Python's with
statement.

Author:
    Todd Gamblin, tgamblin@llnl.gov
"""
from contextlib import contextmanager
from OpenGL.GL import *
#from glefix import *

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

# Precalculated for polycylinder with 10 faces
# sin 36, cos 36, cos 18, sin 18, two midpoints
# away from axes
cyltrigs = [ 0.587785, 0.809017, 0.951057, 0.309017 ];

# Braindead replacement
# Not that color is not used by us
# and we only use middle two values of points
def notGlePolyCylinder(points, color, radius):

    trigs = [radius * x for x in cyltrigs];

    # Different per radius of cylinder
    if abs(points[1][0] - points[2][0]) > 1e-6:
        with glSection(GL_QUAD_STRIP):
            glNormal3f(0, 0, 1.)
            glVertex(points[1][0], 0, radius)
            glVertex(points[2][0], 0, radius)
            glNormal3f(0, cyltrigs[0], cyltrigs[1])
            glVertex(points[1][0], trigs[0], trigs[1])
            glVertex(points[2][0], trigs[0], trigs[1])
            glNormal3f(0, cyltrigs[2], cyltrigs[3])
            glVertex(points[1][0], trigs[2], trigs[3])
            glVertex(points[2][0], trigs[2], trigs[3])
            glNormal3f(0, cyltrigs[2], -cyltrigs[3])
            glVertex(points[1][0], trigs[2], -trigs[3])
            glVertex(points[2][0], trigs[2], -trigs[3])
            glNormal3f(0, cyltrigs[0], -cyltrigs[1])
            glVertex(points[1][0], trigs[0], -trigs[1])
            glVertex(points[2][0], trigs[0], -trigs[1])
            glNormal3f(0, 0, -1.)
            glVertex(points[1][0], 0, -radius)
            glVertex(points[2][0], 0, -radius)
            glNormal3f(0, -cyltrigs[0], -cyltrigs[1])
            glVertex(points[1][0], -trigs[0], -trigs[1])
            glVertex(points[2][0], -trigs[0], -trigs[1])
            glNormal3f(0, -cyltrigs[2], -cyltrigs[3])
            glVertex(points[1][0], -trigs[2], -trigs[3])
            glVertex(points[2][0], -trigs[2], -trigs[3])
            glNormal3f(0, -cyltrigs[2], cyltrigs[3])
            glVertex(points[1][0], -trigs[2], trigs[3])
            glVertex(points[2][0], -trigs[2], trigs[3])
            glNormal3f(0, -cyltrigs[0], cyltrigs[1])
            glVertex(points[1][0], -trigs[0], trigs[1])
            glVertex(points[2][0], -trigs[0], trigs[1])
            glNormal3f(0, 0, 1.)
            glVertex(points[1][0], 0, radius)
            glVertex(points[2][0], 0, radius)
    elif abs(points[1][1] - points[2][1]) > 1e-6:
        p1 = points[1][1]
        p2 = points[2][1]
        with glSection(GL_QUAD_STRIP):
            glNormal3f(0, 0, 1.)
            glVertex(0, p1, radius)
            glVertex(0, p2, radius)
            glNormal3f(cyltrigs[0], 0, cyltrigs[1])
            glVertex(trigs[0], p1, trigs[1])
            glVertex(trigs[0], p2, trigs[1])
            glNormal3f(cyltrigs[2], 0, cyltrigs[3])
            glVertex(trigs[2], p1, trigs[3])
            glVertex(trigs[2], p2, trigs[3])
            glNormal3f(cyltrigs[2], 0, -cyltrigs[3])
            glVertex(trigs[2], p1, -trigs[3])
            glVertex(trigs[2], p2, -trigs[3])
            glNormal3f(cyltrigs[0], 0, -cyltrigs[1])
            glVertex(trigs[0], p1, -trigs[1])
            glVertex(trigs[0], p2, -trigs[1])
            glNormal3f(0, 0, -1.)
            glVertex(0, p1, -radius)
            glVertex(0, p2, -radius)
            glNormal3f(-cyltrigs[0], 0, -cyltrigs[1])
            glVertex(-trigs[0], p1, -trigs[1])
            glVertex(-trigs[0], p2, -trigs[1])
            glNormal3f(-cyltrigs[2], 0, -cyltrigs[3])
            glVertex(-trigs[2], p1, -trigs[3])
            glVertex(-trigs[2], p2, -trigs[3])
            glNormal3f(-cyltrigs[2], 0, cyltrigs[3])
            glVertex(-trigs[2], p1, trigs[3])
            glVertex(-trigs[2], p2, trigs[3])
            glNormal3f(-cyltrigs[0], 0, cyltrigs[1])
            glVertex(-trigs[0], p1, trigs[1])
            glVertex(-trigs[0], p2, trigs[1])
            glNormal3f(0, 0, 1.)
            glVertex(0, p1, radius)
            glVertex(0, p2, radius)
    else:
        p1 = points[1][2]
        p2 = points[2][2]
        with glSection(GL_QUAD_STRIP):
            glNormal3f(0, 1., 0)
            glVertex(0, radius, p1)
            glVertex(0, radius, p2)
            glNormal3f(cyltrigs[0], cyltrigs[1], 0)
            glVertex(trigs[0], trigs[1], p1)
            glVertex(trigs[0], trigs[1], p2)
            glNormal3f(cyltrigs[2], cyltrigs[3], 0)
            glVertex(trigs[2], trigs[3], p1)
            glVertex(trigs[2], trigs[3], p2)
            glNormal3f(cyltrigs[2], -cyltrigs[3], 0)
            glVertex(trigs[2], -trigs[3], p1)
            glVertex(trigs[2], -trigs[3], p2)
            glNormal3f(cyltrigs[0], -cyltrigs[1], 0)
            glVertex(trigs[0], -trigs[1], p1)
            glVertex(trigs[0], -trigs[1], p2)
            glNormal3f(0, -1., 0)
            glVertex(0, -radius, p1)
            glVertex(0, -radius, p2)
            glNormal3f(-cyltrigs[0], -cyltrigs[1], 0)
            glVertex(-trigs[0], -trigs[1], p1)
            glVertex(-trigs[0], -trigs[1], p2)
            glNormal3f(-cyltrigs[2], -cyltrigs[3], 0)
            glVertex(-trigs[2], -trigs[3], p1)
            glVertex(-trigs[2], -trigs[3], p2)
            glNormal3f(-cyltrigs[2], cyltrigs[3], 0)
            glVertex(-trigs[2], trigs[3], p1)
            glVertex(-trigs[2], trigs[3], p2)
            glNormal3f(-cyltrigs[0], cyltrigs[1], 0)
            glVertex(-trigs[0], trigs[1], p1)
            glVertex(-trigs[0], trigs[1], p2)
            glNormal3f(0, 1., 0)
            glVertex(0, radius, p1)
            glVertex(0, radius, p2)


# Braindead replacement 
def notGlutSolidCube(size):
    p = size / 2
    n = -1 * p
    with glSection(GL_QUADS): # front
        glNormal3f(0, 0, 1.)
        glVertex(n, p, n)
        glVertex(n, n, n)
        glVertex(p, n, n)
        glVertex(p, p, n)
    with glSection(GL_QUADS): # top
        glNormal3f(0, 1., 0)
        glVertex(n, p, p)
        glVertex(n, p, n)
        glVertex(p, p, n)
        glVertex(p, p, p)
    with glSection(GL_QUADS): # right
        glNormal3f(1., 0, 0)
        glVertex(p, p, n)
        glVertex(p, n, n)
        glVertex(p, n, p)
        glVertex(p, p, p)
    with glSection(GL_QUADS): # back
        glNormal3f(0, 0, -1.)
        glVertex(p, p, p)
        glVertex(p, n, p)
        glVertex(n, n, p)
        glVertex(n, p, p)
    with glSection(GL_QUADS): # bottom
        glNormal3f(0, -1., 0)
        glVertex(p, n, p)
        glVertex(p, n, n)
        glVertex(n, n, n)
        glVertex(n, n, p)
    with glSection(GL_QUADS): # left
        glNormal3f(-1., 0, 0)
        glVertex(n, p, p)
        glVertex(n, n, p)
        glVertex(n, n, n)
        glVertex(n, p, n)


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
