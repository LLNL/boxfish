.. _file-format-label:

File Format
===========

Boxfish reads data in the form of space-separated tables annotated with YAML
headers describing the data columns. Meta information for each table may also
be included as an additional YAML header. To tie data together from a single
run, there should be a file composed of YAML documents which contains the meta
information for the entire run (e.g. hardware and application information), a
document for each table file, and a document for each projection. 


Meta File
---------
The first document in the run meta-file contains run-wide information. In the
below example, this is information about the hardware. Boxfish modules may
depend on a subset of this information and be expecting it in a certain
format. In the below example, the information is required by Torus modules.
Each YAML file should also have a ``key`` in its first document that indicates
a unique ID for teh run. This will be used in the future to add files to a run
after the initial meta file has been processed.

.. code-block:: yaml

  ---
  key: UUID
  date: 2011-06-06
  author: DEI
  hardware: {
    network: torus,
    nodes: 1024,
    coords: [x, y, z],
    coords_table: nodes.yaml,
    dim: {x: 8, y: 8, z: 16},
    source_coords: {x: sx, y: sy, z: sz},
    destination_coords: {x: tx, y: ty, z: tz},
    link_coords_table: links.yaml
  }
  ---
  ...table documents or projection documents...

Each table is assumed to have a column for the ID of its primary data object,
e.g. nodes, ranks, or communicators. This is denoted by the ``field`` in the
table's YAML document in the run meta-file. The domain and subdomain are
marked by ``domain`` and ``type``. The ``filename`` is the path to the table
relative to the meta-file. 

.. code-block:: yaml

   ---
   filetype: table
   filename: nodes.yaml
   domain: HW
   type: NODE
   field: nodeid
   flags: 0
   ---

Projections should also be listed in the run meta-file. Each projection has a
list of two mappings under ``subdomain`` which contain the domain, subdomain,
and field name for both the source and destination of the projection. In the
case of a file projection, the field name should match that in the file. In
the case of all others, it should be the field name to use if a table was
created based on the projection. The ``type`` refers to the particular
projection object that will be created. If that type of projection requires
keyword arguments, they should be defined in this document as well.  In the
example, ``node_policy`` and ``link_policy`` are keyword arguments specific to
the ``node link`` projection.

.. code-block:: yaml

  ---
  filetype: projection
  type: node link
  node_policy: Source
  link_policy: Source
  subdomain:
  - { domain: HW, type: NODE, field: nodeid }
  - { domain: HW, type: LINK, field: linkid }
  flags: 0
  ---

The final document in the run meta-file should end with a line containing only
``...``.  Other YAML documents in the meta-file are separated with ``---``.

Table Files
-----------
The header for the individual table files should contain two YAML
documents. The first one contains the unique ``key`` field as with the run
meta-file as well as any other table-specific meta information. When searching
meta-information, Boxfish gives priority to the run's meta information if a
run and a table have information with the same name.

The second document in the table file's header describes each column of the
table with its name and type. As with the run meta-file, the final YAML
document should end with ``...``.

.. code-block:: yaml

  ---
  key: UUID
  ---
  - [nodeid, int32]
  - [x, int32]
  - [y, int32]
  - [z, int32]
  - [flops, int64]
  ...
