from shell import BoxShell, ConicalShell
from super_solid import Cube, Cylinder, Sphere
from super_solid import Union, Difference, Intersection, Hull
from super_solid import Translate, Mirror, Scale, Rotate
from super_solid import rotation_matrix
import numpy as np
from scipy.optimize import minimize


def fit_cone_to_points(points):

    origin0 = [700., -1500., -700.]
    v0 = [-1., -0.5, 0.]
    psi0 = 70 * np.pi / 180.
    phi0 = 5 * np.pi / 180.
    x0 = np.array([*origin0, *v0, psi0, phi0])

    def get_points_in_cone_frame(points, origin, v, psi):
        """
        points: [N, 3] array of points to transform
        origin: [3] array of origin of the cone
        v: [3] array with rotation axis
        psi: angle of rotation
        NOTE: this inverts the cone rotation
        """
        mat = rotation_matrix(v, -psi)
        return np.einsum('ij,dj->di', mat, (points - origin))

    def opt_func(x, points):
        """origin, v, psi, phi"""
        origin = x[0:3]
        v = x[3:6]
        psi = x[6]
        phi = x[7]
        points = get_points_in_cone_frame(points, origin, v, psi)
        r2_points = points[:, 0] ** 2 + points[:, 1] ** 2
        r2_cone = (points[:, 2] * np.tan(phi)) ** 2
        return np.square((np.sqrt(r2_cone) - np.sqrt(r2_points))).mean()

    res = minimize(opt_func, x0, args=(points), method='Nelder-Mead', tol=1e-6)

    return res.x

def fit_oriented_box_to_extent(points):

    x0 = 0.
    def opt_func(x, points):
        mat = rotation_matrix([0., 0., 1.], -x)
        rotated_points = np.einsum('ij,dj->di', mat, points)
        area = (rotated_points[0:2].max() - rotated_points[0:2].min()).prod()
        return area

    res = minimize(opt_func, x0, args=(points), method='Nelder-Mead', tol=1e-6)

    mat = rotation_matrix([0., 0., 1.], -res.x)
    rotated_points = np.einsum('ij,dj->di', mat, points)
    extent_min = np.array([*rotated_points[:,0:2].min(axis=0), points[:,2].min()])
    extent_max = np.array([*rotated_points[:,0:2].max(axis=0), points[:,2].max()])
    size = extent_max - extent_min
    loc = (extent_max + extent_min) / 2
    return res.x[0] * 180 / np.pi, size, loc

def get_cone(origin, v, psi, phi):
    z1 = 10.
    z2 = 3000.
    r1 = np.tan(phi) * z1
    r2 = np.tan(phi) * z2
    return Cylinder((z2 - z1), r1=r1, r2=r2, center=False).translate([0., 0., z1]).rotate(psi * 180 / np.pi, v).translate(origin)

def get_conical_shell(origin, v, psi, phi, thickness):
    z2 = 3000.
    r2 = np.tan(phi) * z2
    return ConicalShell(z2, r2, thickness).translate([0., 0., -z2]).rotate(180., [1., 0., 0.]).rotate(psi * 180 / np.pi, v).translate(origin)

def get_points_from_transform(kb):

    kr = kb.args.key_hole_rim_width #key hole rim width
    kh = kb.args.keyswitch_height
    kw = kb.args.keyswitch_width
    pt = kb.args.plate_thickness

    extent = Cube([kw + kr * 2, kh + kr * 2, pt], center=True).translate([0., 0., pt / 2])

    points = []
    for i in range(kb.args.n_thumbs):
        points.append(kb.transform_thumb(extent, i).get_points())

    return np.concatenate(points, axis=0)
