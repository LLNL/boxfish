#
# A subdomain is a list of identifiers (usually indices) defining a list of
# points in some domain
#


class SubDomain(list):

    def __init__(self,copy = list()):
       list.__init__(self,copy)

    def __getslice__(self,i,j):
        return self.__class__(list.__getslice__(self,i,j))

    def subdomain(self):
        return self.domain() + "_" + self.typename()

    def typename(self):
        raise NotImplementedError( "Should have implemented this" )

    def domain(self):
        raise NotImplementedError( "Should have implemented this" )

    def subclasses(self,sub = list()):

        ret = list()

        if len(sub) == 0:
            sub = SubDomain.__subclasses__()

        for s in sub:
            if len(s.__subclasses__()) == 0:
                ret.append(s().subdomain())
            else:
                ret += self.subclasses(s.__subclasses__())

        return ret

    # For getting types from strings like during input file reading.
    def findSubdomain(self, type_string, sub = list()):
        type_string = type_string.lower()
        ret = None

        if len(sub) == 0:
            sub = SubDomain.__subclasses__()

        for s in sub:
            if len(s.__subclasses__()) == 0:
                if type_string == s().subdomain().lower():
                    return s()
            else:
                found = self.findSubdomain(type_string, s.__subclasses__())
                if found is not None:
                    ret = found

        return ret

    def instantiate(self,subdomain,data=list()):

        if len(self.__class__.__subclasses__()) == 0:
            if self.subdomain() == subdomain:
                return self.__class__(data)
            else:
                return None
        else:
            for s in self.__class__.__subclasses__():
                result = s().instantiate(subdomain,data)
                if result != None:
                    return result
            return None

class HWSubDomain(SubDomain):

    def __init__(self, elements = list()):

        SubDomain.__init__(self,elements)

    def domain(self):
        return "HW"

class Cores(HWSubDomain):

    def __init__(self, elements = list()):
        HWSubDomain.__init__(self,elements)

    def typename(self):
        return "core"


class Nodes(HWSubDomain):

    def __init__(self, elements = list()):
        HWSubDomain.__init__(self,elements)

    def typename(self):
        return "node"

class Links(HWSubDomain):

    def __init__(self, elements = list()):
        HWSubDomain.__init__(self, elements)

    def typename(self):
        return "link"


class CommSubDomain(SubDomain):

    def __init__(self, elements = list()):

        SubDomain.__init__(self,elements)

    def domain(self):
        return "comm"


class Ranks(CommSubDomain):

    def __init__(self, elements = list()):
        CommSubDomain.__init__(self,elements)

    def typename(self):
        return "rank"

class Communicators(CommSubDomain):

    def __init__(self, elements = list()):
        CommSubDomain.__init__(self,elements)

    def typename(self):
        return "communicator"




if __name__ == '__main__':

    print "Alive"

    s = SubDomain()
    print s.findSubdomain('comm_rank')
