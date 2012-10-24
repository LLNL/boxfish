Overview
========


Structure of Boxfish
--------------------
The main structure of Boxfish is a tree of modules. The policies and data
transformations of any module node in the tree apply to all modules in the
subtree of that node. This allows users to create sets of views that have the
same filters applied to them and share selection and other scene information. 

The Boxfish tree structure is shown in the Boxfish GUI through containment. A
child module's titlebar is beneath the titlebar of the parent module. Subtrees
may be re-parented by dragging the subtree root module under the new parent's
title bar.

Scene Propagation Policy
------------------------
There are three main types of scene information in Boxfish. HighlightScenes
represent selected (and therefore highlighted) entities. AttributeScenes
contain coloring information for specific groups of attributes. ModuleScenes
are module-specific (e.g. rotation for a 3D view module).

There are two options for each module instance for HighlightScenes and
ModuleScenes. The options are apply/accept and propagate. The apply/accept
option indicates whether the module instance will overwrite its own scene
information with any applicable scene information is receives from its parent.

The propagate option indicates whether the module will propagate scene
information to all of its children. If this option is set on, then all of its
children will also set their propagation option on, ensuring that the full
subtree behaves the same.

For AttributeScenes, the two options apply to each requested group of
attributes in each module. Some modules may make multiple disparate requests
(e.g. a set of attributes for nodes and a set for links).

Data Storage Structure
----------------------
Boxfish stores all of the inputted performance data in a hierarchy known as
the ``DataTree``. This structure allows a logical display of the data
available as well as an understood method for retrieving related data
associated with any node in the tree. 

The first level of the Boxfish DataTree contains runs, representing groupings
of data taken under the same system and application configuration. The run may
contain meta-information about the conditions under which the data was
gathered. Some of this information may be required by individual Boxfish
modules. For example, the 3D Torus View requires meta-information indicating
the run was done on a torus/mesh network and meta-information about the size
and shape of that network.

Beneath the run level in the hierarchy is a level for groupings. There are two
groupings, one for tables and one for projections. This purpose of this level
is entirely for these groupings. There is no other functionality.

The third level of the hierarchy has tables and projections, under their
respective grouping node. A table node includes any table-specific
meta-information as well as the Table object itself. A projection node
includes any projection-specific meta-information as well as the Projection
object itself.

Beneath the table nodes are attribute nodes. These contain the names of the
columns represented in the parent table. These nodes allow users to pick
particular attributes of interest out of the GUI.

Data Format
-----------
Boxfish reads data in the form of space-separated tables annotated with YAML
headers describing the data columns. Meta information for each table may also
be included as an additional YAML header. To tie data together from a single
run, there should be a file composed of YAML documents which contains the meta
information for the entire run (e.g. hardware and application information), a
document for each table file, and a document for each projection. The final
document in the run meta-file should end with a line containing only ``...``.

The first document in the run meta-file contains run-wide information. In the
below example, this is information about the hardware. Each YAML file should
also have a ``key`` in its first document that indicates a unique ID for teh
run. This will be used later to add files to a run after the initial meta file
has been processed.

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
