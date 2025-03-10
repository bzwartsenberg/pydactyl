#!/usr/bin/env ipython
from super_solid import Hull, Union, Difference, Intersection
from super_solid import Cube, Cylinder, Sphere
from super_solid import Translate, Rotate, Scale
from super_solid import SuperSolid
import numpy as np
eps = 1e-1

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

    def union(self, other, outer=True):
        """Create a union between self and the other shell
        Args:
            other: Shell or SuperSolid
            """

        if issubclass(type(other), Shell):
            new_outer = Union()(self.get_outer(), other.outer)
            new_inner = Union()(self.get_inner(), other.inner)

            if outer:
                self_cut_shell = Difference()(self.get_shell(), other.get_inner())
                other_cut_shell = Difference()(other.get_shell(), self.get_outer())
            else:
                self_cut_shell = Difference()(self.get_shell(), other.get_outer())
                other_cut_shell = Difference()(other.get_shell(), self.get_inner())
            new_shell = Union()(self_cut_shell, other_cut_shell)
        else:
            new_inner = self.get_inner().union(other)
            new_outer = self.get_outer().union(other)
            new_shell = self.get_shell().union(other)

        return Shell(new_inner, new_outer, new_shell)

    #TODO: check the difference and intersection cutting for inner/outer
    def difference(self, other, outer=True):
        """Create a difference between self and the other shell
        Args:
            other: Shell or SuperSolid
            """
        if issubclass(type(other), Shell):
            new_outer = Difference()(self.get_outer(), other.outer)
            new_inner = Difference()(self.get_inner(), other.inner)
            if outer:
                self_cut_shell = Difference()(self.get_shell(), other.get_outer())
                other_cut_shell = Intersection()(other.get_shell(), self.get_outer())
            else:
                self_cut_shell = Difference()(self.get_shell(), other.get_inner())
                other_cut_shell = Intersection()(other.get_shell(), self.get_inner())
            new_shell = Union()(self_cut_shell, other_cut_shell)
        else:
            new_inner = self.get_inner().difference(other)
            new_outer = self.get_outer().difference(other)
            new_shell = self.get_shell().difference(other)
        return Shell(new_inner, new_outer, new_shell)

    def intersection(self, other, outer=True):
        """Create an intersection between self and the other shell
        Args:
            otherl: Shell or SuperSolid object
            """
        if issubclass(type(other), Shell):
            new_outer = Intersection()(self.get_outer(), other.outer)
            new_inner = Intersection()(self.get_inner(), other.inner)
            if outer:
                self_cut_shell = Intersection()(self.get_shell(), other.get_outer())
                other_cut_shell = Intersection()(other.get_shell(), self.get_inner())
            else:
                self_cut_shell = Intersection()(self.get_shell(), other.get_inner())
                other_cut_shell = Intersection()(other.get_shell(), self.get_outer())
            new_shell = Union()(self_cut_shell, other_cut_shell)
        else:
            new_inner = self.get_inner().intersection(other)
            new_outer = self.get_outer().intersection(other)
            new_shell = self.get_shell().intersection(other)
        return Shell(new_inner, new_outer, new_shell)

    def rotate(self, a, v):
        new_inner = self.get_inner().rotate(a, v)
        new_outer = self.get_outer().rotate(a, v)
        new_shell = self.get_shell().rotate(a, v)
        return Shell(new_inner, new_outer, new_shell)

    def translate(self, v):
        new_inner = self.get_inner().translate(v)
        new_outer = self.get_outer().translate(v)
        new_shell = self.get_shell().translate(v)
        return Shell(new_inner, new_outer, new_shell)

    def scale(self, v):
        new_inner = self.get_inner().scale(v)
        new_outer = self.get_outer().scale(v)
        new_shell = self.get_shell().scale(v)
        return Shell(new_inner, new_outer, new_shell)

    def mirror(self, v):
        new_inner = self.get_inner().mirror(v)
        new_outer = self.get_outer().mirror(v)
        new_shell = self.get_shell().mirror(v)
        return Shell(new_inner, new_outer, new_shell)


#TODO: update to only close one end by choice?
class CylinderShell(Shell):
    def __init__(self, h, r, thickness, close_ends=False, center=True, segments=50):
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
        self.size = np.array(size)
        self.outer = Cube(self.size, center=center)

        if center:
            mins = - self.size / 2. + np.ones(3) * thickness
            maxs = self.size / 2. - np.ones(3) * thickness
        else:
            mins = np.ones(3) * thickness
            maxs = self.size / 2.

        if not close_top:
            maxs[2] += thickness + eps

        if not close_bottom:
            mins[2] -= (thickness + eps)

        inner_offset = (maxs + mins) / 2
        inner_size = (maxs - mins)

        self.inner = Translate(inner_offset)(Cube(inner_size, center=True))

        self.shell = Difference()(self.outer, self.inner)

class RoundedBoxShell(Shell):
    def __init__(self, size, thickness, radius, round_top=True, round_bottom=False, segments=50):
        assert radius > thickness, "Cannot round corners if radius < thickness"
        inner = []
        outer = []
        for i,j in zip([1, 1, -1, -1], [1, -1, 1, -1]):
            if round_top:
                outer.append(Sphere(r=radius, segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, size[2] / 2 - radius]))
                inner.append(Sphere(r=(radius - thickness), segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, size[2] / 2 - radius]))
            else:
                outer.append(Cylinder(2 * radius, r=(radius), segments=segments, center=True).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, size[2] / 2 - radius]))
                inner.append(Cylinder(2 * radius - 2 * thickness, r=(radius-thickness), segments=segments, center=True).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, size[2] / 2 - radius]))
            if round_bottom:
                outer.append(Sphere(r=radius, segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, - size[2] / 2 + radius]))
                inner.append(Sphere(r=(radius - thickness), segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, - size[2] / 2 + radius]))
            else:
                outer.append(Cylinder(2 * radius, r=(radius), segments=segments, center=True).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, - size[2] / 2 + radius]))
                inner.append(Cylinder(2 * radius - 2 * thickness, r=(radius-thickness), segments=segments, center=True).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, -size[2] / 2 + radius]))

        self.inner = Hull()(*inner)
        self.outer = Hull()(*outer)
        self.shell = Difference()(self.outer, self.inner)

class RoundedBoxShellNoHulls(Shell): #Slow, very very slow
    def __init__(self, size, thickness, radius, round_top=True, round_bottom=False, segments=50):
        boxshell = BoxShell(size, thickness, close_top=True, close_bottom=True, center=True)

        assert radius > thickness, "Cannot round corners if radius < thickness"

        outer = boxshell.outer
        inner = boxshell.inner

        self.size = size
        self.radius = radius

        outer_corners = []
        outer_fills = []
        outer = []

        outer = [Cube(np.array(size) - 2.0 * radius, center=True)]
        for i,j in zip([1, 1, -1, -1], [1, -1, 1, -1]):
            outer.append(Cylinder(size[2] - 2 * radius, r=radius, center=True, segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, 0.]))
            if j == 1:
                outer.append(Cube([radius, size[1] - 2 * radius, size[2] - 2 * radius], center=True).translate([i * (size[0] - radius) / 2, 0., 0.]))
                outer.append(Cube([size[0] - 2 * radius, radius, size[2] - 2 * radius], center=True).translate([0., i * (size[1] - radius) / 2, 0.]))
                outer.append(Cube([size[0] - 2 * radius, size[1] - 2 * radius, radius], center=True).translate([0., 0., i * (size[2] - radius) / 2]))
            if round_top:
                if j == 1:
                    outer.append(Cylinder(size[0] - 2 * radius, r=radius, center=True, segments=segments).rotate(90, [0., 1., 0]).translate([0., (size[1] / 2 - radius) * i, size[2] / 2 - radius]))
                    outer.append(Cylinder(size[1] - 2 * radius, r=radius, center=True, segments=segments).rotate(90, [1., 0., 0]).translate([(size[0] / 2 - radius) * i, 0., size[2] / 2 - radius]))
                outer.append(Sphere(r=radius, segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, size[2] / 2 - radius]))
            else:
                outer.append(Cylinder(radius, r=radius, segments=segments, center=True).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, (size[2] - radius) / 2]))
                if j == 1:
                    outer.append(Cube([radius, size[1] - 2 * radius, radius], center=True).translate([i * (size[0] - radius) / 2, 0., (size[2] - radius) / 2]))
                    outer.append(Cube([size[0] - 2 * radius, radius, radius], center=True).translate([0., i * (size[1] - radius) / 2, (size[2] - radius) / 2]))

            if round_bottom:
                if j == 1:
                    outer.append(Cylinder(size[0] - 2 * radius, r=radius, center=True, segments=segments).rotate(90, [0., 1., 0]).translate([0., (size[1] / 2 - radius) * i, -size[2] / 2 + radius]))
                    outer.append(Cylinder(size[1] - 2 * radius, r=radius, center=True, segments=segments).rotate(90, [1., 0., 0]).translate([(size[0] / 2 - radius) * i, 0., -size[2] / 2 + radius]))
                outer.append(Sphere(r=radius, segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, -size[2] / 2 + radius]))
            else:
                outer.append(Cylinder(radius, r=radius, segments=segments, center=True).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, -(size[2] - radius) / 2]))
                if j == 1:
                    outer.append(Cube([radius, size[1] - 2 * radius, radius], center=True).translate([i * (size[0] - radius) / 2, 0., -(size[2] - radius) / 2]))
                    outer.append(Cube([size[0] - 2 * radius, radius, radius], center=True).translate([0., i * (size[1] - radius) / 2, -(size[2] - radius) / 2]))

        size = np.array(size) - 2.0 * thickness
        radius = radius - thickness

        inner = [Cube(np.array(size) - 2.0 * radius, center=True)]
        for i,j in zip([1, 1, -1, -1], [1, -1, 1, -1]):
            inner.append(Cylinder(size[2] - 2 * radius, r=radius, center=True, segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, 0.]))
            if j == 1:
                inner.append(Cube([radius, size[1] - 2 * radius, size[2] - 2 * radius], center=True).translate([i * (size[0] - radius) / 2, 0., 0.]))
                inner.append(Cube([size[0] - 2 * radius, radius, size[2] - 2 * radius], center=True).translate([0., i * (size[1] - radius) / 2, 0.]))
                inner.append(Cube([size[0] - 2 * radius, size[1] - 2 * radius, radius], center=True).translate([0., 0., i * (size[2] - radius) / 2]))
            if round_top:
                if j == 1:
                    inner.append(Cylinder(size[0] - 2 * radius, r=radius, center=True, segments=segments).rotate(90, [0., 1., 0]).translate([0., (size[1] / 2 - radius) * i, size[2] / 2 - radius]))
                    inner.append(Cylinder(size[1] - 2 * radius, r=radius, center=True, segments=segments).rotate(90, [1., 0., 0]).translate([(size[0] / 2 - radius) * i, 0., size[2] / 2 - radius]))
                inner.append(Sphere(r=radius, segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, size[2] / 2 - radius]))
            else:
                inner.append(Cylinder(radius, r=radius, segments=segments, center=True).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, (size[2] - radius) / 2]))
                if j == 1:
                    inner.append(Cube([radius, size[1] - 2 * radius, radius], center=True).translate([i * (size[0] - radius) / 2, 0., (size[2] - radius) / 2]))
                    inner.append(Cube([size[0] - 2 * radius, radius, radius], center=True).translate([0., i * (size[1] - radius) / 2, (size[2] - radius) / 2]))

            if round_bottom:
                if j == 1:
                    inner.append(Cylinder(size[0] - 2 * radius, r=radius, center=True, segments=segments).rotate(90, [0., 1., 0]).translate([0., (size[1] / 2 - radius) * i, -size[2] / 2 + radius]))
                    inner.append(Cylinder(size[1] - 2 * radius, r=radius, center=True, segments=segments).rotate(90, [1., 0., 0]).translate([(size[0] / 2 - radius) * i, 0., -size[2] / 2 + radius]))
                inner.append(Sphere(r=radius, segments=segments).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, -size[2] / 2 + radius]))
            else:
                inner.append(Cylinder(radius, r=radius, segments=segments, center=True).translate([(size[0] / 2 - radius) * i, (size[1] / 2 - radius) * j, -(size[2] - radius) / 2]))
                if j == 1:
                    inner.append(Cube([radius, size[1] - 2 * radius, radius], center=True).translate([i * (size[0] - radius) / 2, 0., -(size[2] - radius) / 2]))
                    inner.append(Cube([size[0] - 2 * radius, radius, radius], center=True).translate([0., i * (size[1] - radius) / 2, -(size[2] - radius) / 2]))

        self.outer = Union()(*outer)
        self.inner = Union()(*inner)
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

class PlateShell(Shell):
    def __init__(self, thickness, extent, buffer=None):
        """A plate that acts as a shell, the buffer is the perpendicular direction that is used to cut/include other parts
        The default plate is in the x,y plane
        Args:
            thickness: the thickness of the plate
            extent: the size in x and y
            buffer: the region to cut in the z direction, this points to positive x
        """
        if buffer is None:
            buffer = extent
        self.inner = Cube([extent + eps, extent + eps, buffer + eps]).translate([- (extent + eps) / 2., - (extent + eps) / 2., thickness / 2])
        self.outer = Cube([extent, extent, buffer + thickness]).translate([- extent / 2., - extent / 2, - thickness / 2])
        self.shell = Difference()(self.outer, self.inner)

class WalledCylinderShells(Shell):
    def __init__(self, cylinders, xs, thickness, y_min, y_max, z_min, z_max):
        """Create a shell from cylinder shells, separated at x intervals by a straight wall
        Args:
            cylinders: list of shell objects
            xs: list length n+1 with separating x's
            thickness: thickness of the walls separating
            y_min, y_max, z_min, z_max: extent of walls and cut boxes into y and z
        """
        inners = []
        outers = []
        shells = []
        for i in range(len(cylinders)):
            #TODO: offset, epsilon?
            inner_cut_cube = box_around([xs[i] + thickness / 2, y_min, z_min], [xs[i+1] - thickness / 2, y_max, z_max])
            # TODO: figure out how to do walls
            inner = cylinders[i].get_inner().intersection(inner_cut_cube)
            if i < len(cylinders) - 1:
                wall = box_around([xs[i + 1] - thickness / 2, y_min, z_min], [xs[i + 1] + thickness / 2, y_max, z_max])
                inner = inner.union(wall.intersection(cylinders[i].get_inner(), cylinders[i+1].get_inner()))
            inners.append(inner)


            shell = cylinders[i].get_shell().intersection(inner_cut_cube)

            outer_cut_cube = box_around([xs[i] - thickness / 2, y_min, z_min], [xs[i+1] + thickness / 2, y_max, z_max])
            # TODO: figure out how to do walls
            outer = cylinders[i].get_outer().intersection(outer_cut_cube)
            outers.append(outer)

            if i > 0:
                wall = box_around([xs[i] - thickness / 2, y_min, z_min], [xs[i] + thickness / 2, y_max, z_max])
                wall_a = wall.intersection(cylinders[i - 1].get_outer()).difference(cylinders[i].get_inner())
                wall = box_around([xs[i] - thickness / 2, y_min, z_min], [xs[i] + thickness / 2, y_max, z_max])
                wall_b = wall.intersection(cylinders[i].get_outer()).difference(cylinders[i - 1].get_inner())
                shell = shell.union(wall_a, wall_b)
            shells.append(shell)
        # end walls:
        wall = box_around([xs[0] - thickness / 2, y_min, z_min], [xs[0] + thickness / 2, y_max, z_max])
        wall = wall.intersection(cylinders[0].get_outer())
        shells.append(wall)
        wall = box_around([xs[-1] - thickness / 2, y_min, z_min], [xs[-1] + thickness / 2, y_max, z_max])
        wall = wall.intersection(cylinders[-1].get_outer())
        shells.append(wall)

        self.inner = Union()(*inners)
        self.outer = Union()(*outers)
        self.shell = Union()(*shells)

class TentedBoxShell(Shell):
    pass

class TentedRoundedShell(Shell):
    def __init__(self, xy_min, xy_max, at_z, z_below, tent_function, thickness, radius, segments=50):
        """
        Args:
            xy_min, xy_max, at_z: extent and location in z BEFORE tenting
            z_below: space to add below AFTER tenting
            tent_function: function that can tent and offset a shape
        Note: assumes tenting is around the y axis
        """
        xy_max, xy_min = np.array(xy_max), np.array(xy_min)
        size_xy = xy_max - xy_min
        loc_xy = (xy_min + xy_max) / 2
        loc = np.array([*loc_xy, at_z - radius])
        inner = []
        outer = []
        for i,j in zip([1, 1, -1, -1], [1, -1, 1, -1]):
            outer.append(Sphere(r=radius, segments=segments).translate([(size_xy[0] / 2 - radius) * i, (size_xy[1] / 2 - radius) * j, 0.]).translate(loc))
            inner.append(Sphere(r=(radius - thickness), segments=segments).translate([(size_xy[0] / 2 - radius) * i, (size_xy[1] / 2 - radius) * j, 0.]).translate(loc))

        inner = [tent_function(shape) for shape in inner]
        outer = [tent_function(shape) for shape in outer]

        outer_posns = np.concatenate([o.get_points() for o in outer])
        sorted_outer_posns = outer_posns[outer_posns[:,2].argsort()]

        # first two should be the lower ones, last two the higher
        # we want the z-height of the lowest one, set the x to x - l / cos(theta), where
        # tan(theta) = dz / dx
        high = sorted_outer_posns[2]
        low = sorted_outer_posns[0]


        dx = abs(low[0] - high[0])
        dz = abs(low[2] - high[2])


        w = size_xy[0] / np.cos(np.arctan(dz / dx))


        self.outer_xy = []
        for i in [1, -1]:
            outer.append(Sphere(r=radius, segments=segments).translate([low[0] - w, i * (size_xy[1] / 2 - radius) + loc_xy[1], low[2]]))
            inner.append(Sphere(r=radius - thickness, segments=segments).translate([low[0] - w, i * (size_xy[1] / 2 - radius) + loc_xy[1], low[2]]))

        #     # and bottoms:
            outer.append(Sphere(r=radius, segments=segments).translate([low[0], i * (size_xy[1] / 2 - radius) + loc_xy[1], low[2] - z_below]))
            outer.append(Sphere(r=radius, segments=segments).translate([low[0] - w, i * (size_xy[1] / 2 - radius) + loc_xy[1], low[2] - z_below]))
            inner.append(Sphere(r=radius - thickness, segments=segments).translate([low[0], i * (size_xy[1] / 2 - radius) + loc_xy[1], low[2] - z_below]))
            inner.append(Sphere(r=radius - thickness, segments=segments).translate([low[0] - w, i * (size_xy[1] / 2 - radius) + loc_xy[1], low[2] - z_below]))

            self.outer_xy.append([low[0] - w - radius, i * (size_xy[1] / 2 ) + loc_xy[1]])
            self.outer_xy.append([low[0] + radius, i * (size_xy[1] / 2 ) + loc_xy[1]])

        self.inner = Hull()(*inner)
        self.outer = Hull()(*outer)
        self.shell = Difference()(self.outer, self.inner)

    def get_screw_corners(self):
        return self.outer_xy

def box_around(mins, maxs):
    mins = np.array(mins)
    maxs = np.array(maxs)
    assert np.all(maxs > mins), 'max has to be bigger than min everywhere'
    center = (maxs + mins) / 2
    size = maxs - mins
    return Cube(size, center=True).translate(center)

def half_cylinder_shell(h, r, thickness):
    shell = CylinderShell(h, r, thickness, center=True)
    cube_size = np.array([r, 2 * r, h]) * 1.1
    cube_offset = np.array([r, 0., 0.]) * 0.55
    return shell.difference(Cube(cube_size, center=True).translate(cube_offset))
