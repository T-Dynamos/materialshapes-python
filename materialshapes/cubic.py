import math
from dataclasses import dataclass

from materialshapes.point import Point, lerp
from materialshapes.utils import convex, direction_vector, distance, distance_epsilon


@dataclass
class Cubic:
    anchor0_x: float
    anchor0_y: float
    control0_x: float
    control0_y: float
    control1_x: float
    control1_y: float
    anchor1_x: float
    anchor1_y: float

    _vals = [
        "anchor0_x",
        "anchor0_y",
        "control0_x",
        "control0_y",
        "control1_x",
        "control1_y",
        "anchor1_x",
        "anchor1_y",
    ]

    @property
    def _points(self):
        return [getattr(self, val) for val in self._vals]

    @classmethod
    def from_points(
        cls, anchor0: Point, control0: Point, control1: Point, anchor1: Point
    ):
        return cls(
            anchor0_x=anchor0.x,
            anchor0_y=anchor0.y,
            control0_x=control0.x,
            control0_y=control0.y,
            control1_x=control1.x,
            control1_y=control1.y,
            anchor1_x=anchor1.x,
            anchor1_y=anchor1.y,
        )

    @classmethod
    def straight_line(cls, x0: float, y0: float, x1: float, y1: float) -> "Cubic":
        control0_x = lerp(x0, x1, 1 / 3)
        control0_y = lerp(y0, y1, 1 / 3)
        control1_x = lerp(x0, x1, 2 / 3)
        control1_y = lerp(y0, y1, 2 / 3)
        return cls(x0, y0, control0_x, control0_y, control1_x, control1_y, x1, y1)

    @classmethod
    def circular_arc(
        cls,
        center_x: float,
        center_y: float,
        x0: float,
        y0: float,
        x1: float,
        y1: float,
    ) -> "Cubic":
        p0d = direction_vector(x0 - center_x, y0 - center_y)
        p1d = direction_vector(x1 - center_x, y1 - center_y)
        rotated_p0 = p0d.rotate90()
        rotated_p1 = p1d.rotate90()
        clockwise = rotated_p0.dot_product_xy(x1 - center_x, y1 - center_y) >= 0
        cosa = p0d.dot_product(p1d)

        # p0 ~= p1
        if cosa > 0.999:
            return cls.straight_line(x0, y0, x1, y1)

        k = (
            distance(x0 - center_x, y0 - center_y)
            * 4
            / 3
            * (math.sqrt(2 * (1 - cosa)) - math.sqrt(1 - cosa**2))
            / (1 - cosa)
        )
        k *= 1 if clockwise else -1

        return cls(
            x0,
            y0,
            x0 + rotated_p0.x * k,
            y0 + rotated_p0.y * k,
            x1 - rotated_p1.x * k,
            y1 - rotated_p1.y * k,
            x1,
            y1,
        )

    @classmethod
    def empty(cls, x0: float, y0: float):
        return Cubic(x0, y0, x0, y0, x0, y0, x0, y0)

    def point_on_curve(self, t: float) -> Point:
        u = 1 - t
        x = (
            self.anchor0_x * (u * u * u)
            + self.control0_x * (3 * t * u * u)
            + self.control1_x * (3 * t * t * u)
            + self.anchor1_x * (t * t * t)
        )

        y = (
            self.anchor0_y * (u * u * u)
            + self.control0_y * (3 * t * u * u)
            + self.control1_y * (3 * t * t * u)
            + self.anchor1_y * (t * t * t)
        )

        return Point(x, y)

    def zero_length(self) -> bool:
        return (
            abs(self.anchor0_x - self.anchor1_x) < distance_epsilon
            and abs(self.anchor0_y - self.anchor1_y) < distance_epsilon
        )

    def convex_to(self, next: "Cubic") -> bool:
        prev_vertex = Point(self.anchor0_x, self.anchor0_y)
        curr_vertex = Point(self.anchor1_x, self.anchor1_y)
        next_vertex = Point(next.anchor1_x, next.anchor1_y)
        return convex(prev_vertex, curr_vertex, next_vertex)

    def _zero_ish(self, value: float) -> bool:
        return abs(value) < distance_epsilon

    def calculate_bounds(self, bounds: list, approximate: bool = False):
        assert len(bounds) == 4, "Bounds array size should be 4."

        if self.zero_length():
            bounds[0] = self.anchor0_x
            bounds[1] = self.anchor0_y
            bounds[2] = self.anchor0_x
            bounds[3] = self.anchor0_y
            return

        min_x = min(self.anchor0_x, self.anchor1_x)
        min_y = min(self.anchor0_y, self.anchor1_y)
        max_x = max(self.anchor0_x, self.anchor1_x)
        max_y = max(self.anchor0_y, self.anchor1_y)

        if approximate:
            bounds[0] = min(min_x, min(self.control0_x, self.control1_x))
            bounds[1] = min(min_y, min(self.control0_y, self.control1_y))
            bounds[2] = max(max_x, max(self.control0_x, self.control1_x))
            bounds[3] = max(max_y, max(self.control0_y, self.control1_y))
            return

        xa = (
            -self.anchor0_x + 3 * self.control0_x - 3 * self.control1_x + self.anchor1_x
        )
        xb = 2 * self.anchor0_x - 4 * self.control0_x + 2 * self.control1_x
        xc = -self.anchor0_x + self.control0_x

        if self._zero_ish(xa):
            if xb != 0:
                t = 2 * xc / (-2 * xb)
                if 0 <= t <= 1:
                    x = self.point_on_curve(t).x
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)
        else:
            xs = xb * xb - 4 * xa * xc
            if xs >= 0:
                t1 = (-xb + math.sqrt(xs)) / (2 * xa)
                if 0 <= t1 <= 1:
                    x = self.point_on_curve(t1).x
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)

                t2 = (-xb - math.sqrt(xs)) / (2 * xa)
                if 0 <= t2 <= 1:
                    x = self.point_on_curve(t2).x
                    min_x = min(min_x, x)
                    max_x = max(max_x, x)

        ya = (
            -self.anchor0_y + 3 * self.control0_y - 3 * self.control1_y + self.anchor1_y
        )
        yb = 2 * self.anchor0_y - 4 * self.control0_y + 2 * self.control1_y
        yc = -self.anchor0_y + self.control0_y

        if self._zero_ish(ya):
            if yb != 0:
                t = 2 * yc / (-2 * yb)
                if 0 <= t <= 1:
                    y = self.point_on_curve(t).y
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)
        else:
            ys = yb * yb - 4 * ya * yc
            if ys >= 0:
                t1 = (-yb + math.sqrt(ys)) / (2 * ya)
                if 0 <= t1 <= 1:
                    y = self.point_on_curve(t1).y
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)

                t2 = (-yb - math.sqrt(ys)) / (2 * ya)
                if 0 <= t2 <= 1:
                    y = self.point_on_curve(t2).y
                    min_y = min(min_y, y)
                    max_y = max(max_y, y)

        bounds[0] = min_x
        bounds[1] = min_y
        bounds[2] = max_x
        bounds[3] = max_y

    def split(self, t: float) -> tuple:
        u = 1 - t
        point = self.point_on_curve(t)

        cubic1 = Cubic(
            self.anchor0_x,
            self.anchor0_y,
            self.anchor0_x * u + self.control0_x * t,
            self.anchor0_y * u + self.control0_y * t,
            self.anchor0_x * (u * u)
            + self.control0_x * (2 * u * t)
            + self.control1_x * (t * t),
            self.anchor0_y * (u * u)
            + self.control0_y * (2 * u * t)
            + self.control1_y * (t * t),
            point.x,
            point.y,
        )

        cubic2 = Cubic(
            point.x,
            point.y,
            self.control0_x * (u * u)
            + self.control1_x * (2 * u * t)
            + self.anchor1_x * (t * t),
            self.control0_y * (u * u)
            + self.control1_y * (2 * u * t)
            + self.anchor1_y * (t * t),
            self.control1_x * u + self.anchor1_x * t,
            self.control1_y * u + self.anchor1_y * t,
            self.anchor1_x,
            self.anchor1_y,
        )

        return cubic1, cubic2

    def reverse(self) -> "Cubic":
        return Cubic(
            self.anchor1_x,
            self.anchor1_y,
            self.control1_x,
            self.control1_y,
            self.control0_x,
            self.control0_y,
            self.anchor0_x,
            self.anchor0_y,
        )

    def __add__(self, other: "Cubic") -> "Cubic":
        if not isinstance(other, Cubic):
            raise TypeError(f"Cannot add {type(other)} to Cubic")
        return Cubic(*[self._points[i] + other._points[i] for i in range(8)])

    def __mul__(self, x: float) -> "Cubic":
        return Cubic(*[self._points[i] * x for i in range(8)])

    def __truediv__(self, x: float) -> "Cubic":
        return self * (1.0 / x)

    def transformed(self, transformer) -> "Cubic":
        new_cubic = _MutableCubic()
        [setattr(new_cubic, val, getattr(self, val)) for val in self._vals]
        new_cubic.transform(transformer)
        return new_cubic

    def __str__(self) -> str:
        return (
            f"anchor0: ({self.anchor0_x}, {self.anchor0_y}) "
            f"control0: ({self.control0_x}, {self.control0_y}), "
            f"control1: ({self.control1_x}, {self.control1_y}), "
            f"anchor1: ({self.anchor1_x}, {self.anchor1_y})"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Cubic):
            return False
        return self._points == other._points


class _MutableCubic(Cubic):
    def __init__(self, *args, **kwargs):
        super().__init__(*[0] * 8)

    def _transform_one_point(self, func, ix: int):
        pts = self._points
        result = func(pts[ix], pts[ix + 1])
        setattr(self, self._vals[ix], result[0])
        setattr(self, self._vals[ix + 1], result[1])

    def transform(self, func):
        for _ in range(0, 8, 2):
            self._transform_one_point(func, _)

    def interpolate(self, c1: Cubic, c2: Cubic, progress: float):
        c1pt = c1._points
        c2pt = c2._points
        for i, val in enumerate(self._vals):
            setattr(self, val, lerp(c1pt[i], c2pt[i], progress))
