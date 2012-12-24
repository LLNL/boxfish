.. _projections-label:

Projections
===========

Projections define the mapping of one entity to another and are used to
calculate and display data associated with one entity and subdomain to
another. Valid projections on a run should be defined in the run's meta-file.
Boxfish is capable of chaining existing projections together as necessary in
order to project data whenever possible. 

All projections require ``filetype``, ``type``, ``subdomain``, and ``flags``
fields. The ``filetype`` field will always bee ``projection`` (as opposed to
``table`` for data tables). The ``type`` refers to the string specifying the
type of projection. ``flags`` will be used in the future, and can be set to
``0`` for now.

The ``subdomain`` field defines the source and destination domain. The overall
domain is listed in ``domain``. The particular entity within that domain is
listed in ``type``. Finally, a fieldname for that domain is listed under
``field``. In file-based projections, the fieldname is used for accessing the
appropriate data column in the file. The fieldname may also be used in the
user interface to denote the id attribute of that entity.

.. code-block:: yaml

  ---
  filetype: projection
  type: identity
  subdomain:
  - { domain: HW, type: NODE, field: nodeid }
  - { domain: COMM, type: RANK, field: mpirank }
  flags: 0
  ---

.. toctree::
   :maxdepth: 2

   projections/identity
   projections/file
   projections/nodelink
