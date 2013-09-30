import numpy as np
import itertools
import functools
from Query import *

class Table(object):
  """A (B)ox(F)ishTable is a wrapper around a numpy array of records that
  additionally keeps track of its corresponding domain and allows to query
  attributes of this domain and potentially reduce them."""

  # This is the global dictionary to map strings to aggregator functions
  operator = {
    'sum'   : np.sum,
    'mean'  : np.mean,
    'max'   : np.max,
    'min'   : np.min,
    'var'   : np.var,
    'count' : np.size,
    'N.A.'  : lambda x: x,
    }

  relations = {
    '='  : np.ndarray.__eq__,
    '!=' : np.ndarray.__ne__,
    '<'  : np.ndarray.__lt__,
    '<=' : np.ndarray.__le__,
    '>'  : np.ndarray.__gt__,
    '>=' : np.ndarray.__ge__,
  }

  logicals = {
    'and' : np.ndarray.__and__,
    'or'  : np.ndarray.__or__,
  }

  def __init__(self):

    super(Table, self).__init__()


  def fromYAML(self,domain_type,primary_key, filename):
    """Load a table from a yaml file. The domain type provides the context for
       this data, the key idicates the name used for the context in the
       file.
       Parameters:
         domain_type    a SubDomain type or corresponding to the primary key
                        of this table
         primary_key    the string key used in the file for the primary domain
         filename       the name of the yaml file
    """

    import YamlLoader as yl

    self._domainType = domain_type
    self._key = primary_key

    self._data = yl.load_yaml(filename)

  def fromArray(self,domain_type,primary_key, data, names):
    """Load a table from a given numpy array of records. The function will make
       a copy of the given data. The domain type provides the context for the
       attributes and the primary key the corresponding string key used in the
       table.
       Parameters:

         domain_type   a SubDomain type or corresponding to the primary key
                       of this table
         primary_key   the string key used in the file for the primary domain
         data          the numpy array of records
         names         the column names
    """

    if primary_key not in names:
      raise ValueError("This table does not contain the given key.")

    self._domainType = domain_type
    self._key = primary_key

    self._data = np.array([x for x in zip(*data)])
    self._data.dtype.names = names

  def fromRecArray(self,domain_type,primary_key, data):
    """Load a table from a given numpy recarray. The function will make
       a copy of the given data. The domain type provides the context for the
       attributes and the primary key the corresponding string key used in the
       table.
       Parameters:

         domain_type   a SubDomain type or corresponding to the primary key
                       of this table
         primary_key   the string key used in the file for the primary domain
         data          the numpy array of records
    """

    if primary_key not in data.dtype.names:
      raise ValueError("This table does not contain the given key.")

    self._domainType = domain_type
    self._key = primary_key

    self._data = data


  def fromExisting(self, domain_type, primary_key, table):
    """Load a table using a different (potentially) different domain_type and key.
       This function will *not* create a copy of the data but instead create a
       "view" of an existsing table.
       Parameters:

         domain_type   a SubDomain type corresponding to the primary key
                       of this table
         primary_key   the string key used in the file for the primary domain
         table         the reference table
     """

    self._domainType = domain_type
    self._key = primary_key

    self._data = table._data


  def identifiers(self):
    """Return some representation of all the rows in the table.
    """
    return range(len(self._data))


  def attributes(self):
    """Return a list of attributes of this table.
    """

    try:
      self._data
    except:
      return list()

    return self._data.dtype.names

  def domain(self):

    try:
      return self._domainType.domain()
    except:
      raise ValueError("Using an uninitialized table.")

  def subdomain(self):

    try:
      return self._domainType.subdomain()
    except:
      raise ValueError("Using an uninitialized table.")

  def typename(self):

    try:
      return self._domainType.typename()
    except:
      raise ValueError("Using an uninitialized table.")


  def evaluate(self, query):
    """Evalue the query. If the table is not initialized or does not contain the
       attribute asked for in the query a list of 0's will be returned
       Paramters:

         query  the query to evaluate
    """

    result = [0] * len(query.subdomain)

    try:
      self._data
    except:
      return result,False

    if not isinstance(query.subdomain,self._domainType):
      print "Type mismatch. Could not evaluate query."
      return result, False

    if query.attribute not in self.attributes():
      print "Attribute mismatch. Could not find attribute in the table."
      return result, False


    for i,p in enumerate(query.subdomain):
      indices = np.array([],dtype=int)

      try:
        for x in p:
          indices = np.concatenate((indices,np.where(self._data[self._key] == x)[0]))
      except:
        indices = np.where(self._data[self._key] == p)[0]

      if len(indices) == 0:
        result[i] = 0
      else:
        result[i] = self.operator[query.aggregator](self._data[indices][query.attribute])

    return result, True

  def group_attributes_by_attributes(self, identifiers, given_attrs,
    desired_attrs, aggregator):
    """Determine list of desired attributed aggregated by set of given
       attributes. This does an attribute look up/group by type operation.

       Right now we treat these attributes separately, but we could define
       perhaps a list of lists style such that we could aggregate multiple
       columns and produce a single column. 

       Parameters
           identifiers
               list of valid identifiers for this query

           given_attrs
               attributes to group by

           desired_attrs
               attributes to find

           aggregator
               for compressing multiple rows of desired_attrs

       Returns
           group_list
              list of tuples of the groups

           desired_list
              list of desired attribute values
    """
    group_list = list()
    group_dict = dict()

    # For the found values
    desired_list = list()
    for attr in desired_attrs:
      desired_list.append(list())

    # Only go through the numpy table once for this group by
    for row in self._data:
        row_tuple = tuple([row[x] for x in given_attrs])
        if row_tuple in group_dict:
            for i, attr in enumerate(desired_attrs):
                group_dict[row_tuple][i].append(row[attr])
        else:
            group_dict[row_tuple] = list()
            for i, attr in enumerate(desired_attrs):
                group_dict[row_tuple].append([row[attr]])

    for group_tuple in group_dict:
        if len(group_dict[group_tuple][0]) > 0:
            for i, attr_list in enumerate(desired_list):
                aggr_values = np.array(self.operator[aggregator](
                  group_dict[group_tuple][i])).flatten()
                for i in aggr_values:
                    attr_list.append(i)
                    group_list.append(group_tuple)

    return group_list, desired_list

  def attributes_by_identifiers(self, identifiers, attributes, unique = True):
    """Get list of all attributes from a set of identifiers. Not sure
       this is a good idea.
    """
    attr_list = list()
    if unique:
      for attr in attributes:
        attr_list.append(np.unique(self._data[identifiers][attr]))
    else:
      for attr in attributes:
        attr_list.append(list(self._data[identifiers][attr]))

    return attr_list


  def attributes_by_conditions(self, identifiers, desired_attrs, conditions,
    unique = True):
    """Get all rows of the desired attributes where the conditions
       are met. Conditions is an object of class Clause where each
       subclause should apply directly to this table.
    """
    where_clause = self.build_where_clause(conditions, identifiers)
    if where_clause is None:
        new_identifiers = identifiers
    else:
        indices = np.where(where_clause)
        new_identifiers = [identifiers[x] for x in indices[0]]

    attr_list = list()
    if unique:
      for attr in desired_attrs:
        attr_list.append(np.unique(self._data[new_identifiers][attr]))
    else:
      for attr in desired_attrs:
        attr_list.append(list(self._data[new_identifiers][attr]))

    return attr_list


  def subset_by_key(self, identifiers, subdomain):
    """Determine the subset of valid identifiers based on some query given the
       initial set of identifiers.

       identifiers = initial set of identifiers
       subdomain = subdomain containing list of keys we are subsetting by

       This could be done with subset_by_conditions but we special-case
       this for convenience since we will be using this a lot when we've
       mapped outside data onto the primary key and are performing some
       operation on it in a filter.
    """
    if len(subdomain) == 0:
      return []
    subset_filter = True
    for index in subdomain:
      subset_filter = subset_filter | \
        (self._data[self._key][identifiers] == index)
    indices = np.where(subset_filter)
    return [identifiers[x] for x in indices[0]]


  def subset_by_conditions(self, identifiers, conditions):
    """Determine the subset of valid identifiers based on some conditions
       within this table and an initial set of identifiers.

       identifiers = initial set of identifiers of rows.
       conditions = an object of class Clause that should contain only
       Clauses that can be evaluated on this table.
    """
    where_clause = self.build_where_clause(conditions, identifiers)
    if where_clause is None:
        return identifiers

    indices = np.where(where_clause)
    return [identifiers[x] for x in indices[0]]


  def subset_by_outside_values(self, identifiers, attributes,
    relation, outside_list, aggregator = 'sum', table_first = True):
    # TODO: turn the default values into kwargs and extend so that
    # there may be conditions or extra columns or something... or 
    # never use this query since it was created for a now defunct
    # scheme of doing queries
    """Determine the subset of valid identifiers based on a relation
       with given outside values.

       identifiers = iniital set of identifiers on rows
       attributes = list of attributes of this table for comparison
       relation = comparison relation with outside values
       outside = list of (id, value) tuples where id maps to this table's id
       aggregator = aggregator for the attributes if need be
       table_first = this table is first: attribute relation outside_list
                     rather than outside_list relation attribute
    """

    if len(attributes) == 1: # We can build a simple set of queries out of this
        conditions = list()
        for table_id, value in outside_list:
            c1 = Clause('=', TableAttribute(self._key), table_id)
            if table_first:
                c2 = Clause(relation, TableAttribute(attributes[0]), value)
            else:
                c2 = Clause(relation, value, TableAttribute(attributes[0]))
            conditions.append(Clause('and', c1, c2))

        where_clause = self.build_where_clause(Clause('or', *conditions))
        if where_clause is None:
            return identifiers

        indices = np.where(where_clause)
        return [identifiers[x] for x in indices[0]]
    else:
        aggregation_operator = self.operator[aggregator]
        if relation in self.relations:
            relation_operator = self.relations[relation]
        elif relation in self.logicals:
            relation_operator = self.logicals[relation]
        else:
            raise ValueError("Unrecognized relation %s in clause" % relation)

        indices = set()
        for i, row in enumerate(self._data[identifiers]):
            attribute_list = list()
            for attribute in attributes:
                attribute_list.append(row[attribute])
            attribute_value = aggregation_operator(np.array(attribute_list))
            for table_id, value in outside_list:
                if table_id == row[self._key] \
                    and ((table_first
                    and relation_operator(attribute_value, value))
                    or (not table_first
                    and relation_operator(value, attribute_value))):
                    indices.add(i)

        indices = list(indices)
        return [identifiers[x] for x in indices]




  def build_where_clause(self, condition, identifiers):

    operator = self.get_operator(condition.relation)

    if len(condition.clauses) < 1:
      raise ValueError("No clauses in given condition.")

    where_clause = None
    if isinstance(condition.clauses[0], Clause): # These are clauses, recurse
        for c in condition.clauses:
            if where_clause is None:
                where_clause = self.build_where_clause(c, identifiers)
            else:
                child_clause = self.build_where_clause(c, identifiers)
                if child_clause is not None:
                    where_clause = operator(where_clause, child_clause)

    elif ((isinstance(condition.clauses[0], TableAttribute) \
        and condition.clauses[0].name in self.attributes()) \
        or (isinstance(condition.clauses[1], TableAttribute)
        and condition.clauses[1].name in self.attributes())):
        # This is a simple clause that we can just build 

        if isinstance(condition.clauses[0], TableAttribute):
            attribute = condition.clauses[0]
            value = condition.clauses[1]
        else:
            attribute = condition.clauses[1]
            value = condition.clauses[0]

        np_type = self._data[attribute.name].dtype
        value = self.numpy_cast(value, np_type, attribute.name)

        if isinstance(condition.clauses[0], TableAttribute):
            return operator(self._data[attribute.name][identifiers], value)
        else:
            return operator(value, self._data[attribute.name][identifiers])


    return where_clause

  def get_operator(self, relation):
    if relation in self.relations:
      return self.relations[relation]
    elif relation in self.logicals:
      return self.logicals[relation]
    else:
      raise ValueError("Unrecognized relation in clause.")

  def numpy_cast(self, value, np_type, name):

      try:
          caster = np.empty((1), dtype=[('cast', np_type)])
          caster[0]['cast'] = value
          return caster[0]['cast']
      except:
          raise ValueError("Incompatible value: %s for attribute %s",
              value, name)



if __name__ == '__main__':
  from YamlLoader import *
  from DataObject import *
  #from Query import *

  data = load_yaml("bgpcounter_data.yaml")

  table = Table()
  table.fromArray(Ranks,'mpirank',data)

  r = Ranks([[0,1,2],[1,2,3],2])
  #q = Query(r,'x','max')
  #print table.reduce(q)

