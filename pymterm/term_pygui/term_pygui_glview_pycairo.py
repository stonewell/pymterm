#coding=utf-8
import logging
import os
import select
import socket
import sys
import time
import traceback
import string
import threading
import array

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb, TabView
from GUI import application
from GUI.Files import FileType
from GUI.Geometry import pt_in_rect, offset_rect, rects_intersect
from GUI.Colors import rgb
from GUI.Files import FileType, DirRef, FileRef
from GUI import FileDialogs
from GUI.GL import GLView, GLConfig
from GUI.GLTextures import Texture as GTexture
from GUI.Alerts import stop_alert

from OpenGL.GL import glClearColor, glClear, glBegin, glColor3f, glVertex2i, glEnd, \
    GL_COLOR_BUFFER_BIT, GL_TRIANGLES
from OpenGL.GL import *
from OpenGL.GLU import *

try:
    import cairo
except:
    logging.exception('cairo not found')
    import gtk.cairo as cairo
import pango
import pangocairo
import numpy

import cap.cap_manager
from session import create_session
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import term.term_keyboard
import term_pygui_key_translate
from term import TextAttribute, TextMode, set_attr_mode, reserve
from term_menu import basic_menus

from term_pygui_glview_base import TerminalPyGUIGLViewBase, _get_surf, TextureBase
from term_pygui_view_base import SINGLE_WIDE_CHARACTERS
import term_pygui_glview_base

from functools32 import lru_cache

term_pygui_glview_base.create_line_surface = lambda w,h: cairo.ImageSurface(cairo.FORMAT_ARGB32, int(w), int(h))

class Texture(TextureBase):
    def __init__(self):
        super(Texture, self).__init__()

    def _decode_texture_data(self, data):
        return data.get_width(), data.get_height(), str(data.get_data()), GL_BGRA

    def _pre_render(self):
        glTranslate(-1, -1, 0)
        glScale(2.0/self.w, 2.0/self.h, 1)

class TerminalPyGUIGLView(TerminalPyGUIGLViewBase):

    def __init__(self, **kwargs):
        TerminalPyGUIGLViewBase.__init__(self, **kwargs)

    def _get_texture(self):
        return Texture()

    def _create_canvas_texture(self, width, height):
        background_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
        background_context = cairo.Context(background_surf)

        background_context.rectangle(0,0,width,height)
        r,g,b,a = self._get_color(self.session.cfg.default_background_color)
        background_context.set_source_rgba(r, g, b, a)
        background_context.fill()

        # draw on background
        self._draw_canvas(background_context)

        return background_surf

    def _prepare_line_context(self, line_surf, width, height):
        line_context = cairo.Context(line_surf)

        f_o = cairo.FontOptions()
        f_o.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        f_o.set_hint_style(cairo.HINT_STYLE_SLIGHT)
        f_o.set_hint_metrics(cairo.HINT_METRICS_ON)
        line_context.set_font_options(f_o)

        r,g,b,a = self._get_color(self.session.cfg.default_background_color)
        line_context.set_source_rgba(r, g, b, a)
        line_context.rectangle(0, 0, width, height)
        line_context.fill()
        line_p_context = pangocairo.CairoContext(line_context)
        if sys.platform.startswith('win'):
            line_p_context.set_antialias(cairo.ANTIALIAS_DEFAULT)
        else:
            line_p_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

        return (line_context, line_p_context)

    def _paint_line_surface(self, v_context, line_surf, x, y):
        v_context.set_source_surface(line_surf, x, y)
        v_context.paint()

    def _layout_line_text(self, context, text, font, l, t, col_width, h, cur_f_color):
        line_context, line_p_context = context

        l = line_p_context.create_layout()
        l.set_font_description(font)
        l.set_text(text)
        line_p_context.update_layout(l)

        t_w, t_h = l.get_pixel_size()
        t_w = t_w if t_w >= col_width else col_width

        return t_w, self._get_line_height(), l

    def _fill_line_background(self, context, cur_b_color, l, t, w, h):
        line_context, line_p_context = context
        r, g, b, a = self._get_color(cur_b_color)

        line_context.set_source_rgba(r, g, b, a)
        line_context.rectangle(l, t, w, h)
        line_context.fill()

    def _draw_layouted_line_text(self, context, layout, cur_f_color, l, t, w, h):
        line_context, line_p_context = context
        ink, logic = layout.get_line(0).get_pixel_extents()
        ascent, descent = self._get_layout_metrics()

        r, g, b, a = self._get_color(cur_f_color)
        line_context.set_source_rgba(r, g, b, a)
        line_context.move_to(l + pango.LBEARING(logic), h - descent -pango.ASCENT(logic))
        line_p_context.update_layout(layout)
        line_p_context.show_layout(layout)

    def _find_font_desc(self, font_name):
        font_map = pangocairo.cairo_font_map_get_default()
        families = font_map.list_families()

        for family in families:
            for face in family.list_faces():
                _font_name = '{} {}'.format(family.get_name() , face.get_face_name())
                if font_name == _font_name or font_name == family.get_name():
                    return face.describe()

        return None

    @lru_cache(1)
    def _get_font(self):
        font_name = self.font_name

        if not font_name:
            stop_alert("render cairoe unable to find a valid font name, please use --font_name or pymterm.json to set font name")
            sys.exit(1)

        font = self._find_font_desc(font_name)

        if not font:
            font = pango.FontDescription(' '.join([font_name, str(self.font_size)]))
        else:
            font.set_size(int(self.font_size) * pango.SCALE)

        return font

    @lru_cache(200)
    def _get_size(self, f = None, t = ''):
        if f is None:
            f = self._get_font()

        l = self._get_size_layout()
        l.set_font_description(f)
        l.set_text(t)

        return l.get_pixel_size()

    @lru_cache(1)
    def _get_layout_metrics(self):
        f = self._get_font()

        l = self._get_size_layout()
        l.set_font_description(f)
        l.set_text(SINGLE_WIDE_CHARACTERS)
        ink, logic = l.get_line(0).get_pixel_extents()

        return (pango.ASCENT(logic), pango.DESCENT(logic))

    @lru_cache(1)
    def _get_size_layout(self):
        c = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 0, 0))
        p_c = pangocairo.CairoContext(c)
        l = p_c.create_layout()

        return l

    def _get_color(self, rgba):
        r, g, b, a = map(lambda x: float(x) / 255, rgba)

        return (r, g, b, a)
