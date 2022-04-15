from solid import union, difference, intersection, hull
from solid import cube, sphere, cylinder
from solid import translate, mirror, scale, rotate
import numpy as np


class Cube(cube):

    def __init__(self, size, center=False):
        super().__init__(size, center=center)
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
class Cylinder(cylinder):

    def __init__(self, h, r=None, r1=None, r2=None, center=False, segments=None):
        super().__init__(h=h, r=r, r1=r1, r2=r2, center=center, segments=segments)
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
class Sphere(sphere):

    #TODO: add segments around the perimiters, in "number of segments", as given
    def __init__(self, r, segments=None):
        super().__init__(r=r, segments=segments)
        self.points = np.array([
            [0.0, 0.0, 0.0],
        ])

    def get_points(self):
        return self.points

# TODO: expand functionality to full openscad style:
class Rotate(rotate):

    def __init__(self, a, v):
        """Generate a rotation
        Args:
            a: angle (degrees)
            v: vector around which to rotate
        """
        super().__init__(a=a, v=v)

        self.rotation_matrix = rotation_matrix(v, a * np.pi / 180.)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(np.einsum('ij,dj->di', self.rotation_matrix, child.get_points()))
        return np.concatenate(points, axis=0)


# TODO: expand functionality to full openscad style:
class Translate(translate):

    def __init__(self, v):
        """Generate a translation
        Args:
            v: vector of the translation
        """
        super().__init__(v=v)

        self.v = np.array(v)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points() + self.v.reshape((1,3)))
        return np.concatenate(points, axis=0)

class Scale(scale):

    def __init__(self, v):
        """Generate a scaling
        Args:
            v: scale parameters
        """
        super().__init__(v=v)

        self.v = np.array(v)

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points() * self.v.reshape((1,3)))
        return np.concatenate(points, axis=0)

class Mirror(mirror):

    def __init__(self, v):
        """Generate a mirror about a plane through the origin with normal v
        Args:
            v: normal vector
        """
        super().__init__(v=v)

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

class Union(union):

    def __init__(self):
        super().__init__()

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points())
        return np.concatenate(points, axis=0)

class Intersection(intersection):

    def __init__(self):
        super().__init__()

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points())
        return np.concatenate(points, axis=0)

class Difference(difference):

    def __init__(self):
        super().__init__()

    def get_points(self):
        points = []
        for child in self.children:
            points.append(child.get_points())
        return np.concatenate(points, axis=0)

class Hull(hull):

    def __init__(self):
        super().__init__()

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
