#coding=utf-8
try:
    import cairo
except:
    import gtk.cairo as cairo
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
print families[0]

# to see family names:
print sorted([f.get_name() for f in   font_map.list_families()])

font_name = ['Noto Sans Mono CJK SC',
                 'WenQuanYi Micro Hei Mono',
                 'YaHei Consolas Hybrid',
                 'Menlo Regular'][1]
pc = pango.Context()
pc.set_language(pango.Language("zh_CN.UTF-8"))

font = pango.FontDescription(' '.join([font_name, str(26)]))

context.translate(50,25)

p_c = pangocairo_context = pangocairo.CairoContext(context)
pangocairo_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

l = p_c.create_layout()
l.set_font_description(font)
attrList, t, c = pango.parse_markup(u"哈哈")
l.set_text(t)
l.set_attributes(attrList)

print l.get_pixel_extents(), l.get_pixel_size(), l.get_size(), font.get_size() / pango.SCALE, l.get_line(0).get_pixel_extents()

context.set_source_rgb(0, 0, 0)
context.rectangle(0, 0, 153, 41)
context.stroke()
pangocairo_context.update_layout(l)
pangocairo_context.show_layout(l)
l.set_text('abcd')
pangocairo_context.update_layout(l)
pangocairo_context.show_layout(l)


print pc.get_language(), dir(pc)
with open("cairo_text.png", "wb") as image_file:
    surf.write_to_png(image_file)
