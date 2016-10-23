import gtk
import cairo, pango, pangocairo

class DemoPb(gtk.DrawingArea):
    
    def __init__(self):
        super(DemoPb, self).__init__()
        self.connect("expose_event", self.expose)

    def expose(self, widget, event):
        context = widget.window.cairo_create()
        context.rectangle(event.area.x, event.area.y,
                               event.area.width, event.area.height)
        context.clip()
        self.draw(context)
        return False
    
    def draw(self, context):
        context.set_source_rgb(0,0,0)
        context.paint()        
        # The more you scale, the bigger the problem
        #context.scale(self.allocation.height/2, self.allocation.height/2)
        context.scale(self.allocation.height/10, self.allocation.height/10)
        
        cr = pangocairo.CairoContext(context)
        layout = cr.create_layout()
        layout.set_text( " text with Fr in the middle ")
        #layout.set_font_description(pango.FontDescription("Times 0.3"))
        # no problem when using a font without kerning
        layout.set_font_description(pango.FontDescription("WenQuanYi Micro Hei Mono .3"))
        layout.set_width(-1)
        layout.set_alignment(pango.ALIGN_LEFT)
        cr.set_source_rgb(1, 1, 1)
        cr.update_layout(layout)
        cr.show_layout(layout)            
    
def main():
    window = gtk.Window()
    window.set_size_request(800,600)
    display = DemoPb()
    window.add(display)
    window.connect("destroy", gtk.main_quit)
    window.show_all()    
    gtk.main()
    
if __name__ == "__main__":    
    main()    
