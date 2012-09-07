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
          clauses = list()
          for key in subdomain:
              clauses.append((self._destination_key, "=", key, "or"))
          conditions = Clause("or", *clauses)
          identfiers = self._table.subset_by_attributes(\
              self._table.identifiers(), conditions)
          keys = self._table.attribute_by_identifiers(identifiers,\
              [self._source_key])

      return keys

class NodeLinkProjection(Projection):
    """Common Node-Link mappings, defined by policy:

       Source: Links mapped to their source node. Nodes mapped to all links
               emanating from them.

       Destination: Links mapped to their destination node. Nodes mapped to
                    link ends.

       Both: Double counts... links mapped to both source and destination 
             nodes. Nodes mapped onto all links they are incident upon.


       Note: 'node_policy' cover how nodes map onto links; 'link_policy'
       covers how links map onto nodes.
    """
    def __init__(self, run, node_policy = 'Source', link_policy = 'Source'):
        """Construct a NodeLink Projection.

        run: RunItem governing this projection
        node_policy: how nodes map onto links
        link_policy: how links map onto nodes

        Policies: 'Source', 'Destination', and 'Both'
        """
        super(NodeLinkProjection, self).__init__(Node, Link)

        self.run = run
        self.node_policy = node_policy
        self.link_policy = link_policy

        # TODO: A lot of boring stuff to handle errors and set 
        # defaults. Eventually we would like to read the default
        # information from the user's .boxfishconfig before going
        # to our own hardcoded defaults
        hardware_info = run["hardware"]

        self.source_table = run.getTable(hardware_info["coords_table"])
        self.destination_table = run.getTable(
            hardware_info["link_coords_table"])

        self.coords = hardware["coords"]
        self.source_coords = hardware["source_coords"]
        self.destination_coords = hardware["destination_coords"]


    def project(self, subdomain, destination):

        if destination == self.destination: # Nodes -> Links
            # Find coords from given node IDs. Find matching
            # link coords. Return link IDs
            identifiers = self.source_table._table.subset_by_key(
                self.source_table._table.identifiers(), #identifiers
                subdomain) # valid node IDs
            valid_coords = self.source_table._table.attributes_by_identifiers(
                identifiers, self.coords, unique = False) # We want all
            
            conditions = list()
            if self.node_policy == 'Source':
                conditions.append(())

        else: # Links -> Nodes
            # Find coords from given link IDs. Find matching
            # node coords. Return node IDs.
            pass

