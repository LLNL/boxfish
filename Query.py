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


class Clause(object):
    """This represents a clause for a logicals. Examples:

       Clause('and', c1, c2, c3, c4) -> ((c1 and c2) and c3) and c4
       Clause('<', TableAttribute('x'), 4) -> table.x < 4
       Clause('=', TableAttribute('name'), 'ycomm') -> table.name == 'ycomm'
    """

    def __init__(self, relation, *clauses):
        super(Clause, self).__init__()

        self.relation = relation
        self.clauses = clauses

    def addStatements(*clauses):
        self.clauses.extend(clauses)


class TableAttribute(object):
    """Represents a table attribute for the purpose of querying."""

    def __init__(self, name):
        super(TableAttribute, self).__init__()

        self.name = name
