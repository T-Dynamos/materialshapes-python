import math
from typing import List, Optional

from materialshapes.corner_rounding import CornerRounding
from materialshapes.cubic import Cubic
from materialshapes.features import CornerFeature, EdgeFeature, Feature
from materialshapes.point import Point, interpolate, lerp
from materialshapes.utils import (
    convex,
    direction_vector,
    distance,
    distance_epsilon,
    distance_squared,
    radial_to_cartesian,
    two_pi,
)


def calculate_center(vertices: list[float]) -> Point:
    cumulative_x = 0.0
    cumulative_y = 0.0
    index = 0

    while index < len(vertices):
        cumulative_x += vertices[index]
        index += 1
        cumulative_y += vertices[index]
        index += 1

    count = len(vertices) // 2
    return Point(cumulative_x / count, cumulative_y / count)


def _pill_star_vertices_from_num_verts(
    num_vertices_per_radius: int,
    width: float,
    height: float,
    inner_radius: float,
    vertex_spacing: float,
    start_location: float,
    center_x: float,
    center_y: float,
) -> list[float]:
    endcap_radius = min(width, height)
    v_seg_len = max(height - width, 0)
    h_seg_len = max(width - height, 0)
    v_seg_half = v_seg_len / 2
    h_seg_half = h_seg_len / 2

    circle_perimeter = two_pi * endcap_radius * lerp(inner_radius, 1, vertex_spacing)
    perimeter = 2 * h_seg_len + 2 * v_seg_len + circle_perimeter

    sections = [0.0] * 11
    sections[0] = 0
    sections[1] = v_seg_len / 2
    sections[2] = sections[1] + circle_perimeter / 4
    sections[3] = sections[2] + h_seg_len
    sections[4] = sections[3] + circle_perimeter / 4
    sections[5] = sections[4] + v_seg_len
    sections[6] = sections[5] + circle_perimeter / 4
    sections[7] = sections[6] + h_seg_len
    sections[8] = sections[7] + circle_perimeter / 4
    sections[9] = sections[8] + v_seg_len / 2
    sections[10] = perimeter

    t_per_vertex = perimeter / (2 * num_vertices_per_radius)
    inner = False
    curr_sec_index = 0
    sec_start = 0.0
    sec_end = sections[1]
    t = start_location * perimeter

    result = [0.0] * (num_vertices_per_radius * 4)
    array_index = 0

    rect_br = Point(h_seg_half, v_seg_half)
    rect_bl = Point(-h_seg_half, v_seg_half)
    rect_tl = Point(-h_seg_half, -v_seg_half)
    rect_tr = Point(h_seg_half, -v_seg_half)

    for _ in range(num_vertices_per_radius * 2):
        bounded_t = t % perimeter
        if bounded_t < sec_start:
            curr_sec_index = 0

        while bounded_t >= sections[(curr_sec_index + 1) % len(sections)]:
            curr_sec_index = (curr_sec_index + 1) % len(sections)
            sec_start = sections[curr_sec_index]
            sec_end = sections[(curr_sec_index + 1) % len(sections)]

        t_in_section = bounded_t - sec_start
        t_proportion = t_in_section / (sec_end - sec_start)

        curr_radius = endcap_radius * inner_radius if inner else endcap_radius
        sec_handlers = {
            0: lambda: Point(curr_radius, t_proportion * v_seg_half),
            1: lambda: radial_to_cartesian(curr_radius, t_proportion * math.pi / 2)
            + rect_br,
            2: lambda: Point(h_seg_half - t_proportion * h_seg_len, curr_radius),
            3: lambda: radial_to_cartesian(
                curr_radius, math.pi / 2 + t_proportion * math.pi / 2
            )
            + rect_bl,
            4: lambda: Point(-curr_radius, v_seg_half - t_proportion * v_seg_len),
            5: lambda: radial_to_cartesian(
                curr_radius, math.pi + t_proportion * math.pi / 2
            )
            + rect_tl,
            6: lambda: Point(-h_seg_half + t_proportion * h_seg_len, -curr_radius),
            7: lambda: radial_to_cartesian(
                curr_radius, 1.5 * math.pi + t_proportion * math.pi / 2
            )
            + rect_tr,
        }
        vertex = sec_handlers.get(
            curr_sec_index,
            lambda: Point(curr_radius, -v_seg_half + t_proportion * v_seg_half),
        )()

        result[array_index] = vertex.x + center_x
        result[array_index + 1] = vertex.y + center_y
        array_index += 2
        t += t_per_vertex
        inner = not inner

    return result


def vertices_from_num_verts(
    num_vertices: int,
    radius: float,
    center_x: float,
    center_y: float,
) -> List[float]:
    result = [0.0] * (num_vertices * 2)

    array_index = 0
    for i in range(num_vertices):
        angle = math.pi * 2 * i / num_vertices
        vertex = radial_to_cartesian(radius, angle) + Point(center_x, center_y)
        result[array_index] = vertex.x
        array_index += 1
        result[array_index] = vertex.y
        array_index += 1

    return result


def _star_vertices_from_num_verts(
    num_vertices_per_radius: int,
    radius: float,
    inner_radius: float,
    center_x: float,
    center_y: float,
) -> list[float]:
    result = [0.0] * (num_vertices_per_radius * 4)
    array_index = 0

    for i in range(num_vertices_per_radius):
        vertex = radial_to_cartesian(
            radius,
            math.pi / num_vertices_per_radius * 2 * i,
        )
        result[array_index] = vertex.x + center_x
        array_index += 1
        result[array_index] = vertex.y + center_y
        array_index += 1

        vertex = radial_to_cartesian(
            inner_radius,
            math.pi / num_vertices_per_radius * (2 * i + 1),
        )
        result[array_index] = vertex.x + center_x
        array_index += 1
        result[array_index] = vertex.y + center_y
        array_index += 1

    return result


class _RoundedCorner:
    d1 = Point.zero
    d2 = Point.zero
    p0 = Point.zero
    p1 = Point.zero
    p2 = Point.zero
    center = Point.zero
    corner_radius = 0
    smoothing = 0
    cos_angle = 0
    sin_angle = 0
    expected_round_cut = 0
    rounding = CornerRounding()

    def __init__(self, p0, p1, p2, rounding: CornerRounding):
        self.p0 = p0
        self.p1 = p1
        self.p2 = p2
        self.rounding = rounding

        v01 = p0 - p1
        v21 = p2 - p1
        d01 = v01.get_distance()
        d21 = v21.get_distance()

        if d01 > 0 and d21 > 0:
            self.d1 = v01 / d01
            self.d2 = v21 / d21
            self.corner_radius = rounding.radius if rounding else 0
            self.smoothing = rounding.smoothing if rounding else 0

            self.cos_angle = self.d1.dot_product(self.d2)
            self.sin_angle = math.sqrt(1 - self.cos_angle**2)

            self.expected_round_cut = (
                self.corner_radius * (self.cos_angle + 1) / self.sin_angle
                if self.sin_angle > 1e-3
                else 0
            )

        self.center = Point.zero

    @property
    def expected_cut(self):
        return (1 + self.smoothing) * self.expected_round_cut

    def get_cubics(self, allowed_cut0, allowed_cut1):
        allowed_cut = min(allowed_cut0, allowed_cut1)

        if (
            self.expected_round_cut < distance_epsilon
            or allowed_cut < distance_epsilon
            or self.corner_radius < distance_epsilon
        ):
            self.center = self.p1
            return [Cubic.straight_line(self.p1.x, self.p1.y, self.p1.x, self.p1.y)]

        actual_round_cut = min(allowed_cut, self.expected_round_cut)

        actual_smoothing0 = self._calculate_actual_smoothing_value(allowed_cut0)
        actual_smoothing1 = self._calculate_actual_smoothing_value(allowed_cut1)

        actual_r = self.corner_radius * actual_round_cut / self.expected_round_cut
        center_distance = math.sqrt(actual_r**2 + actual_round_cut**2)

        self.center = (
            self.p1 + ((self.d1 + self.d2) / 2).get_direction() * center_distance
        )
        circle_intersection0 = self.p1 + self.d1 * actual_round_cut
        circle_intersection2 = self.p1 + self.d2 * actual_round_cut

        flanking0 = self._compute_flanking_curve(
            actual_round_cut,
            actual_smoothing0,
            self.p1,
            self.p0,
            circle_intersection0,
            circle_intersection2,
            self.center,
            actual_r,
        )
        flanking2 = self._compute_flanking_curve(
            actual_round_cut,
            actual_smoothing1,
            self.p1,
            self.p2,
            circle_intersection2,
            circle_intersection0,
            self.center,
            actual_r,
        ).reverse()

        return [
            flanking0,
            Cubic.circular_arc(
                self.center.x,
                self.center.y,
                flanking0.anchor1_x,
                flanking0.anchor1_y,
                flanking2.anchor0_x,
                flanking2.anchor0_y,
            ),
            flanking2,
        ]

    def _calculate_actual_smoothing_value(self, allowed_cut):
        if allowed_cut > self.expected_cut:
            return self.smoothing
        elif allowed_cut > self.expected_round_cut:
            return self.smoothing * (
                (allowed_cut - self.expected_round_cut)
                / (self.expected_cut - self.expected_round_cut)
            )
        else:
            return 0

    def _compute_flanking_curve(
        self,
        actual_round_cut,
        actual_smoothing,
        corner,
        side_start,
        circle_segment_intersection,
        other_circle_segment_intersection,
        circle_center,
        actual_r,
    ):
        side_direction = (side_start - corner).get_direction()
        curve_start = corner + side_direction * actual_round_cut * (
            1 + actual_smoothing
        )

        p = interpolate(
            circle_segment_intersection,
            (circle_segment_intersection + other_circle_segment_intersection) / 2,
            actual_smoothing,
        )

        curve_end = (
            circle_center
            + direction_vector(p.x - circle_center.x, p.y - circle_center.y) * actual_r
        )

        circle_tangent = (curve_end - circle_center).rotate90()
        anchor_end = (
            self._line_intersection(
                side_start, side_direction, curve_end, circle_tangent
            )
            or circle_segment_intersection
        )

        anchor_start = (curve_start + anchor_end * 2) / 3
        return Cubic.from_points(curve_start, anchor_start, anchor_end, curve_end)

    def _line_intersection(self, p0, d0, p1, d1):
        rotated_d1 = d1.rotate90()
        den = d0.dot_product(rotated_d1)

        if abs(den) < distance_epsilon:
            return None

        num = (p1 - p0).dot_product(rotated_d1)

        if abs(den) < distance_epsilon * abs(num):
            return None

        k = num / den
        return p0 + d0 * k


class RoundedPolygon:
    def __init__(self, features: List[Feature], center: Point):
        self.features = features
        self.center = center
        self.cubics = []
        self._init_cubics()

        prev_cubic = self.cubics[-1]
        for cubic in self.cubics:
            if (
                abs(cubic.anchor0_x - prev_cubic.anchor1_x) > distance_epsilon
                or abs(cubic.anchor0_y - prev_cubic.anchor1_y) > distance_epsilon
            ):
                raise ValueError(
                    "RoundedPolygon must be contiguous, with the anchor points of all "
                    "curves matching the anchor points of the preceding and succeeding "
                    "cubics."
                )
            prev_cubic = cubic

    def _init_cubics(self):
        first_cubic = None
        last_cubic = None
        first_feature_split_start = None
        first_feature_split_end = None

        if self.features and len(self.features[0].cubics) == 3:
            center_cubic = self.features[0].cubics[1]
            start, end = center_cubic.split(0.5)
            first_feature_split_start = [self.features[0].cubics[0], start]
            first_feature_split_end = [end, self.features[0].cubics[2]]

        for i in range(len(self.features) + 1):
            if i == 0 and first_feature_split_end is not None:
                feature_cubics = first_feature_split_end
            elif i == len(self.features):
                if first_feature_split_start is not None:
                    feature_cubics = first_feature_split_start
                else:
                    break
            else:
                feature_cubics = self.features[i].cubics

            for cubic in feature_cubics:
                if not cubic.zero_length():
                    if last_cubic is not None:
                        self.cubics.append(last_cubic)
                    last_cubic = cubic
                    if first_cubic is None:
                        first_cubic = cubic
                else:
                    if last_cubic is not None:
                        points = last_cubic._points[:]
                        points[6] = cubic.anchor1_x
                        points[7] = cubic.anchor1_y
                        last_cubic = Cubic(*points)

        if last_cubic and first_cubic:
            self.cubics.append(
                Cubic(
                    last_cubic.anchor0_x,
                    last_cubic.anchor0_y,
                    last_cubic.control0_x,
                    last_cubic.control0_y,
                    last_cubic.control1_x,
                    last_cubic.control1_y,
                    first_cubic.anchor0_x,
                    first_cubic.anchor0_y,
                )
            )
        else:
            cx = self.center.x
            cy = self.center.y
            self.cubics.append(Cubic(cx, cy, cx, cy, cx, cy, cx, cy))

    @classmethod
    def from_features(cls, features, center_x=float("nan"), center_y=float("nan")):
        if len(features) < 2:
            raise ValueError("polygons must have at least 2 features.")

        if math.isnan(center_x) or math.isnan(center_y):
            vertices = []
            for feature in features:
                for cubic in feature.cubics:
                    vertices.append(cubic.anchor0_x)
                    vertices.append(cubic.anchor0_y)

            center = calculate_center(vertices)
            c_x = center_x if not math.isnan(center_x) else center.x
            c_y = center_y if not math.isnan(center_y) else center.y
            return cls(features, Point(c_x, c_y))

        return cls(features, Point(center_x, center_y))

    @classmethod
    def from_vertices(
        cls,
        vertices: list[float],
        rounding: CornerRounding = CornerRounding.unrounded,
        per_vertex_rounding: list[CornerRounding] | None = None,
        center_x: float = float("1e-323"),
        center_y: float = float("1e-323"),
    ):
        if len(vertices) < 6:
            raise ValueError("Polygons must have at least 3 vertices.")
        if len(vertices) % 2 != 0:
            raise ValueError("The vertices array should have even size.")
        if per_vertex_rounding is not None and len(per_vertex_rounding) * 2 != len(
            vertices
        ):
            raise ValueError(
                "per_vertex_rounding list should be either None or the same size as the number of vertices (vertices.size / 2)."
            )

        corners = []
        n = len(vertices) // 2
        rounded_corners = []

        for i in range(n):
            vtx_rounding = per_vertex_rounding[i] if per_vertex_rounding else rounding
            prev_index = ((i + n - 1) % n) * 2
            next_index = ((i + 1) % n) * 2
            rounded_corners.append(
                _RoundedCorner(
                    Point(vertices[prev_index], vertices[prev_index + 1]),
                    Point(vertices[i * 2], vertices[i * 2 + 1]),
                    Point(vertices[next_index], vertices[next_index + 1]),
                    vtx_rounding,
                )
            )

        cut_adjusts = []
        for i in range(n):
            corner = rounded_corners[i]
            next_corner = rounded_corners[(i + 1) % n]
            expected_round_cut = (
                corner.expected_round_cut + next_corner.expected_round_cut
            )
            expected_cut = corner.expected_cut + next_corner.expected_cut

            vtx_x = vertices[i * 2]
            vtx_y = vertices[i * 2 + 1]
            next_vtx_x = vertices[((i + 1) % n) * 2]
            next_vtx_y = vertices[((i + 1) % n) * 2 + 1]
            side_size = distance(vtx_x - next_vtx_x, vtx_y - next_vtx_y)

            if expected_round_cut > side_size:
                cut_adjusts.append((side_size / expected_round_cut, 0))
            elif expected_cut > side_size:
                cut_adjusts.append(
                    (
                        1,
                        (side_size - expected_round_cut)
                        / (expected_cut - expected_round_cut),
                    )
                )
            else:
                cut_adjusts.append((1, 1))

        for i in range(n):
            allowed_cuts = [0, 0]
            for delta in range(2):
                round_cut_ratio, cut_ratio = cut_adjusts[(i + n - 1 + delta) % n]
                rc = rounded_corners[i].expected_round_cut
                ec = rounded_corners[i].expected_cut
                allowed_cuts[delta] = rc * round_cut_ratio + (ec - rc) * cut_ratio

            corners.append(
                rounded_corners[i].get_cubics(allowed_cuts[0], allowed_cuts[1])
            )

        temp_features = []
        for i in range(n):
            prev_index = (i + n - 1) % n
            next_index = (i + 1) % n
            curr = Point(vertices[i * 2], vertices[i * 2 + 1])
            prev = Point(vertices[prev_index * 2], vertices[prev_index * 2 + 1])
            next = Point(vertices[next_index * 2], vertices[next_index * 2 + 1])
            is_convex = convex(prev, curr, next)

            temp_features.append(CornerFeature(corners[i], convex=is_convex))
            temp_features.append(
                EdgeFeature(
                    [
                        Cubic.straight_line(
                            corners[i][-1].anchor1_x,
                            corners[i][-1].anchor1_y,
                            corners[(i + 1) % n][0].anchor0_x,
                            corners[(i + 1) % n][0].anchor0_y,
                        )
                    ]
                )
            )

        if center_x == float("1e-323") or center_y == float("1e-323"):
            center = calculate_center(vertices)
            c_x = center.x
            c_y = center.y
        else:
            c_x = center_x
            c_y = center_y

        return cls.from_features(temp_features, center_x=c_x, center_y=c_y)

    @staticmethod
    def from_vertices_num(
        num_vertices: int,
        radius: float = 1.0,
        center_x: float = 0.0,
        center_y: float = 0.0,
        rounding: CornerRounding = CornerRounding.unrounded,
        per_vertex_rounding: Optional[List[CornerRounding]] = None,
    ) -> "RoundedPolygon":
        if num_vertices < 3:
            raise ValueError("num_vertices must be at least 3.")

        vertices = vertices_from_num_verts(num_vertices, radius, center_x, center_y)

        return RoundedPolygon.from_vertices(
            vertices,
            rounding=rounding,
            per_vertex_rounding=per_vertex_rounding,
            center_x=center_x,
            center_y=center_y,
        )

    @classmethod
    def from_existing(cls, rounded_polygon: "RoundedPolygon") -> "RoundedPolygon":
        return cls._(rounded_polygon.features, rounded_polygon.center)

    @classmethod
    def circle(
        cls,
        num_vertices: int = 8,
        radius: float = 1,
        center_x: float = 0,
        center_y: float = 0,
    ) -> "RoundedPolygon":
        if num_vertices < 3:
            raise ValueError("Circle must have at least three vertices.")

        # Half of the angle between two adjacent vertices on the polygon.
        theta = math.pi / num_vertices
        # Radius of the underlying RoundedPolygon object given the desired radius.
        polygon_radius = radius / math.cos(theta)

        return cls.from_vertices_num(
            num_vertices,
            radius=polygon_radius,
            center_x=center_x,
            center_y=center_y,
            rounding=CornerRounding(radius=radius),
        )

    @classmethod
    def rectangle(
        cls,
        width: float = 2,
        height: float = 2,
        rounding: CornerRounding = CornerRounding().unrounded,
        per_vertex_rounding: list[CornerRounding] | None = None,
        center_x: float = 0,
        center_y: float = 0,
    ) -> "RoundedPolygon":
        left = center_x - width / 2
        top = center_y - height / 2
        right = center_x + width / 2
        bottom = center_y + height / 2

        return cls.from_vertices(
            [right, bottom, left, bottom, left, top, right, top],
            rounding=rounding,
            per_vertex_rounding=per_vertex_rounding,
            center_x=center_x,
            center_y=center_y,
        )

    @classmethod
    def star(
        cls,
        num_vertices_per_radius: int,
        radius: float = 1,
        inner_radius: float = 0.5,
        rounding: CornerRounding = CornerRounding().unrounded,
        inner_rounding: CornerRounding | None = None,
        per_vertex_rounding: list[CornerRounding] | None = None,
        center_x: float = 0,
        center_y: float = 0,
    ) -> "RoundedPolygon":
        if radius <= 0 or inner_radius <= 0:
            raise ValueError("Star radii must both be greater than 0.")
        if inner_radius >= radius:
            raise ValueError("inner_radius must be less than radius.")

        pv_rounding = per_vertex_rounding
        if pv_rounding is None and inner_rounding is not None:
            pv_rounding = [
                rounding if i % 2 == 0 else inner_rounding
                for i in range(num_vertices_per_radius * 2)
            ]

        return cls.from_vertices(
            _star_vertices_from_num_verts(
                num_vertices_per_radius,
                radius,
                inner_radius,
                center_x,
                center_y,
            ),
            rounding=rounding,
            per_vertex_rounding=pv_rounding,
            center_x=center_x,
            center_y=center_y,
        )

    @classmethod
    def pill(
        cls,
        width: float = 2,
        height: float = 1,
        smoothing: float = 0,
        center_x: float = 0,
        center_y: float = 0,
    ) -> "RoundedPolygon":
        if width <= 0 or height <= 0:
            raise ValueError("Pill shapes must have positive width and height.")

        w_half = width / 2
        h_half = height / 2

        return cls.from_vertices(
            [
                w_half + center_x,
                h_half + center_y,
                -w_half + center_x,
                h_half + center_y,
                -w_half + center_x,
                -h_half + center_y,
                w_half + center_x,
                -h_half + center_y,
            ],
            rounding=CornerRounding(
                radius=min(w_half, h_half),
                smoothing=smoothing,
            ),
            center_x=center_x,
            center_y=center_y,
        )

    @classmethod
    def pill_star(
        cls,
        width: float = 2,
        height: float = 1,
        num_vertices_per_radius: int = 8,
        inner_radius_ratio: float = 0.5,
        rounding: CornerRounding = CornerRounding().unrounded,
        inner_rounding: CornerRounding | None = None,
        per_vertex_rounding: list[CornerRounding] | None = None,
        vertex_spacing: float = 0.5,
        start_location: float = 0,
        center_x: float = 0,
        center_y: float = 0,
    ) -> "RoundedPolygon":
        if width <= 0 or height <= 0:
            raise ValueError("Pill shapes must have positive width and height.")
        if inner_radius_ratio <= 0 or inner_radius_ratio > 1:
            raise ValueError("inner_radius_ratio must be in (0, 1] range.")
        if vertex_spacing < 0 or vertex_spacing > 1:
            raise ValueError("vertex_spacing must be in [0, 1] range.")
        if start_location < 0 or start_location > 1:
            raise ValueError("start_location must be in [0, 1] range.")

        pv_rounding = per_vertex_rounding
        if pv_rounding is None and inner_rounding is not None:
            pv_rounding = [
                rounding if i % 2 == 0 else inner_rounding
                for i in range(num_vertices_per_radius * 2)
            ]

        return cls.from_vertices(
            _pill_star_vertices_from_num_verts(
                num_vertices_per_radius,
                width,
                height,
                inner_radius_ratio,
                vertex_spacing,
                start_location,
                center_x,
                center_y,
            ),
            rounding=rounding,
            per_vertex_rounding=pv_rounding,
            center_x=center_x,
            center_y=center_y,
        )

    def transformed(self, f):
        new_center = self.center.transformed(f)
        new_features = self.features
        new_features = [feature.transformed(f) for feature in self.features]
        return RoundedPolygon(new_features, new_center)

    def normalized(self):
        bounds = self.calculate_bounds()
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        side = max(width, height)

        offset_x = (side - width) / 2 - bounds[0]
        offset_y = (side - height) / 2 - bounds[1]

        return self.transformed(
            lambda x, y: ((x + offset_x) / side, (y + offset_y) / side)
        )

    def calculate_bounds(self, bounds=None, approximate=True):
        if bounds is None:
            bounds = [0.0] * 4
        if len(bounds) < 4:
            raise ValueError("Required bounds size of 4.")

        min_x = float("inf")
        min_y = float("inf")
        max_x = float("-inf")
        max_y = float("-inf")

        temp = [0.0] * 4
        for cubic in self.cubics:
            cubic.calculate_bounds(temp, approximate=approximate)
            min_x = min(min_x, temp[0])
            min_y = min(min_y, temp[1])
            max_x = max(max_x, temp[2])
            max_y = max(max_y, temp[3])

        bounds[0] = min_x
        bounds[1] = min_y
        bounds[2] = max_x
        bounds[3] = max_y
        return bounds

    def calculate_max_bounds(self, bounds: list[float] | None = None) -> list[float]:
        if bounds is None:
            bounds = [0.0] * 4

        if len(bounds) < 4:
            raise ValueError("Required bounds size of 4.")

        max_dist_squared = 0.0
        for cubic in self.cubics:
            anchor_distance = distance_squared(
                cubic.anchor0_x - self.center.x, cubic.anchor0_y - self.center.y
            )
            middle_point = cubic.point_on_curve(0.5)
            middle_distance = distance_squared(
                middle_point.x - self.center.x, middle_point.y - self.center.y
            )
            max_dist_squared = max(max_dist_squared, anchor_distance, middle_distance)

        distance = math.sqrt(max_dist_squared)

        bounds[0] = self.center.x - distance
        bounds[1] = self.center.y - distance
        bounds[2] = self.center.x + distance
        bounds[3] = self.center.y + distance

        return bounds

    def __str__(self):
        return (
            f"[RoundedPolygon. "
            f"Cubics = {', '.join(map(str, self.cubics))}"
            f" || Features = {', '.join(map(str, self.features))}"
            f" || Center = ({self.center_x}, {self.center_y})]"
        )
