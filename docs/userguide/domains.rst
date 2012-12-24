.. _domains-label:

Domains
=======

Domains are the contexts in which performance data is collected. Entities in
these domains are logical (and sometimes physical) objects with which
individual measurements, known as attributes, are associated. Boxfish can
project attribute data from one entity in one domain to another entity in
potentially another domain. In order to perform these operations, projections
are defined in the run meta-file and entity and domain information is attached
to each data file. The built-in domains and entities are described here and their
identifiers, used in the input files, are listed as well.

============= ========== ===========================================
   Domain     Identifier                Description
============= ========== ===========================================
  Hardware        HW      The physical system. 
Communication    COMM     Messaging between processes.
 Application      APP     The space of the application, such as grid
                          cells in physical space.
============= ========== ===========================================




============= ============ ============== =================================
   Entity      Identifier     Domain                 Description
============= ============ ============== =================================
    Node          NODE       Hardware      Hardware node.
    Link          LINK       Hardware      Network link.
    Rank          RANK      Communication  Single process.
Communicator  COMMUNICATOR  Communication  Communication group of processes.
    Patch         PATCH      Application   Volume of physical space.
============= ============ ============== =================================

Domains and entities can also be defined by user contributed modules. Check
their documentation for the appropriate identifier to use.


