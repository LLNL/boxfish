from PySide.QtCore import *
from PySide.QtGui import *
from FilterCoupler import *
from Query import *

class Filter(QObject):
    """This class represents a filter on a data stream/query."""

    def __init__(self):
        """Construct a Filter."""
        super(Filter, self).__init__()

    def process(self, table, identifiers):
        """Given a TableItem from the DataTree and a list of identifiers
           to consider from that TableItem's table, applies itself (as
           a filter) and returns the filtered list of identifiers.
        """
        raise NotImplementedError("Filter has no process method")


class SimpleWhereFilter(Filter):
    """A filter constructed out of a Clause object."""

    def __init__(self, conditions):
        """Construct a SimpleWhereFilter from the given Clause object."""
        super(SimpleWhereFilter, self).__init__()

        self.conditions = conditions

    def process(self, table, identifiers):
        """Given a TableItem from the DataTree and a list of identifiers
           to consider from that TableItem's table, applies its
           condition (Clause object) and returns the filtered list of
           identifiers.
        """
        return table.evaluate(self.conditions, identifiers)
