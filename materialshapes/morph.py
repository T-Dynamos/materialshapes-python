from materialshapes.cubic import Cubic
from materialshapes.feature_mapping import feature_mapper
from materialshapes.point import lerp
from materialshapes.polygon_measure import LengthMeasurer, MeasuredPolygon
from materialshapes.utils import angle_epsilon, positive_modulo


class Morph:
    def __init__(self, start, end):
        self._start = start
        self._end = end
        self._morph_match = self._match(start, end)

    @staticmethod
    def _match(p1, p2):
        measured_polygon1 = MeasuredPolygon.measure_polygon(LengthMeasurer(), p1)
        measured_polygon2 = MeasuredPolygon.measure_polygon(LengthMeasurer(), p2)

        features1 = measured_polygon1.features
        features2 = measured_polygon2.features

        double_mapper = feature_mapper(features1, features2)

        polygon2_cut_point = double_mapper.map(0)

        bs1 = measured_polygon1
        bs2 = measured_polygon2.cut_and_shift(polygon2_cut_point)

        ret = []
        i1 = 0
        i2 = 0
        b1 = bs1.get_or_none(i1)
        i1 += 1
        b2 = bs2.get_or_none(i2)
        i2 += 1

        while b1 is not None and b2 is not None:
            b1a = 1.0 if i1 == len(bs1) else b1.end_outline_progress
            b2a = (
                1.0
                if i2 == len(bs2)
                else double_mapper.map_back(
                    positive_modulo(b2.end_outline_progress + polygon2_cut_point, 1)
                )
            )

            minb = min(b1a, b2a)

            if b1a > minb + angle_epsilon:
                seg1, newb1 = b1.cut_at_progress(minb)
            else:
                seg1, newb1 = b1, bs1.get_or_none(i1)
                i1 += 1

            if b2a > minb + angle_epsilon:
                seg2, newb2 = b2.cut_at_progress(
                    positive_modulo(double_mapper.map(minb) - polygon2_cut_point, 1)
                )
            else:
                seg2, newb2 = b2, bs2.get_or_none(i2)
                i2 += 1

            ret.append((seg1.cubic, seg2.cubic))
            b1 = newb1
            b2 = newb2

        assert b1 is None and b2 is None, (
            "Expected both Polygon's Cubics to be fully matched"
        )
        return ret

    def calculate_bounds(self, bounds=None, approximate=True):
        bounds = bounds or [0.0] * 4
        self._start.calculate_bounds(bounds=bounds, approximate=approximate)
        min_x, min_y, max_x, max_y = bounds
        self._end.calculate_bounds(bounds=bounds, approximate=approximate)
        bounds[0] = min(min_x, bounds[0])
        bounds[1] = min(min_y, bounds[1])
        bounds[2] = max(max_x, bounds[2])
        bounds[3] = max(max_y, bounds[3])
        return bounds

    def calculate_max_bounds(self, bounds=None):
        bounds = bounds or [0.0] * 4
        self._start.calculate_max_bounds(bounds)
        min_x, min_y, max_x, max_y = bounds
        self._end.calculate_max_bounds(bounds)
        bounds[0] = min(min_x, bounds[0])
        bounds[1] = min(min_y, bounds[1])
        bounds[2] = max(max_x, bounds[2])
        bounds[3] = max(max_y, bounds[3])
        return bounds

    def as_cubics(self, progress):
        result = []
        first_cubic = None
        last_cubic = None

        for c1, c2 in self._morph_match:
            interpolated = Cubic(
                *[lerp(c1._points[i], c2._points[i], progress) for i in range(8)]
            )
            if last_cubic:
                result.append(last_cubic)
            else:
                first_cubic = interpolated
            last_cubic = interpolated

        if last_cubic and first_cubic:
            result.append(
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

        return result
