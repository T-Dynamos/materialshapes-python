import math
from typing import Callable, List

import cairo

from materialshapes.point import Point

distance_epsilon = 1e-5
angle_epsilon = 1e-6
relaxed_distance_epsilon = 5e-3
two_pi = math.pi * 2


# minimal copy of vector_math/vector_math_64.dart
class Matrix4:
    def __init__(self):
        self.m = [
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ]

    @staticmethod
    def identity():
        return Matrix4()

    def multiply(self, other):
        result = Matrix4()
        for i in range(4):
            for j in range(4):
                result.m[i][j] = sum(self.m[i][k] * other.m[k][j] for k in range(4))
        return result

    def rotate_z(self, radians):
        c, s = math.cos(radians), math.sin(radians)
        rotation = Matrix4()
        rotation.m[0][0] = c
        rotation.m[0][1] = -s
        rotation.m[1][0] = s
        rotation.m[1][1] = c
        return self.multiply(rotation)

    def scale(self, sx, sy):
        scaling = Matrix4()
        scaling.m[0][0] = sx
        scaling.m[1][1] = sy
        return self.multiply(scaling)

    def transform_point(self, x, y):
        nx = self.m[0][0] * x + self.m[0][1] * y + self.m[0][3]
        ny = self.m[1][0] * x + self.m[1][1] * y + self.m[1][3]
        return (nx, ny)

    def as_point_transformer(self):
        return lambda x, y: self.transform_point(x, y)


def distance(x: float, y: float) -> float:
    return math.sqrt(x * x + y * y)


def distance_squared(x: float, y: float) -> float:
    return x * x + y * y


def direction_vector(x: float, y: float) -> Point:
    d = distance(x, y)
    if d == 0:
        raise ValueError("Required distance greater than zero.")
    return Point(x / d, y / d)


def direction_vector_from_angle(angle_radians: float) -> Point:
    return Point(math.cos(angle_radians), math.sin(angle_radians))


def radial_to_cartesian(
    radius: float, angle_radians: float, center: Point = Point(0, 0)
) -> Point:
    direction = direction_vector_from_angle(angle_radians)
    return direction * radius + center


def square(x: float) -> float:
    return x * x


def positive_modulo(num: float, mod: float) -> float:
    return (num % mod + mod) % mod


def collinear_ish(
    aX: float,
    aY: float,
    bX: float,
    bY: float,
    cX: float,
    cY: float,
    tolerance: float = distance_epsilon,
) -> bool:
    ab = Point(bX - aX, bY - aY).rotate_90()
    ac = Point(cX - aX, cY - aY)
    dot_product = ab.dot_product(ac).abs()
    relative_tolerance = tolerance * ab.get_distance() * ac.get_distance()
    return dot_product < tolerance or dot_product < relative_tolerance


def convex(previous: Point, current: Point, next: Point) -> bool:
    return (current - previous).clockwise(next - current)


def find_minimum(
    v0: float, v1: float, f: Callable[[float], float], tolerance: float = 1e-3
) -> float:
    a, b = v0, v1
    while b - a > tolerance:
        c1 = (2 * a + b) / 3
        c2 = (2 * b + a) / 3
        if f(c1) < f(c2):
            b = c2
        else:
            a = c1
    return (a + b) / 2


def binary_search_by(
    sorted_list: List,
    key: Callable,
    compare: Callable,
    value: any,
    start: int = 0,
    end: int = None,
) -> int:
    if end is None:
        end = len(sorted_list)

    min_idx = start
    max_idx = end

    while min_idx < max_idx:
        mid = min_idx + ((max_idx - min_idx) >> 1)
        element = sorted_list[mid]
        comp = compare(key(element), value)

        if comp == 0:
            return mid
        elif comp < 0:
            min_idx = mid + 1
        else:
            max_idx = mid

    return -min_idx - 1


def path_from_cubics(
    ctx: cairo.Context,
    cubics: list,
    start_angle: int,
    repeat_path: bool,
    close_path: bool,
    rotation_pivot_x: float,
    rotation_pivot_y: float,
):
    first = True
    first_cubic = None

    ctx.new_path()

    for cubic in cubics:
        if first:
            ctx.move_to(cubic.anchor0_x, cubic.anchor0_y)
            if start_angle != 0:
                first_cubic = cubic
            first = False

        ctx.curve_to(
            cubic.control0_x,
            cubic.control0_y,
            cubic.control1_x,
            cubic.control1_y,
            cubic.anchor1_x,
            cubic.anchor1_y,
        )

    if repeat_path:
        first_in_repeat = True
        for cubic in cubics:
            if first_in_repeat:
                ctx.line_to(cubic.anchor0_x, cubic.anchor0_y)
                first_in_repeat = False

            ctx.curve_to(
                cubic.control0_x,
                cubic.control0_y,
                cubic.control1_x,
                cubic.control1_y,
                cubic.anchor1_x,
                cubic.anchor1_y,
            )

    if close_path:
        ctx.close_path()

    if start_angle != 0 and first_cubic is not None:
        angle_to_first = math.atan2(
            cubics[0].anchor0_y - rotation_pivot_y,
            cubics[0].anchor0_x - rotation_pivot_x,
        )
        rotation_angle = -angle_to_first + (start_angle * math.pi / 180)

        # Rotate around the pivot point
        ctx.translate(rotation_pivot_x, rotation_pivot_y)
        ctx.rotate(rotation_angle)
        ctx.translate(-rotation_pivot_x, -rotation_pivot_y)

    return ctx


def path_from_rounded_polygon(
    ctx: cairo.Context,
    rounded_polygon,
    start_angle=0,
    repeat_path=False,
    close_path=True,
):
    return path_from_cubics(
        ctx=ctx,
        cubics=rounded_polygon.cubics,
        start_angle=start_angle,
        repeat_path=repeat_path,
        close_path=close_path,
        rotation_pivot_x=rounded_polygon.center.x,
        rotation_pivot_y=rounded_polygon.center.y,
    )


def path_from_morph(
    ctx: cairo.Context,
    morph,
    progress,
    start_angle=0,
    repeat_path=False,
    close_path=True,
    rotation_pivot_x=0,
    rotation_pivot_y=0,
):
    return path_from_cubics(
        ctx=ctx,
        cubics=morph.as_cubics(progress),
        start_angle=start_angle,
        repeat_path=repeat_path,
        close_path=close_path,
        rotation_pivot_x=rotation_pivot_x,
        rotation_pivot_y=rotation_pivot_y,
    )
