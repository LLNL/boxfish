from BFTable import *

class DataStore(object):
  """A data store is a collection of tables keyed by subdomain. It is designed
  to keep a variable number of tables (or other look-up structures) and answer
  simple reduce-queries"""

  def __init__(self):
        
    object.__init__(self)

    # A dictionary of lists of tables for each subdomain
    self._tables = dict()
    
  def addTable(self, table):

    if table.subdomain() not in self._tables:
      self._tables[table.subdomain()] = [table]
    else:
      self._tables[table.subdomain()] = self._tables[table.subdomain()].append(table)

  def attributes(self):
    """Return a hierarchical dictionary of dictionaries storing which attributes
       are available for which domain / context. The dictionary will have the
       following structure:
       { domain_name_0 : { subdomain_0 : set(attribute_0, ..., attribute_n),
                               :
                               :
                           subdomain_m : set(attribute_0, ..., attribute_n) }
               :
               :
         domain_name_k : { subdomain_0 : set(attribute_0, ..., attribute_n),
                               :
                               :
                           subdomain_m : set(attribute_0, ..., attribute_n) }}
    """

    result = dict()
    for subtable in self._tables.itervalues():
      for table in subtable:
        
        if table.domain() not in result:
          result[table.domain()] = dict()

        if table.subdomain() not in result[table.domain()]:
          result[table.domain()][table.subdomain()] = table.attributes()
        else:
          result[table.domain()][table.subdomain()].add(table.attributes())
      
    return result

  def evaluate(self, query):
    """Try to evaluate the given query. If no table can be found to satisfy the
       query a list of 0's will be returned
    """

    # The reference to a table containing the attribute
    data = None

    # Find a table which contains this attribute. Is there a case in which
    # multiple tables contain the same attribute ? Shouldn't they be the same ?
    # Right now we pick the first one we find
    for t in self._tables[query.subdomain.subdomain()]:
      if query.attribute in t.attributes():
        data = t;

    if not data:
      print "Attribute mismatch: Could not find table with the given attribute for the the subdomain"
      return [0] * len(query.subdomain), False

    return data.evaluate(query)
            
        
if __name__ == '__main__':
  from YamlLoader import *
  from DataObject import *
  from Query import *

  data = load_yaml("bgpcounter_data.yaml")

  # Create a first table for mpiranks 
  table = BFTable()
  table.fromArray(Ranks,'mpirank',data)

  # for testing purposes create another view of the table assuming timesteps
  # actually indicates core id
  table2 = BFTable()
  table2.fromExisting(Cores,'timesteps',table)
  
  store = DataStore()
  store.addTable(table)
  store.addTable(table2)
    
  print store.attributes(), "\n\n"

  # Try out a simple query. First we create a general multi-valued subdomain of ranks
  r = Ranks(((0,1,2), (3,4,5), 6))

  # Then make it into a query for the mean of 'stores'
  q = Query(r,'stores','mean')

  # Now we evaluate query
  print store.evaluate(q)
  
