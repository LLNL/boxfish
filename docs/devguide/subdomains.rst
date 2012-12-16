Creating New Domains and Subdomains
===================================
In Boxfish, a domain is a logical area from which data may be collected.
Examples include communication, hardware, and application. A subdomain is a
logical entity within that domain. Examples include MPI ranks and
communicators in the communication domain; nodes, links, and processors in the
hardware domain; and cells in the application domain. These lists are not
comprehensive, so new domains and subdomains may be created.

Both domains and subdomains are subclasses of ``Subdomain``. A domain must
implement the class method ``domain`` and a subdomain must implement both
``domain`` and ``typename``. Current Boxfish practice is to have the subdomain
subclass its domain and then only implement ``typename``. Both ``domain`` and
``typename`` return a unique string for the class. This string will be used to
specify subdomains in inputs files. The example below shows the existing code
for the hardware links.::

  class HWSubDomain(SubDomain):

    def __init__(self, elements = list()):
      super(HWSubDomain, self).__init__(elements)

    @classmethod
    def domain(cls):
      return "HW"

  class Links(HWSubDomain):

    def __init__(self, elements = list()):
      super(Links, self).__init__(elements)

    @classmethod
    def typename(cls):
      return "link"

