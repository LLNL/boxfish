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



class Identity(Projection):
  """A default identify mapping, for example, for the standard MPI rank <-> core
     mapping
  """

  def __init__(self,source = "undefined", destination = "undefined"):

    Projection.__init__(self,source,destination)

  def project(self,subdomain,destination):

    result = SubDomain().instantiate(destination,subdomain)
    return result

  
