import math
from dataclasses import dataclass
from types import SimpleNamespace
from typing import List

from materialshapes.corner_rounding import CornerRounding
from materialshapes.point import Point
from materialshapes.rounded_polygon import RoundedPolygon
from materialshapes.utils import Matrix4


@dataclass(frozen=True)
class _PointNRound:
    p: Point
    r: CornerRounding = CornerRounding.unrounded


def _do_repeat(
    points: List[_PointNRound], reps: int, center: Point, mirroring: bool
) -> List[_PointNRound]:
    result = []

    if mirroring:
        measures = []
        for point in points:
            offset = point.p - center
            measures.append(
                SimpleNamespace(
                    angle=offset.angle_radians, distance=offset.get_distance()
                )
            )

        actual_reps = reps * 2
        section_angle = 2 * math.pi / actual_reps

        for r in range(actual_reps):
            for index in range(len(points)):
                i = index if r % 2 == 0 else len(points) - 1 - index
                if i > 0 or r % 2 == 0:
                    if r % 2 == 0:
                        angle = section_angle * r + measures[i].angle
                    else:
                        angle = (
                            section_angle * r
                            + section_angle
                            - measures[i].angle
                            + 2 * measures[0].angle
                        )
                    final_point = (
                        Point(math.cos(angle), math.sin(angle)) * measures[i].distance
                        + center
                    )
                    result.append(_PointNRound(final_point, points[i].r))
    else:
        np = len(points)
        for i in range(np * reps):
            rotated = points[i % np].p.rotate((i // np) * 360 / reps, center=center)
            result.append(_PointNRound(rotated, points[i % np].r))

    return result


@staticmethod
def _custom_polygon(
    pnr: List[_PointNRound], reps: int, center=Point(0.5, 0.5), mirroring=False
):
    actual_points = _do_repeat(pnr, reps, center, mirroring)

    vertices = [0.0] * (len(actual_points) * 2)
    per_vertex_rounding = [CornerRounding().unrounded] * len(actual_points)

    for i, ap in enumerate(actual_points):
        per_vertex_rounding[i] = ap.r
        j = i * 2
        vertices[j] = ap.p.x
        vertices[j + 1] = ap.p.y

    return RoundedPolygon.from_vertices(
        vertices,
        per_vertex_rounding=per_vertex_rounding,
        center_x=center.x,
        center_y=center.y,
    )


class MaterialShapes:
    _corner_round_15 = CornerRounding(radius=0.15)
    _corner_round_20 = CornerRounding(radius=0.2)
    _corner_round_30 = CornerRounding(radius=0.3)
    _corner_round_50 = CornerRounding(radius=0.5)
    _corner_round_100 = CornerRounding(radius=1)

    _negative_45_radians = -math.pi * 45 / 180
    _negative_90_radians = -math.pi * 90 / 180
    _negative_135_radians = -math.pi * 135 / 180

    circle = RoundedPolygon.circle(10, 0.5, 0.5, 0.5)

    square = RoundedPolygon.rectangle(
        1, 1, rounding=_corner_round_30, center_x=0.5, center_y=0.5
    )

    slanted = _custom_polygon(
        [
            _PointNRound(
                Point(0.926, 0.970), CornerRounding(radius=0.189, smoothing=0.811)
            ),
            _PointNRound(
                Point(-0.021, 0.967), CornerRounding(radius=0.187, smoothing=0.057)
            ),
        ],
        2,
    ).normalized()

    arch = (
        RoundedPolygon.from_vertices_num(
            4,
            per_vertex_rounding=[
                _corner_round_100,
                _corner_round_100,
                _corner_round_20,
                _corner_round_20,
            ],
        )
        .transformed(
            Matrix4.identity().rotate_z(_negative_135_radians).as_point_transformer()
        )
        .normalized()
    )

    semiCircle = RoundedPolygon.rectangle(
        1.6,
        1,
        per_vertex_rounding=[
            _corner_round_20,
            _corner_round_20,
            _corner_round_100,
            _corner_round_100,
        ],
    ).normalized()

    oval = (
        RoundedPolygon.circle()
        .transformed(
            Matrix4.identity()
            .rotate_z(_negative_45_radians)
            .scale(1.0, 0.64)
            .as_point_transformer()
        )
        .normalized()
    )

    pill = _custom_polygon(
        [
            _PointNRound(Point(0.961, 0.039), CornerRounding(radius=0.426)),
            _PointNRound(Point(1.001, 0.428), CornerRounding().unrounded),
            _PointNRound(Point(1, 0.609), CornerRounding(radius=1)),
        ],
        2,
        mirroring=True,
    ).normalized()

    triangle = (
        RoundedPolygon.from_vertices_num(3, rounding=_corner_round_20)
        .transformed(
            Matrix4.identity().rotate_z(_negative_90_radians).as_point_transformer()
        )
        .normalized()
    )

    arrow = _custom_polygon(
        [
            _PointNRound(Point(0.5, 0.892), CornerRounding(radius=0.313)),
            _PointNRound(Point(-0.216, 1.05), CornerRounding(radius=0.207)),
            _PointNRound(
                Point(0.499, -0.16), CornerRounding(radius=0.215, smoothing=1)
            ),
            _PointNRound(Point(1.225, 1.06), CornerRounding(radius=0.211)),
        ],
        1,
    ).normalized()

    fan = _custom_polygon(
        [
            _PointNRound(
                Point(1.004, 1), CornerRounding(radius=0.148, smoothing=0.417)
            ),
            _PointNRound(Point(0, 1), CornerRounding(radius=0.151)),
            _PointNRound(Point(0, -0.003), CornerRounding(radius=0.148)),
            _PointNRound(Point(0.978, 0.02), CornerRounding(radius=0.803)),
        ],
        1,
    ).normalized()

    diamond = _custom_polygon(
        [
            _PointNRound(
                Point(0.5, 1.096), CornerRounding(radius=0.151, smoothing=0.524)
            ),
            _PointNRound(Point(0.04, 0.5), CornerRounding(radius=0.159)),
        ],
        2,
    ).normalized()

    clamShell = _custom_polygon(
        [
            _PointNRound(Point(0.171, 0.841), CornerRounding(radius=0.159)),
            _PointNRound(Point(-0.02, 0.5), CornerRounding(radius=0.140)),
            _PointNRound(Point(0.17, 0.159), CornerRounding(radius=0.159)),
        ],
        2,
    ).normalized()

    pentagon = _custom_polygon(
        [
            _PointNRound(Point(0.5, -0.009), CornerRounding(radius=0.172)),
            _PointNRound(Point(1.03, 0.365), CornerRounding(radius=0.164)),
            _PointNRound(Point(0.828, 0.97), CornerRounding(radius=0.169)),
        ],
        1,
        mirroring=True,
    ).normalized()

    gem = _custom_polygon(
        [
            _PointNRound(
                Point(0.499, 1.023), CornerRounding(radius=0.241, smoothing=0.778)
            ),
            _PointNRound(Point(-0.005, 0.792), CornerRounding(radius=0.208)),
            _PointNRound(Point(0.073, 0.258), CornerRounding(radius=0.228)),
            _PointNRound(Point(0.433, -0), CornerRounding(radius=0.491)),
        ],
        1,
        mirroring=True,
    ).normalized()

    sunny = RoundedPolygon.star(
        num_vertices_per_radius=8, inner_radius=0.8, rounding=_corner_round_15
    ).normalized()

    verySunny = _custom_polygon(
        [
            _PointNRound(Point(0.5, 1.080), CornerRounding(radius=0.085)),
            _PointNRound(Point(0.358, 0.843), CornerRounding(radius=0.085)),
        ],
        8,
    ).normalized()

    cookie4Sided = _custom_polygon(
        [
            _PointNRound(Point(1.237, 1.236), CornerRounding(radius=0.258)),
            _PointNRound(Point(0.5, 0.918), CornerRounding(radius=0.233)),
        ],
        4,
    ).normalized()

    cookie6Sided = _custom_polygon(
        [
            _PointNRound(Point(0.723, 0.884), CornerRounding(radius=0.394)),
            _PointNRound(Point(0.5, 1.099), CornerRounding(radius=0.398)),
        ],
        6,
    ).normalized()

    cookie7Sided = (
        RoundedPolygon.star(
            num_vertices_per_radius=7, inner_radius=0.75, rounding=_corner_round_50
        )
        .transformed(
            Matrix4.identity().rotate_z(_negative_90_radians).as_point_transformer()
        )
        .normalized()
    )

    cookie9Sided = (
        RoundedPolygon.star(
            num_vertices_per_radius=9, inner_radius=0.8, rounding=_corner_round_50
        )
        .transformed(
            Matrix4.identity().rotate_z(_negative_90_radians).as_point_transformer()
        )
        .normalized()
    )

    cookie12Sided = (
        RoundedPolygon.star(
            num_vertices_per_radius=12, inner_radius=0.8, rounding=_corner_round_50
        )
        .transformed(
            Matrix4.identity().rotate_z(_negative_90_radians).as_point_transformer()
        )
        .normalized()
    )

    clover4Leaf = _custom_polygon(
        [
            _PointNRound(Point(0.5, 0.074), CornerRounding().unrounded),
            _PointNRound(Point(0.725, -0.099), CornerRounding(radius=0.476)),
        ],
        4,
        mirroring=True,
    ).normalized()

    clover8Leaf = _custom_polygon(
        [
            _PointNRound(Point(0.5, 0.036), CornerRounding().unrounded),
            _PointNRound(Point(0.758, -0.101), CornerRounding(radius=0.209)),
        ],
        8,
    ).normalized()

    burst = _custom_polygon(
        [
            _PointNRound(Point(0.5, -0.006), CornerRounding(radius=0.006)),
            _PointNRound(Point(0.592, 0.158), CornerRounding(radius=0.006)),
        ],
        12,
    ).normalized()

    softBurst = _custom_polygon(
        [
            _PointNRound(Point(0.193, 0.277), CornerRounding(radius=0.053)),
            _PointNRound(Point(0.176, 0.055), CornerRounding(radius=0.053)),
        ],
        10,
    ).normalized()

    boom = _custom_polygon(
        [
            _PointNRound(Point(0.457, 0.296), CornerRounding(radius=0.007)),
            _PointNRound(Point(0.5, -0.051), CornerRounding(radius=0.007)),
        ],
        15,
    ).normalized()

    softBoom = _custom_polygon(
        [
            _PointNRound(Point(0.733, 0.454), CornerRounding().unrounded),
            _PointNRound(Point(0.839, 0.437), CornerRounding(radius=0.532)),
            _PointNRound(
                Point(0.949, 0.449), CornerRounding(radius=0.439, smoothing=1)
            ),
            _PointNRound(Point(0.998, 0.478), CornerRounding(radius=0.174)),
        ],
        16,
        mirroring=True,
    ).normalized()

    flower = _custom_polygon(
        [
            _PointNRound(Point(0.370, 0.187), CornerRounding().unrounded),
            _PointNRound(Point(0.416, 0.049), CornerRounding(radius=0.381)),
            _PointNRound(Point(0.479, 0.001), CornerRounding(radius=0.095)),
        ],
        8,
        mirroring=True,
    ).normalized()

    puffy = (
        _custom_polygon(
            [
                _PointNRound(Point(0.5, 0.053), CornerRounding().unrounded),
                _PointNRound(Point(0.545, -0.04), CornerRounding(radius=0.405)),
                _PointNRound(Point(0.670, -0.035), CornerRounding(radius=0.426)),
                _PointNRound(Point(0.717, 0.066), CornerRounding(radius=0.574)),
                _PointNRound(Point(0.722, 0.128), CornerRounding().unrounded),
                _PointNRound(Point(0.777, 0.002), CornerRounding(radius=0.36)),
                _PointNRound(Point(0.914, 0.149), CornerRounding(radius=0.66)),
                _PointNRound(Point(0.926, 0.289), CornerRounding(radius=0.66)),
                _PointNRound(Point(0.881, 0.346), CornerRounding().unrounded),
                _PointNRound(Point(0.940, 0.344), CornerRounding(radius=0.126)),
                _PointNRound(Point(1.003, 0.437), CornerRounding(radius=0.255)),
            ],
            2,
            mirroring=True,
        )
        .transformed(Matrix4.identity().scale(1.0, 0.742).as_point_transformer())
        .normalized()
    )

    puffyDiamond = _custom_polygon(
        [
            _PointNRound(Point(0.87, 0.13), CornerRounding(radius=0.146)),
            _PointNRound(Point(0.818, 0.357), CornerRounding().unrounded),
            _PointNRound(Point(1, 0.332), CornerRounding(radius=0.853)),
        ],
        4,
        mirroring=True,
    ).normalized()

    ghostish = _custom_polygon(
        [
            _PointNRound(Point(0.5, 0), CornerRounding(radius=1)),
            _PointNRound(Point(1, 0), CornerRounding(radius=1)),
            _PointNRound(Point(1, 1.14), CornerRounding(radius=0.254, smoothing=0.106)),
            _PointNRound(Point(0.575, 0.906), CornerRounding(radius=0.253)),
        ],
        1,
        mirroring=True,
    ).normalized()

    pixelCircle = _custom_polygon(
        [
            _PointNRound(Point(0.5, 0), CornerRounding().unrounded),
            _PointNRound(Point(0.704, 0), CornerRounding().unrounded),
            _PointNRound(Point(0.704, 0.065), CornerRounding().unrounded),
            _PointNRound(Point(0.843, 0.065), CornerRounding().unrounded),
            _PointNRound(Point(0.843, 0.148), CornerRounding().unrounded),
            _PointNRound(Point(0.926, 0.148), CornerRounding().unrounded),
            _PointNRound(Point(0.926, 0.296), CornerRounding().unrounded),
            _PointNRound(Point(1, 0.296), CornerRounding().unrounded),
        ],
        2,
        mirroring=True,
    ).normalized()

    pixelTriangle = _custom_polygon(
        [
            _PointNRound(Point(0.11, 0.5), CornerRounding().unrounded),
            _PointNRound(Point(0.113, 0), CornerRounding().unrounded),
            _PointNRound(Point(0.287, 0), CornerRounding().unrounded),
            _PointNRound(Point(0.287, 0.087), CornerRounding().unrounded),
            _PointNRound(Point(0.421, 0.087), CornerRounding().unrounded),
            _PointNRound(Point(0.421, 0.17), CornerRounding().unrounded),
            _PointNRound(Point(0.56, 0.17), CornerRounding().unrounded),
            _PointNRound(Point(0.56, 0.265), CornerRounding().unrounded),
            _PointNRound(Point(0.674, 0.265), CornerRounding().unrounded),
            _PointNRound(Point(0.675, 0.344), CornerRounding().unrounded),
            _PointNRound(Point(0.789, 0.344), CornerRounding().unrounded),
            _PointNRound(Point(0.789, 0.439), CornerRounding().unrounded),
            _PointNRound(Point(0.888, 0.439), CornerRounding().unrounded),
        ],
        1,
        mirroring=True,
    ).normalized()

    bun = _custom_polygon(
        [
            _PointNRound(Point(0.796, 0.5), CornerRounding().unrounded),
            _PointNRound(Point(0.853, 0.518), CornerRounding(radius=1)),
            _PointNRound(Point(0.992, 0.631), CornerRounding(radius=1)),
            _PointNRound(Point(0.968, 1), CornerRounding(radius=1)),
        ],
        2,
        mirroring=True,
    ).normalized()

    heart = _custom_polygon(
        [
            _PointNRound(Point(0.5, 0.268), CornerRounding(radius=0.016)),
            _PointNRound(Point(0.792, -0.066), CornerRounding(radius=0.958)),
            _PointNRound(Point(1.064, 0.276), CornerRounding(radius=1)),
            _PointNRound(Point(0.501, 0.946), CornerRounding(radius=0.129)),
        ],
        1,
        mirroring=True,
    ).normalized()

    all = {
        "circle": circle,
        "square": square,
        "slanted": slanted,
        "arch": arch,
        "semiCircle": semiCircle,
        "oval": oval,
        "pill": pill,
        "triangle": triangle,
        "arrow": arrow,
        "fan": fan,
        "diamond": diamond,
        "clamShell": clamShell,
        "pentagon": pentagon,
        "gem": gem,
        "sunny": sunny,
        "verySunny": verySunny,
        "cookie4Sided": cookie4Sided,
        "cookie6Sided": cookie6Sided,
        "cookie7Sided": cookie7Sided,
        "cookie9Sided": cookie9Sided,
        "cookie12Sided": cookie12Sided,
        "clover4Leaf": clover4Leaf,
        "clover8Leaf": clover8Leaf,
        "burst": burst,
        "softBurst": softBurst,
        "boom": boom,
        "softBoom": softBoom,
        "flower": flower,
        "puffy": puffy,
        "puffyDiamond": puffyDiamond,
        "ghostish": ghostish,
        "pixelCircle": pixelCircle,
        "pixelTriangle": pixelTriangle,
        "bun": bun,
        "heart": heart,
    }
