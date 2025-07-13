from typing import List, Tuple

from materialshapes.features import CornerFeature, Feature
from materialshapes.float_mapping import (
    DoubleMapper,
    progress_distance,
    progress_in_range,
)
from materialshapes.point import Point
from materialshapes.utils import binary_search_by, distance_epsilon

# type alias
MeasuredFeatures = List["ProgressableFeature"]


class ProgressableFeature:
    def __init__(self, progress: float, feature: Feature):
        self.progress = progress
        self.feature = feature

    def __eq__(self, other):
        return (
            isinstance(other, ProgressableFeature)
            and self.progress == other.progress
            and self.feature == other.feature
        )

    def __hash__(self):
        return hash((self.progress, self.feature))


class DistanceVertex:
    def __init__(
        self, distance: float, f1: ProgressableFeature, f2: ProgressableFeature
    ):
        self.distance = distance
        self.f1 = f1
        self.f2 = f2


def feature_mapper(
    features1: MeasuredFeatures, features2: MeasuredFeatures
) -> DoubleMapper:
    filtered_features1 = [f for f in features1 if f.feature.is_corner]
    filtered_features2 = [f for f in features2 if f.feature.is_corner]

    feature_progress_mapping = do_mapping(filtered_features1, filtered_features2)
    return DoubleMapper(feature_progress_mapping)


def do_mapping(
    features1: List[ProgressableFeature], features2: List[ProgressableFeature]
) -> List[Tuple[float, float]]:
    distance_vertex_list = []

    for f1 in features1:
        for f2 in features2:
            d = feature_dist_squared(f1.feature, f2.feature)
            if d != float("inf"):
                distance_vertex_list.append(DistanceVertex(d, f1, f2))

    distance_vertex_list.sort(key=lambda d: d.distance)

    if not distance_vertex_list:
        return [(0.0, 0.0), (0.5, 0.5)]

    if len(distance_vertex_list) == 1:
        d = distance_vertex_list[0]
        f1, f2 = d.f1.progress, d.f2.progress
        return [(f1, f2), ((f1 + 0.5) % 1, (f2 + 0.5) % 1)]

    helper = _MappingHelper()
    for d in distance_vertex_list:
        helper.add_mapping(d.f1, d.f2)

    return helper.mapping


class _MappingHelper:
    def __init__(self):
        self.mapping: List[Tuple[float, float]] = []
        self._used_f1 = set()
        self._used_f2 = set()

    def add_mapping(self, f1: ProgressableFeature, f2: ProgressableFeature):
        if f1 in self._used_f1 or f2 in self._used_f2:
            return

        index = binary_search_by(
            self.mapping,
            key=lambda it: it[0],
            compare=lambda a, b: (a > b) - (a < b),
            value=f1.progress,
        )

        if index >= 0:
            raise ValueError("Two features can't have the same progress.")

        insertion_index = -index - 1
        n = len(self.mapping)

        if n >= 1:
            before1, before2 = self.mapping[(insertion_index + n - 1) % n]
            after1, after2 = self.mapping[insertion_index % n]

            if (
                progress_distance(f1.progress, before1) < distance_epsilon
                or progress_distance(f1.progress, after1) < distance_epsilon
                or progress_distance(f2.progress, before2) < distance_epsilon
                or progress_distance(f2.progress, after2) < distance_epsilon
            ):
                return

            if n > 1 and not progress_in_range(f2.progress, before2, after2):
                return

        self.mapping.insert(insertion_index, (f1.progress, f2.progress))
        self._used_f1.add(f1)
        self._used_f2.add(f2)


def feature_dist_squared(f1: Feature, f2: Feature) -> float:
    if isinstance(f1, CornerFeature) and isinstance(f2, CornerFeature):
        if f1.convex != f2.convex:
            return float("inf")
    p1 = feature_representative_point(f1)
    p2 = feature_representative_point(f2)
    return (p1 - p2).get_distance_squared()


def feature_representative_point(feature: Feature) -> Point:
    cubics = feature.cubics
    x = (cubics[0].anchor0_x + cubics[-1].anchor1_x) / 2
    y = (cubics[0].anchor0_y + cubics[-1].anchor1_y) / 2
    return Point(x, y)
