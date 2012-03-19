from DataStore import *
from Context import *
from Query import *

class QueryEngine(object):

  def __init__(self):

    object.__init__(self)

    self.dataStore = DataStore()
    self.attributes = self.dataStore.attributes()

  def attributes(self):
    """Return a hierarchical dictionary of available attributes. See the
       DataStore for more details on the format.
    """

    return self.attributes

  
  def addTable(self,table):
    """Add the given table to the internal data store."""

    self.dataStore.addTable(table)
    self.attributes = self.dataStore.attributes()


  def addProjection(self,projection):
    """Add the given projection to the internal context map"""

    self.context.addProjection(projection)

  def isSimple(self,query):

    if query.subdomain.domain() in self.attributes:
      if query.subdomain.subdomain() in self.attributes[query.subdomain.domain()]:
        if query.attribute in self.attributes[query.subdomain.domain()][query.subdomain.subdomain()]:
          return True
        
    return False

  def evaluate(self, query, context = Context()):

    # If this query can be evaluated without a projection
    if self.isSimple(query):
      return self.dataStore.evaluate(query)

    # Otherwise we will have to find a projection which will allow us to
    # evaluate the query

    for domain in self.attributes:
      for subdomain in self.attributes[domain]:

        # If the data store contains the desired attribute and the context
        # relates thecorresponding subdomain with the given one we can satisfy
        # the query. NOTE THAT:
        # 1) There might be more than one map available and we just take the first one
        # 2) We construct the subdomain name by hardcoding the same rule used by the
        #    the SubDomain class. is this gets changed this code has to change as well
        if (query.attribute in self.attributes[domain][subdomain] and
            context.relates(query.subdomain.subdomain(),subdomain)) :

            mapped = context.project(query.subdomain,subdomain)

            return self.dataStore.evaluate(Query(mapped,query.attribute,query.aggregator))
            
    # If we get here we could not find a way to satisfy the query
    print "Warning: Could not evalute the query: ", query
    return [0] * len(query.subdomain), False
  

  def getSubDomain(self,name):
    """Return the complete subdomain corresponding to the given name"""

    return self.dataStore.getSubDomain(name)
