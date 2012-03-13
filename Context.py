from SubDomain import *
from Projection import *

class Context(object):

  def __init__(self):

    object.__init__(self)

    self.relations = dict()


  def addProjection(self,projection):

    self.relations[(projection.source,projection.destination)] = projection
    self.relations[(projection.destination,projection.source)] = projection


  def relates(self,source,destination):

    if isinstance(source,str) and isinstance(destination,str):
      return (source,destination) in self.relations
    elif isinstance(source,SubDomain) and isinstance(destination,str):
      return (source.subdomain(),destination) in self.relations
    elif isinstance(source,str) and isinstance(destination,SubDomain):
      return (source,destination.subdomain()) in self.relations
    else:
      return (source.subdomain(),destination.subdomain()) in self.relations
     


  def project(self,subdomain,destination):

    if not (subdomain.subdomain(),destination) in self.relations:
      raise ValueError("%s and %s are not related in this context." % (subdomain.subdomain(),destination))

    projection = self.relations[(subdomain.subdomain(),destination)]

    return projection.project(subdomain,destination)
    
