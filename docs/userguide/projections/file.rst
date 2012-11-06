File Projection
===============

In the file projection, the mapping between the IDs of two entities is
described by a file. The file should be in the same format as a data table
file. The file will be two columns, one for each entity, named with the token
described in ``field``. Each row in the file will define a mapping between a
single ID of each entity. As such, some IDs may appear in multiple rows if
they map to multiple IDs of the other entity.

The format for adding such a projection adds the ``filename`` field which
contains the relative path to the file where the projection is defined.

.. code-block:: yaml

  ---
  filetype: projection
  type: file
  filename: map.yaml
  - { domain: HW, type: NODE, field: nodeid }
  - { domain: COMM, type: RANK, field: mpirank }
  flags: 0
  ---
