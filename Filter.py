
from PySide.QtCore import *
from PySide.QtGui import *
from FilterCoupler import *
from Query import *

class Filter(QObject):

    def __init__(self):
        super(Filter, self).__init__()

    # This takes a set of input and creates an output.
    # This might also do input and output checking,
    # if the filter cares about it.
    def process(self, columns, identifiers):
        raise NotImplementedError("Filter has no process method")


class IdentityFilter(Filter):

    def __init__(self):
        super(IdentityFilter, self).__init__()

    def process(self, columns, identifiers):
        return  identifiers

class SimpleWhereFilter(Filter):

    def __init__(self, attribute, value):
        super(SimpleWhereFilter, self).__init__()

        self.attribute = attribute
        self.value = value

    def process(self, table, identifiers):
        return table.subset_by_attributes(identifiers,
            Clause("=", TableAttribute(self.attribute), self.value))
