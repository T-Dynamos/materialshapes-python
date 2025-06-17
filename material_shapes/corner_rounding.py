class CornerRounding:
    unrounded = None

    def __init__(self, radius=0, smoothing=0):
        if radius < 0:
            raise ValueError("radius must be greater than or equal to zero")
        if not (0 <= smoothing <= 1):
            raise ValueError("smoothing must be in the range [0, 1]")

        self.radius = radius
        self.smoothing = smoothing

    def __repr__(self):
        return f"CornerRounding(radius={self.radius}, smoothing={self.smoothing})"


CornerRounding.unrounded = CornerRounding(0, 0)
