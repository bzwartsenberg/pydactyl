# About
This is a pythonized version of the dactyl-manuform family of keybaords. 

I have attempted to simplify certain crucial elements such as the placement functions and its parametrization. In the dactyl keybaord series, all keys are placed on a torus, with common radii and center location. To generate appropriate stagger for different fingers, manual offsets are implemented.

This design uses a slightly different philosophy. Each finger column is assigned its own set of parameters, consisting of a torus center location, major radius, minor radius, major angle and minor angle. 

To reproduce the dactyl type keyplacement, the radii and offset angles should be set to the same values for each of the columns, and only the center location should get a translation. 

For the thumb cluster, a similar approach is taken, except that the keys are placed on the concave part of the torus, rather than the convex part.

The current setup allows more flexibility, such as for example a pinky column that fans outward slightly.

Another added benefit of this approach is that it allows the formation of a plate consisting of segments of ablate ellipsoids, which is a different style than the webbing created between keyswitch holes in the original. This is part aesthetics, but more importantly it does away with the triangle hulls that are created in the original, which are incompatible with the generation of STP files. The Model generated here can be imported in FreeCAD, and exported to STP, so that it can be used downstream in applications like Fusion360, which is more accessible to many hobbyists than the programmatic design in Python. 


# How to 

# Create your own
