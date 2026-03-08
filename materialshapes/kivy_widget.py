import os
from math import cos, exp, pi

from kivy.animation import Animation, AnimationTransition
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.logger import Logger
from kivy.properties import (
    ColorProperty,
    NumericProperty,
    StringProperty,
    ObjectProperty,
    OptionProperty,
)
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

from materialshapes import MaterialShapes
from materialshapes.morph import Morph
from materialshapes.renderer import (
    GenericPathBuilder,
    center_crop_square,
    render,
    HAS_THORVG,
    HAS_CAIRO,
)
from materialshapes.utils import path_from_morph, path_from_rounded_polygon

_BACKEND_LOGGED = False


class MaterialShape(Widget):
    shape = StringProperty("heart")
    image = StringProperty("")
    fill_color = ColorProperty([0.25, 0.1, 0.4, 1])
    bg_color = ColorProperty([0, 0, 0, 0])
    padding = NumericProperty(dp(10))
    backend = OptionProperty("thorvg", options=["thorvg", "cairo"])

    damping = NumericProperty(0.25)
    stiffness = NumericProperty(6)

    # internal props
    material_shapes = MaterialShapes()
    progress = NumericProperty(0)
    texture = ObjectProperty(None, allownone=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with self.canvas:
            Color(1, 1, 1, 1)
            self._rect = Rectangle(pos=self.pos, size=self.size)

        self._log_backend()
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
                    "backend",
                ],
                self.update_texture,
            )
        )
        self.bind(size=self.delayed_texture_update, pos=self._update_rect)
        self.bind(texture=self._on_texture)
        AnimationTransition.spring = self.spring

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size

    def _on_texture(self, *args):
        self._rect.texture = self.texture

    def _log_backend(self):
        global _BACKEND_LOGGED
        if _BACKEND_LOGGED:
            return

        backend = self.backend
        if backend == "thorvg" and not HAS_THORVG:
            if HAS_CAIRO:
                Logger.warning(
                    f"MaterialShapes: ThorVG requested but not available. Falling back to Cairo."
                )
                self.backend = "cairo"
            else:
                Logger.error(
                    "MaterialShapes: No rendering backend available (ThorVG/Cairo)."
                )
        elif backend == "cairo" and not HAS_CAIRO:
            if HAS_THORVG:
                Logger.warning(
                    f"MaterialShapes: Cairo requested but not available. Falling back to ThorVG."
                )
                self.backend = "thorvg"
            else:
                Logger.error(
                    "MaterialShapes: No rendering backend available (ThorVG/Cairo)."
                )

        Logger.info(f"MaterialShapes: Using {self.backend.upper()} backend.")
        _BACKEND_LOGGED = True

    _d_event = None

    def delayed_texture_update(self, *args):
        self._update_rect()
        # resizing image is expensive
        if self._d_event:
            self._d_event.cancel()
            self._d_event = None
        if os.path.exists(self.image):
            self._d_event = Clock.schedule_once(self.update_texture, 0.1)
        else:
            self.update_texture()

    _image_cache = {}

    def update_texture(self, *args):
        w, h = int(self.width), int(self.height)
        if w <= 0 or h <= 0:
            return

        center_x, center_y = w // 2, h // 2
        shape_size = max(1, min(w, h) - int(self.padding) * 2)

        builder = GenericPathBuilder()
        builder.translate(center_x - shape_size // 2, center_y - shape_size // 2)
        builder.scale(float(shape_size), float(shape_size))
        self._get_shape_path(builder)

        img_obj = None
        if os.path.exists(self.image):
            img_obj = center_crop_square(self.image, shape_size, self._image_cache)

        rgba = render(
            width=w,
            height=h,
            bg_rgba=self.bg_color,
            path_builder=builder,
            fill_rgba=None if img_obj is not None else self.fill_color,
            image=img_obj,
            image_x=center_x - shape_size // 2,
            image_y=center_y - shape_size // 2,
            image_w=shape_size,
            image_h=shape_size,
            backend=self.backend,
        )

        tex = self.texture
        if not tex or tex.size != (w, h):
            tex = Texture.create(size=(w, h), colorfmt="rgba")
            tex.flip_vertical()
            self.texture = tex

        tex.blit_buffer(rgba, colorfmt="rgba", bufferfmt="ubyte")
        self.canvas.ask_update()

    def _get_shape_path(self, path_builder):
        if self._current_morph:
            path_from_morph(
                path_builder,
                self._current_morph,
                self.progress,
            )
        else:
            shape = self.material_shapes.all.get(self.shape)
            path_from_rounded_polygon(path_builder, shape)

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

        self._anim = Animation(progress=1, d=d, t=self.spring)
        self._anim.bind(on_complete=self._on_morph_finished)
        if on_complete:
            self._anim.bind(on_complete=on_complete)
        self._anim.start(self)

    def _on_morph_finished(self, *args):
        self.shape = self._morph_to_icon
        self._current_morph = None
        self.progress = 0
