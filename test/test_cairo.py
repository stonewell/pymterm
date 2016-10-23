#coding=utf-8
import cairo
import pango
import pangocairo
import sys
import numpy
surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, 320, 120)
context = cairo.Context(surf)

#draw a background rectangle:
context.rectangle(0,0,320,120)
context.set_source_rgb(1, 1, 1)
context.fill()
#get font families:

font_map = pangocairo.cairo_font_map_get_default()
families = font_map.list_families()

# to see family names:
print sorted([f.get_name() for f in   font_map.list_families()])

font_name = ['Noto Sans Mono CJK SC',
                 'WenQuanYi Micro Hei Mono'][1]
font = pango.FontDescription(' '.join([font_name, str(26)]))

context.translate(50,25)

p_c = pangocairo_context = pangocairo.CairoContext(context)
pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
l = p_c.create_layout()
l.set_font_description(font)
l.set_text(u'abcd')
print l.get_pixel_extents(), l.get_pixel_size(), l.get_size(), font.get_size() / pango.SCALE

context.set_source_rgb(0, 0, 0)
context.rectangle(0, 0, 153, 41)
context.stroke()
pangocairo_context.update_layout(l)
pangocairo_context.show_layout(l)

print dir(surf.get_data().tolist())
with open("cairo_text.png", "wb") as image_file:
    surf.write_to_png(image_file)
