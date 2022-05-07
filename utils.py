#!/usr/bin/env ipython
from shell import BoxShell, RoundedBoxShell, TentedRoundedShell
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

    at_x = (points0[:,0].max() + points1[:,0].min()) / 2

    extent = maxima - minima
    extent = np.array([thickness, *extent[1:]])

    offset = (maxima + minima) / 2
    offset = np.array([at_x, *offset[1:]])

    return Translate(offset)(Cube(extent, center=True))


def get_hulls(kb, extent_min, extent_max, interpolate_z=False):
    orig_extent_max = extent_max
    orig_extent_min = extent_min
    space_max = np.array([3., 3., -5.])
    space_min = np.array([3., 3., 0.])
    extent_max = extent_max + space_max
    extent_min = extent_min - space_min
    d = 0.1
    i2range = 2 * (max([kb.column_nrows[j] for j in range(kb.args.ncols)]) + 1)
    j2range = 2 * (kb.args.ncols + 1)

    def is_key(i2, j2):
        # check if the grid square between i2,j2 and i2+1 and j2+1 is a key hole
        i, j = (i2 - 1) // 2, (j2 - 1) // 2
        rem_i, rem_j = (i2 - 1) % 2, (j2 - 1) % 2
        if rem_i != 0 or rem_j != 0:
            return False
        if j >= 0 and j < kb.args.ncols and i >= 0 and i < kb.column_nrows[j]:
            return True
        else:
            return False

    def is_end(i2, j2):
        return i2 == 0 or j2 == 0 or (i2 == (i2range - 1)) or (j2 == (j2range - 1))

    def is_corner(i2, j2):
        return ((i2 == 0) and (j2 == 0)) or ((i2 == (i2range - 1)) and (j2 == 0)) or ((i2 == 0) and (j2 == (j2range - 1))) or ((i2 == (i2range - 1)) and (j2 == (j2range - 1)))

    def walk_to_nearest_key(i2, j2, di2=0, dj2=0):
        iterations = 0
        while not (is_key(2 * ( (i2 - 1) // 2) + 1, 2 * ( (j2 - 1) // 2) + 1) or is_end(i2, j2)):
            iterations += 1
            i2 += di2
            j2 += dj2
            if iterations > 10:
                raise RuntimeError(f"You're walking the wrong way my friend: i2 {i2}, j2 {j2}, di2 {di2}, dj2: {dj2}")
        return i2, j2

    def get_regular_post(i2, j2):
        sx = kb.args.keyswitch_width / 2+ kb.args.key_hole_rim_width
        sy = kb.args.keyswitch_height / 2+ kb.args.key_hole_rim_width
        c = Cube([d, d, kb.args.plate_thickness], center=True)
        bl = c.translate([-sx, -sy, kb.args.plate_thickness/2])
        br = c.translate([sx, -sy, kb.args.plate_thickness/2])
        tl = c.translate([-sx, sy, kb.args.plate_thickness/2])
        tr = c.translate([sx, sy, kb.args.plate_thickness/2])
        i, j = (i2 - 1) // 2, (j2 - 1) // 2
        rem_i, rem_j = (i2 - 1) % 2, (j2 - 1) % 2
        posts = {(0, 0) : tl, (0, 1) : tr, (1, 0): bl, (1, 1): br}
        return kb.transform_switch(posts[(rem_i, rem_j)], i, j, tent_and_z_offset=False)

    def get_y_between_for_i(i2p1, j2p1,i2p2, j2p2, i2):
        if is_end(i2p1, j2p1):
            if j2p1 == 0:
                y1 = extent_max[1]
            else:
                y1 = extent_min[1]
        else:
            y1 = get_regular_post(i2p1, j2p1).get_points().mean(axis=0)[1]
        if is_end(i2p2, j2p2):
            if j2p2 == 0:
                y2 = extent_max[1]
            else:
                y2 = extent_min[1]
        else:
            y2 = get_regular_post(i2p2, j2p2).get_points().mean(axis=0)[1]

        y = y1
        if not (i2p2 == i2p1):
            y = y + (y2 - y1) * (i2 - i2p1) / (i2p2 - i2p1)
        return y

    def get_x_between_for_j(i2p1, j2p1,i2p2, j2p2, j2):
        if is_end(i2p1, j2p1):
            if i2p1 == 0:
                x1 = extent_max[0]
            else:
                x1 = extent_min[0]
        else:
            x1 = get_regular_post(i2p1, j2p1).get_points().mean(axis=0)[0]
        if is_end(i2p2, j2p2):
            if i2p2 == 0:
                x2 = extent_max[0]
            else:
                x2 = extent_min[0]
        else:
            x2 = get_regular_post(i2p2, j2p2).get_points().mean(axis=0)[0]

        x = x1
        if not (j2p2 == j2p1):
            x = x + (x2 - x1) * (j2 - j2p1) / (j2p2 - j2p1)
        return x

    def get_end_post(i2, j2):
        if is_corner(i2, j2):
            tr = [extent_min[0] * (1 - np.sign(j2)) + extent_max[0] * np.sign(j2), extent_max[1] * (1 - np.sign(i2)) + extent_min[1] * np.sign(i2), extent_max[2] - kb.args.case_thickness / 2]
        elif i2 == 0:
            i2p1, j2p1 = walk_to_nearest_key(i2 + 1, j2, di2=-1)
            i2p2, j2p2 = walk_to_nearest_key(i2 + 1, j2, di2=1)
            x = get_x_between_for_j(i2p1, j2p1, i2p2, j2p2, j2)
            tr = [x, extent_max[1], extent_max[2] - kb.args.case_thickness / 2]
        elif j2 == 0:
            i2p1, j2p1 = walk_to_nearest_key(i2, j2 + 1, di2=-1)
            i2p2, j2p2 = walk_to_nearest_key(i2, j2 + 1, di2=1)
            y = get_y_between_for_i(i2p1, j2p1, i2p2, j2p2, i2)
            tr = [extent_min[0], y, extent_max[2] - kb.args.case_thickness / 2]
        elif i2 == (i2range - 1):
            i2p1, j2p1 = walk_to_nearest_key(i2 - 1, j2, di2=-1)
            i2p2, j2p2 = walk_to_nearest_key(i2 - 1, j2, di2=1)
            x = get_x_between_for_j(i2p1, j2p1, i2p2, j2p2, j2)
            tr = [x, extent_min[1], extent_max[2] - kb.args.case_thickness / 2]
        elif j2 == (j2range - 1):
            i2p1, j2p1 = walk_to_nearest_key(i2, j2 - 1, di2=-1)
            i2p2, j2p2 = walk_to_nearest_key(i2, j2 - 1, di2=1)
            y = get_y_between_for_i(i2p1, j2p1, i2p2, j2p2, i2)
            tr = [extent_max[0], y, extent_max[2] - kb.args.case_thickness / 2]
        return Cube([d, d, kb.args.case_thickness], center=True).translate(tr)

    def get_regular_or_end_post(i2, j2):
        if is_key(2 * ( (i2 - 1) // 2) + 1, 2 * ( (j2 - 1) // 2) + 1):
            return get_regular_post(i2, j2)
        elif is_end(i2, j2):
            return get_end_post(i2, j2)
        else:
            raise RuntimeError('something went wrong')

    def get_interpolate(i2, j2):
        i2p1, _ = walk_to_nearest_key(i2, j2, di2=-1)
        i2p2, _ = walk_to_nearest_key(i2, j2, di2=1)
        _, j2p1 = walk_to_nearest_key(i2, j2, dj2=-1)
        _, j2p2 = walk_to_nearest_key(i2, j2, dj2=1)

        pos_ip1 = get_regular_or_end_post(i2p1, j2).get_points().mean(axis=0)
        pos_ip2 = get_regular_or_end_post(i2p2, j2).get_points().mean(axis=0)
        pos_jp1 = get_regular_or_end_post(i2, j2p1).get_points().mean(axis=0)
        pos_jp2 = get_regular_or_end_post(i2, j2p2).get_points().mean(axis=0)
        y = pos_ip1[1] + ((i2 - i2p1) / (i2p2 - i2p1) * (pos_ip2[1] - pos_ip1[1]))
        x = pos_jp1[0] + ((j2 - j2p1) / (j2p2 - j2p1) * (pos_jp2[0] - pos_jp1[0]))
        if interpolate_z:
            z = 0.5 * (pos_jp1[2] + ((j2 - j2p1) / (j2p2 - j2p1) * (pos_jp2[2] - pos_jp1[2])) + pos_ip1[2] + ((i2 - i2p1) / (i2p2 - i2p1) * (pos_ip2[2] - pos_ip1[2])))
        else:
            z = extent_max[2]
        return Cube([d, d, kb.args.plate_thickness], center=True).translate([x, y, z])

    def get_post(i2, j2):
        if is_key(2 * ( (i2 - 1) // 2) + 1, 2 * ( (j2 - 1) // 2) + 1):
            return get_regular_post(i2, j2)
            # return Cube([d, d, kb.args.plate_thickness], center=True).translate(extent_max)
        elif is_end(i2, j2):
            return get_end_post(i2, j2)
            # return Cube([d, d, kb.args.plate_thickness], center=True).translate(extent_max)
        else:
            # return Cube([d, d, kb.args.plate_thickness], center=True).translate(extent_max)
            return get_interpolate(i2, j2)

    def get_hull(i2, j2, i2p1, j2p1):
        return Hull()(get_post(i2,j2), get_post(i2,j2p1), get_post(i2p1,j2), get_post(i2p1, j2p1))

    def get_block(i2, j2, i2p1, j2p1, at_z):
        p1 = get_post(i2,j2)
        p2 = get_post(i2,j2p1)
        p3 = get_post(i2p1,j2)
        p4 = get_post(i2p1,j2p1)
        pts = [Cube([d, d, kb.args.plate_thickness], center=True).translate([*p.get_points().mean(axis=0)[0:2], at_z]) for p in [p1, p2, p3, p4]]
        pts = pts + [p1, p2, p3, p4]
        return Hull()(*pts)

    hulls = []
    for i2 in range(i2range - 1):
        for j2 in range(j2range - 1):
            if not is_key(i2, j2):
                # hulls.append(get_post(i2, j2))
                hulls.append(get_hull(i2, j2, i2+1, j2+1))

    z_max = get_post(0,0).get_points().max(axis=0)[2]
    for i2 in range(i2range - 1):
        for j2 in range(j2range - 1):
            z = get_post(0,0).get_points().max(axis=0)[2]
            if z > z_max:
                z_max = z

    outer = []
    for i2 in range(i2range - 1):
        for j2 in range(j2range - 1):
            outer.append(get_block(i2, j2, i2+1, j2+1, z_max + 20.))

    hulls = Union()(hulls)
    outer = Union()(outer)
    xy_space = (np.array([*kb.args.grid_xy_space, 0]) - space_max) * np.array([1., 1., 0.])
    box_extent_max = extent_max + xy_space
    box_extent_min = extent_min - xy_space

    cutout_size = orig_extent_max + np.array([0., 0., 2.]) - orig_extent_min + 2 * space_min
    cutout_offset = (orig_extent_max + np.array([0., 0., 2.]) + orig_extent_min) / 2
    cutout = Cube(cutout_size, center=True).translate(cutout_offset)

    if kb.args.rounded_grid_case:
        shell = TentedRoundedShell(box_extent_min[0:2], box_extent_max[0:2], box_extent_max[2],
                                    z_below=100.,
                                    tent_function=kb.tent_and_z_offset,
                                    thickness=kb.args.case_thickness, radius=kb.args.grid_radius)
    else:
        raise RuntimeError()
        # shell = BoxShell(size, kb.args.case_thickness).translate(loc)
    cutout = kb.tent_and_z_offset(cutout)
    hulls = kb.tent_and_z_offset(hulls)
    outer = kb.tent_and_z_offset(outer)
    shell.shell = shell.shell.difference(cutout).union(hulls)
    shell.outer = shell.outer.difference(outer).union(hulls)
    shell.inner = shell.inner.difference(outer)

    return shell

def get_holder_with_hook(x_size, y_size, z_size, pcb_thickness, hook_width=3.0, hook_depth=2.0, hook_height=1.5, hook_offset=0.):
    c = Cube([x_size, y_size, z_size], center=True).translate([0., 0., z_size / 2])

    hook_back = Cube([hook_width, hook_depth, z_size + pcb_thickness + hook_height], center=True).translate([0., -hook_depth / 2, z_size / 2 + pcb_thickness / 2 + hook_height / 2])
    hook_cut = Cube([2 * hook_width, 2 * hook_height, 2 * hook_height], center=True).rotate(45, [1., 0., 0.]).translate([0., hook_height, np.sqrt(2) * hook_height])
    hook = Cube([hook_width, hook_height, hook_height], center=True).translate([0., hook_height / 2, hook_height / 2])

    hook = hook.difference(hook_cut).translate([0., 0., z_size + pcb_thickness]).union(hook_back).translate([hook_offset, -y_size / 2, 0.])

    return c.union(hook).translate([0., -y_size/2, -z_size - pcb_thickness])
