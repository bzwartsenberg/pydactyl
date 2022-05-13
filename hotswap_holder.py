from argparse import Namespace
import argparse
from types import SimpleNamespace

from super_solid import Cube, Cylinder, Sphere
from super_solid import Union, Difference, Intersection, Hull
from super_solid import Translate, Mirror, Scale, Rotate
from shell import CylinderShell, BoxShell, SphericalShell, ConicalShell, PlateShell, TentedRoundedShell, WalledCylinderShells, half_cylinder_shell, Shell, RoundedBoxShell
import yaml

from utils import get_holder_with_hook
from main import Keyboard

# parser = argparse.ArgumentParser()

# Keyboard.add_args(parser)

# args = parser.parse_args()

# kb = Keyboard(args)

keyswitch_height = 13.8
keyswitch_width = 13.9

mount_width = keyswitch_width + 3.0
mount_height = keyswitch_height + 3.0

holder_x = mount_width
holder_thickness = (holder_x - keyswitch_width) / 2 # rim width
holder_y = keyswitch_height + 2 * holder_thickness

swap_x = holder_x
swap_y = holder_y
swap_z = 3.
swap_offset_xyz = [0., 0., - swap_z / 2]
square_led_size = 6
hotswap_x2 = (holder_x / 3) * 1.85
hotswap_y1 = 4.3 # first y-size of kailh hotswap holder
hotswap_y2 = 6.2 # second y-size of kailh hotswap holder
hotswap_z = swap_z + 0.5 # thickness of kailn hotswap holder + some margin of printing error (0.5mm)
hotswap_cutout_z_offset = -2.6
hotswap_cutout_1_y_offset = 4.95
hotswap_cutout_2_y_offset = 4
hotswap_case_cutout_x_extra = 2.75

swap_holder = Cube([swap_x, swap_y, swap_z], center=True).translate(swap_offset_xyz)


hotswap_x = holder_x
hotswap_x3 = holder_x / 4
hotswap_y3 = hotswap_y1 / 2

hotswap_cutout_1_x_offset = 0.01
hotswap_cutout_3_x_offset = holder_x / 2 - hotswap_x3 / 2.01
hotswap_cutout_4_x_offset = hotswap_x3 / 2.01 - holder_x / 2


hotswap_cutout_led_x_offset = 0
hotswap_cutout_led_y_offset = -7

hotswap_cutout_1 = Cube([holder_x, hotswap_y1, hotswap_z], center=True).translate([0.01, 4.95, hotswap_cutout_z_offset])
hotswap_cutout_2 = Cube([hotswap_x2, hotswap_y2, hotswap_z], center=True).translate([-holder_x / 4.5, 4.0, hotswap_cutout_z_offset])
hotswap_cutout_3 = Cube([holder_x / 4., hotswap_y1 / 2, hotswap_z], center=True).translate([holder_x / 2 - hotswap_x3 / 2.01, 7.4, hotswap_cutout_z_offset])
hotswap_cutout_4 = Cube([holder_x / 4., hotswap_y1 / 2, hotswap_z], center=True).translate([- holder_x / 2 + hotswap_x3 / 2.01, 7.4, hotswap_cutout_z_offset])

hotswap_led_cutout = Cube([square_led_size, square_led_size, 10.], center=True).translate([hotswap_cutout_led_x_offset, hotswap_cutout_led_y_offset, hotswap_cutout_z_offset])
cutouts = Union()(*[hotswap_cutout_1, hotswap_cutout_2, hotswap_cutout_3, hotswap_cutout_4])


diode_wire_dia = 0.75
diode_wire_channel_depth = 1.5 * diode_wire_dia
diode_body_width = 1.95
diode_body_length = 4
diode_corner_hole = Cylinder(h=2*hotswap_z, r=diode_wire_dia, segments=50, center=True).translate([-6.55, -6.75, 0])

diode_socket_hole_right = Cylinder(h=hotswap_z, r=diode_wire_dia, center=True, segments=50).translate([6.85, 3.5, 0])
diode_channel_pin_right = Cube([diode_wire_dia, 2.5, diode_wire_channel_depth], center=True).rotate(-18., [0., 0., 1]).translate([6.45, 2., -0.49 * diode_wire_channel_depth])
diode_channel_pin_right_lower = Cube([diode_wire_dia, 2.5, diode_wire_channel_depth], center=True).rotate(-45., [0., 0., 1]).translate([5.95, -2.3, -0.49 * diode_wire_channel_depth])
diode_channel_pin_right_joint = Cube([diode_wire_dia*2, 5.0, diode_wire_channel_depth], center=True).rotate(-90., [0., 0., 1]).translate([2.95, -3.0, -0.49 * diode_wire_channel_depth])
diode_loc_x = -6.25
diode_loc_y = -.0
diode_view_hole = Cube([diode_body_width / 2, diode_body_length / 1.25, 2 * hotswap_z], center=True).translate([diode_loc_x, diode_loc_y, 0])
diode_body = Cube([diode_body_width, diode_body_length, diode_body_width], center=True).translate([diode_loc_x, diode_loc_y, -0.49 * diode_wire_channel_depth])
diode_cutout = Union()(diode_view_hole,  diode_body).mirror([1.,0.,0.]).union(diode_socket_hole_right, diode_channel_pin_right, diode_channel_pin_right_lower, diode_channel_pin_right_joint)

fac = 1.3
wire_right = Cube([diode_wire_dia*fac, 9.4, diode_wire_channel_depth*fac], center=True).rotate(-90., [0., 0., 1]).translate([0.50, -3.0, -0.49 * fac * diode_wire_channel_depth])
wire_right_hole = Cylinder(h=2*hotswap_z, r=diode_wire_dia, segments=50, center=True).translate([-4.85, -6.25, 0])
wire_right2 = Cube([diode_wire_dia*fac, 2.4, diode_wire_channel_depth*fac], center=True).rotate(-00., [0, 0., 1]).translate([-4.85, -4.89, -0.49 * fac* diode_wire_channel_depth])
wire_right3 = Cube([diode_wire_dia*fac, 1.5, diode_wire_channel_depth*fac], center=True).rotate(-45., [0., 0., 1]).translate([-4.45, -3.45, -0.49 * fac* diode_wire_channel_depth])
wire_right_cutout = Union()(wire_right, wire_right_hole, wire_right2, wire_right3)
# wire_right = Cube([diode_wire_dia, 10.0, diode_wire_channel_depth], center=True).rotate(-90., [0., 0., 1]).translate([0.00, -3.0, -0.49 * diode_wire_channel_depth])




fac = 1.2
left_wire_x = -6.85
wire_left_hole = Cylinder(h=2*hotswap_z, r=diode_wire_dia, segments=50, center=True).translate([left_wire_x, -6.25, 0])
wire_socket_hole_left = Cylinder(h=hotswap_z, r=diode_wire_dia, center=True, segments=50).translate([left_wire_x, 1.5, 0])
wire_left = Cube([fac*diode_wire_dia, 7.6, diode_wire_channel_depth], center=True).rotate(-00., [0., 0., 1]).translate([left_wire_x, -2.8, -0.49 * diode_wire_channel_depth])
wire_left_cutout = Union()(wire_socket_hole_left, wire_left_hole, wire_left)
# diode_channel_pin_left = Cube([diode_wire_dia, 2.5, diode_wire_channel_depth], center=True).rotate(10., [0., 0., 1]).translate([-6.55, 0., -0.49 * diode_wire_channel_depth])
# diode = Union()(diode_socket_hole_right, diode_channel_pin_right)
# other_diode = Union()(diode_socket_hole_left, diode_socket_hole_right, diode_channel_pin_left, diode_channel_pin_right)


main_axis_hole = Cylinder(h=10., r=4.1 / 2, center=True, segments=50)
pin_hole = Cylinder(h=10., r=3.3/2, center=True, segments=50)
plus_hole = pin_hole.translate([2.54, 5.08, 0])
minus_hole = pin_hole.translate([-3.81, 2.54, 0])

model = swap_holder.difference(cutouts,
                               main_axis_hole,
                               plus_hole,
                               minus_hole,
                               # diode_cutout,
                               # diode_cutout.mirror([1.,0.,0]),
                               wire_left_cutout,
                               wire_right_cutout,
                               diode_cutout,
                               hotswap_led_cutout)
# model = cutouts


model.write_scad('things/holder.scad')
# (difference
#             ; (union
#                     swap-holder
#                     ; (debug diode-channel-wire))
#             main-axis-hole
#             plus-hole
#             minus-hole
#             friction-hole-left
#             friction-hole-right
#             diode-cutout
#             diode-socket-hole-left
#             diode-channel-pin-left
#             (mirror [1 0 0] diode-cutout)
#             diode-socket-hole-right
#             diode-channel-pin-right
#             hotswap-cutout
#             hotswap-led-cutout)
