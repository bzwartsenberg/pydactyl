from solid import union, difference, intersection, hull
from solid import cube, sphere, cylinder
from solid import translate, mirror, scale, rotate
from solid import scad_render_to_file
import numpy as np

class SuperSolid():
    """Parent class with some useful shortcuts for a more pythonic feel"""

    def rotate(self, a, v):
        """apply a rotation
        Args:
            a: angle (degrees)
            v: vector around which to rotate
        """
        return Rotate(a, v)(self)

    def translate(self, v):
        """apply a translation
        Args:
            v: vector of the translation
        """
        return Translate(v)(self)

    def scale(self, v):
        """Apply a scaling
        Args:
            v: scale parameters
        """
        return Scale(v=v)(self)

    def mirror(self, v):
        """Apply a mirror about a plane through the origin with normal v
        Args:
            v: normal vector
        """
        return Mirror(v=v)(self)

    def union(self, *objects):
        """Apply a union with other objects
        Args:
            *objects: any objects to uniuon with
        """
        return Union()(self, *objects)

    def difference(self, *objects):
        """Apply a difference with other objects
        Args:
            *objects: any objects to difference with
        """
        return Difference()(self, *objects)

    def intersection(self, *objects):
        """Apply an intersection with other objects
        Args:
            *objects: any objects to intersection with
        """
        return Intersection()(self, *objects)

    def hull(self, *objects):
        """Apply a hull with other objects
        Args:
            *objects: any objects to hull with
        """
        return Hull()(self, *objects)

    def __sum__(self, *args):
        return Union()(self, *args)

    def __sub__(self, *args):
        return Difference()(self, *args)

    def __mul__(self, *args):
        return Intersection()(self, *args)

    def write_scad(self, path):
        scad_render_to_file(self, path)


class Cube(SuperSolid, cube):

    def __init__(self, size, center=False):
        cube.__init__(self, size, center=center)
        size = np.array(size)
        self.points = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [1.0, 1.0, 0.0],
            [0.0, 1.0, 1.0],
            [1.0, 0.0, 1.0],
            [1.0, 1.0, 1.0],
        ]) * size.reshape((1, -1))

        if center:
            self.points -= 0.5 * size.reshape((1, -1))

    def get_points(self):
        return self.points

    def is_in(self, points):
        #TODO: return an array of equal size to points with True or False
        pass


#TODO: expand to the full definition:
class Cylinder(SuperSolid, cylinder):

    def __init__(self, h, r=None, r1=None, r2=None, center=False, segments=None):
        cylinder.__init__(self, h=h, r=r, r1=r1, r2=r2, center=center, segments=segments)
        self.points = np.array([
            [0.0, 0.0, 0.0],
            [0.0, 0.0, h],
        ])
        #TODO: add segments around the perimiters, in "number of segments", as given

        if center:
            self.points -= 0.5 * np.array([[0., 0., h]])

    def get_points(self):
        return self.points


#TODO: expand to full def:
class Sphere(SuperSolid, sphere):

    #TODO: add segments around the perimiters, in "number of segments", as given
    def __init__(self, r, segments=None):
        sphere.__init__(self, r=r, segments=segments)
        self.points = np.array([
            [0.0, 0.0, 0.0],
        ])

    def get_points(self):
        return self.points

# TODO: expand functionality to full openscad style:
class Rotate(SuperSolid, rotate):

    def __init__(self, a, v):
        """Generate a rotation
        Args:
            a: angle (degrees)
            v: vector around which to rotate
        """
        rotate.__init__(self, a=a, v=v)

        self.rotation_matrix = rotation_matrix(v, a * np.pi / 180.)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(np.einsum('ij,dj->di', self.rotation_matrix, child.get_points()))
        return np.concatenate(points, axis=0)


# TODO: expand functionality to full openscad style:
class Translate(SuperSolid, translate):

    def __init__(self, v):
        """Generate a translation
        Args:
            v: vector of the translation
        """
        translate.__init__(self, v=v)

        self.v = np.array(v)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points() + self.v.reshape((1,3)))
        return np.concatenate(points, axis=0)

class Scale(SuperSolid, scale):

    def __init__(self, v):
        """Generate a scaling
        Args:
            v: scale parameters
        """
        scale.__init__(self, v=v)

        self.v = np.array(v)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points() * self.v.reshape((1,3)))
        return np.concatenate(points, axis=0)

class Mirror(SuperSolid, mirror):

    def __init__(self, v):
        """Generate a mirror about a plane through the origin with normal v
        Args:
            v: normal vector
        """
        mirror.__init__(self, v=v)

        self.v = np.array(v)
        self.v_norm = self.v / np.linalg.norm(self.v)

    def get_points(self):
        points = []
        for child in self.children:
            child_points = child.get_points()
            #project onto normal vector:
            projections = np.dot(child_points, self.v_norm).reshape((-1,1)) * self.v_norm.reshape((1, 3))
            #and subtract twice to get mirror
            points.append(child_points - 2 * projections)
        return np.concatenate(points, axis=0)

class Union(SuperSolid, union):

    def __init__(self):
        union.__init__(self)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points())
        return np.concatenate(points, axis=0)

class Intersection(SuperSolid, intersection):

    def __init__(self):
        intersection.__init__(self)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points())
        return np.concatenate(points, axis=0)

class Difference(SuperSolid, difference):

    def __init__(self):
        difference.__init__(self)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points())
        return np.concatenate(points, axis=0)

class Hull(SuperSolid, hull):

    def __init__(self):
        hull.__init__(self)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points())
        return np.concatenate(points, axis=0)

def rotation_matrix(axis, theta):
    axis = axis / np.linalg.norm(axis)
    rot = np.zeros((3,3))

    ux, uy, uz = axis
    s = np.sin(theta)
    c = np.cos(theta)
    mc = (1 - c)

    rot[0, 0] = c + (ux ** 2) * mc
    rot[1, 0] = uy * ux * mc + uz * s
    rot[2, 0] = uz * ux * mc - uy * s


    rot[0, 1] = ux * uy * mc - uz * s
    rot[1, 1] = c + (uy ** 2) * mc
    rot[2, 1] = uz * uy * mc + ux * s

    rot[0, 2] = ux * uz * mc + uy * s
    rot[1, 2] = uy * uz * mc - ux * s
    rot[2, 2] = c + (uz ** 2) * mc

    return rot
