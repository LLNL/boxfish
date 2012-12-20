Modules
=======

Modules in Boxfish are tools for interacting with, manipulating or visualizing
data. Boxfish opens with a FilterBox module which will be the ancestor of all
other modules. To start using a module, drag its name from the Module List
onto an existing module. The new module will become a child of the one it was
dragged onto. If that module does not accept children, the new module will
become a child of the first ancestor that accepts children.

Clicking and dragging the titlebar will allow changing the module's placement
amongst its siblings or hiding it beneath a sibling. Clicking and dragging the
black bar beneath the title bar will allow re-parenting the module to
whichever parent module it is dropped upon.

Double-clicking on any module will bring up that module's Tab Dialog. This
dialog includes settings and other controls related to the module. Every
module has a Scene Policy tab which determines how actions in this tab affect
other modules and vice versa. For every type of scene information, there are
two properties, propagate and accept.

The propagate property determines whether the scene information will be
propagated to other modules. Once a module sets scene information to
propagate, all of its children will be set to do the same. If you cannot
uncheck this property, it is probably because a parent module has the property
checked. If you want sibling modules to share scene information, check the
propagate property in their parent module.

The accept property determines whether propagated scene information from other
modules will be applied to the current module.

There are three different types of scene information: highlight, module, and
attribute. Highlight scene information includes selected entities in any
module. Propagating highlight information will cause a selection in one module
to project the selection onto other modules.  Module scene information is
module-specific and may be things like the rotation in a 3D visualization
module. In this example, propagation module scene information will cause the
rotation in one module to force the same rotation in all other instances of
that module.

Attribute scene information includes the color maps of sets of attributes.
Modules that have multiple entities which to color (e.g. nodes and links in a
hardware visualization) may have separate scene policies for each of those
entities. Propagating attribute scene information causes the color maps to be
the same for any other set of entities displaying the same set of attributes.
For example, two modules showing packet data will be forced to have the same
color map, but a third module showing load data would not because load is not
the same attribute.

In the future, attribute scene information will be able to propagate data
range information along with the color map.

Note that these propagations will only occur for modules for which these
features are supported. It is up to the module designer to determine which
propagations to support and how to display them.

.. toctree::
   :maxdepth: 2

   mods/filterbox
   mods/3dtorus2d
   mods/3dtorus3d
   mods/table
   mods/plotter
