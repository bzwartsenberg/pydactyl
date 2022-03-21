import argparse
from solid import union, difference, cube, sphere, scad_render_to_file, translate, mirror, rotate, hull, cylinder
import sys

# def cube(x, y=None, z=None):
#     if y is None:

class Keyboard():

    def __init__(self, args):

        self.args = args

    def single_keyhole(self):

        keyhole = cube(10)

        # some shortcuts
        kr = 1.5 #TODO make parameter
        kh = self.args.keyswitch_height
        kw = self.args.keyswitch_width
        pt = self.args.plate_thickness

        #top wall
        translation = translate([0., kr / 2 + kh / 2, pt / 2])
        top_wall = translation(cube([kw + kr * 2, kr, pt], center=True))

        #side wall:
        translation = translate([kr / 2 + kw / 2, 0., pt / 2])
        left_wall = translation(cube([kr, kh + kr * 2, pt], center=True))

        #side-nub:
        rt = self.args.retention_tab_thickness
        st = self.args.side_nub_thickness
        rht = pt - rt
        nw = 2.75  # nub width
        rotation = rotate(90, [1, 0, 0])
        translation = translate([kw /2, 0, 0])
        partial_side_nub_1 = rotation(translation(cylinder(1.0, nw, center=True, segments=30)))
        partial_side_nub_2 = translate([kr / 2 + kw / 2, 0, st / 2])(cube([kr, nw, st], center=True))
        side_nub = translate([0., 0., pt - st])(hull()(partial_side_nub_1, partial_side_nub_2))

        plate_half = left_wall + top_wall

        if self.args.create_side_nubs:
            plate_half = plate_half + side_nub


        top_nub = translate([kw / 2, 0, rht / 2])(cube([5., 5., rht], center=True))
        top_nub_pair = top_nub + mirror([0, 1, 0])(mirror([1, 0, 0])(top_nub))

        plate = plate_half + mirror([0, 1, 0])(mirror([1, 0, 0])(plate_half))
        plate = plate - rotate(90, [0, 0, 1])(top_nub_pair)

        return plate


    def get_model(self):

        return self.single_keyhole()


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
if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    Keyboard.add_args(parser)

    args = parser.parse_args()

    kb = Keyboard(args)

    keyhole = kb.single_keyhole()

    kb.to_scad(model=keyhole, fname='things/test.scad')
