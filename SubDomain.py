class SubDomain(list):
    """A SubDomain is a list of identifiers of representatives of some
       domain.
    """

    def __init__(self,copy = list()):
       super(SubDomain, self).__init__(copy)

    def __getslice__(self,i,j):
        return self.__class__(list.__getslice__(self,i,j))

    @classmethod
    def subdomain(cls):
        return cls.domain() + "_" + cls.typename()

    @classmethod
    def typename(cls):
        raise NotImplementedError( "Should have implemented this" )

    @classmethod
    def domain(cls):
        raise NotImplementedError( "Should have implemented this" )

    @classmethod
    def subclasses(cls,sub = list()):

        ret = list()

        if len(sub) == 0:
            sub = SubDomain.__subclasses__()

        for s in sub:
            if len(s.__subclasses__()) == 0:
                ret.append(s.subdomain())
            else:
                ret += cls.subclasses(s.__subclasses__())

        return ret

    @classmethod
    def instantiate(cls,subdomain,data=list()):

        if len(cls.__subclasses__()) == 0:
            if cls.subdomain().upper() == subdomain.upper():
                return cls(data)
            else:
                return None
        else:
            for s in cls.__subclasses__():
                result = s.instantiate(subdomain,data)
                if result != None:
                    return result
            return None

class HWSubDomain(SubDomain):

    def __init__(self, elements = list()):
        super(HWSubDomain, self).__init__(elements)

    @classmethod
    def domain(cls):
        return "HW"

class Cores(HWSubDomain):

    def __init__(self, elements = list()):
        super(Cores, self).__init__(elements)

    @classmethod
    def typename(cls):
        return "core"


class Nodes(HWSubDomain):

    def __init__(self, elements = list()):
        super(Nodes, self).__init__(elements)

    @classmethod
    def typename(cls):
        return "node"

class Links(HWSubDomain):

    def __init__(self, elements = list()):
        super(Links, self).__init__(elements)

    @classmethod
    def typename(cls):
        return "link"


class CommSubDomain(SubDomain):

    def __init__(self, elements = list()):
        super(CommSubDomain, self).__init__(elements)

    @classmethod
    def domain(cls):
        return "comm"


class Ranks(CommSubDomain):

    def __init__(self, elements = list()):
        super(Ranks, self).__init__(elements)

    @classmethod
    def typename(cls):
        return "rank"

class Communicators(CommSubDomain):

    def __init__(self, elements = list()):
        super(Communicators, self).__init__(elements)

    @classmethod
    def typename(cls):
        return "communicator"


class AppSubDomain(SubDomain):

    def __init__(self, elements = list()):
        super(AppSubDomain, self).__init__(elements)

    @classmethod
    def domain(cls):
        return "app"

class Patches(AppSubDomain):

    def __init__(self, elements = list()):
        super(Patches, self).__init__(elements)

    @classmethod
    def typename(cls):
        return "patch"


if __name__ == '__main__':

    print "Alive"

    s = SubDomain()
    print s.findSubdomain('comm_rank')
