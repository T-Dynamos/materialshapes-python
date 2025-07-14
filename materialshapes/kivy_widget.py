import os
import time
from math import cos, exp, pi

import cairo
from kivy.animation import Animation, AnimationTransition
from kivy.clock import Clock
from kivy.graphics import Rectangle
from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.metrics import dp
from kivy.properties import (
    ColorProperty,
    ListProperty,
    NumericProperty,
    ObjectProperty,
    StringProperty,
)
from kivy.uix.image import Image as KIVYImage
from PIL import Image

from materialshapes import MaterialShapes
from materialshapes.morph import Morph
from materialshapes.utils import path_from_morph, path_from_rounded_polygon


class MaterialShape(KIVYImage):
    shape = StringProperty("heart")
    image = StringProperty("")
    fill_color = ColorProperty([0.25, 0.1, 0.4, 1])
    bg_color = ColorProperty([0, 0, 0, 0])
    padding = NumericProperty(dp(10))

    damping = NumericProperty(0.25)
    stiffness = NumericProperty(6)

    # internal props
    material_shapes = MaterialShapes()
    progress = NumericProperty(0)
    _rectangle = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        Clock.schedule_once(lambda dt: self.update_texture())
        self.bind(
            **dict.fromkeys(
                [
                    "shape",
                    "fill_color",
                    "bg_color",
                    "padding",
                    "progress",
                    "image",
                ],
                self.update_texture,
            )
        )
        self.bind(size=self.delayed_texture_update)
        AnimationTransition.spring = self.spring

    _d_event = None

    def delayed_texture_update(self, *args):
        # resizing image is expensive
        if self._d_event:
            self._d_event.cancel()
            self._d_event = None
        if os.path.exists(self.image):
            self._d_event = Clock.schedule_once(self.update_texture, 0.1)
        else:
            self.update_texture()

    def update_texture(self, *args):
        w, h = int(self.width), int(self.height)
        center_x, center_y = w // 2, h // 2

        shape_size = min(w, h) - int(self.padding) * 2

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(surface)
        ctx.set_source_rgba(*self.bg_color)
        ctx.paint()
        ctx.translate(center_x - shape_size // 2, center_y - shape_size // 2)

        if os.path.exists(self.image):
            ctx.set_source(self.get_img_pattern(shape_size))
        else:
            # rgba to bgra
            rgba = list(self.fill_color)
            bgra = [rgba[2], rgba[1], rgba[0], rgba[3]]
            ctx.set_source_rgba(*bgra)

        ctx.scale(*[shape_size] * 2)
        self._get_shape_path(ctx)
        ctx.fill()

        buf = surface.get_data()
        tex = Texture.create(size=self.size, colorfmt="rgba")
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.flip_vertical()

        self.texture = tex

    _image_cache = {}

    def get_img_pattern(self, shape_size):
        img_key = f"{self.image}_{shape_size}"
        if not (pattern := self._image_cache.get(img_key)):
            im = self._crop_center_square_resize(self.image, shape_size)
            pattern = self._image_cache[img_key] = cairo.SurfacePattern(
                self._from_pil(im)
            )
        return pattern

    _pil_cache = {}

    def _crop_center_square_resize(self, path, new_size):
        img = self._pil_cache.get(path)
        if img is None:
            img = self._pil_cache[path] = Image.open(path)

        min_dim = min(img.size)
        x = (img.width - min_dim) // 2
        y = (img.height - min_dim) // 2
        box = (x, y, x + min_dim, y + min_dim)
        return img.crop(box).resize((new_size, new_size), Image.LANCZOS)

    def _from_pil(
        self,
        im: Image.Image,
        alpha: float = 1.0,
        format: cairo.Format = cairo.FORMAT_ARGB32,
    ):
        if "A" not in im.getbands():
            im.putalpha(int(alpha * 255))
        arr = bytearray(im.tobytes("raw", "RGBA"))
        return cairo.ImageSurface.create_for_data(arr, format, im.width, im.height)

    def _get_shape_path(self, ctx):
        if self._current_morph:
            path_from_morph(
                ctx,
                self._current_morph,
                self.progress,
            )
        else:
            shape = self.material_shapes.all.get(self.shape)
            path_from_rounded_polygon(ctx, shape)

    def s_rotate(self, progress: float) -> float:
        return progress 

    def spring(self, progress: float) -> float:
        if progress <= 0.0:
            return 0.0
        if progress >= 1.0:
            return 1.0

        omega = self.stiffness * pi
        decay = exp(-self.damping * omega * progress)
        oscillation = cos(omega * progress * (1 - self.damping))

        return 1 - (decay * oscillation)

    _current_morph = None
    _morph_to_icon = None
    _anim = None
    def morph_to(self, new_icon: str, d=0.5, t="spring", on_complete=None):

        if self._anim is not None:
            self._anim.cancel(self)
            self._anim = None

        self._morph_to_icon = new_icon
        start_shape = self.material_shapes.all.get(self.shape)
        end_shape = self.material_shapes.all.get(new_icon)
        self._current_morph = Morph(start_shape, end_shape)

        self.progress = 0

        self._anim = Animation(progress=1, d=d, t="spring")
        self._anim.bind(on_complete=self._on_morph_finished)
        if on_complete:
            self._anim.bind(on_complete=on_complete)
        self._anim.start(self)

    def _on_morph_finished(self, *args):
        self.shape = self._morph_to_icon
        self._current_morph = None
        self.progress = 0
