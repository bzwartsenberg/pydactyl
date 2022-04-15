#!/usr/bin/env ipython
from super_solid import Union, Difference, Intersection
from super_solid import Cube, Cylinder, Sphere
from super_solid import Translate, Rotate, Scale
import numpy as np
eps = 1

class Shell():
    def __init__(self, inner, outer, shell):
        self.inner = inner
        self.outer = outer
        self.shell = shell

    def get_inner(self):
        return self.inner

    def get_outer(self):
        return self.outer

    def get_shell(self):
        return self.shell

    def union(self, other_shell, outer=True):
        """Create a union between self and the other shell
        Args:
            other_shell: Shell object
            """
        new_outer = Union()(self.get_outer(), other_shell.outer)
        new_inner = Union()(self.get_inner(), other_shell.inner)

        if outer:
            self_cut_shell = Difference()(self.get_shell(), other_shell.get_inner())
            other_cut_shell = Difference()(other_shell.get_shell(), self.get_outer())
        else:
            self_cut_shell = Difference()(self.get_shell(), other_shell.get_outer())
            other_cut_shell = Difference()(other_shell.get_shell(), self.get_inner())
        new_shell = Union()(self_cut_shell, other_cut_shell)

        return Shell(new_outer, new_inner, new_shell)

    def difference(self, other_shell, outer=True):
        """Create a difference between self and the other shell
        Args:
            other_shell: Shell object
            """
        new_outer = Difference()(self.get_outer(), other_shell.outer)
        new_inner = Difference()(self.get_inner(), other_shell.inner)
        if outer:
            self_cut_shell = Difference()(self.get_shell(), other_shell.get_outer())
            other_cut_shell = Intersection()(other_shell.get_shell(), self.get_outer())
        else:
            self_cut_shell = Difference()(self.get_shell(), other_shell.get_inner())
            other_cut_shell = Intersection()(other_shell.get_shell(), self.get_inner())
        new_shell = Union()(self_cut_shell, other_cut_shell)
        return Shell(new_outer, new_inner, new_shell)

    def intersection(self, other_shell, outer=True):
        """Create an intersection between self and the other shell
        Args:
            other_shell: Shell object
            """
        new_outer = Intersection()(self.get_outer(), other_shell.outer)
        new_inner = Intersection()(self.get_inner(), other_shell.inner)
        if outer:
            self_cut_shell = Intersection()(self.get_shell(), other_shell.get_outer())
            other_cut_shell = Intersection()(other_shell.get_shell(), self.get_inner())
        else:
            self_cut_shell = Intersection()(self.get_shell(), other_shell.get_inner())
            other_cut_shell = Intersection()(other_shell.get_shell(), self.get_outer())
        new_shell = Union()(self_cut_shell, other_cut_shell)
        return Shell(new_outer, new_inner, new_shell)

    def rotate(self, a, v):
        new_inner = Rotate(a, v)(self.get_inner())
        new_outer = Rotate(a, v)(self.get_outer())
        new_shell = Rotate(a, v)(self.get_shell())
        return Shell(new_inner, new_outer, new_shell)

    def translate(self, s):
        new_inner = Translate(s)(self.get_inner())
        new_outer = Translate(s)(self.get_outer())
        new_shell = Translate(s)(self.get_shell())
        return Shell(new_inner, new_outer, new_shell)

    def scale(self, s):
        new_inner = Scale(s)(self.get_inner())
        new_outer = Scale(s)(self.get_outer())
        new_shell = Scale(s)(self.get_shell())
        return Shell(new_inner, new_outer, new_shell)

    def subtract(self, other_object):
        new_inner = Difference()(self.inner, other_object)
        new_outer = Difference()(self.outer, other_object)
        new_shell = Difference()(self.shell, other_object)
        return Shell(new_inner, new_outer, new_shell)

#TODO: update to only close one end by choice?
class CylinderShell(Shell):
    def __init__(self, h, r, thickness, close_ends=False, center=True, segments=False):
        if close_ends:
            self.inner = Cylinder(h - thickness, r=(r - thickness), center=center, segments=segments)
        else:
            self.inner = Cylinder(h + eps, r=(r - thickness), center=center, segments=segments)
        self.outer = Cylinder(h, r=r, center=center, segments=segments)
        self.shell = Difference()(self.outer, self.inner)

class BoxShell(Shell):
    def __init__(self, size, thickness, close_top=True, close_bottom=False, center=True):
        if type(size) is float or type(size) is int:
            size = [size, size, size]
        size = np.array(size)
        self.outer = Cube(size, center=center)

        if center:
            mins = - size / 2. + np.ones(3) * thickness
            maxs = size / 2. - np.ones(3) * thickness
        else:
            mins = np.ones(3) * thickness
            maxs = size / 2.

        if not close_top:
            maxs[2] += thickness + eps

        if not close_bottom:
            mins[2] -= (thickness + eps)

        inner_offset = (maxs + mins) / 2
        inner_size = (maxs - mins)

        self.inner = Translate(inner_offset)(Cube(inner_size, center=True))

        self.shell = Difference()(self.outer, self.inner)

class SphericalShell(Shell):
    def __init__(self, r, thickness, segments=50):
        self.outer = Sphere(r, segments=segments)
        self.inner = Sphere(r - thickness, segments=segments)
        self.shell = Difference()(self.outer, self.inner)

class ConicalShell(Shell):
    def __init__(self, h, r, thickness, center=False, segments=50):

        self.outer = Cylinder(h, r1=r, r2=0., center=center, segments=segments)
        if not center:
            theta = np.arctan(r / h)
            h_inner = h - thickness / np.sin(theta) + eps
            r_inner = r - thickness / np.cos(theta)
        else:
            raise NotImplementedError()
        self.inner = Translate([0., 0., -eps])(Cylinder(h_inner, r1=r_inner, r2=0., center=center, segments=segments))
        self.shell = Difference()(self.outer, self.inner)
