from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from materialshapes.kivy_widget import MaterialShape
from kivy.uix.boxlayout import BoxLayout
from kivy.metrics import dp
from kivy.properties import ColorProperty, ObjectProperty
from kivy.uix.behaviors import ButtonBehavior

class TapShape(ButtonBehavior, MaterialShape):
    outline_color = ColorProperty([0,0,0,0])

KV = '''

<TapShape>:
    canvas:
        Color:
            rgba:root.outline_color
        Line:
            rectangle: (self.x, self.y, self.width, self.height)

BoxLayout:
    orientation: 'vertical'
    padding:dp(20)
    GridLayout:
        cols:5
        id:grid
        spacing:dp(5)
        size_hint_y:0.6

    MaterialShape:
        id: shape
        # Photo by Prince Akachi on Unsplash
        # https://unsplash.com/photos/woman-smiling-beside-red-wall-LWkFHEGpleE
        image:"./examples/test_img.jpg"
        shape: 'circle'
        fill_color: [1,1,1,1]
        size_hint_y: 0.35
        padding:dp(30)
    
    Label:
        id: shape_label
        text: app.current_shape_name
        size_hint_y:0.05
        font_size: '20sp'
        halign:"center"
'''

class TestApp(App):
    current_shape_name = StringProperty("")

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        shape_widget = self.root.ids.shape
        self.shape_names = list(shape_widget.material_shapes.all.keys())
        self.update_label(self.shape_names.index(shape_widget.shape))
        
        for _ in range(0, len(self.shape_names)):

            wid = TapShape()
            wid.shape = self.shape_names[_]
            wid.padding = dp(3)
            wid.fill_color = [1,1,1,1]
            
            if wid.shape == shape_widget.shape:
                wid.outline_color = [1,0,0,1]
            else:
                wid.outline_color = [0,0,0,0]

            wid.on_release = lambda *args, _=_, wid=wid: self.morph_to(_, wid)
            self.root.ids.grid.add_widget(wid)
    
    def morph_to(self, index, wid):
        self.root.ids.shape.morph_to(wid.shape)
        
        for widget in self.root.ids.grid.children:
            widget.outline_color = [0,0,0,0]
        
        wid.outline_color = [1, 0, 0, 1]
        self.update_label(index)

    def update_label(self, index):
        self.current_shape_name = self.shape_names[index]
 
TestApp().run()
