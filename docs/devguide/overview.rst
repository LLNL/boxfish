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
contain coloring and range information for specific groups of attributes.
ModuleScenes are module-specific (e.g. rotation for a 3D view module).

There are two options for each module instance for HighlightScenes and
ModuleScenes. The options are apply/accept and propagate. The apply/accept
option indicates whether the module instance will overwrite its own scene
information with any applicable scene information it receives from its parent.

The propagate option indicates whether the module will propagate scene
information to all of its children. If this option is set on, then all of its
children will also set their propagation option on, ensuring that the entire
subtree behaves the same.

For AttributeScenes, the two options apply to each requested group of
attributes in each module. Some modules may make multiple disparate requests
(e.g. a set of attributes for nodes and a set for links) but both will be
governed by the same propagation option. 

More explanation and examples are in the user guide under the :ref:`Scene
Policy <policies-label>` section of :ref:`bfmodules`.  Instructions on
incorporating these features into your module are found in
:ref:`selection-propagation-label` and :ref:`module-scene-label`.

Data Storage Structure
----------------------
Boxfish stores all of the input performance data in a hierarchy known as
the ``DataTree``. This structure allows a logical display of the data
available as well as an understood method for retrieving related data
associated with any node in the tree. 

The first level of the Boxfish ``DataTree`` contains runs, representing
groupings of data taken under the same system and application configuration.
The run may contain meta-information about the conditions under which the data
was gathered. Some of this information may be required by individual Boxfish
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
