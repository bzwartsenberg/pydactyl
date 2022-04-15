#!/usr/bin/env ipython
from super_solid import Cube, Cylinder, Sphere
from super_solid import Union, Difference, Intersection, Hull
from super_solid import Translate, Mirror, Scale, Rotate
from super_solid import rotation_matrix
import numpy as np

def rotate_around_origin(shape, origin, angle, axis):
    shape = shape.translate([-v for v in origin]).rotate(angle, axis).translate(origin)
    return shape

def get_spherical_shell(outer_radius, thickness, segments=50):

    shell = Difference()(Sphere(outer_radius, segments=segments), Sphere(outer_radius - thickness, segments=segments))

    return shell


def get_cylindrical_shell(outer_radius, thickness, z, segments=50, center=True):

    shell = Difference()(Cylinder(z, r=outer_radius, center=center, segments=segments), Cylinder(z * 1.1, r=outer_radius - thickness, center=center, segments=segments))
    return shell


def half_cylindrical_shell(outer_radius, thickness, length, segments=50):
    """Generate a cylinder shell, centered at the origin, with its axis along the x-axis, restricted to z < 0"""

    shell = Rotate(90, [0, 1, 0])(get_cylindrical_shell(outer_radius, thickness, length, segments=segments, center=True))

    shell = Difference()(shell, Translate([-0.55 * length, -1.1 * outer_radius, 0])(Cube([1.1 * length, 2.2 * outer_radius, 1.1 * outer_radius])))

    return shell

def half_cylinder(radius, length, segments=50):
    """Generate a cylinder shell, centered at the origin, with its axis along the x-axis, restricted to z < 0"""
    cyl = Cylinder(length, r=radius, center=center, segments=segments)
    shell = Rotate(90, [0, 1, 0])(cyl)

    shell = Difference()(shell, Translate([-0.55 * length, -1.1 * outer_radius, 0])(Cube([1.1 * length, 2.2 * outer_radius, 1.1 * outer_radius])))

    return shell

def cube_around_points(points, margin=0.):
    """find a cube that fits around points, with margin margin"""
    if not type(margin) == list:
        margin = [margin] * 3


    minima = points.min(axis=0) - np.array(margin)
    maxima = points.max(axis=0) + np.array(margin)

    extent = maxima - minima
    offset = (maxima + minima) / 2

    return Translate(offset)(Cube(extent, center=True))


def cube_surrounding_column(points, points_lower, points_upper, margin=0.):
    """Get a cube surrounding the points in column, but between the points of two other columns"""
    if not type(margin) == list:
        margin = [margin] * 3

    minima = points.min(axis=0) - np.array(margin)
    maxima = points.max(axis=0) + np.array(margin)

    x_min = (minima[0] + points_lower[:,0].max()) / 2
    x_max = (maxima[0] + points_upper[:,0].min()) / 2

    minima = np.array([x_min, *minima[1:]])
    maxima = np.array([x_max, *maxima[1:]])

    extent = maxima - minima
    offset = (maxima + minima) / 2

    return Translate(offset)(Cube(extent, center=True))


def get_y_wall_between_points(points0, points1, thickness, margin):

    if not type(margin) == list:
        margin = [margin] * 3

    maxima = np.concatenate((points0, points1)).max(axis=0) + np.array(margin)
    minima = np.concatenate((points0, points1)).min(axis=0) - np.array(margin)
    print(points0, points1, maxima, minima)

    print(points0[:,0].max())
    print(points1[:,0].min())
    at_x = (points0[:,0].max() + points1[:,0].min()) / 2
    print(at_x)

    extent = maxima - minima
    extent = np.array([thickness, *extent[1:]])

    offset = (maxima + minima) / 2
    offset = np.array([at_x, *offset[1:]])

    return Translate(offset)(Cube(extent, center=True))
