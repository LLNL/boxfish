"""\
Support for nicely indented GL sections in python using Python's with statement.
Author:
    Todd Gamblin, tgamblin@llnl.gov
"""
import contextlib
from OpenGL.GL import *

@contextlib.contextmanager
def glSection(type):
    glBegin(type)
    yield
    glEnd()
