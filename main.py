import argparse
from solid_update import Cube, Cylinder, Sphere
from solid_update import Union, Difference, Intersection, Hull
from solid_update import Translate, Mirror, Scale, Rotate
from solid_update import rotation_matrix
from solid import scad_render_to_file
import sys
import numpy as np
from collections import defaultdict

# def cube(x, y=None, z=None):
#     if y is None:
#
def rotate_around_origin(shape, origin, angle, axis):
    shape = Translate([-v for v in origin])(shape)
    shape = Rotate(angle, axis)(shape)
    shape = Translate(origin)(shape)

    return shape


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
        partial_side_nub_1 = rotation(translation(Cylinder(1.0, nw, center=True, segments=30)))
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

        # tenting angle
        shape = rotate_around_origin(shape, [0., 0., 0.], self.tenting_angle, [0., 1., 0.])

        #z offset:
        shape = Translate(np.array([0., 0., self.keyboard_z_offset]))(shape)

        return shape

    def dactyl_transform_switch(self, shape, row, col):
        """Key placement function

        Places shape according to the internal key column dictionary, with the cap tops on a torus
        Note:
        Need (these operations are applied in order):
          - minor radius of the torus, row angle spacing, and row offset angle
          - major radius of the torus, column angle
          - rotation of the torus around the z axis  (always 0 for dactyl)
          - origin of the torus  (column-offset for dactyl)
        >this does not do the tenting or final z offset
        """
        cap_top_height = self.args.plate_thickness + self.args.key_height  #this is the distance from the bottom of the plate, to top of key
        #
        # "mount-height" in dactyl, this is the spacing between keysthat is used to determine the radius of rows and colums,
        # together with the angles alpha and beta, by imposing that every key be on a circle segment with a fixed angle,
        # of vertical size mh = 2 * r * sin(angle / 2), with r the radius that is used to place the keys, and angle the fixed angle
        mh = self.args.keyswitch_height + 2 * self.args.key_hole_rim_width

        rr = (self.args.extra_height + mh) / 2 / np.sin(self.args.alpha * np.pi / 180 / 2) + cap_top_height
        cr = (self.args.extra_height + mh) / 2 / np.sin(self.args.beta * np.pi / 180 / 2) + cap_top_height

        #rotate around x for row offset:
        shape = rotate_around_origin(shape, [0., 0., rr], (self.center_row - row) * self.args.alpha, [1., 0., 0.])

        #rotate around y for column offset
        shape = rotate_around_origin(shape, [0., 0., cr], (self.center_col - col) * self.args.beta, [0., 1., 0.])

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


    def get_spherical_shell(self):
        cap_top_height = self.args.plate_thickness + self.args.key_height
        mh = self.args.keyswitch_height + 3.0

        rr = (self.args.extra_height + mh) / 2 / np.sin(self.args.alpha * np.pi / 180 / 2) + cap_top_height

        shell = Translate([0., 0., rr])(Sphere(rr + 0.2 * self.args.plate_thickness, segments=50) - Sphere(rr - 0.8 * self.args.plate_thickness, segments=50))

        limit_box = Translate([-70., -10., -20])(Cube([80., 90., 100.]))

        cut_shell = shell * limit_box

        return cut_shell

    def get_shell_with_cutouts_for_column(self, col):

        ## make a toroidal shell
        ##
        ## make a box that limits that shell that is a boundary with the next column
        pass


    def get_model(self):

        shell = self.get_spherical_shell()

        key_holes = []
        for j in range(self.args.ncols):
            for i in range(self.column_nrows[j]):
                key_holes.append(self.transform_switch(self.single_keyhole(), i, j))



        shell = shell - self.transform_switch(self.switch_cutout(), i, j)


        for i in range(5):
            key_holes.append(self.transform_thumb(i, self.single_keyhole()))
        # for i in range(1): # for debugging
        #     for j in range(1):
        #         test = Cube([10., 10., 10.])
        #         print(f"unrotated points for row {i} col {j} ", test.get_points())
        #         rot_test = self.transform_switch(test, i, j)
        #         print(f"unrotated points for row {i} col {j} ", rot_test.get_points())
        #         key_holes.append(self.transform_switch(self.single_keyhole(), i, j))

        #         shell = shell - self.transform_switch(self.switch_cutout(), i, j)

        return sum(key_holes) 


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
