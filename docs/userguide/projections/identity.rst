Identity Projection
===================

The identity projection is used when the IDs of one entity match the IDs of
another. Depending on how nodes are numbered and MPI processes are mapped,
this might be the projection between node ID and process ID (MPI rank).
Boxfish must be informed of this projection in the run meta-file:

.. code-block:: yaml

  ---
  filetype: projection
  type: identity
  - { domain: HW, type: NODE, field: nodeid }
  - { domain: COMM, type: RANK, field: mpirank }
  flags: 0
  ---
