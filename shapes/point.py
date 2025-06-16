import math
from dataclasses import dataclass


@dataclass(frozen=True)
class Point:
    x: float
    y: float

    zero = None  # Placeholder for static value below

    def copy(self):
        return Point(self.x, self.y)

    def rotate90(self):
        return Point(-self.y, self.x)

    def rotate(self, degrees, center=None):
        if center is None:
            center = Point.zero
        radians = degrees * math.pi / 180
        off = self - center
        cos_theta = math.cos(radians)
        sin_theta = math.sin(radians)
        return (
            Point(
                off.x * cos_theta - off.y * sin_theta,
                off.x * sin_theta + off.y * cos_theta,
            )
            + center
        )

    def translate(self, dx, dy):
        return Point(self.x + dx, self.y + dy)

    def scale(self, sx, sy):
        return Point(self.x * sx, self.y * sy)

    @property
    def angle_degrees(self):
        return math.degrees(self.angle_radians)

    @property
    def angle_radians(self):
        return math.atan2(self.y, self.x)

    def get_distance(self):
        return math.sqrt(self.x**2 + self.y**2)

    def get_distance_squared(self):
        return self.x**2 + self.y**2

    def dot_product(self, other):
        return self.x * other.x + self.y * other.y

    def dot_product_xy(self, other_x, other_y):
        return self.x * other_x + self.y * other_y

    def clockwise(self, other):
        return (self.x * other.y - self.y * other.x) > 0

    def get_direction(self):
        d = self.get_distance()
        if d == 0:
            raise ValueError("Can't get the direction of a 0-length vector")
        return self / d

    def __neg__(self):
        return Point(-self.x, -self.y)

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __add__(self, other):
        return Point(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar):
        return Point(self.x * scalar, self.y * scalar)

    def __truediv__(self, scalar):
        return Point(self.x / scalar, self.y / scalar)

    def __mod__(self, scalar):
        return Point(self.x % scalar, self.y % scalar)

    def transformed(self, func):
        x2, y2 = func(self.x, self.y)
        return Point(x2, y2)

    def __eq__(self, other):
        return isinstance(other, Point) and self.x == other.x and self.y == other.y

    def __hash__(self):
        return hash((self.x, self.y))


Point.zero = Point(0.0, 0.0)


def lerp(start: float, stop: float, fraction: float) -> float:
    return start * (1 - fraction) + stop * fraction


def interpolate(start: Point, stop: Point, fraction: float) -> Point:
    return Point(lerp(start.x, stop.x, fraction), lerp(start.y, stop.y, fraction))
