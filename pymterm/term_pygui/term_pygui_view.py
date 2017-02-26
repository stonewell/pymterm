#coding=utf-8
import logging
import sys

from GUI import View
from GUI import FileDialogs
from GUI import application
from GUI.Alerts import stop_alert, ask
from GUI.Colors import rgb
from GUI.Files import FileType
from GUI.Files import FileType, DirRef, FileRef
import GUI.Font
from GUI.Geometry import pt_in_rect, offset_rect, rects_intersect
from GUI.StdColors import black, red, blue
from GUI.StdFonts import application_font
from functools32 import lru_cache

import cap.cap_manager
from session import create_session
from term import TextAttribute, TextMode, set_attr_mode, reserve
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
from term_menu import basic_menus
import term_pygui_key_translate
from term_pygui_view_base import TerminalPyGUIViewBase
import term_pygui_view_base


#put View on right to make Base class method override happer
#because python resolve method from left to right
class TerminalPyGUIView(TerminalPyGUIViewBase, View):

    def __init__(self, **kwargs):
        self._refresh_font(kwargs['model'].cfg)

        TerminalPyGUIViewBase.__init__(self, **kwargs)
        View.__init__(self, **kwargs)

    def draw(self, canvas, update_rect):
        try:
            self._draw(canvas, update_rect)
        except:
            logging.getLogger('term_pygui').exception('draw failed')

    def _draw(self, canvas, update_rect):
        self._setup_canvas(canvas)

        canvas.fillcolor = self._get_color(self.session.cfg.default_background_color)
        width, height = self.size
        canvas.fill_frame_rect((0, 0, width, height))

        term_pygui_view_base.create_line_surface = lambda w,h: canvas

        self._draw_canvas(canvas)

    def _paint_line_surface(self, v_context, line_surf, x, y):
        pass

    def _prepare_line_context(self, line_surf, x, y, width, height):
        return (line_surf, x, y, width, height)

    def _layout_line_text(self, context, text, font, left, top, layout_width, layout_height, cur_f_color):
        canvas, x, y, width, height = context

        return (self._get_width(canvas.font, text), layout_height, text)

    def _fill_line_background(self, line_context, cur_b_color, l, t, w, h):
        canvas, x, y, width, height = line_context
        tmp_c, canvas.fillcolor = canvas.fillcolor, self._get_color(cur_b_color)
        tmp_p_c, canvas.pencolor = canvas.pencolor, self._get_color(cur_b_color)

        canvas.fill_frame_rect((x + l, y + t,
                                    x + l + w,
                                    y + t + h))
        canvas.fillcolor,canvas.pencolor = tmp_c, tmp_p_c

    def _draw_layouted_line_text(self, line_context, layout, cur_f_color, l, t, w, h):
        canvas, x, y, width, height = line_context

        tmp_c, canvas.textcolor = canvas.textcolor, self._get_color(cur_f_color)
        tmp_p_c, canvas.pencolor = canvas.pencolor, self._get_color(cur_f_color)
        canvas.moveto(x + l, y + t + canvas.font.ascent)
        canvas.show_text(layout)

        canvas.textcolor, canvas.pencolor = tmp_c, tmp_p_c

    def _do_cache(self):
        return False

    def setup_menus(self, m):
        View.setup_menus(self, m)
        super(TerminalPyGUIView, self).setup_menus(m)

    def resized(self, delta):
        View.resized(self, delta)
        TerminalPyGUIViewBase.resized(self, delta)

    def _setup_canvas(self, canvas):
        canvas.set_font(self._get_font())

    @lru_cache(1)
    def _get_font(self):
        font_name = self.font_name

        if not font_name:
            stop_alert("render native unable to find a valid font name, please use --font_name or pymterm.json to set font name")
            sys.exit(1)

        return GUI.Font(family=font_name,
                        size=self.font_size)

    @lru_cache(200)
    def _get_size(self, f = None, t = ''):
        if f is None:
            f = self._get_font()

        w = f.width(t)
        return w, f.line_height
