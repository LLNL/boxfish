from SubDomain import *

class Projection(object):

  def __init__(self,source = "undefined", destination = "undefined"):
    object.__init__(self)

    if isinstance(source,str):
      self.source = source
    elif isinstance(source,SubDomain):
      self.source = source.subdomain()
    else:
      raise ValueError("A projection can only be initialized with names or SubDomains")

    if isinstance(destination,str):
      self.destination = destination
    elif isinstance(destination,SubDomain):
      self.destination = destination.subdomain()
    else:
      raise ValueError("A projection can only be initialized with names or SubDomains")


  def relates(self,source,destination):

    return (((self.source == source) and (self.destination == destination)) or
            ((self.source == destination) and (self.destination == source)))


class IdentityProjection(Projection):
  """A default identify mapping, for example, for the standard MPI rank <-> core
     mapping
  """

  def __init__(self,source = "undefined", destination = "undefined"):

    Projection.__init__(self,source,destination)

  def project(self,subdomain,destination):

    result = SubDomain().instantiate(destination,subdomain)
    return result


class TableProjection(Projection):
  """Mapping defined by Table.
  """

  def __init__(self, source = "undefined", destination = "undefined", \
    source_key = None, destination_key = None, table = None):
    super(TableProjection, self).__init__(source, destination)

    self._table = table
    self._source_key = source_key
    self._destination_key = destination_key


  def project(self, subdomain, destination):

      if destination == self.destination:
          identifiers = self._table.subset_by_key(subdomain)
          keys = self._table.attribute_by_identfiers(identifiers,\
              [self._destination_key])
      else:
          conditions = list()
          for key in subdomain:
              conditions.append((self._destination_key, "=", key, "or"))
          identfiers = self._table.subset_by_attributes(\
              self._table.identifiers(), conditions)
          keys = self._table.attribute_by_identifiers(identifiers,\
              [self._source_key])

      return keys



