import argparse
from super_solid import Cube, Cylinder, Sphere
from super_solid import Union, Difference, Intersection, Hull
from super_solid import Translate, Mirror, Scale, Rotate
from super_solid import rotation_matrix
from solid import scad_render_to_file
import sys
import numpy as np
from collections import defaultdict
from thumb_utils import fit_cone_to_points, fit_oriented_box_to_extent, get_cone, get_conical_shell, get_points_from_transform
from utils import cube_around_points, cube_surrounding_column, get_cylindrical_shell, get_holder_with_hook, get_hulls, get_y_wall_between_points, rotate_around_origin, get_spherical_shell, half_cylindrical_shell
from shell import CylinderShell, BoxShell, RoundedBoxShell, SphericalShell, ConicalShell, TentedRoundedShell, WalledCylinderShells, half_cylinder_shell
import yaml
from types import SimpleNamespace
from pprint import pprint

eps = 1e-1

class Keyboard():

    def __init__(self, args):

        self.load_config(args)
        self.parse_config()

        # self.args = args


        #often used, and shortcuts
        self.cap_top_height = self.args.plate_thickness + self.args.key_height  #this is the distance from the bottom of the plate, to top of key
        self.cth = self.cap_top_height # shortcut

    def load_config(self, args):
        with open(f'config/{args.config}.yaml', 'r') as f:
            config = yaml.safe_load(f)
        print(f'Using {args.config} configuration:')
        pprint(config)
        self.args = SimpleNamespace(**config, **args.__dict__)

    def parse_config(self):
        #TODO: clean up
        self.thumb_offsets = np.array([6., -3., 7.])

        for i in range(self.args.ncols):
            if not hasattr(self.args, f'column_{i}'):
                column_dict = {'angle': i * self.args.beta + self.args.column_angle_offset}
                column_dict.update(self.args.default_column) # TODO: check if this gives problems with mutable objects like lists?
                setattr(self.args, f'column_{i}', column_dict)

        # TODO: clean this up, so that it is not necessary anymore
        self.tenting_angle = self.args.tenting_angle
        self.keyboard_z_offset = self.args.keyboard_z_offset
        self.major_radii = {i : self.args.column_radius for i in range(self.args.ncols)} #radius of column rotation
        self.major_angle = {i : getattr(self.args, f'column_{i}')['angle'] for i in range(self.args.ncols)} #column angle
        self.minor_radii = {i : getattr(self.args, f'column_{i}')['row_radius']  for i in range(self.args.ncols)}
        self.minor_angle_offset = {i : getattr(self.args, f'column_{i}')['row_angle_offset'] for i in range(self.args.ncols)}
        self.minor_angle_delta = {i : self.args.alpha for i in range(self.args.ncols)}
        self.z_rotation_angle = {i : getattr(self.args, f'column_{i}')['z_rotation_angle']  for i in range(self.args.ncols)}
        self.column_offsets = {i : getattr(self.args, f'column_{i}')['column_offset']  for i in range(self.args.ncols)}
        self.column_nrows = {i : getattr(self.args, f'column_{i}')['nrows']  for i in range(self.args.ncols)}



    #TODO: clean up
    def single_keyhole(self):

        # some shortcuts
        kr = self.args.key_hole_rim_width #key hole rim width
        kh = self.args.keyswitch_height
        kw = self.args.keyswitch_width
        pt = self.args.plate_thickness

        #top wall
        translation = Translate([0., kr / 2 + kh / 2, pt / 2])
        top_wall = translation(Cube([kw + kr * 2, kr, pt], center=True))

        #side wall:
        translation = Translate([kr / 2 + kw / 2, 0., pt / 2])
        left_wall = translation(Cube([kr, kh + kr * 2, pt], center=True))

        #side-nub:
        rt = self.args.retention_tab_thickness
        st = self.args.side_nub_thickness
        rht = pt - rt
        nw = 2.75  # nub width
        rotation = Rotate(90, [1, 0, 0])
        translation = Translate([kw /2, 0, 0])
        partial_side_nub_1 = rotation(translation(Cylinder(1.0, r=nw, center=True, segments=30)))
        partial_side_nub_2 = Translate([kr / 2 + kw / 2, 0, st / 2])(Cube([kr, nw, st], center=True))
        side_nub = Translate([0., 0., pt - st])(Hull()(partial_side_nub_1, partial_side_nub_2))

        plate_half = Union()(left_wall, top_wall)

        if self.args.create_side_nubs:
            plate_half = Union()(plate_half, side_nub)


        top_nub = Translate([kw / 2, 0, rht / 2])(Cube([5., 5., rht], center=True))
        top_nub_pair = Union()(top_nub, Mirror([0, 1, 0])(Mirror([1, 0, 0])(top_nub)))

        plate = Union()(plate_half, Mirror([0, 1, 0])(Mirror([1, 0, 0])(plate_half)))
        plate = Difference()(plate, Rotate(90, [0, 0, 1])(top_nub_pair))

        return plate

    def switch_cutout(self):
        kr = self.args.key_hole_rim_width
        return Cube([self.args.keyswitch_width + 2 * kr, self.args.keyswitch_height + 2 * kr, 7.], center=True)

    def transform_row(self, shape, row, col):
        """First part of the key placement function,
        Places keys by a rotation around x, for parameters given for col, row
        Args:
            shape: the object to be transformed
            row: row index
            col: column index
        """
        total_rr = self.minor_radii[col] + self.cth # row radius
        #rotate around x for row offset:
        row_angle = self.minor_angle_offset[col] + self.minor_angle_delta[col] * row
        shape = rotate_around_origin(shape, [0., 0., total_rr], row_angle, [1., 0., 0.])
        return shape

    def transform_column(self, shape, col):
        """Second part of the key placement function,
        Places keys by a rotation around y, then a rotation around z and an arbitrary translation
        Args:
            shape: the object to be transformed
            row: row index
            col: column index
        """
        total_cr = self.major_radii[col] + self.cth # column radius
        #rotate around y for column offset
        shape = rotate_around_origin(shape, [0., 0., total_cr], self.major_angle[col], [0., 1., 0.])
        #rotate around z:
        shape = rotate_around_origin(shape, [0., 0., 0.], self.z_rotation_angle[col], [0., 0., 1.])
        #translation per column (origin of torus)
        shape = shape.translate(self.column_offsets[col])
        return shape

    def transform_switch(self, shape, row, col, tent_and_z_offset=True):
        """Key placement function

        Places shape according to the internal key column dictionary, with the CAP TOPS on a torus,
        the holes will follow larger radii. See individual placement function for purpose of
        each of the parameters
        Note:
        Need the following parameters: (these operations are applied in order):
          - minor radius of the torus, row angle spacing, and row offset angle
          - major radius of the torus, column angle
          - rotation of the torus around the z axis  (always 0 for dactyl)
          - origin of the torus  (column-offset for dactyl)
          - overal tenting angle and z offset
        """
        shape = self.transform_row(shape, row, col)
        shape = self.transform_column(shape, col)
        if tent_and_z_offset:
            shape = self.tent_and_z_offset(shape)
        return shape


    def tent_and_z_offset(self, shape):
        """
        Third part of the placement function: overal tenting angle and z offset
        Args:
            shape: shape to be transformed
        """
        # tenting angle
        shape = rotate_around_origin(shape, [0., 0., 0.], self.tenting_angle, [0., 1., 0.])
        #z offset:
        shape = shape.translate(np.array([0., 0., self.keyboard_z_offset]))
        return shape

    def get_thumb_origin(self):
        #TODO: use the interface I made for this
        # position at col 1, and lastrow
        position = np.array([-4.18483045012826, -33.155898546096395, 24.16276298368095])
        return position

    def transform_thumb(self, shape, i):
        # these should be on circles around some origin
        # give a normal vector, and rotate around it,
        # Then take an orthobgonal vector, and rotate around that too, but with opposite curvature
        # This should create a saddle point

        thumb_origin = self.get_thumb_origin()

        if i == 0:
            shape = rotate_around_origin(shape, [0., 0., 0.], 14., [1., 0., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], -15., [0., 1., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], 10., [0., 0., 1.])
            shape = Translate(thumb_origin)(shape)
            shape = Translate(np.array([-15., -10., 5.]))(shape)
        elif i == 1:
            shape = rotate_around_origin(shape, [0., 0., 0.], 10., [1., 0., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], -23., [0., 1., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], 25., [0., 0., 1.])
            shape = Translate(thumb_origin)(shape)
            shape = Translate(np.array([-35., -16., -2.]))(shape)
        elif i == 2:
            shape = rotate_around_origin(shape, [0., 0., 0.], 10., [1., 0., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], -23., [0., 1., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], 25., [0., 0., 1.])
            shape = Translate(thumb_origin)(shape)
            shape = Translate(np.array([-23., -34., -6.]))(shape)
        elif i == 3:
            shape = rotate_around_origin(shape, [0., 0., 0.], 6., [1., 0., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], -34., [0., 1., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], 35., [0., 0., 1.])
            shape = Translate(thumb_origin)(shape)
            shape = Translate(np.array([-39., -43., -16.]))(shape)
        elif i == 4:
            shape = rotate_around_origin(shape, [0., 0., 0.], 6., [1., 0., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], -32., [0., 1., 0.])
            shape = rotate_around_origin(shape, [0., 0., 0.], 35., [0., 0., 1.])
            shape = Translate(thumb_origin)(shape)
            shape = Translate(np.array([-51., -25., -11.5]))(shape)
        return shape

    def get_thumb_case_and_limit_box(self):
        points = get_points_from_transform(self)
        oriented_box_ang, oriented_size, oriented_loc = fit_oriented_box_to_extent(points)
        space = np.array(self.args.thumb_space)
        extent_max = points.max(axis=0) + space
        extent_min = points.min(axis=0) - space
        if self.args.thumb_case == 'cone':
            x = fit_cone_to_points(points)
            shell = get_conical_shell(x[0:3], x[3:6], x[6], x[7], self.args.case_thickness, segments=self.args.cone_segments)
            if self.args.rounded_thumb_case:
                square_box = RoundedBoxShell(extent_max - extent_min, self.args.case_thickness, radius=self.args.thumb_radius, round_top=False, round_bottom=False).translate((extent_max + extent_min) / 2)
                square_limit_box = RoundedBoxShell(extent_max - extent_min - space + 2 * np.array([self.args.thumb_extra_x_space, 0., 500]), self.args.case_thickness, radius=self.args.thumb_radius, round_top=False, round_bottom=False).translate((extent_max + extent_min) / 2).translate([-self.args.thumb_extra_x_space, 0., 0.])
                oriented_box = RoundedBoxShell(oriented_size + 2 * space, self.args.case_thickness, radius=self.args.thumb_radius, round_top=False, round_bottom=False).translate(oriented_loc).rotate(oriented_box_ang, [0., 0., 1.])
                oriented_limit_box = RoundedBoxShell(oriented_size + 2 * space + 2 * np.array([self.args.thumb_extra_x_space, -eps, 500]), self.args.case_thickness, radius=self.args.thumb_radius, round_top=False, round_bottom=False).translate(oriented_loc).translate([-self.args.thumb_extra_x_space, 0., 0.]).rotate(oriented_box_ang, [0., 0., 1.])
            else:
                square_box = BoxShell(extent_max - extent_min, self.args.case_thickness).translate((extent_max + extent_min) / 2)
                square_limit_box = BoxShell(extent_max - extent_min - np.array([2 * space[0] - eps -self.args.case_thickness, 2 * space[1] - eps -self.args.case_thickness, 100.]), self.args.case_thickness).translate((extent_max + extent_min) / 2)
                oriented_box = BoxShell(oriented_size + space, self.args.case_thickness).translate(oriented_loc).rotate(oriented_box_ang, [0., 0., 1.])
                oriented_limit_box = BoxShell(oriented_size + 2 * np.array([0., 0., 500]), self.args.case_thickness).translate(oriented_loc).rotate(oriented_box_ang, [0., 0., 1.])
            if self.args.thumb_box == 'square':
                box = square_box
                limit_box = square_limit_box
            elif self.args.thumb_box == 'oriented':
                box = oriented_box
                limit_box = oriented_limit_box
            elif self.args.thumb_box == 'intersection':
                box = oriented_box.intersection(square_box)
                limit_box = oriented_limit_box.intersection(square_limit_box)
            else:
                raise ValueError(f'Unkown value for thumb_box {self.args.thumb_box}')
            shell = shell.intersection(box)
        else:
            raise ValueError(f'Unkown thumb case type {self.args.thumb_case}')

        return shell, limit_box

    def get_shell_for_column(self, col):
        # get a half cylindrical shell
        total_rr = self.minor_radii[col] + self.cth
        cylinder_h = 50. #TODO: make a param?
        shell = half_cylinder_shell(cylinder_h, total_rr + self.args.plate_thickness / 2, self.args.plate_thickness).rotate(-90, [0., 1., 0.]).translate([0., 0., total_rr])

        shell = self.transform_column(shell, col)
        return shell

    def get_key_separations(self):
        x_margin = 2.#TODO: make parameter, used for the cylinders with walls
        x_loc = []
        extent_min = []
        extent_max = []
        for j in range(self.args.ncols - 1):
            point_dummy = Cube([self.args.keyswitch_height + 2 * self.args.key_hole_rim_width, self.args.keyswitch_width + 2 * self.args.key_hole_rim_width, self.args.plate_thickness], center=True)
            points0 = Union()([self.transform_column(self.transform_row(point_dummy, i, j), j) for i in range(self.column_nrows[j])]).get_points()
            points1 = Union()([self.transform_column(self.transform_row(point_dummy, i, j + 1), j + 1) for i in range(self.column_nrows[j + 1])]).get_points()
            if j == 0:
                x_loc.append(points0[:,0].min() - x_margin)
            x_loc.append((points0[:,0].max() + points1[:,0].min())/2)
            if j == self.args.ncols - 2:
                x_loc.append(points1[:,0].max() + x_margin)
            extent_min.append(points0.min(axis=0, keepdims=True))
            extent_max.append(points0.max(axis=0, keepdims=True))
            extent_min.append(points1.min(axis=0, keepdims=True))
            extent_max.append(points1.max(axis=0, keepdims=True))
        extent_min = np.concatenate(extent_min, axis=0).min(axis=0)
        extent_max = np.concatenate(extent_max, axis=0).max(axis=0)
        return x_loc, extent_min, extent_max

    def get_switch_min(self):
        switch_dummy = Cube([self.args.keyswitch_height + 2 * self.args.key_hole_rim_width, self.args.keyswitch_width + 2 * self.args.key_hole_rim_width, self.args.keyswitch_space_below], center=True).translate([0., 0., - (self.args.keyswitch_space_below) / 2 + self.args.plate_thickness])
        all_points = []
        dummies = []
        for j in range(self.args.ncols):
            for i in range(self.column_nrows[j]):
                tr_switch_dummy = self.tent_and_z_offset(self.transform_column(self.transform_row(switch_dummy, i, j), j))
                dummies.append(tr_switch_dummy)
                all_points.append(tr_switch_dummy.get_points())
        for i in range(self.args.n_thumbs):
                tr_switch_dummy = self.transform_thumb(switch_dummy, i, )
                dummies.append(tr_switch_dummy)
                all_points.append(tr_switch_dummy.get_points())
        all_points = np.concatenate(all_points, axis=0)
        switch_min = all_points[:,2].min()
        return switch_min


    def get_hulls(self, extent_min, extent_max):
        return get_hulls(self, extent_min, extent_max)

    def get_case(self):
        x_loc, extent_min, extent_max = self.get_key_separations()
        space = np.array(self.args.grid_xy_space)

        if self.args.main_grid_support_type == 'cylinders':
            shells = []
            for j in range(self.args.ncols):
                shells.append(self.get_shell_for_column(j))
            support = WalledCylinderShells(shells, x_loc, thickness=self.args.case_thickness * 0.8, y_min=-100, y_max=100., z_min=-100, z_max=100)
            if self.args.rounded_grid_case:
                case = TentedRoundedShell(extent_min[0:2] - space, extent_max[0:2] + space, extent_max[2],
                                          z_below=100.,
                                          tent_function=self.tent_and_z_offset,
                                          thickness=self.args.case_thickness, radius=self.args.grid_radius)
            else:
                raise RuntimeError('')
            case = case.difference(self.tent_and_z_offset(support))
        elif self.args.main_grid_support_type == 'hulls':
            case = self.get_hulls(extent_min, extent_max)
        else:
            raise ValueError(f'Unkown grid support type {self.args.main_grid_support_type}')

        return case

    def get_screw_inserts(self, screw_corners, case_split_z):

        outer = Cylinder(self.args.screw_insert_h , r=self.args.screw_insert_od / 2 + 1.6, center=True, segments=30).translate([0., 0., (self.args.screw_insert_h ) / 2])
        inner = Cylinder(self.args.screw_insert_h + 2 * eps, r=self.args.screw_insert_od / 2, center=True, segments=30).translate([0., 0., -eps]).translate([0., 0., (self.args.screw_insert_h) / 2])

        insert_post = outer.difference(inner)

        insert_posts = []
        for screw_corner in screw_corners:
            d = self.args.screw_inset
            s = np.array(screw_corner) - np.sign(np.array(screw_corner)) * d
            insert_posts.append(insert_post.translate([*s, case_split_z]))

        return insert_posts

    def get_screw_hole_cutouts(self, screw_corners, bottom_case_h):
        screw_hole_cutouts = []
        for screw_corner in screw_corners:
            d = self.args.screw_inset
            s = np.array(screw_corner) - np.sign(np.array(screw_corner)) * d

            cutout = CylinderShell((bottom_case_h) * 2 + self.args.case_thickness, self.args.screw_head_size / 2 + self.args.case_thickness, self.args.case_thickness, close_ends=True, segments=50).translate([0., 0., -bottom_case_h  -self.args.case_thickness / 2])
            cutout.shell = cutout.shell.difference(Cylinder(2 * self.args.case_thickness, self.args.screw_od / 2, center=True, segments=50))
            screw_hole_cutouts.append(cutout.translate([*s, 0.]))
        return screw_hole_cutouts

    def get_trs_holder(self, z_size):
        trs_hole_size = 5.0
        holder = get_holder_with_hook(self.args.trs_rest_width, self.args.trs_pcb_length, z_size - trs_hole_size / 2, self.args.trs_pcb_thickness, hook_height=1.0, hook_width=self.args.trs_rest_width)
        holder = holder.translate([0., 0., - trs_hole_size / 2])
        cutout = Cylinder(5.0, r=trs_hole_size / 2, center=True, segments=50).rotate(90., [1., 0., 0.])
        return holder, cutout

    def get_microcontroller_holder(self, z_size):
        usb_c_size = 2.8
        usb_c_width = 9.
        holder = get_holder_with_hook(self.args.mc_rest_width, self.args.mc_pcb_length + 0.5, z_size - usb_c_size / 2, self.args.mc_pcb_thickness, hook_height=1.0, hook_width=self.args.mc_rest_width)
        holder = holder.translate([0., 0., - usb_c_size / 2])
        c1 = Cylinder(5.0, r=usb_c_size / 2, center=True, segments=50).rotate(90., [1., 0., 0.]).translate([usb_c_width / 2 - usb_c_size / 2, 0., 0.])
        c2 = Cylinder(5.0, r=usb_c_size / 2, center=True, segments=50).rotate(90., [1., 0., 0.]).translate([-usb_c_width / 2 + usb_c_size / 2, 0., 0.])
        cutout = Hull()(c1, c2)
        return holder, cutout

    def make_models(self):

        key_holes = []
        cutouts = []
        for j in range(self.args.ncols):
            for i in range(self.column_nrows[j]):
                key_holes.append(self.transform_switch(self.single_keyhole(), i, j))
                cutouts.append(self.transform_switch(self.switch_cutout(), i, j))

        case = self.get_case()
        screw_corners = [np.array(s) for s in case.get_screw_corners()]
        screw_corners.append(screw_corners[2] + np.array(self.args.thumb_extra_screw_offset))
        screw_corners[2] += np.array(self.args.thumb_screw_offset) #TODO: clean this up

        for i in range(self.args.n_thumbs):
            key_holes.append(self.transform_thumb(self.single_keyhole(), i))
            cutouts.append(self.transform_thumb(self.switch_cutout(), i))

        thumb_case, limit_box = self.get_thumb_case_and_limit_box()
        case = case.difference(limit_box, outer=True)
        case = case.union(thumb_case, outer=False)

        switch_min = self.get_switch_min()

        bottom_plate = BoxShell([1000., 1000., 1000.], self.args.case_thickness, center=True).translate([0., 0., -500. + switch_min - self.args.space_below_lowest_switch])

        case = case.difference(bottom_plate)

        case_split_z = switch_min +  self.args.cut_relative_to_lowest_switch
        bottom_case_h = self.args.space_below_lowest_switch + self.args.cut_relative_to_lowest_switch

        xy_offset = screw_corners[0]
        trs_holder, trs_cutout = self.get_trs_holder(bottom_case_h)
        trs_holder, trs_cutout = trs_holder.rotate(90, [0., 0., 1.]), trs_cutout.rotate(90, [0., 0., 1.])
        trs_holder = trs_holder.translate([*xy_offset, 0]).translate([self.args.case_thickness, -self.args.trs_y_offset, case_split_z])
        trs_cutout = trs_cutout.translate([*xy_offset, 0]).translate([0., -self.args.trs_y_offset, case_split_z])

        mc_holder, mc_cutout = self.get_microcontroller_holder(bottom_case_h)
        insert_posts = self.get_screw_inserts(screw_corners, case_split_z)
        mc_holder = mc_holder.translate([*xy_offset, 0]).translate([self.args.mc_x_offset, -self.args.case_thickness, case_split_z])
        mc_cutout = mc_cutout.translate([*xy_offset, 0]).translate([self.args.mc_x_offset, 0., case_split_z])

        cut_bottom = Cube([1000., 1000., 1000.], center=True).translate([0., 0., 500. + case_split_z])

        screw_hole_cutouts = self.get_screw_hole_cutouts(screw_corners, bottom_case_h)

        bottom_model = case
        for screw_hole_cutout in screw_hole_cutouts:
            bottom_model = bottom_model.difference(screw_hole_cutout.translate([0., 0., case_split_z]), outer=False)

        bottom_model = bottom_model.shell.difference(cut_bottom).difference(trs_cutout).difference(mc_cutout).union(trs_holder).union(mc_holder)

        self.bottom_model = bottom_model

        for cutout in cutouts:
            case = case.difference(cutout)

        cut = Cube([1000., 1000., 1000.], center=True).translate([0., 0., -500. + case_split_z])

        self.top_model = case.shell.difference(cut).difference(trs_cutout).difference(mc_cutout) + sum(key_holes) + sum(insert_posts)
        # self.top_model = case.shell.difference(cut) + sum(key_holes)

        self.top_and_bottom = self.bottom_model.translate([0., 0., -1]).union(self.top_model)


    def to_scad(self, model, fname=None):

        if fname is None:
            fname = self.args.output_file_name

        scad_render_to_file(model, fname)

    @staticmethod
    def add_args(parser):
        parser.add_argument('--output-file-name', default="things/model.scad", type=str,
                               help='Output filename')
        parser.add_argument('--config', default="dactyl", type=str,
                               help='Name of the yaml configuration')

        # parser.add_argument('--keyswitch-width', default=14.2, type=float,
        #                        help='width of the keyswitch')
        # parser.add_argument('--keyswitch-height', default=14.2, type=float,
        #                        help='height of the keyswitch')
        # parser.add_argument('--plate-thickness', default=2.0, type=float,
        #                        help='Thickness of the mounting plate')
        # parser.add_argument('--side-nub-thickness', default=4.0, type=float,
        #                        help='Thickness of side nubs')
        # parser.add_argument('--retention-tab-thickness', default=1.5, type=float,
        #                        help='Thickness of retention tabs')
        # parser.add_argument('--key-hole-rim-width', default=1.5, type=float,
        #                        help='Thickness of the rim around the key-holes')
        # parser.add_argument('--create-side-nubs', default=0, type=int,
        #                        help='Create side nubs for the key holes')

        # parser.add_argument('--alpha', default=15, type=float,
        #                        help='Row angle')
        # parser.add_argument('--beta', default=5, type=float,
        #                        help='Column angle')

        # parser.add_argument('--key-height', default=12.7, type=float,
        #                        help='Key height')
        # parser.add_argument('--extra-height', default=1.0, type=float,
        #                        help='Extra height for key spacing')

        # parser.add_argument('--nrows', default=4, type=int,
        #                        help='Create side nubs for the key holes')
        # parser.add_argument('--ncols', default=5, type=int,
        #                        help='Create side nubs for the key holes')

        # parser.add_argument('--column-0-parameters', default=[], nargs='+', type=int,
        #                         help='Minor radius, major radius, minor angle offset, major angle offset,')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    Keyboard.add_args(parser)

    args = parser.parse_args()

    kb = Keyboard(args)
    # print(kb.minor_angle_offset)
    # print(kb.minor_angle_delta)
    # print(kb.major_angle)
    # print(kb.z_rotation_angle)
    # print(kb.column_offsets)
    # print(kb.column_nrows)
    # print(kb.major_radii)
    # print(kb.minor_radii)

    kb.make_models()

    plate = kb.single_keyhole()


    kb.to_scad(kb.bottom_model, fname='things/bottom_model.scad')
    kb.to_scad(kb.top_model, fname='things/model.scad')

    kb.to_scad(plate, fname='things/plate.scad')
