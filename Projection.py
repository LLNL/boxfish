from SubDomain import *

def InputFileKey(input_file_key, enabled = True):
    """InputFileKey decorator :
       input_file_key - name that can be used to instantiate from file
       enabled - true if the user can create one
    """
    def input_file_key_inner(cls):
        cls.input_file_key = input_file_key
        cls.enabled = enabled
        return cls
    return input_file_key_inner

@InputFileKey("N/A", enabled = False)
class Projection(object):

  def __init__(self,source = "undefined", destination = "undefined", **kwargs):
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

  
  def instantiate(self, key, source, destination, **kwargs):

      if self.__class__.input_file_key == key:
          return self.__class__(source, destination, **kwargs)
      else:
          for s in self.__class__.__subclasses__():
              result = s().instantiate(key, source, destination, **kwargs)
              if result is not None:
                  return result
          return None

@InputFileKey("identity")
class IdentityProjection(Projection):
  """A default identify mapping, for example, for the standard MPI rank <-> core
     mapping
  """

  def __init__(self,source = "undefined", destination = "undefined", **kwargs):
    super(IdentityProjection, self).__init__(source,destination,**kwargs)

  def project(self,subdomain,destination):

    result = SubDomain().instantiate(destination,subdomain)
    return result


@InputFileKey("file")
class TableProjection(Projection):
  """Mapping defined by Table.
  """

  def __init__(self, source = "undefined", destination = "undefined", **kwargs):
    super(TableProjection, self).__init__(source, destination, **kwargs)

    if kwargs:
        if 'source_key' not in kwargs or 'destination_key' not in kwargs\
            or 'table' not in kwargs:
            raise ValueError("TableProjection constructor requires source_key, "
                + "destination_key, and table.")
        self._table = kwargs["table"]
        self._source_key = kwargs["source_key"]
        self._destination_key = kwargs["destination_key"]


  def project(self, subdomain, destination):

      if destination == self.destination:
          identifiers = self._table.subset_by_key(subdomain)
          keys = self._table.attribute_by_identfiers(identifiers,\
              [self._destination_key])
      else:
          clauses = list()
          for key in subdomain:
              clauses.append(Clause("=", TableAttribute(self._destination_key),
                  key))
          conditions = Clause("or", *clauses)
          identfiers = self._table.subset_by_attributes(\
              self._table.identifiers(), conditions)
          keys = self._table.attribute_by_identifiers(identifiers,\
              [self._source_key])


      return Subdomain().instantiate(destination, keys)



@InputFileKey("node link")
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

       This class assumes that there will be a table with coordinates for
       the nodes and coordinates of the source and destination for links.
       The projection is based upon these coordinates.
    """
    def __init__(self, source = "undefined", destination = "undefined", **kwargs):
        """Construct a NodeLink Projection.

        run: RunItem governing this projection
        node_policy: how nodes map onto links
        link_policy: how links map onto nodes

        Policies: 'Source', 'Destination', and 'Both'
        """
        super(NodeLinkProjection, self).__init__(Nodes(), Links(), **kwargs)

        if kwargs:
            if 'run' not in kwargs or 'node_policy' not in kwargs\
                or 'link_policy' not in kwargs:
                raise ValueError("NodeLinkProjection constructor requires " 
                + "run, node_policy, and link_policy.")

            self.run = kwargs['run']
            self.node_policy = kwargs['node_policy']
            self.link_policy = kwargs['link_policy']

            # TODO: A lot of boring stuff to handle errors and set 
            # defaults. Eventually we would like to read the default
            # information from the user's .boxfishconfig before going
            # to our own hardcoded defaults
            hardware_info = self.run["hardware"]

            self.source_table = self.run.getTable(hardware_info["coords_table"])
            self.destination_table = self.run.getTable(
                hardware_info["link_coords_table"])

            self.coords = hardware_info["coords"]
            self.source_coords = [hardware_info["source_coords"][coord] 
                for coord in self.coords]
            self.destination_coords = [hardware_info["destination_coords"][coord] 
                for coord in self.coords]


    def project(self, subdomain, destination):
        source_table = self.source_table._table
        destination_table = self.destination_table._table

        if destination == self.destination: # Nodes -> Links
            # Find coords from given node IDs. Find matching
            # link coords. Return link IDs
            identifiers = source_table.subset_by_key(
                source_table.identifiers(), #identifiers
                subdomain) # valid node IDs
            valid_coords = source_table.attributes_by_identifiers(
                identifiers, self.coords, unique = False) # We want all
            # Note: valid_coords is a list of lists, one for each coord, 
            # in the order of self.coords
            coord_tuples = set(zip(*valid_coords))
            
            conditions = list()
            if self.node_policy == 'Source' or self.node_policy == 'Both':
                for coord_tuple in coord_tuples:
                    conditions.append(self.source_coords, coord_tuple)
            if self.node_policy == 'Destination' or self.node_policy == 'Both':
                for coord_tuple in coord_tuples:
                    conditions.append(self.source_coords, coord_tuple)

            links = destination_table.attributes_by_conditions(
                destination_table.identifiers(), # identifiers
                [self.destination_table["field"]], # link id
                Clause('or', *conditions)) # we are fine with unique here

            return Subdomain().instantiate(destination, links)
        else: # Links -> Nodes
            # Find coords from given link IDs. Find matching
            # node coords. Return node IDs.
            identifiers = destination_table.subset_by_key(
                destination_table.identifiers(), #identifiers
                subdomain) # valid link IDs

            conditions = list()
            if self.link_policy == 'Source' or self.link_policy == 'Both':
                valid_coords = destination_table.attributes_by_identifiers(
                    identifiers, self.source_coords, unique = False)
                coord_tuples = set(zip(*valid_coords))
                for coord_tuple in coord_tuples:
                    conditions.append(self.coords, coord_tuple)
            if self.link_policy == 'Destination' or self.link_policy == 'Both':
                valid_coords = destination_table.attributes_by_identifiers(
                    identifiers, self.destination_coords, unique = False)
                coord_tuples = set(zip(*valid_coords))
                for coord_tuple in coord_tuples:
                    conditions.append(self.coords, coord_tuple)

            nodes = source_table.attributes_by_conditions(
                source_table.identifiers(), # identifiers
                [self.source_table["field"]], # node id
                Clause('or', conditions)) # we are fine with unique here
            return Subdomain().instantiate(destination, nodes)


    def build_coord_clause(self, coord_names, coord_values):
        """
           coord_names: names of the coordinates given in values
           coord_values: values for each of those coords
           new_coord_names: what the coord names are for the query.
        """

        clauses = list()
        for coord, value in zip(coord_names, coord_values):
            clauses.append(Clause("=", TableAttribute(coord), value))
        return Clause("and", *clauses)
