from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from material_shapes.kivy_widget import MaterialShape

KV = '''
BoxLayout:
    orientation: 'vertical'
    
    MaterialShape:
        id: shape
        image:"matthew-stephenson-Tn9BuH_vvuc-unsplash.jpg"
        shape: 'circle'
        fill_color: 0.9, 0.3, 0.5, 1
        size_hint:1, 0.9
        padding:dp(30)
 
    Label:
        id: shape_label
        text: app.current_shape_name
        size_hint_y: 0.1
        font_size: '20sp'
        halign:"center"
        bold: True
    
    BoxLayout:
        size_hint_y: 0.1
        Button:
            text: 'Prev'
            on_release: app.prev_shape()
        Button:
            text: 'Next'
            on_release: app.next_shape()
'''

class TestApp(App):
    current_shape_name = StringProperty("")

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        shape_widget = self.root.ids.shape
        self.shape_names = list(shape_widget.material_shapes.all.keys())
        self.current_index = self.shape_names.index(shape_widget.shape)
        self.update_label()

    def morph_to_index(self, index):
        shape_widget = self.root.ids.shape
        self.current_index = index % len(self.shape_names)
        next_shape = self.shape_names[self.current_index]
        shape_widget.morph_to(next_shape)
        self.update_label()

    def update_label(self):
        self.current_shape_name = self.shape_names[self.current_index]

    def next_shape(self):
        self.morph_to_index(self.current_index + 1)

    def prev_shape(self):
        self.morph_to_index(self.current_index - 1)
 
if __name__ == '__main__':
    TestApp().run()

