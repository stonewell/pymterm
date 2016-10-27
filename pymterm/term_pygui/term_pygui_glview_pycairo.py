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

from term_pygui_view_base import TerminalPyGUIViewBase, SINGLE_WIDE_CHARACTERS

from functools32 import lru_cache

class __cached_line_surf(object):
    pass

@lru_cache(maxsize=1000)
def _get_surf(k, width, line_height):
    cached_line_surf = __cached_line_surf()
    cached_line_surf.cached = False
    cached_line_surf.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(line_height))

    return cached_line_surf

class Texture(GTexture):
    def __init__(self):
        super(Texture, self).__init__(GL_TEXTURE_2D)

    def load_texture(self, data):
        self.w, self.h = data.get_width(), data.get_height()
        if sys.platform.startswith('win'):
            texture_data = str(data.get_data())
        else:
            texture_data = numpy.ndarray(shape=(self.w, self.h, 4),
                                             dtype=numpy.uint8,
                                             buffer=data.get_data())

        self.bind()

        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.w,
                     self.h, 0, GL_BGRA, GL_UNSIGNED_BYTE,
                     texture_data)
        
    def do_setup(self):
        glMatrixMode(GL_PROJECTION)

        glLoadIdentity()
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def _pre_render(self):
        #glRotatef(180, 1, 0, 0)
        glTranslate(-1, -1, 0)
        glScale(2.0/self.w, 2.0/self.h, 1)
        pass

    def render(self):
        self._pre_render()
        self.bind()
        self.draw(0, 0, self.h, self.w)

    def draw(self, top, left, bottom, right):
        glBegin(GL_QUADS)

        # The top left of the image must be the indicated position
        glTexCoord2f(0.0, 1.0)
        glVertex2f(left, top)

        glTexCoord2f(1.0, 1.0)
        glVertex2f(right, top)

        glTexCoord2f(1.0, 0.0)
        glVertex2f(right, bottom)

        glTexCoord2f(0.0, 0.0)
        glVertex2f(left, bottom)

        glEnd()

#put View on right to make Base class method override happer
#because python resolve method from left to right
class TerminalPyGUIGLView(TerminalPyGUIViewBase, GLView):

    def __init__(self, **kwargs):
        pf = GLConfig(double_buffer = True)
        TerminalPyGUIViewBase.__init__(self, **kwargs)
        GLView.__init__(self, pf, size=self.get_prefered_size(), **kwargs)

    def init_context(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def _get_texture(self):
        return Texture()

    def render(self):
        try:
            self._draw()
        except:
            logging.getLogger('term_pygui').exception('draw failed')

    def _draw(self):
        width , height = self.size

        background_surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, int(width), int(height))
        background_context = cairo.Context(background_surf)

        background_context.rectangle(0,0,width,height)
        r,g,b,a = self._get_color(self.session.cfg.default_background_color)
        background_context.set_source_rgba(r, g, b, a)
        background_context.fill()

        # Display some text
        self._draw2(background_context)

        texture = self._get_texture()
        texture.load_texture(background_surf)
        texture.render()
        texture.deallocate()

    def _draw2(self, v_context):
        x = self.padding_x
        b_x = self.padding_x
        y = self.padding_y

        lines = [line[:] for line in self.lines]
        line_options = [line_option[:] for line_option in self.line_options]

        c_col, c_row = self.term_cursor

        s_f, s_t = self.get_selection()

        s_f_c, s_f_r = s_f
        s_t_c, s_t_r = s_t


        last_f_color = self.session.cfg.default_foreground_color
        last_b_color = self.session.cfg.default_background_color
        last_mode = 0

        font = self._get_font();

        line_height = self._get_line_height()
        col_width = int(self._get_col_width())
        ascent, descent = self._get_layout_metrics()

        width, height = self.size

        for i in range(len(lines)):
            x = b_x = self.padding_x
            line = lines[i]
            line_option = line_options[i] if i < len(line_options) else []

            last_mode &= ~TextMode.CURSOR
            last_mode &= ~TextMode.SELECTION

            # temprary add cusor and selection mode
            if self.cursor_visible and i == c_row:
                reserve(line_option, c_col + 1, TextAttribute(None, None, None))
                reserve(line, c_col + 1, ' ')
                line_option[c_col] = set_attr_mode(line_option[c_col], TextMode.CURSOR)

            if s_f != s_t:
                if s_f_r == s_t_r and i == s_f_r:
                    reserve(line_option, s_t_c, TextAttribute(None, None, None))
                    for mm in range(s_f_c, s_t_c):
                        line_option[mm] = set_attr_mode(line_option[mm], TextMode.SELECTION)
                else:
                    if i == s_f_r:
                        reserve(line_option, len(line), TextAttribute(None, None, None))
                        for mm in range(s_f_c, len(line)):
                            line_option[mm] = set_attr_mode(line_option[mm], TextMode.SELECTION)
                    elif i == s_t_r:
                        reserve(line_option, s_t_c, TextAttribute(None, None, None))
                        for mm in range(0, s_t_c):
                            line_option[mm] = set_attr_mode(line_option[mm], TextMode.SELECTION)
                    elif i > s_f_r and i < s_t_r:
                        reserve(line_option, len(line), TextAttribute(None, None, None))
                        for mm in range(len(line)):
                            line_option[mm] = set_attr_mode(line_option[mm], TextMode.SELECTION)

            col = 0
            last_col = 0
            text = ''
            last_option = None

            key = self._get_cache_key(line, line_option)
            cached_line_surf = _get_surf(key, width, line_height)
            line_surf = cached_line_surf.surf

            if cached_line_surf.cached:
                v_context.set_source_surface(line_surf, 0, y)
                v_context.paint()
                
                y += line_height
                continue

            cached_line_surf.cached = True
            line_context = cairo.Context(line_surf)
            r,g,b,a = self._get_color(self.session.cfg.default_background_color)
            line_context.set_source_rgba(r, g, b, a)
            line_context.rectangle(0, 0, width, line_height)
            line_context.fill()
            line_p_context = pangocairo.CairoContext(line_context)
            line_p_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)

            def render_text(t, xxxx):
                cur_f_color, cur_b_color = last_f_color, last_b_color

                if len(t) == 0:
                    return xxxx

                t = self.norm_text(t)

                if len(t) == 0:
                    return xxxx

                if last_mode & TextMode.REVERSE:
                    cur_f_color, cur_b_color = last_b_color, last_f_color

                if last_mode & TextMode.CURSOR:
                    cur_f_color, cur_b_color = cur_b_color, self.session.cfg.default_cursor_color

                if last_mode & TextMode.SELECTION:
                    cur_f_color = self._merge_color(cur_f_color, self.selection_color)
                    cur_b_color = self._merge_color(cur_b_color, self.selection_color)

                l = line_p_context.create_layout()
                l.set_font_description(font)
                l.set_text(t)
                line_p_context.update_layout(l)

                ink, logic = l.get_line(0).get_pixel_extents()
                t_w, t_h = l.get_pixel_size()
                t_w = t_w if t_w >= col_width else col_width

                if cur_b_color != self.session.cfg.default_background_color:
                    r, g, b, a = self._get_color(cur_b_color)
                    line_context.set_source_rgba(r, g, b, a)
                    line_context.rectangle(xxxx, 0, t_w, line_height)
                    line_context.fill()
        
                r, g, b, a = self._get_color(cur_f_color)
                line_context.set_source_rgba(r, g, b, a)
                line_context.move_to(xxxx, line_height - descent -pango.ASCENT(logic))
                line_p_context.update_layout(l)
                line_p_context.show_layout(l)

                return xxxx + t_w

            for col in range(len(line_option)):
                if line_option[col] is None:
                    continue

                if last_option == line_option[col]:
                    continue

                f_color, b_color, mode = line_option[col]

                n_f_color, n_b_color, n_mode = last_f_color, last_b_color, last_mode

                # foreground
                if f_color and len(f_color) > 0:
                    n_f_color = f_color
                elif f_color is None:
                    n_f_color = self.session.cfg.default_foreground_color

                # background
                if b_color and len(b_color) > 0:
                    n_b_color = b_color
                elif b_color is None:
                    n_b_color = self.session.cfg.default_background_color

                #mode
                if mode is not None:
                    n_mode = mode
                else:
                    n_mode &= ~TextMode.CURSOR
                    n_mode &= ~TextMode.SELECTION

                if (n_f_color, n_b_color, n_mode) == (last_f_color, last_b_color, last_mode):
                    continue

                if last_col < col:
                    #b_x = render_text(''.join(line[last_col: col]), b_x)
                    for r_col in range(last_col, col):
                        render_text(line[r_col], b_x)
                        b_x += col_width

                last_col = col
                last_option = line_option[col]
                last_f_color, last_b_color, last_mode = n_f_color, n_b_color, n_mode

            if last_col < len(line):
                #b_x = render_text(''.join(line[last_col:]), b_x)
                for r_col in range(last_col, len(line)):
                    render_text(line[r_col], b_x)
                    b_x += col_width

            v_context.set_source_surface(line_surf, 0, y)
            v_context.paint()

            y += line_height

    def setup_menus(self, m):
        GLView.setup_menus(self, m)
        super(TerminalPyGUIGLView, self).setup_menus(m)

    def viewport_changed(self):
        width, height = self.size

        if width <= 0 or height <= 0:
            return

        GLView.viewport_changed(self)

        self.resized((1, 1))

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
        font_name = ['Noto Sans Mono CJK SC Regular'
                         ,'WenQuanYi Micro Hei Mono'
                         ,'Menlo Regular'
                         ,'WenQuanYi Micro Hei'
                         ,'Sans'
                         , 'Lucida Console'
                         ][1]
        font = self._find_font_desc(font_name)

        if not font:
            font = pango.FontDescription(' '.join([font_name, str(self.font_size)]))
        else:
            font.set_size(int(self.font_size) * pango.SCALE)
        return font

    def get_prefered_size(self):
        f = self._get_font()
        w = self._get_col_width()
        w = int(w * self.visible_cols + self.padding_x * 2 + 0.5)
        h = int(self._get_line_height() * self.visible_rows + self.padding_y * 2 + 0.5)

        return (w, h)

    def _get_width(self, f = None, t = ''):
        w, h = self._get_size(f, t)
        return w

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

    @lru_cache(1)
    def _get_line_height(self):
        f = self._get_font()

        w, h = self._get_size(f, 'ABCDabcd')

        return h + 1

    def _get_cache_key(self, line, line_option):
        line_key = self._get_line_cache_key(line)
        line_option_key = self._get_line_option_cache_key(line_option)

        return '{}_{}'.format(line_key, line_option_key)

    def _get_line_cache_key(self, line):
        return repr(line)

    def _get_line_option_cache_key(self, line_option):
        return repr(line_option)

    def _get_color(self, rgba):
        r, g, b, a = map(lambda x: float(x) / 255, rgba)

        return (r, g, b, a)
