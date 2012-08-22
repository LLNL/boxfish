from SubDomain import *

class Query(object):
  """A query encapsulates a query for data encoded as the subdomain, and
     attribute name, and an optional aggregator
  """

  def __init__(self, sub = SubDomain(), attribute = "Undefined", aggregator = "mean"):
    object.__init__(self)

    if not issubclass(sub.__class__,SubDomain):
      raise ValueError("The first argument of a query must be a subdomain.")

    self.subdomain = sub
    self.attribute = attribute
    self.aggregator = aggregator

  def __str__(self):

    return self.subdomain.subdomain() + ": " + self.subdomain.__str__() + " attr: \"%s\", agg: \"%s\"" % (self.attribute,self.aggregator)

