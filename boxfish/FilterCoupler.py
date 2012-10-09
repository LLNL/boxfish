from PySide.QtCore import Slot,Signal,QObject
from Table import *

# FilterCouplers form a chain from a module's data request to the top of 
# Boxfish's tree. At each module, they may attach a modifier (filter).
# parent - this is the originating agent down the chain
# name - this is for the user interface. If a Module has two separate
# data requests (e.g. nodes and links), they can be differentiated
# in the interface using this.
class FilterCoupler(QObject):
    """Representation of a the filter that should be applied to a set
       of data in a module. These form the chain down the Module
       hierarchy to be applied to the data. They also handle changes
       in applied filters and placement in the filter hierarchy.
    """

    changeSignal = Signal(QObject)
    deleteSignal = Signal(QObject)

    def __init__(self, name, parent = None, modifier = None):
        """Construct a FilterCoupler.

           parent
               The ModuleAgent making this request down the chain.

           modifier
               The filter associated with this coupler.

           name
               A tag for use with any user interface.
        """
        super(FilterCoupler, self).__init__()
        self.name = name
        self.parent = parent
        self.upstream_chain = list()

        # parent will deleteCoupler
        self.deleteSignal.connect(parent.deleteCoupler)
        self._modifier = modifier # e.g. filter

        # chain of modifiers this data has gone through
        self._modifier_chain = list()

    @property
    def modifier(self):
        """The filter associated with this particular coupler."""
        return self._modifier

    @modifier.setter
    def modifier(self, mod):
        self._modifier = mod
        self.modifierChanged()

    @property
    def modifier_chain(self):
        """The chain of modifiers to this point down the coupler chain."""
        return self._modifier_chain

    @modifier_chain.setter
    def modifier_chain(self, chain):
        self._modifier_chain = chain[:]

    def createUpstream(self, parent, modifier):
        """Creates a FilterCoupler that is directly upstream from
           this one. The only initial difference is the change
           in parent.
        """
        upstream = FilterCoupler(self.name, parent, modifier)

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
        """When signalled about a change upstream, reconstructs the
           potentially changed modifier chain and propagates the change
           downward.
        """
        # Get modifier chain from upstream
        self.upstream_chain = upstream.modifier_chain[:]
        self.modifier_chain = self.upstream_chain[:]

        # Apply modifier
        if self.modifier is not None:
            self.modifier_chain.append(self.modifier) # Grow modifier chain

        # Send downward
        self.changeSignal.emit(self)

    def modifierChanged(self):
        """When the modifier associated with this coupler is changed,
           the modifier_chain must be reconstructed and propagated
           downward.
        """
        self.modifier_chain = self.upstream_chain[:]
        if self.modifier is not None:
            self.modifier_chain.append(self.modifier)

        self.changeSignal.emit(self)

    # Disconnect an upstream FilterCoupler marked for deletion
    @Slot(QObject)
    def upstreamDeleted(self, upstream):
        """Handles the clean up when the upstream coupler is deleted."""
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


