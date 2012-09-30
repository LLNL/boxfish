from SubDomain import *

class Clause(object):
    """This represents a clause for query. Examples:

       Clause('and', c1, c2, c3, c4) -> ((c1 and c2) and c3) and c4
       Clause('<', TableAttribute('x'), 4) -> table.x < 4
       Clause('=', TableAttribute('name'), 'ycomm') -> table.name == 'ycomm'
    """

    def __init__(self, relation, *clauses):
        """Construct a Clause with the given relation between pairs from
           the given clauses. Here clauses may be Clause objects,
           TableAttribute objects, or scalars.
        """
        super(Clause, self).__init__()

        self.relation = relation
        self.clauses = clauses

    def addStatements(self, *clauses):
        """Add more Clauses or scalars to existing clauses list."""
        self.clauses.extend(clauses)

    def __str__(self):
        """Represent this Clause as a string."""
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
        """Returns the set of all TableAttributes names found anywhere
           in this Clause object.
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
        """Construct a TableAttribute object with the given name. Optionally
           may be associated with a specific TableItem.
        """
        super(TableAttribute, self).__init__()

        self.name = name
        self.table = table # optionally force particular table

    def __str__(self):
        """Returns the name associated with this TableAttribute."""
        if self.table is None:
            return str(self.name)
        else:
            return str(self.table.name) + "." + str(self.name)
