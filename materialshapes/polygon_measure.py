from typing import List, Optional, Tuple

from materialshapes.cubic import Cubic
from materialshapes.feature_mapping import ProgressableFeature
from materialshapes.features import CornerFeature, Feature
from materialshapes.point import Point
from materialshapes.rounded_polygon import RoundedPolygon
from materialshapes.utils import distance_epsilon, positive_modulo


class Measurer:
    def measure_cubic(self, cubic: Cubic) -> float:
        raise NotImplementedError

    def find_cubic_cut_point(self, cubic: Cubic, measure: float) -> float:
        raise NotImplementedError


class MeasuredCubic:
    def __init__(
        self,
        measurer: "Measurer",
        cubic: Cubic,
        start_outline_progress: float,
        end_outline_progress: float,
    ):
        assert 0 <= start_outline_progress <= 1
        assert 0 <= end_outline_progress <= 1
        assert end_outline_progress >= start_outline_progress

        self.measurer = measurer
        self.cubic: Cubic = cubic
        self._start_outline_progress = start_outline_progress
        self._end_outline_progress = end_outline_progress
        self.measured_size = measurer.measure_cubic(cubic)

    @property
    def start_outline_progress(self) -> float:
        return self._start_outline_progress

    @property
    def end_outline_progress(self) -> float:
        return self._end_outline_progress

    def update_progress_range(
        self,
        start_outline_progress: Optional[float] = None,
        end_outline_progress: Optional[float] = None,
    ):
        start_outline_progress = start_outline_progress or self._start_outline_progress
        end_outline_progress = end_outline_progress or self._end_outline_progress

        if end_outline_progress < start_outline_progress:
            raise ValueError("end_outline_progress must be >= start_outline_progress")

        self._start_outline_progress = start_outline_progress
        self._end_outline_progress = end_outline_progress

    def cut_at_progress(
        self, cut_outline_progress: float
    ) -> Tuple["MeasuredCubic", "MeasuredCubic"]:
        cut_outline_progress = max(
            self._start_outline_progress,
            min(self._end_outline_progress, cut_outline_progress),
        )

        outline_progress_size = (
            self._end_outline_progress - self._start_outline_progress
        )
        progress_from_start = cut_outline_progress - self._start_outline_progress
        relative_progress = progress_from_start / outline_progress_size

        t = self.measurer.find_cubic_cut_point(
            self.cubic,
            relative_progress * self.measured_size,
        )

        if not (0 <= t <= 1):
            raise ValueError("Cubic cut point must be between 0 and 1")

        c1, c2 = self.cubic.split(t)
        return (
            MeasuredCubic(
                measurer=self.measurer,
                cubic=c1,
                start_outline_progress=self._start_outline_progress,
                end_outline_progress=cut_outline_progress,
            ),
            MeasuredCubic(
                measurer=self.measurer,
                cubic=c2,
                start_outline_progress=cut_outline_progress,
                end_outline_progress=self._end_outline_progress,
            ),
        )

    def __repr__(self) -> str:
        return f"MeasuredCubic([{self._start_outline_progress} .. {self._end_outline_progress}], size={self.measured_size}, cubic={self.cubic})"


class LengthMeasurer(Measurer):
    _segments: int = 3

    def measure_cubic(self, cubic: Cubic) -> float:
        return self._closest_progress_to(cubic, float("inf"))[1]

    def find_cubic_cut_point(self, cubic: Cubic, m: float) -> float:
        return self._closest_progress_to(cubic, m)[0]

    def _closest_progress_to(
        self, cubic: Cubic, threshold: float
    ) -> Tuple[float, float]:
        total = 0.0
        remainder = threshold
        prev = Point(cubic.anchor0_x, cubic.anchor0_y)

        for i in range(self._segments + 1):
            progress = i / self._segments
            point = cubic.point_on_curve(progress)
            segment = (point - prev).get_distance()

            if segment >= remainder:
                return (
                    progress - (1.0 - remainder / segment) / self._segments,
                    threshold,
                )

            remainder -= segment
            total += segment
            prev = point

        return 1.0, total


class MeasuredPolygon:
    def __init__(
        self,
        measurer: "Measurer",
        features: List[ProgressableFeature],
        cubics: List[Cubic],
        outline_progress: List[float],
    ):
        assert len(outline_progress) == len(cubics) + 1, (
            "Outline progress length is expected to be the cubics length + 1"
        )
        assert outline_progress[0] == 0, (
            "First outline progress value is expected to be zero"
        )
        assert outline_progress[-1] == 1, (
            "Last outline progress value is expected to be one"
        )

        self._measurer = measurer
        self._features = features
        measured_cubics: List[MeasuredCubic] = []
        start_outline_progress = 0.0

        for i, cubic in enumerate(cubics):
            if (outline_progress[i + 1] - outline_progress[i]) > distance_epsilon:
                measured_cubics.append(
                    MeasuredCubic(
                        measurer=measurer,
                        cubic=cubic,
                        start_outline_progress=start_outline_progress,
                        end_outline_progress=outline_progress[i + 1],
                    )
                )
                start_outline_progress = outline_progress[i + 1]

        measured_cubics[-1].update_progress_range(end_outline_progress=1)
        self._cubics = measured_cubics

    @classmethod
    def measure_polygon(
        cls, measurer: "Measurer", polygon: "RoundedPolygon"
    ) -> "MeasuredPolygon":
        cubics: List[Cubic] = []
        feature_to_cubic: List[Tuple["Feature", int]] = []

        for feature_index, feature in enumerate(polygon.features):
            for cubic_index, cubic in enumerate(feature.cubics):
                if (
                    isinstance(feature, CornerFeature)
                    and cubic_index == len(feature.cubics) // 2
                ):
                    feature_to_cubic.append((feature, len(cubics)))
                cubics.append(cubic)

        measures: List[float] = [0.0] * (len(cubics) + 1)
        total_measure = 0.0

        for i, cubic in enumerate(cubics):
            measure = measurer.measure_cubic(cubic)
            if measure < 0:
                raise ValueError("Measured cubic is expected to be >= 0")
            total_measure += measure
            measures[i + 1] = total_measure

        outline_progress = [m / total_measure for m in measures]

        features = [
            ProgressableFeature(
                positive_modulo(
                    (outline_progress[ix] + outline_progress[ix + 1]) / 2, 1
                ),
                feature,
            )
            for feature, ix in feature_to_cubic
        ]

        return cls(
            measurer=measurer,
            features=features,
            cubics=cubics,
            outline_progress=outline_progress,
        )

    @property
    def features(self) -> List[ProgressableFeature]:
        return list(self._features)

    @property
    def first(self) -> MeasuredCubic:
        return self._cubics[0]

    @property
    def last(self) -> MeasuredCubic:
        return self._cubics[-1]

    def __len__(self) -> int:
        return len(self._cubics)

    def __getitem__(self, index: int) -> MeasuredCubic:
        return self._cubics[index]

    def get_or_none(self, index: int) -> Optional[MeasuredCubic]:
        if index < 0 or index >= len(self._cubics):
            return None
        return self._cubics[index]

    def cut_and_shift(self, cutting_point: float) -> "MeasuredPolygon":
        if not (0 <= cutting_point <= 1):
            raise ValueError("Cutting point must be between 0 and 1")

        if cutting_point < distance_epsilon:
            return self

        target_index = next(
            i
            for i, c in enumerate(self._cubics)
            if cutting_point >= c._start_outline_progress
            and cutting_point <= c._end_outline_progress
        )
        target = self._cubics[target_index]

        b1, b2 = target.cut_at_progress(cutting_point)

        ret_cubics: List[Cubic] = [b2.cubic]
        for i in range(1, len(self._cubics)):
            idx = (i + target_index) % len(self._cubics)
            ret_cubics.append(self._cubics[idx].cubic)
        ret_cubics.append(b1.cubic)

        ret_outline_progress = [0.0] * (len(self._cubics) + 2)
        for i in range(len(ret_outline_progress)):
            if i == 0:
                ret_outline_progress[i] = 0
            elif i == len(ret_outline_progress) - 1:
                ret_outline_progress[i] = 1
            else:
                cubic_index = (target_index + i - 1) % len(self._cubics)
                ret_outline_progress[i] = positive_modulo(
                    self._cubics[cubic_index]._end_outline_progress - cutting_point,
                    1,
                )

        new_features = [
            ProgressableFeature(
                positive_modulo(f.progress - cutting_point, 1),
                f.feature,
            )
            for f in self._features
        ]

        return MeasuredPolygon(
            measurer=self._measurer,
            features=new_features,
            cubics=ret_cubics,
            outline_progress=ret_outline_progress,
        )
