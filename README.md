**ALPHA SOFTWARE, NOT READY FOR USE**

This is currently made available for developers, don't expect this to be
usable for a while. Core language primitives work for the most part, but
things are missing and the stuff that does work doesn't work exactly like it
does in openscad.

An openscad interpretor written in python and using signed-distance functions.

We use [fogleman's SDF library](https://github.com/fogleman/sdf) which makes exentsive use
of numpy.

# Instalation

## CLI

Presuming that your system has good cli support, first install [pipx](https://pypa.github.io/pipx/)

Then simply run `pipx install pysdfscad[qtgui]`

## Differences from openscad

While we aim to be fully compatible with openscad there are some difference. If
you don't see that difference mentioned here, well that's probably a bug
that needs fixing.

Right now we are **NOT FEATURE COMPLETE WITH OPENSCAD**. A number of openscad
feature remain unimplemented.

 * OpenScad meshes will be simpler and have smaller filesizes

PySdfScad constructes meshes by sampling a signed distance field, this essentially means that
the entire object has the same amount of triangles for a given surface area, whether that surface
is a large flat plain or a complicated curve.

This is something that can be improved upon in the future (look into collinear mesh simplification), 
but it's likely PySdfScad meshes will always be a bit "messier".

 * You can assign geometry objects to variables, and write functions that modify geometry.

For example constructs like  `"foo=sphere(r=2);` will work. This is because signed distance function
based geometry is... based on functions. This is a somewhat advanced feature that you
probably don't need to worry about, but if you ever wished you could store an object in an array, well
now you can.

 * There are a lot more options for modifying a mesh

This is really the reason this project exists, our [underlying library](https://github.com/fogleman/sdf#miscellaneous)
 supports a number of more complicated ways of modifying geometry. and we expose
that as new openscad operators. For example you can use the `shell(thickness=0.2){...}`
operator to make objects hollow (amazing for things like pipes), or use
`smooth_union` to join two objects with a smooth fillet.

 * You can't color a mesh, or make parts of it transparent

This is another thing that can probably be fixed eventually, but is still quite challenging.

# ToDo:

 - [ ] Error messages are bad (include line numbers and stuff)
 - [x] No flow control (if statements don't exist)
 - [x] No ranges
 - [ ] Functions/Operators raise exception is arguments are missing. In openscad
    they just raise soft warnings or provide a default.
 - [ ] Minkowski/hull operators require SDF functions I don't know how to implement
 - [ ] Openscad does something weird to their floats when you echo them, and that makes
    it hard to write test cases.
