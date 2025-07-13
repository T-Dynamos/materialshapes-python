import cairo
import os
from materialshapes import MaterialShapes
from materialshapes.utils import path_from_rounded_polygon

os.makedirs("shapes_png", exist_ok=True)

spacing = 50
size = 400
width, height = [size]*2
translate_x, translate_y = [spacing/2]*2
scale_factor = width - spacing

material_shapes = MaterialShapes()

fill_r, fill_g, fill_b = (0x40 / 255, 0x2F / 255, 0x67 / 255)

for name, shape in material_shapes.all.items():
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    ctx.set_source_rgb(1, 1, 1)
    ctx.rectangle(0, 0, width, height)
    ctx.fill()

    ctx.translate(translate_x, translate_y)
    ctx.scale(scale_factor, scale_factor)

    path_from_rounded_polygon(ctx, shape)

    ctx.set_source_rgb(fill_r, fill_g, fill_b)
    ctx.fill()

    output_path = f"shapes_png/{name}.png"
    surface.write_to_png(output_path)
    print(f"Saved: {output_path}")
