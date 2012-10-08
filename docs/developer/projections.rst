Writing New Projections
=======================
A projection converts the identifiers from one subdomain into the identifiers
of another. This mapping may be one-to-one or one-to-many. Boxfish projections
all subclass ``Projection``.::

  @InputFileKey("my projection")
  class MyProjection(Projection):

    def __init__(self, source = "undefined", destination = "undefined",
      **kwargs):
      super(MyProjection, self).__init__(source, destination, **kwargs)

While the projection has an input ``source`` and ``destination`` subdomain, it
should be able to project in either direction. The ``**kwargs`` may contain
projection-specific information. The contents of ``**kwargs`` generally come
from the information included in the meta-file of a run.

The decorator ``@InputFileKey`` is used to denote the string that will
indicate to the run meta-file that this type of projection should be created. 

Every projection must implement ``project``.::

  def project(self, subdomain, destination):
    if destination == self.destination:
      # Compute source IDs from subdomain
      return SourceSubDomain(source_ids)
    else:
      # Compute destination IDs from subdomain
      return DestinationSubDomain(destination_ids)

Here ``subdomain`` is a ``SubDomain`` object containing identifiers from
either the projection's ``source`` or ``destination`` subdomain. If they are
from the ``source`` subdomain, the parameter ``destination`` should be an
object of the ``destination`` subdomain. If they are from the ``destination``
subdomain, the parameter ``destination`` should be an object of the ``source``
subdomain. The return value be an object of the requested ``destination``
subdomain that contains the identifiers that the parameter ``subdomain`` maps
to in the projection.
