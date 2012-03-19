import numpy as np

class BFTable(object):
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

  def __init__(self):

    object.__init__(self)


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

  def fromArray(self,domain_type,primary_key, data):
    """Load a table from a given numpy array of records. The function will make
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

    self._data = np.array(data)


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

  def attributes(self):
    """Return a set of attributes of this table. Note that the attributes do
    *not* contain the primary key which is considered special.
    """
    
    try:
      self._data
    except:
      return set()

    result = set()
    for d in self._data.dtype.names:
      if d != self._key:
        result.add(d)

    return result
      
  def domain(self):

    try:
      return self._domainType().domain()
    except:
      raise ValueError("Using an uninitialized table.")

  def subdomain(self):

    try:
      return self._domainType().subdomain()
    except:
      raise ValueError("Using an uninitialized table.")

  def typename(self):

    try:
      return self._domainType().typename()
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


if __name__ == '__main__':
  from YamlLoader import *
  from DataObject import *
  from Query import *

  data = load_yaml("bgpcounter_data.yaml")

  table = BFTable()
  table.fromArray(Ranks,'mpirank',data)

  r = Ranks([[0,1,2],[1,2,3],2])
  q = Query(r,'x','max')
  print table.reduce(q)

      
