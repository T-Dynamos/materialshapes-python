from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.properties import StringProperty
from shapes.kivy_widget import MaterialIcon

KV = '''
BoxLayout:
    orientation: 'vertical'
    
    MaterialIcon:
        id: icon
        icon: 'heart'
        fill_color: 0.9, 0.3, 0.5, 1
        size_hint:1, 0.9
        padding: [dp(30)]*4
        pos_hint: {'center_x': 0.5, 'center_y': 0.5}
    
    Label:
        id: icon_label
        text: app.current_icon_name
        size_hint_y: 0.1
        font_size: '20sp'
        halign:"center"
        bold: True
    
    BoxLayout:
        size_hint_y: 0.1
        Button:
            text: 'Prev'
            on_release: app.prev_icon()
        Button:
            text: 'Next'
            on_release: app.next_icon()
'''

class TestApp(App):
    current_icon_name = StringProperty("")

    def build(self):
        return Builder.load_string(KV)

    def on_start(self):
        icon_widget = self.root.ids.icon
        self.icon_names = list(icon_widget.material_shapes.all.keys())
        self.current_index = self.icon_names.index(icon_widget.icon)
        self.update_label()

    def morph_to_index(self, index):
        icon_widget = self.root.ids.icon
        self.current_index = index % len(self.icon_names)
        next_icon = self.icon_names[self.current_index]
        icon_widget.morph_to(next_icon)
        self.update_label()

    def update_label(self):
        self.current_icon_name = self.icon_names[self.current_index]

    def next_icon(self):
        self.morph_to_index(self.current_index + 1)

    def prev_icon(self):
        self.morph_to_index(self.current_index - 1)
 
if __name__ == '__main__':
    TestApp().run()

