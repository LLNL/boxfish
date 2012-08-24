
from PySide.QtCore import *
from PySide.QtGui import *
from BFColumn import *

class BFFilter(QObject):

    def __init__(self):
        super(BFFilter, self).__init__()

    # This takes a set of input and creates an output.
    # This might also do input and output checking,
    # if the filter cares about it.
    def process(self, columns):
        raise NotImplementedError("Filter has no process method")


class IdentityFilter(BFFilter):

    def __init__(self):
        super(IdentityFilter, self).__init__()

    def process(self, columns, identifiers):
        return  identifiers
