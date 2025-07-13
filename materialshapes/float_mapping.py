from materialshapes.utils import distance_epsilon


def progress_in_range(
    progress: float, progress_from: float, progress_to: float
) -> bool:
    if progress_to >= progress_from:
        return progress_from <= progress <= progress_to
    else:
        return progress >= progress_from or progress <= progress_to


def positive_modulo(a: float, b: float) -> float:
    return (a % b + b) % b


def linear_map(x_values: list[float], y_values: list[float], x: float) -> float:
    if not (0 <= x <= 1):
        raise ValueError(f"Invalid progress {x}")

    segment_start_index = -1

    for i in range(len(x_values)):
        if progress_in_range(x, x_values[i], x_values[(i + 1) % len(x_values)]):
            segment_start_index = i
            break

    if segment_start_index == -1:
        raise RuntimeError("segment_start_index not found.")

    segment_end_index = (segment_start_index + 1) % len(x_values)

    segment_size_x = positive_modulo(
        x_values[segment_end_index] - x_values[segment_start_index], 1
    )
    segment_size_y = positive_modulo(
        y_values[segment_end_index] - y_values[segment_start_index], 1
    )

    position_in_segment = (
        0.5
        if segment_size_x < 0.001
        else positive_modulo(x - x_values[segment_start_index], 1) / segment_size_x
    )

    return positive_modulo(
        y_values[segment_start_index] + segment_size_y * position_in_segment, 1
    )


def validate_progress(p: list[float]):
    if not p:
        raise ValueError("List is empty.")

    prev = p[-1]
    wraps = 0

    for curr in p:
        if not (0 <= curr < 1):
            raise ValueError(f"Progress outside of range: {p}")
        if abs(progress_distance(curr, prev)) <= distance_epsilon:
            raise ValueError(f"Progress repeats a value: {p}")
        if curr < prev:
            wraps += 1
            if wraps > 1:
                raise ValueError(f"Progress wraps more than once: {p}")
        prev = curr


def progress_distance(p1: float, p2: float) -> float:
    diff = abs(p1 - p2)
    return min(diff, 1.0 - diff)


class DoubleMapper:
    identity = None
    _source_values = []
    _target_values = []

    def __init__(self, mappings: list[tuple[float, float]]):
        self._source_values = [pair[0] for pair in mappings]
        self._target_values = [pair[1] for pair in mappings]

        validate_progress(self._source_values)
        validate_progress(self._target_values)

    def map(self, x: float) -> float:
        return linear_map(self._source_values, self._target_values, x)

    def map_back(self, x: float) -> float:
        return linear_map(self._target_values, self._source_values, x)


DoubleMapper.identity = DoubleMapper([(0.0, 0.0), (0.5, 0.5)])
