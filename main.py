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

# def cube(x, y=None, z=None):
#     if y is None:
#

class Keyboard():

    def __init__(self, args):

        self.args = args

        # TODO: add to arguments
        self.tenting_angle = np.pi / 12 * 180. / np.pi
        self.keyboard_z_offset = 9.
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
        kr = 1.5 # TODO: merge with other parameter
        return Cube([self.args.keyswitch_width + 2 * kr, self.args.keyswitch_height + 2 * kr, 50.], center=True)


    def transform_switch(self, shape, row, col):
        """Key placement function

        Places shape according to the internal key column dictionary, with the CAP TOPS on a torus, the holes will follow larger radii
        Note:
        Need (these operations are applied in order):
          - minor radius of the torus, row angle spacing, and row offset angle
          - major radius of the torus, column angle
          - rotation of the torus around the z axis  (always 0 for dactyl)
          - origin of the torus  (column-offset for dactyl)
          - overal tenting angle and z offset
        >this does not do the tenting or final z offset

        """
        cap_top_height = self.args.plate_thickness + self.args.key_height  #this is the distance from the bottom of the plate, to top of key
        total_rr = self.minor_radii[col] + cap_top_height
        total_cr = self.major_radii[col] + cap_top_height

        #rotate around x for row offset:
        row_angle = self.minor_angle_offset[col] + self.minor_angle_delta[col] * row
        shape = rotate_around_origin(shape, [0., 0., total_rr], row_angle, [1., 0., 0.])

        #rotate around y for column offset
        shape = rotate_around_origin(shape, [0., 0., total_cr], self.major_angle[col], [0., 1., 0.])

        shape = rotate_around_origin(shape, [0., 0., 0.], self.z_rotation_angle[col], [0., 0., 1.])

        #translation per column (origin of torus)
        shape = Translate(self.column_offsets[col])(shape)
        return shape


    def tent_and_z_offset(self, shape):
        """
          - overal tenting angle and z offset
        """
        # tenting angle
        shape = rotate_around_origin(shape, [0., 0., 0.], self.tenting_angle, [0., 1., 0.])

        #z offset:
        shape = Translate(np.array([0., 0., self.keyboard_z_offset]))(shape)
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

    def get_vertical_wall_between_shells(self, col0, col1):
        """get a vertical wall between the shells of col0 and col1"""

        cap_top_height = self.args.plate_thickness + self.args.key_height  #this is the distance from the bottom of the plate, to top of key
        total_rr0 = self.minor_radii[col0] + cap_top_height
        total_rr1 = self.minor_radii[col1] + cap_top_height
        outer_cylinder_0 = Translate([0., 0., r=total_rr0 + self.args.plate_thickness])(Rotate(90, [0,1,0])(Cylinder(50., total_rr0 + self.args.plate_thickness, center=True)))
        inner_cylinder_0 = Translate([0., 0., r=total_rr0 + self.args.plate_thickness])(Rotate(90, [0,1,0])(Cylinder(50., total_rr0, center=True)))
        outer_cylinder_1 = Translate([0., 0., r=total_rr0 + self.args.plate_thickness])(Rotate(90, [0,1,0])(Cylinder(50., total_rr1 + self.args.plate_thickness, center=True)))
        inner_cylinder_1 = Translate([0., 0., r=total_rr0 + self.args.plate_thickness])(Rotate(90, [0,1,0])(Cylinder(50., total_rr1, center=True)))
        #TODO: update this with with a rotate_column function
        #rotate around y for column offset
        total_cr = self.major_radii[col0] + cap_top_height
        outer_cylinder_0 = rotate_around_origin(outer_cylinder_0, [0., 0., total_cr], self.major_angle[col0], [0., 1., 0.])
        outer_cylinder_0 = rotate_around_origin(outer_cylinder_0, [0., 0., 0.], self.z_rotation_angle[col0], [0., 0., 1.])
        inner_cylinder_0 = rotate_around_origin(inner_cylinder_0, [0., 0., total_cr], self.major_angle[col0], [0., 1., 0.])
        inner_cylinder_0 = rotate_around_origin(inner_cylinder_0, [0., 0., 0.], self.z_rotation_angle[col0], [0., 0., 1.])
        #translation per column (origin of torus)
        outer_cylinder_0 = Translate(self.column_offsets[col0])(outer_cylinder_0)
        inner_cylinder_0 = Translate(self.column_offsets[col0])(inner_cylinder_0)

        total_cr = self.major_radii[col1] + cap_top_height
        outer_cylinder_1 = rotate_around_origin(outer_cylinder_1, [0., 0., total_cr], self.major_angle[col1], [0., 1., 0.])
        outer_cylinder_1 = rotate_around_origin(outer_cylinder_1, [0., 0., 0.], self.z_rotation_angle[col1], [0., 0., 1.])
        inner_cylinder_1 = rotate_around_origin(inner_cylinder_1, [0., 0., total_cr], self.major_angle[col1], [0., 1., 0.])
        inner_cylinder_1 = rotate_around_origin(inner_cylinder_1, [0., 0., 0.], self.z_rotation_angle[col1], [0., 0., 1.])
        #translation per column (origin of torus)
        outer_cylinder_1 = Translate(self.column_offsets[col1])(outer_cylinder_1)
        inner_cylinder_1 = Translate(self.column_offsets[col1])(inner_cylinder_1)

        #TODO: consolidate this as I have already calculated the points
        point_dummy = Cube([self.args.keyswitch_height + 2 * self.args.key_hole_rim_width, self.args.keyswitch_width + 2 * self.args.key_hole_rim_width, self.args.plate_thickness], center=True)
        points0 = Union()([self.transform_switch(point_dummy, i, col0) for i in range(self.column_nrows[col0])]).get_points()
        points1 = Union()([self.transform_switch(point_dummy, i, col1) for i in range(self.column_nrows[col1])]).get_points()

        #TODO: make parameter
        wall_thickness = 1.0
        wall0 = get_y_wall_between_points(points0, points1, wall_thickness, margin=[0., 50., 20.])
        wall1 = get_y_wall_between_points(points0, points1, wall_thickness, margin=[0., 50., 20.])

        wall0 = Difference()(Intersection()(outer_cylinder_1, wall0), inner_cylinder_0)
        wall1 = Difference()(Intersection()(outer_cylinder_0, wall1), inner_cylinder_1)

        return wall0 + wall1





    def get_shell_with_cutouts_for_column(self, col):
        # get a half cylindrical shell
        cap_top_height = self.args.plate_thickness + self.args.key_height  #this is the distance from the bottom of the plate, to top of key
        total_rr = self.minor_radii[col] + cap_top_height
        shell = Translate([0., 0., total_rr + self.args.plate_thickness])(half_cylindrical_shell(total_rr + self.args.plate_thickness, self.args.plate_thickness, 50.))

        total_cr = self.major_radii[col] + cap_top_height

        #TODO: update this with with a rotate_column function
        #rotate around y for column offset
        shell = rotate_around_origin(shell, [0., 0., total_cr], self.major_angle[col], [0., 1., 0.])
        shell = rotate_around_origin(shell, [0., 0., 0.], self.z_rotation_angle[col], [0., 0., 1.])
        #translation per column (origin of torus)
        shell = Translate(self.column_offsets[col])(shell)

        # get points:
        cutout = Cube([self.args.keyswitch_height + 2 * self.args.key_hole_rim_width, self.args.keyswitch_width + 2 * self.args.key_hole_rim_width, 10.], center=True)
        point_dummy = Cube([self.args.keyswitch_height + 2 * self.args.key_hole_rim_width, self.args.keyswitch_width + 2 * self.args.key_hole_rim_width, self.args.plate_thickness], center=True)
        cutouts = []
        points = []
        for i in range(self.column_nrows[col]):
            cutouts.append(self.transform_switch(cutout, i, col))
            points.append(self.transform_switch(cutout, i, col))

        points = Union()(*points).get_points()

        #TODO: make param
        boundary_margin = 15.0
        if col < self.args.ncols - 1:
            upper_points = Union()([self.transform_switch(point_dummy, i, col + 1) for i in range(self.column_nrows[col + 1])]).get_points()
        else:
            upper_points = np.array([[points[:,0].max() + 2 * boundary_margin, points[:,1].mean(), points[:,2].mean()]]) # times 2 because it finds midway
        if col > 0:
            lower_points = Union()([self.transform_switch(point_dummy, i, col - 1) for i in range(self.column_nrows[col - 1])]).get_points()
        else:
            lower_points = np.array([[points[:,0].min() - 2 * boundary_margin, points[:,1].mean(), points[:,2].mean()]]) # times 2 because it finds midway

        shell = Difference()(shell, *cutouts)


        shell = Intersection()(cube_surrounding_column(points, lower_points, upper_points, margin=[0., 50., 50.]), shell)


        #TODO: make parameters

        # fit a box: around the cutouts, and difference


        #
        #

        ## make a toroidal shell
        ##
        ## make a box that limits that shell that is a boundary with the next column
        return shell


    def get_model(self):

        key_holes = []
        shells = []
        for j in range(self.args.ncols):
            shells.append(self.get_shell_with_cutouts_for_column(j))
            if j < self.args.ncols - 1:
                shells.append(self.get_vertical_wall_between_shells(j, j + 1))
            for i in range(self.column_nrows[j]):
                key_holes.append(self.transform_switch(self.single_keyhole(), i, j))

        key_holes = [self.tent_and_z_offset(shape) for shape in key_holes]
        shells = [self.tent_and_z_offset(shape) for shape in shells]


        # for i in range(5):
        #     key_holes.append(self.transform_thumb(i, self.single_keyhole()))

        return sum(key_holes)  + sum(shells)


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
