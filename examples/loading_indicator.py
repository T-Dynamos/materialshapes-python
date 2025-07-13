from kivy.app import App
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.properties import NumericProperty, ListProperty, ColorProperty
from materialshapes.kivy_widget import MaterialShape
from kivy.utils import get_color_from_hex


class RotatingShape(MaterialShape):
    rotation_angle = NumericProperty(0)

KV = '''
#: import get_color_from_hex kivy.utils.get_color_from_hex

<RotatingShape>:
    canvas.before:
        PushMatrix
        Rotate:
            angle: -self.rotation_angle
            origin: self.center
    canvas.after:
        PopMatrix

BoxLayout:
    orientation: "vertical"
    spacing: dp(10)

    AnchorLayout:
        canvas.before:
            Color:
                rgba: get_color_from_hex("#C7B3FC")
            Rectangle:
                pos: self.pos
                size: self.size

        RotatingShape:
            id: morph_shape
            shape: 'circle'
            fill_color: get_color_from_hex("#685496")
            size_hint: None, None
            size: [size_slider.value] * 2
            damping: damping_slider.value
            stiffness: stiffness_slider.value
            padding: self.size[0] * (1 - 0.82)
            canvas.before:
                Color:
                    rgba: get_color_from_hex("#F7F2FA")
                Ellipse:
                    size: self.size
                    pos: self.pos

    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: self.minimum_height
        spacing: dp(8)
        padding:dp(10)

        # Size Slider
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)

            Label:
                text: "Size"
                size_hint_x: None
                width: dp(60)
            Slider:
                id: size_slider
                min: dp(50)
                max: dp(300)
                value: dp(100)
            Label:
                text: f"{int(size_slider.value)}"
                size_hint_x: None
                width: dp(40)

        # Damping Slider
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)

            Label:
                text: "Damping"
                size_hint_x: None
                width: dp(60)
            Slider:
                id: damping_slider
                min: 0.0
                max: 1.0
                value: 0.5
            Label:
                text: f"{damping_slider.value:.2f}"
                size_hint_x: None
                width: dp(40)

        # Stiffness Slider
        BoxLayout:
            size_hint_y: None
            height: dp(50)
            spacing: dp(10)

            Label:
                text: "Stiffness"
                size_hint_x: None
                width: dp(60)
            Slider:
                id: stiffness_slider
                min: 1.0
                max: 10.0
                value: 3.0
            Label:
                text: f"{stiffness_slider.value:.2f}"
                size_hint_x: None
                width: dp(40)
'''

class MorphApp(App):
    shape_sequence = ["cookie12Sided", "pentagon", "pill", "verySunny", "cookie4Sided", "oval", "flower", "softBoom"]
    current_index = 0
    duration = 0.65

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        self.shape_widget = self.root.ids.morph_shape
        Clock.schedule_once(self.start_anim_loop, 0.5)

    def start_anim_loop(self, *args):
        self.run_cycle()
        Clock.schedule_interval(self.run_cycle, self.duration)

    def run_cycle(self, *args):
        # Shape morph
        shape = self.shape_sequence[self.current_index % len(self.shape_sequence)]
        self.shape_widget.morph_to(shape, d=self.duration * 0.9)
        # Rotation
        target_angle = (self.current_index + 1) * 90
        Animation(rotation_angle=target_angle, duration=self.duration * 0.8, t='out_cubic').start(self.shape_widget)
        self.current_index += 1


MorphApp().run()

