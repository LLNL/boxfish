from PySide.QtCore import Slot,Signal,QObject
from Table import *

# Column used for input and output
# table - The Table object holding the data, might be from the DataModel
# or something specifically created by the filter
# attribute - the attribute in the table we care about, for self owned
# tables this is probably the only output
# * This is in whatever format the particular Table uses which is
# nice since it could eventually handle range data and so forth
# parent - this is the originating module
# name - this may be for the user interface
class BFColumn(QObject):
    """Representation of columns requested in a single data table and a
       single modifier (e.g. filter) applied to them. These columns are
       meant to be chained to allow alterations to valid rows through
       a sequence of modules.
    """

    changeSignal = Signal(QObject)
    deleteSignal = Signal(QObject)

    def __init__(self, table, attributes, parent = None, modifier = None,
        name = None):
        super(BFColumn, self).__init__()
        self.table = table # This might also be a projection
        self.attributes = attributes
        self.name = name
        self.parent = parent

        # parent will deleteColumn
        self.deleteSignal.connect(parent.deleteColumn)
        self._modifier = modifier # e.g. filter

        # chain of modifiers this data has gone through
        self._modifier_chain = list()

    @property
    def modifier(self):
        return self._modifier

    @modifier.setter
    def modifier(self, mod):
        self._modifier = mod
        self.modifierChanged()

    @property
    def modifier_chain(self):
        return self._modifier_chain

    @modifier_chain.setter
    def modifier_chain(self, chain):
        self._modifier_chain = chain[:]

    def createUpstream(self, parent, modifier):
        """Creates a BFColumn that is directly upstream from
           this one. The only initial difference is the change
           in parent.
        """
        upstream = BFColumn(self.table, self.attributes, \
            parent, modifier, self.name)

        # We listen for the upstream changing or deleting
        upstream.changeSignal.connect(self.upstreamChanged)
        upstream.deleteSignal.connect(self.upstreamDeleted)

        # Upstream listens to this column for deletion as well.
        self.deleteSignal.connect(upstream.delete)
        return upstream

    # When the upstream column changes, we must reapply our
    # modifier and then emit the change downward.
    @Slot(QObject)
    def upstreamChanged(self, upstream):
        # Get modifier chain from upstream
        self.modifier_chain = upstream.modifier_chain

        # Apply modifier
        if self.modifier is not None:
            self.modifier_chain.append(self.modifier) # Grow modifier chain

        # Send downward
        self.changeSignal.emit(self)

    def modifierChanged(self):
        if self.modifier is not None:
            self.modifier_chain.append(self.modifier)

        self.changeSignal.emit(self)

    # Disconnect an upstream BFColumn marked for deletion
    @Slot(QObject)
    def upstreamDeleted(self, upstream):
        upstream.deleteSignal.disconnect(self.upstreamDeleted)
        upstream.changeSignal.disconnect(self.upstreamChanged)

    # We're getting rid of this column, let everyone know.
    # All upstreams will be deleted.
    @Slot(QObject)
    def delete(self, downstream = None):
        """Mark column for deletion. Signals stakeholders.
        """
        # emit delete message
        self.deleteSignal.emit(self)


