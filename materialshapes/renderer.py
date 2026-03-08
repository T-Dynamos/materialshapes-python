import os
import sys
import math
import multiprocessing
import ctypes
from io import BytesIO
from typing import Iterable, Optional, Tuple, Union, Protocol
from PIL import Image

__all__ = ["render", "GenericPathBuilder", "center_crop_square", "HAS_THORVG", "HAS_CAIRO"]

# Try to import thorvg-python from system or external path
HAS_THORVG = False
tvg = None
try:
    import thorvg_python as tvg_lib
    tvg = tvg_lib
    HAS_THORVG = True
except ImportError:
    # If not found, try the specific local path if it exists
    THORVG_PYTHON_PATH = "/home/tdynamos/Downloads/thorvg-python-1.1.1/src"
    if os.path.exists(THORVG_PYTHON_PATH):
        if THORVG_PYTHON_PATH not in sys.path:
            sys.path.insert(0, THORVG_PYTHON_PATH)
        try:
            import thorvg_python as tvg_lib
            tvg = tvg_lib
            HAS_THORVG = True
        except ImportError:
            pass

try:
    import cairo

    HAS_CAIRO = True
except ImportError:
    HAS_CAIRO = False


class PathBuilder(Protocol):
    def new_path(self): ...
    def move_to(self, x: float, y: float): ...
    def line_to(self, x: float, y: float): ...
    def curve_to(
        self, cx1: float, cy1: float, cx2: float, cy2: float, x: float, y: float
    ): ...
    def close_path(self): ...
    def translate(self, tx: float, ty: float): ...
    def scale(self, sx: float, sy: float): ...
    def rotate(self, radians: float): ...


class _Affine2D:
    def __init__(self, a=1.0, b=0.0, c=0.0, d=1.0, e=0.0, f=0.0):
        self.a, self.b, self.c, self.d, self.e, self.f = a, b, c, d, e, f

    def apply(self, x: float, y: float) -> Tuple[float, float]:
        return (
            self.a * x + self.c * y + self.e,
            self.b * x + self.d * y + self.f,
        )

    def multiply(self, other: "_Affine2D") -> "_Affine2D":
        return _Affine2D(
            a=self.a * other.a + self.c * other.b,
            b=self.b * other.a + self.d * other.b,
            c=self.a * other.c + self.c * other.d,
            d=self.b * other.c + self.d * other.d,
            e=self.a * other.e + self.c * other.f + self.e,
            f=self.b * other.e + self.d * other.f + self.f,
        )


class GenericPathBuilder:
    def __init__(self):
        self._transform = _Affine2D()
        self._ops = []
        self._fill_rgba = None
        self._stroke_rgba = None
        self._stroke_width = None
        self._stroke_join = None
        self._stroke_cap = None
        self._stroke_dash = None

    def new_path(self):
        self._ops.clear()
        self._fill_rgba = None
        self._stroke_rgba = None
        self._stroke_width = None
        self._stroke_join = None
        self._stroke_cap = None
        self._stroke_dash = None

    def move_to(self, x: float, y: float):
        self._ops.append(("M", x, y))

    def line_to(self, x: float, y: float):
        self._ops.append(("L", x, y))

    def curve_to(
        self, cx1: float, cy1: float, cx2: float, cy2: float, x: float, y: float
    ):
        self._ops.append(("C", cx1, cy1, cx2, cy2, x, y))

    def close_path(self):
        self._ops.append(("Z",))

    def fill(self, r: int, g: int, b: int, a: int = 255):
        self._fill_rgba = (r, g, b, a)

    def stroke_width(self, width: float):
        self._stroke_width = float(width)

    def stroke_fill(self, r: int, g: int, b: int, a: int = 255):
        self._stroke_rgba = (r, g, b, a)

    def stroke_join_round(self):
        self._stroke_join = "round"

    def stroke_cap_round(self):
        self._stroke_cap = "round"

    def stroke_dash(self, pattern: Iterable[float], offset: float = 0.0):
        self._stroke_dash = (tuple(float(v) for v in pattern), float(offset))

    def translate(self, tx: float, ty: float):
        self._transform = self._transform.multiply(_Affine2D(e=tx, f=ty))

    def scale(self, sx: float, sy: float):
        self._transform = self._transform.multiply(_Affine2D(a=sx, d=sy))

    def rotate(self, radians: float):
        c, s = math.cos(radians), math.sin(radians)
        self._transform = self._transform.multiply(_Affine2D(a=c, b=s, c=-s, d=c))

    def apply_to(self, target, engine=None):
        for op in self._ops:
            if op[0] == "M":
                x, y = self._transform.apply(op[1], op[2])
                target.move_to(x, y)
            elif op[0] == "L":
                x, y = self._transform.apply(op[1], op[2])
                target.line_to(x, y)
            elif op[0] == "C":
                cx1, cy1 = self._transform.apply(op[1], op[2])
                cx2, cy2 = self._transform.apply(op[3], op[4])
                x, y = self._transform.apply(op[5], op[6])
                if hasattr(target, "cubic_to"):
                    target.cubic_to(cx1, cy1, cx2, cy2, x, y)
                else:
                    target.curve_to(cx1, cy1, cx2, cy2, x, y)
            elif op[0] == "Z":
                target.close() if hasattr(target, "close") else target.close_path()

        if self._fill_rgba is not None:
            if hasattr(target, "set_fill_color"):
                target.set_fill_color(*self._fill_rgba)
            elif hasattr(target, "set_source_rgba"):
                # Cairo
                target.set_source_rgba(
                    self._fill_rgba[0] / 255,
                    self._fill_rgba[1] / 255,
                    self._fill_rgba[2] / 255,
                    self._fill_rgba[3] / 255,
                )

        if self._stroke_width is not None:
            if hasattr(target, "set_stroke_width"):
                target.set_stroke_width(self._stroke_width)
            elif hasattr(target, "set_line_width"):
                target.set_line_width(self._stroke_width)

        if self._stroke_join == "round":
            if HAS_THORVG and isinstance(target, tvg.Shape):
                target.set_stroke_join(tvg.StrokeJoin.ROUND)
            elif HAS_CAIRO and isinstance(target, cairo.Context):
                target.set_line_join(cairo.LINE_JOIN_ROUND)

        if self._stroke_cap == "round":
            if HAS_THORVG and isinstance(target, tvg.Shape):
                target.set_stroke_cap(tvg.StrokeCap.ROUND)
            elif HAS_CAIRO and isinstance(target, cairo.Context):
                target.set_line_cap(cairo.LINE_CAP_ROUND)

        if self._stroke_dash is not None:
            pattern, offset = self._stroke_dash
            if hasattr(target, "set_stroke_dash"):
                target.set_stroke_dash(pattern, offset)
            elif hasattr(target, "set_dash"):
                target.set_dash(list(pattern), offset)


# Centralized ThorVG Engine
_TVG_ENGINE = None


def get_tvg_engine():
    global _TVG_ENGINE
    if _TVG_ENGINE is None and HAS_THORVG:
        _TVG_ENGINE = tvg.Engine(threads=multiprocessing.cpu_count())
    return _TVG_ENGINE


def render(
    width: int,
    height: int,
    bg_rgba: Iterable[float],
    path_builder: GenericPathBuilder,
    fill_rgba: Optional[Iterable[float]] = None,
    image: Optional[Image.Image] = None,
    image_x: float = 0,
    image_y: float = 0,
    image_w: float = 0,
    image_h: float = 0,
    backend: str = "thorvg",
) -> bytes:
    if backend == "thorvg":
        return _render_thorvg(
            width,
            height,
            bg_rgba,
            path_builder,
            fill_rgba,
            image,
            image_x,
            image_y,
            image_w,
            image_h,
        )
    elif backend == "cairo":
        return _render_cairo(
            width,
            height,
            bg_rgba,
            path_builder,
            fill_rgba,
            image,
            image_x,
            image_y,
            image_w,
            image_h,
        )
    else:
        raise ValueError(f"Unknown backend: {backend}")


def _render_thorvg(
    width,
    height,
    bg_rgba,
    path_builder,
    fill_rgba,
    image,
    image_x,
    image_y,
    image_w,
    image_h,
) -> bytes:
    if not HAS_THORVG:
        raise RuntimeError("ThorVG not available")

    engine = get_tvg_engine()
    canvas = tvg.SwCanvas(engine)
    canvas.set_target(width, height, cs=tvg.Colorspace.ABGR8888S)

    # BG
    bg = tvg.Shape(engine)
    bg.append_rect(0, 0, float(width), float(height), 0, 0, True)
    bg.set_fill_color(
        int(bg_rgba[0] * 255),
        int(bg_rgba[1] * 255),
        int(bg_rgba[2] * 255),
        int(bg_rgba[3] * 255),
    )
    canvas.add(bg)

    # Shape
    shape = tvg.Shape(engine)
    path_builder.apply_to(shape, engine)

    if image is not None:
        if not isinstance(image, Image.Image):
            raise ValueError("image must be a PIL.Image.Image instance")

        pic = tvg.Picture(engine)
        # Convert to RGBA for consistency
        if image.mode != "RGBA":
            image = image.convert("RGBA")

        # ThorVG Colorspace.ABGR8888 (0) is [R, G, B, A] in memory on little-endian
        # PIL "RGBA" tobytes is [R, G, B, A]
        pic.load_raw(
            image.tobytes("raw", "RGBA"),
            image.width,
            image.height,
            tvg.Colorspace.ABGR8888,
            True,
        )

        pic.set_size(float(image_w), float(image_h))
        pic.translate(float(image_x), float(image_y))
        pic.set_clip(shape)
        canvas.add(pic)
    elif fill_rgba:
        shape.set_fill_color(
            int(fill_rgba[0] * 255),
            int(fill_rgba[1] * 255),
            int(fill_rgba[2] * 255),
            int(fill_rgba[3] * 255),
        )
        canvas.add(shape)
    else:
        canvas.add(shape)

    canvas.draw(True)
    canvas.sync()

    return bytes(canvas.buffer_arr)


def _render_cairo(
    width,
    height,
    bg_rgba,
    path_builder,
    fill_rgba,
    image,
    image_x,
    image_y,
    image_w,
    image_h,
) -> bytes:
    if not HAS_CAIRO:
        raise RuntimeError("Cairo not available")

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    # BG
    ctx.set_source_rgba(*bg_rgba)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()

    # Path
    path_builder.apply_to(ctx)

    if image is not None:
        if not isinstance(image, Image.Image):
            raise ValueError("image must be a PIL.Image.Image instance")

        # Cairo FORMAT_ARGB32 is [B, G, R, A] in memory on little-endian
        if image.mode != "RGBA":
            image = image.convert("RGBA")
        img_data = image.tobytes("raw", "BGRA")
        img_w, img_h = image.width, image.height

        img_surface = cairo.ImageSurface.create_for_data(
            bytearray(img_data), cairo.FORMAT_ARGB32, img_w, img_h
        )

        ctx.save()
        ctx.clip()
        ctx.translate(image_x, image_y)
        ctx.scale(image_w / img_w, image_h / img_h)
        ctx.set_source_surface(img_surface, 0, 0)
        ctx.paint()
        ctx.restore()
    elif fill_rgba:
        ctx.set_source_rgba(*fill_rgba)
        ctx.fill()
    elif path_builder._fill_rgba:
        ctx.fill()

    # Handle stroke if any
    if path_builder._stroke_rgba:
        ctx.set_source_rgba(
            path_builder._stroke_rgba[0] / 255,
            path_builder._stroke_rgba[1] / 255,
            path_builder._stroke_rgba[2] / 255,
            path_builder._stroke_rgba[3] / 255,
        )
        ctx.stroke()

    # Cairo FORMAT_ARGB32 is BGRA in memory on little-endian
    data = surface.get_data()
    # Convert BGRA to RGBA
    img = Image.frombuffer("RGBA", (width, height), data, "raw", "BGRA", 0, 1)
    return img.tobytes("raw", "RGBA")



def center_crop_square(path: str, new_size: int, cache: dict) -> Image.Image:
    key = f"img_{path}_{new_size}"
    if key in cache:
        return cache[key]

    img = Image.open(path)
    min_dim = min(img.size)
    x = (img.width - min_dim) // 2
    y = (img.height - min_dim) // 2
    cropped = img.crop((x, y, x + min_dim, y + min_dim)).resize(
        (new_size, new_size), Image.LANCZOS
    )

    cache[key] = cropped
    return cropped
