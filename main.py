import argparse
from solid_update import Cube, Cylinder, Sphere
from solid_update import Union, Difference, Intersection, Hull
from solid_update import Translate, Mirror, Scale, Rotate
from solid import scad_render_to_file
import sys
import numpy as np

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

    def single_keyhole(self):

        keyhole = Cube(10)

        # some shortcuts
        kr = 1.5 #TODO make parameter
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

        plate_half = left_wall + top_wall

        if self.args.create_side_nubs:
            plate_half = plate_half + side_nub


        top_nub = Translate([kw / 2, 0, rht / 2])(Cube([5., 5., rht], center=True))
        top_nub_pair = top_nub + Mirror([0, 1, 0])(Mirror([1, 0, 0])(top_nub))

        plate = plate_half + Mirror([0, 1, 0])(Mirror([1, 0, 0])(plate_half))
        plate = plate - Rotate(90, [0, 0, 1])(top_nub_pair)

        return plate

    def switch_cutout(self):
        kr = 1.5 # TODO: merge with other parameter
        return Cube([self.args.keyswitch_width + 2 * kr, self.args.keyswitch_height + 2 * kr, 50.], center=True)

    def transform_switch(self, shape, row, col):
        cap_top_height = self.args.plate_thickness + self.args.key_height
        mh = self.args.keyswitch_height + 3.0

        rr = (self.args.extra_height + mh) / 2 / np.sin(self.args.alpha * np.pi / 180 / 2) + cap_top_height
        cr = (self.args.extra_height + mh) / 2 / np.sin(self.args.beta * np.pi / 180 / 2) + cap_top_height

        shape = rotate_around_origin(shape, [0., 0., rr], row * self.args.alpha, [1., 0., 0.])
        shape = rotate_around_origin(shape, [0., 0., cr], col * self.args.beta, [0., 1., 0.])

        return shape

    def get_spherical_shell(self):
        cap_top_height = self.args.plate_thickness + self.args.key_height
        mh = self.args.keyswitch_height + 3.0

        rr = (self.args.extra_height + mh) / 2 / np.sin(self.args.alpha * np.pi / 180 / 2) + cap_top_height

        shell = Translate([0., 0., rr])(Sphere(rr + 0.2 * self.args.plate_thickness, segments=50) - Sphere(rr - 0.8 * self.args.plate_thickness, segments=50))

        limit_box = Translate([-70., -10., -20])(Cube([80., 90., 100.]))

        cut_shell = shell * limit_box

        return cut_shell


    def get_model(self):

        shell = self.get_spherical_shell()

        key_holes = []
        for i in range(-2, self.args.nrows-2):
            for j in range(-2, self.args.ncols-2):
                key_holes.append(self.transform_switch(self.single_keyhole(), i, j))

                shell = shell - self.transform_switch(self.switch_cutout(), i, j)

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
        parser.add_argument('--create-side-nubs', default=1, type=int,
                               help='Create side nubs for the key holes')

        parser.add_argument('--alpha', default=10, type=float,
                               help='Row angle')
        parser.add_argument('--beta', default=10, type=float,
                               help='Column angle')

        parser.add_argument('--key-height', default=12.7, type=float,
                               help='Key height')
        parser.add_argument('--extra-height', default=1.0, type=float,
                               help='Extra height for key spacing')

        parser.add_argument('--nrows', default=4, type=int,
                               help='Create side nubs for the key holes')
        parser.add_argument('--ncols', default=4, type=int,
                               help='Create side nubs for the key holes')


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
