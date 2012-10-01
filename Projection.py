from SubDomain import *
from Query import *

def InputFileKey(input_file_key, enabled = True):
    """Decorator associates the key from a Boxfish meta file with a type
       of projection.

       input_file_key
          The name that can be used to instantiate from file
    """
    def input_file_key_inner(cls):
        cls.input_file_key = input_file_key
        return cls
    return input_file_key_inner


class Projection(object):
    """Projections relate IDs of one domain to IDs of another."""

    def __init__(self,source = "undefined", destination = "undefined",
        **kwargs):
        """Construct a Projection between domains source and destination.
        """
        super(Projection, self).__init__()

        if isinstance(source,str):
            self.source = source
        elif isinstance(source,SubDomain):
            self.source = source.subdomain()
        else:
            raise ValueError("A projection can only be initialized with "
                + "names or SubDomains")

        if isinstance(destination,str):
            self.destination = destination
        elif isinstance(destination,SubDomain):
            self.destination = destination.subdomain()
        else:
            raise ValueError("A projection can only be initialized with "
                + "names or SubDomains")


    def relates(self,source,destination):
        """Returns True if this Projection is between the two given
           domains.
        """
        return (((self.source == source) and
            (self.destination == destination)) or
            ((self.source == destination) and (self.destination == source)))


    def project(self, subdomain, destination):
        """Take the IDs in the given subdomain and returns a SubDomain of
           those IDs as projected into the given destination.
        """
        raise NotImplementedError("Cannot perform projection.")

#  def make_projection_dict(self, subdomain, destination):
#    """Makes a dict from each domain_id in the subdomain.
#       Override to make this less slow.
#    """
#
#    projection_dict = dict()
#    for domain_id in subdomain:
#      projection_dict[domain_id] = self.project(
#          SubDomain.instantiate(subdomain.subdomain(), [domain_id]),
#          destination)
#
#    return projection_dict

    def source_ids(self):
        """Returns all of the ids associated with the source subdomain.
           If unable to calculate these ids, return None.

           This is for making tables out of the subdomain.
        """
        return None

    def destination_ids(self):
        """Returns all of the ids associated with the destination subdomain.
           If unable to calculate these ids, return None.

           This is for making tables out of the subdomain.
        """
        return None

    @classmethod
    def instantiate(cls, key, source, destination, **kwargs):
        """Create a Projection between source and destination where
           the Projection is associated with the given key. The **kwargs
           are any that may be required by the Projection.
        """
        if hasattr(cls, 'input_file_key') and \
            cls.input_file_key.upper() == key.upper():
            return cls(source, destination, **kwargs)
        else:
            for s in cls.__subclasses__():
                result = s.instantiate(key, source, destination, **kwargs)
                if result is not None:
                    return result
            return None


@InputFileKey("identity")
class IdentityProjection(Projection):
    """A default identify mapping, for example, for the standard MPI
       rank <-> core mapping
    """

    def __init__(self,source = "undefined", destination = "undefined",
        **kwargs):
        """Construct an IdentityProjection."""
        super(IdentityProjection, self).__init__(source,destination,**kwargs)

    def project(self,subdomain,destination):
        """Projects the subdomain onto the destination by returning the list
           of IDs found in subdomain packaged in a SubDomain of type
           destination.
        """
        result = SubDomain.instantiate(destination,subdomain)
        return result


@InputFileKey("composition")
class CompositionProjection(Projection):
    """CompositionProjection combines a list of Projections that provide
       a path between source and destination SubDomains.
    """

    def __init__(self,source="undefined", destination="undefined", **kwargs):
        """Construct a CompositionProjection between source and destination.

           Required keyword argument:

           projection_list
               List of (Projection, source, destination) where the first
               entry's source is CompositionProjection's source and the
               last entry's destination is CompositionProjection's
               destination and in between each source is the destination of
               the preceeding tuple.
        """
        super(CompositionProjection, self).__init__(source,destination,
            **kwargs)

        if kwargs:
            if 'projection_list' not in kwargs:
                raise ValueError("CompositionProjection constructor requires "
                    + "projection_list.")
            self._projection_list = kwargs["projection_list"]


    def project(self, subdomain, destination):
        """Convert the IDs in subdomain into a SubDomain of type destination.
        """
        sub = subdomain
        if destination == self.destination:
            for proj, src, dest in self._projection_list:
                sub = proj.project(sub, dest)
        else:
            reverse_list = self._projection_list[:]
            reverse_list.reverse()
            for proj, src, dest in reverse_list:
                sub = proj.project(sub, src)

        return sub

    def source_ids(self):
        """Return a list of all known IDs from the source SubDomain."""
        return self._projection_list[0].source_ids()

    def destination_ids(self):
        """Return a list of all known IDs from the destination Subdomain."""
        return self._projection_list[-1].destination_ids()


@InputFileKey("file")
class TableProjection(Projection):
    """Mapping defined by Table object."""

    def __init__(self, source = "undefined", destination = "undefined",
        **kwargs):
        """Construct a TableProjection between source and destination.

           Required keyword argument:

           table
               Table object defining projection.

           source_key
               The column name of the source IDs in the table

           destination_key
               The column name of the destination IDs in the table
        """
        super(TableProjection, self).__init__(source, destination, **kwargs)

        if kwargs:
            if 'source_key' not in kwargs or 'destination_key' not in kwargs\
                or 'table' not in kwargs:
                raise ValueError("TableProjection constructor requires "
                    + "source_key, destination_key, and table.")
            self._table = kwargs["table"]
            self._source_key = kwargs["source_key"]
            self._destination_key = kwargs["destination_key"]

            self._source_dict = dict()
            self._destination_dict = dict()
            key_lists = self._table.attributes_by_identifiers(
                self._table.identifiers(),
                [self._source_key, self._destination_key],
                unique = False)
            for source, destination in zip(*key_lists):
                if source in self._source_dict:
                    self._source_dict[source].append(destination)
                else:
                    self._source_dict[source] = [destination]

                if destination in self._destination_dict:
                    self._destination_dict[destination].append(source)
                else:
                    self._destination_dict[destination] = [source]


  #def make_projection_dict(self, subdomain, destination):
  #    if destination == self.destination:
          #return self._source_dict
  #        return { key : val for key, val in self._source_dict.iteritems()
  #            if key in subdomain }
  #    else:
          #return self._destination_dict
  #        return { key : val for key, val in self._destination_dict.iteritems()
  #            if key in subdomain }


    def project(self, subdomain, destination):
        """Convert the IDs in subdomain into a SubDomain of type destination.
        """
        keys = list()
        if destination == self.destination:
            for domain_id in subdomain:
                keys.extend(self._source_dict[domain_id])
        else:
            for domain_id in subdomain:
                keys.extend(self._destination_dict[domain_id])

        return SubDomain.instantiate(destination, list(set(keys)))

    def source_ids(self):
        """Return a list of all known IDs from the source SubDomain."""
        return [x for x in self._source_dict]

    def destination_ids(self):
        """Return a list of all known IDs from the destination Subdomain."""
        return [x for x in self._destination_dict]



@InputFileKey("node link")
class NodeLinkProjection(Projection):
    """Common Node-Link mappings, defined by policy:

       Source: Links mapped to their source node. Nodes mapped to all links
               emanating from them.

       Destination: Links mapped to their destination node. Nodes mapped to
                    link ends.

       Both: Double counts. Links mapped to both source and destination
             nodes. Nodes mapped onto all links they are incident upon.


       Note: 'node_policy' cover how nodes map onto links; 'link_policy'
       covers how links map onto nodes.

       This class assumes that there will be a table with coordinates for
       the nodes and coordinates of the source and destination for links.
       The projection is based upon these coordinates.
    """
    def __init__(self, source = "undefined", destination = "undefined",
        **kwargs):
        """Construct a NodeLink Projection.

           Required keyword arguments:

           run
                RunItem governing this projection

           node_policy
                How nodes map onto links

           link_policy
                How links map onto nodes

            Policies: 'Source', 'Destination', and 'Both'

            Source: Links mapped to their source node. Nodes mapped to all
                    links emanating from them.

            Destination: Links mapped to their destination node. Nodes
                         mapped to link ends.

            Both: Double counts. Links mapped to both source and
                  destination nodes. Nodes mapped onto all links they are
                  incident upon.
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

            self.source_table = \
                self.run.getTable(hardware_info["coords_table"])
            self.destination_table = self.run.getTable(
                hardware_info["link_coords_table"])

            self.coords = hardware_info["coords"]
            self.source_coords = [hardware_info["source_coords"][coord]
                for coord in self.coords]
            self.destination_coords \
                = [hardware_info["destination_coords"][coord]
                for coord in self.coords]


            # Nodes and Links are a join on coordinates. We're going to
            # make coordinate dictionaries so we can use them later
            # to build node-link dictionaries based on coords and policies
            self.node_coord_dict = dict()
            self.coord_node_dict = dict()
            self.link_coord_dict_source = dict()
            self.link_coord_dict_destination = dict()
            self.coord_link_dict_source = dict()
            self.coord_link_dict_destination = dict()
            # We can use a group by here because we know there is one
            # node per coordinate
            node_coords, node_ids \
                = self.source_table._table.group_attributes_by_attributes(
                self.source_table._table.identifiers(), self.coords,
                [self.source_table['field']], 'mean')
            for node_coord, node_id in zip(node_coords, node_ids[0]):
                self.node_coord_dict[int(node_id)] = node_coord
                self.coord_node_dict[node_coord] = int(node_id)

            # For links, we also do a group-by, but on both the source
            # and destination coordinates
            coord_len = len(self.coords)
            source_index = coord_len
            destination_index = source_index + coord_len
            #link_coord_names = [self.destination_table['field']]
            link_coord_names = list()
            link_coord_names.extend(self.source_coords)
            link_coord_names.extend(self.destination_coords)
            link_coords, link_ids \
                = self.destination_table._table.group_attributes_by_attributes(
                self.destination_table._table.identifiers(),
                link_coord_names, [self.destination_table['field']], 'mean')
            for link_id, link_tuple in zip(link_ids[0], link_coords):
                link_id = int(link_id)
                source = link_tuple[0:source_index]
                destination = link_tuple[source_index:destination_index]
                if link_id not in self.link_coord_dict_source:
                    self.link_coord_dict_source[link_id] = source
                if link_id not in self.link_coord_dict_destination:
                    self.link_coord_dict_destination[link_id] = destination

                if source not in self.coord_link_dict_source:
                    self.coord_link_dict_source[source] = [link_id]
                elif link_id not in self.coord_link_dict_source[source]:
                    self.coord_link_dict_source[source].append(link_id)
                if destination not in self.coord_link_dict_destination:
                    self.coord_link_dict_destination[destination] = [link_id]
                elif link_id \
                    not in self.coord_link_dict_destination[destination]:
                    self.coord_link_dict_destination[destination].append(
                        link_id)


            self.make_dicts()


    def make_dicts(self):
        """Creates dicts that map node IDs to lists of link IDs and vice
           versa. These are created based on node_policy and link_policy
           and used to peform the projections.
        """
        self.node_dict = dict()
        self.link_dict = dict()
        for node_id in self.node_coord_dict:
            link_list = list()
            if self.node_policy == 'Source' or self.node_policy == 'Both':
                link_list.extend(self.coord_link_dict_source[
                    self.node_coord_dict[node_id]])
            if self.node_policy == 'Destination' or self.node_policy == 'Both':
                link_list.extend(self.coord_link_dict_destination[
                    self.node_coord_dict[node_id]])

            for link_id in link_list:
                if link_id not in self.link_dict:
                    self.link_dict[link_id] = [node_id]
                elif node_id not in self.link_dict[link_id]:
                    self.link_dict[link_id].append(node_id)

            self.node_dict[node_id] = link_list


#    def make_projection_dict(self, subdomain, destination):
#        if destination == self.destination:
#            return { key : val for key, val in self.node_dict.iteritems()
#                if key in subdomain }
#        else:
#            return { key : val for key, val in self.link_dict.iteritems()
#                if key in subdomain }


    def project(self, subdomain, destination):
        """Convert the IDs in subdomain into a SubDomain of type destination.
        """
        keys = list()
        if destination == self.destination: # Nodes -> Links
            for node_id in subdomain:
                keys.extend(self.node_dict[node_id])
        else:
            for link_id in subdomain:
                keys.extend(self.link_dict[link_id])

        return SubDomain.instantiate(destination, list(set(keys)))


    def update_policies(self, node_policy, link_policy):
        """Changes the node and link policies to the ones given and re-makes
           the projection dicts accordingly.
        """
        self.node_policy = node_policy
        self.link_policy = link_policy

        self.makedicts()

    def source_ids(self):
        """Return a list of all known IDs from the source SubDomain."""
        return [x for x in self.node_dict]

    def destination_ids(self):
        """Return a list of all known IDs from the destination Subdomain."""
        return [x for x in self.link_dict]
