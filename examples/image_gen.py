import os

from PIL import Image

from materialshapes import MaterialShapes
from materialshapes.renderer import GenericPathBuilder, render
from materialshapes.utils import path_from_rounded_polygon

os.makedirs("shapes_png", exist_ok=True)

spacing = 50
size = 400
width, height = [size] * 2
translate_x, translate_y = [spacing / 2] * 2
scale_factor = width - spacing

material_shapes = MaterialShapes()

fill_r, fill_g, fill_b = (0x40 / 255, 0x2F / 255, 0x67 / 255)

for name, shape in material_shapes.all.items():
    builder = GenericPathBuilder()
    builder.translate(translate_x, translate_y)
    builder.scale(scale_factor, scale_factor)
    path_from_rounded_polygon(builder, shape)

    rgba = render(
        width=width,
        height=height,
        bg_rgba=(1.0, 1.0, 1.0, 1.0),
        path_builder=builder,
        fill_rgba=(fill_r, fill_g, fill_b, 1.0),
        image_png_bytes=None,
        image_x=0,
        image_y=0,
        image_w=0,
        image_h=0,
    )

    im = Image.frombytes("RGBA", (width, height), rgba)
    output_path = f"shapes_png/{name}.png"
    im.save(output_path)
    print(f"Saved: {output_path}")
