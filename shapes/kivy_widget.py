import os
import time
from math import cos, exp, pi

import cairo
from kivy.animation import Animation, AnimationTransition
from kivy.clock import Clock
from kivy.graphics import Rectangle
from kivy.graphics.texture import Texture
from kivy.properties import ColorProperty, ListProperty, NumericProperty, StringProperty
from kivy.uix.widget import Widget

from shapes.material_shapes import MaterialShapes
from shapes.morph import Morph
from shapes.utils import path_from_morph, path_from_rounded_polygon


def spring(progress: float, damping: float = 0.4, stiffness: float = 6.0) -> float:
    if progress <= 0.0:
        return 0.0
    if progress >= 1.0:
        return 1.0

    omega = stiffness * pi  # angular frequency
    decay = exp(-damping * omega * progress)
    oscillation = cos(omega * progress * (1 - damping))

    return 1 - (decay * oscillation)


AnimationTransition.spring = staticmethod(spring)


class MaterialIcon(Widget):
    icon = StringProperty("triangle")
    fill_color = ColorProperty([0.25, 0.1, 0.4, 1])
    bg_color = ColorProperty([0, 0, 0, 0])
    padding = ListProperty([4, 4, 4, 4])
    progress = NumericProperty(0)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.material_shapes = MaterialShapes()
        self._rectangle = None

        Clock.schedule_once(lambda dt: self.update_texture())

        self.bind(
            pos=self.update_texture,
            size=self.update_texture,
            icon=self.update_texture,
            fill_color=self.update_texture,
            bg_color=self.update_texture,
            padding=self.update_texture,
            progress=self.update_texture,
        )

    def update_texture(self, *args):
        w, h = map(int, self.size)
        pad_left, pad_top, pad_right, pad_bottom = self.padding

        usable_width = w - pad_left - pad_right
        usable_height = h - pad_top - pad_bottom

        if usable_width <= 0 or usable_height <= 0:
            return

        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        ctx = cairo.Context(surface)

        # Background color
        ctx.set_source_rgba(*self.bg_color)
        ctx.paint()

        # Shape transformation

        sx = usable_width
        sy = usable_height
        scale_factor = min(sx, sy)

        offset_x = (usable_width - scale_factor) / 2 + pad_left
        offset_y = (usable_height - scale_factor) / 2 + pad_top

        ctx.translate(offset_x, offset_y)
        ctx.scale(scale_factor, scale_factor)

        if self._current_morph:
            path_from_morph(
                ctx,
                self._current_morph,
                self.progress,
                rotation_pivot_x=3.14 / 2,
                rotation_pivot_y=0,
                start_angle=3.14,
            )
        else:
            path_from_rounded_polygon(ctx, self.material_shapes.all.get(self.icon))

        ctx.set_source_rgba(*self.fill_color)
        ctx.fill()

        # Convert to Kivy texture
        buf = surface.get_data()
        tex = Texture.create(size=(w, h), colorfmt="rgba")
        tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
        tex.flip_vertical()

        if not self._rectangle:
            with self.canvas:
                self._rectangle = Rectangle(texture=tex, pos=self.pos, size=self.size)
        else:
            self._rectangle.texture = tex
            self._rectangle.pos = self.pos
            self._rectangle.size = self.size

    _current_morph = None
    _morph_to_icon = None

    def morph_to(self, new_icon: str, duration=0.4):
        if new_icon == self.icon:
            return

        self._morph_to_icon = new_icon

        start_shape = self.material_shapes.all.get(self.icon)
        end_shape = self.material_shapes.all.get(new_icon)

        self._current_morph = Morph(start_shape, end_shape)
        self.progress = 0.0

        anim = Animation(progress=1, d=duration, t="spring")
        anim.bind(on_complete=self._on_morph_finished)
        anim.start(self)

    def _on_morph_finished(self, *args):
        self.icon = self._morph_to_icon
        self._current_morph = None
        self.progress = 0.0
        self.update_texture()
