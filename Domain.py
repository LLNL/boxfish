
class Domain(object):

  def __init__(self):
        
    object.__init__()
    
    self._tables = dict()
    
    
  def addTable(self, subdomain, table):

    if subdomain.name() in self._tables:
      self._tables[subdomain.name()] = (table)
    else:
      self._tables[subdomain.name()] = self._tables[subdomain.name()].append(table)

  def evaluate(self, subdomain, attribute, aggregate):

    # The reference to a table containing the attribute
    data = None
    
    # Find a table which contains this attribute. Is there a case in which
    # multiple tables contain the same attribute ? Shouldn't they be the same ?
    # Right now we pick the first one we find
    for t in self._table(subdomain.name()]:
      if attribute in t:
        data = t;

    if not data:
      raise ValueError("Could not find attribute %s of %s in any tables I have" % (attribute, aggregate))

    return data.reduce(subdomain,attribute,aggregator)
            
            
        
    
    

    
