Node-Link Projection
====================

The node-link projection maps between nodes and links in the system hardware
based on their specified coordinates. This requires that coordinates for nodes
and links be defined as in the Torus modules.

The format for adding such a projection adds the ``node_policy`` and
``link_policy`` fields which define the mapping behavior of nodes to links and
links to nodes respectively. The valid values of these fields are ``Source``,
``Destination`` and ``Both``. ``Source`` indicates that nodes will be mapped
to links for which they are the source or links will be mapped to their source
node. ``Destination`` indicates that nodes will be mapped to links for which
they are the destination or links will be mapped to their destination node.
``Both`` indicates that nodes will be mapped to links for which they are
source or destination and links will be mapped to both their source and
destination node. 

.. code-block:: yaml

  ---
  filetype: projection
  type: node link
  node_policy: Source
  link_policy: Source
  - { domain: HW, type: NODE, field: nodeid }
  - { domain: COMM, type: RANK, field: mpirank }
  flags: 0
  ---
