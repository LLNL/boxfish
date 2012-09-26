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

    def addStatements(self, *clauses):
        self.clauses.extend(clauses)

    def __str__(self):
        my_str = ""
        if len(self.clauses) >= 2:
            my_str = "( " + str(self.clauses[0]) + " " + self.relation + " "\
                + str(self.clauses[1]) + " "
            prev_clause = self.clauses[1]
            for clause in self.clauses[2:]:
                my_str = my_str + "and " + str(prev_clause) + " " \
                    + self.relation + " " + str(clause) + " "
                prev_clause = clause
            my_str = my_str + ")"
        elif len(self.clauses) == 1:
            my_str = str(self.clauses[0])

        return my_str


    def getAttributes(self):
        """Returns the set of all TableAttributes found in the
           query.
        """
        my_attributes = set()
        for c in self.clauses:
            if isinstance(c, TableAttribute):
                my_attributes.add(c)
            elif isinstance(c, Clause):
                my_attributes = my_attributes.union(c.getAttributes())

        return my_attributes



class TableAttribute(object):
    """Represents a table attribute for the purpose of querying."""

    def __init__(self, name, table = None):
        super(TableAttribute, self).__init__()

        self.name = name
        self.table = table # optionally force particular table

    def __str__(self):
        return str(self.name)
