import argparse
from super_solid import Cube, Cylinder, Sphere
from super_solid import Union, Difference, Intersection, Hull
from super_solid import Translate, Mirror, Scale, Rotate
from super_solid import rotation_matrix
from solid import scad_render_to_file
import sys
import numpy as np
from collections import defaultdict
from utils import cube_around_points, cube_surrounding_column, get_cylindrical_shell, get_y_wall_between_points, rotate_around_origin, get_spherical_shell, half_cylindrical_shell
from shell import CylinderShell, BoxShell, SphericalShell, ConicalShell, WalledCylinderShells, half_cylinder_shell

# def cube(x, y=None, z=None):
#     if y is None:
#

class Keyboard():

    def __init__(self, args):

        self.args = args

        # TODO: add to arguments
        # self.tenting_angle = np.pi / 12 * 180. / np.pi
        self.tenting_angle = 0 * np.pi / 12 * 180. / np.pi
        # self.keyboard_z_offset = 9.
        self.keyboard_z_offset = 0.
        self.thumb_offsets = np.array([6., -3., 7.])
        self.center_col = 2  #TODO: mark params
        self.center_row = self.args.nrows - 3 # TODO: make params

        mh = self.args.keyswitch_height + 2 * self.args.key_hole_rim_width
        cr = (self.args.extra_height + mh) / 2 / np.sin(self.args.beta * np.pi / 180 / 2)
        rr = (self.args.extra_height + mh) / 2 / np.sin(self.args.alpha * np.pi / 180 / 2)
        self.major_radii = {i : cr for i in range(self.args.ncols)} #radius of column rotation
        self.major_angle = {i : (self.center_col - i) * self.args.beta for i in range(self.args.ncols)} #offset angle

        self.minor_radii = {i : rr for i in range(self.args.ncols)}
        self.minor_angle_offset = {i : self.args.alpha * self.center_row for i in range(self.args.ncols)}
        self.minor_angle_delta = {i : -self.args.alpha for i in range(self.args.ncols)}

        self.z_rotation_angle = {i : 0.0 for i in range(self.args.ncols)}
        self.z_rotation_angle[4] = -5.

        self.column_offsets = defaultdict(lambda: np.zeros(3))
        self.column_offsets[2] = np.array([0., 2.82, -4.5])
        self.column_offsets[4] = np.array([5., -8, 5.64])
        self.column_offsets[5] = np.array([0., -12, 5.64])

        self.column_nrows = defaultdict(lambda: self.args.nrows)
        self.column_nrows[0] = self.args.nrows - 1
        self.column_nrows[1] = self.args.nrows - 1
        self.column_nrows[4] = self.args.nrows - 1

        #often used, and shortcuts
        self.cap_top_height = self.args.plate_thickness + self.args.key_height  #this is the distance from the bottom of the plate, to top of key
        self.cth = self.cap_top_height # shortcut

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
        return Cube([self.args.keyswitch_width + 2 * kr, self.args.keyswitch_height + 2 * kr, 50.], center=True)

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

    def transform_switch(self, shape, row, col):
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

    def transform_thumb(self, i, shape):
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


    def get_shell_for_column(self, col):
        # get a half cylindrical shell
        total_rr = self.minor_radii[col] + self.cth
        cylinder_h = 50. #TODO: make a param?
        shell = half_cylinder_shell(cylinder_h, total_rr + self.args.plate_thickness / 2, self.args.plate_thickness).rotate(-90, [0., 1., 0.]).translate([0., 0., total_rr])

        #TODO: decide if to put this in this function or later in the loop?
        shell = self.transform_column(shell, col)
        shell = self.tent_and_z_offset(shell)
        return shell

    def get_key_separations(self):
        x_margin = 2.#TODO: make parameter
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


    def get_case(self, extent_min, extent_max):
        print(extent_min, extent_max)
        size = (extent_max - extent_min) + np.array([5., 5., 2.]) + self.args.plate_thickness#TODO: make param
        offset = (extent_max + extent_min) / 2
        case = BoxShell(size, thickness=self.args.plate_thickness, close_top=True, close_bottom=False).translate(offset)
        return case


    def get_model(self):

        key_holes = []
        shells = []
        for j in range(self.args.ncols):
            shells.append(self.get_shell_for_column(j))
            # if j < self.args.ncols - 1:
                # shells.append(self.get_vertical_wall_between_shells(j, j + 1))
            for i in range(self.column_nrows[j]):
                key_holes.append(self.transform_switch(self.single_keyhole(), i, j))


        x_loc, extent_min, extent_max = self.get_key_separations()
        case = self.get_case(extent_min, extent_max)
        shell = WalledCylinderShells(shells, x_loc, thickness=self.args.plate_thickness, y_min=-100, y_max=100., z_min=-100, z_max=100)
        case = case.difference(shell)

        # for i in range(5):
        #     key_holes.append(self.transform_thumb(i, self.single_keyhole()))

        return sum(key_holes)  + case.get_shell()


    def to_scad(self, model=None, fname=None):

        if fname is None:
            fname = self.args.output_file_name

        if model is None:
            model = self.get_model()

        scad_render_to_file(model, fname)

    @staticmethod
    def add_args(parser):
        parser.add_argument('--output-file-name', default="things/model.scad", type=str,
                               help='Output filename')

        parser.add_argument('--keyswitch-width', default=14.2, type=float,
                               help='width of the keyswitch')
        parser.add_argument('--keyswitch-height', default=14.2, type=float,
                               help='height of the keyswitch')
        parser.add_argument('--plate-thickness', default=2.0, type=float,
                               help='Thickness of the mounting plate')
        parser.add_argument('--side-nub-thickness', default=4.0, type=float,
                               help='Thickness of side nubs')
        parser.add_argument('--retention-tab-thickness', default=1.5, type=float,
                               help='Thickness of retention tabs')
        parser.add_argument('--key-hole-rim-width', default=1.5, type=float,
                               help='Thickness of the rim around the key-holes')
        parser.add_argument('--create-side-nubs', default=0, type=int,
                               help='Create side nubs for the key holes')

        parser.add_argument('--alpha', default=15, type=float,
                               help='Row angle')
        parser.add_argument('--beta', default=5, type=float,
                               help='Column angle')

        parser.add_argument('--key-height', default=12.7, type=float,
                               help='Key height')
        parser.add_argument('--extra-height', default=1.0, type=float,
                               help='Extra height for key spacing')

        parser.add_argument('--nrows', default=4, type=int,
                               help='Create side nubs for the key holes')
        parser.add_argument('--ncols', default=5, type=int,
                               help='Create side nubs for the key holes')

        parser.add_argument('--column-0-parameters', default=[], nargs='+', type=int,
                                help='Minor radius, major radius, minor angle offset, major angle offset,')

parser = argparse.ArgumentParser()

Keyboard.add_args(parser)

args = parser.parse_args([])

kb = Keyboard(args)

model = kb.get_model()

kb.to_scad(model=model, fname='things/model.scad')

if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    Keyboard.add_args(parser)

    args = parser.parse_args()

    kb = Keyboard(args)

    model = kb.get_model()

    kb.to_scad(model=model, fname='things/model.scad')
