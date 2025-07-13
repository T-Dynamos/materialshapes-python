from abc import ABC, abstractmethod

from materialshapes.utils import distance_epsilon


class Feature(ABC):
    def __init__(self, cubics):
        if not cubics:
            raise ValueError("Features need at least one cubic.")
        if not self._is_continuous(cubics):
            raise ValueError(
                "Feature must be continuous, with the anchor points of all cubics "
                "matching the anchor points of the preceding and succeeding cubics."
            )
        self._cubics = cubics

    @staticmethod
    def _is_continuous(cubics):
        prev = cubics[0]
        for cubic in cubics[1:]:
            if (
                abs(cubic.anchor0_x - prev.anchor1_x) > distance_epsilon
                or abs(cubic.anchor0_y - prev.anchor1_y) > distance_epsilon
            ):
                return False
            prev = cubic
        return True

    @classmethod
    def build_ignorable_feature(cls, cubics):
        return EdgeFeature(cubics)

    @classmethod
    def build_edge(cls, cubic):
        return EdgeFeature([cubic])

    @classmethod
    def build_convex_corner(cls, cubics):
        return CornerFeature(cubics, convex=True)

    @classmethod
    def build_concave_corner(cls, cubics):
        return CornerFeature(cubics, convex=False)

    @property
    def cubics(self):
        return list(self._cubics)

    @property
    @abstractmethod
    def is_ignorable_feature(self): ...

    @property
    @abstractmethod
    def is_edge(self): ...

    @property
    @abstractmethod
    def is_corner(self): ...

    @property
    @abstractmethod
    def is_convex_corner(self): ...

    @property
    @abstractmethod
    def is_concave_corner(self): ...

    @abstractmethod
    def transformed(self, f): ...

    @abstractmethod
    def reversed(self): ...


class EdgeFeature(Feature):
    def transformed(self, f):
        return EdgeFeature([c.transformed(f) for c in self._cubics])

    def reversed(self):
        return EdgeFeature([c.reverse() for c in reversed(self._cubics)])

    @property
    def is_ignorable_feature(self):
        return True

    @property
    def is_edge(self):
        return True

    @property
    def is_corner(self):
        return False

    @property
    def is_convex_corner(self):
        return False

    @property
    def is_concave_corner(self):
        return False

    def __str__(self):
        return "Edge"


class CornerFeature(Feature):
    def __init__(self, cubics, convex=True):
        self.convex = convex
        super().__init__(cubics)

    def transformed(self, f):
        return CornerFeature(
            [c.transformed(f) for c in self._cubics], convex=self.convex
        )

    def reversed(self):
        return CornerFeature(
            [c.reverse() for c in reversed(self._cubics)], convex=not self.convex
        )

    @property
    def is_ignorable_feature(self):
        return False

    @property
    def is_edge(self):
        return False

    @property
    def is_corner(self):
        return True

    @property
    def is_convex_corner(self):
        return self.convex

    @property
    def is_concave_corner(self):
        return not self.convex

    def __str__(self):
        cubics_str = ", ".join(f"[{c}]" for c in self._cubics)
        return f"Corner: cubics={cubics_str} convex={self.convex}"
