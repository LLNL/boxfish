Filter Spin
===========

The Filter Spin module adds a simple spinnable filter of the form [attribute]
= [value]. It allows only a single table field as an attribute. The [value]
portion in the spin control, set to allow every value the [attribute] takes
(under the current filters). The user can then user the mouse or arrows to
manipulate the spin control. They can also type an existing value to jump
ahead. This is useful for attributes like time where users may want to step
through the values of the attribute in order.

Like the Filter Box, it is mostly a pass-through module. Its effects are
applied to child modules falling under it. All scene settings are supported,
but do not affect what is shown in the Filter Spin, only the scene information
applied to the child modules.

Note the Filter Spin does not know the data that the modules below it are
requesting and thus cannot affect the data range. If possible, the user should
fix the data range manually so it is constant over the entire spin.
