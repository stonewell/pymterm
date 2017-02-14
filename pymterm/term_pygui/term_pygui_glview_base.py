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

create_line_surface = None

@lru_cache(maxsize=1000)
def _get_surf(k, width, line_height):
    cached_line_surf = __cached_line_surf()
    cached_line_surf.cached = False
    cached_line_surf.surf = create_line_surface(width, line_height)

    return cached_line_surf

class TextureBase(GTexture):
    def __init__(self):
        super(TextureBase, self).__init__(GL_TEXTURE_2D)

    def _decode_texture_data(self, data):
        pass

    def load_texture(self, data):
        self.w, self.h, texture_data, gl_color_format = self._decode_texture_data(data)
        
        self.bind()

        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.w,
                     self.h, 0, gl_color_format, GL_UNSIGNED_BYTE,
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

class TerminalPyGUIGLViewBase(TerminalPyGUIViewBase, GLView):

    def __init__(self, **kwargs):
        pf = GLConfig(double_buffer = True)
        self._refresh_font(kwargs['model'].cfg)
        
        TerminalPyGUIViewBase.__init__(self, **kwargs)
        GLView.__init__(self, pf, size=self.get_prefered_size(), **kwargs)

    def init_context(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def render(self):
        try:
            self._draw()
        except:
            logging.getLogger('term_pygui').exception('glview draw failed')

    def _draw(self):
        width , height = self.size

        canvas = self._create_canvas_texture(width, height)

        texture = self._get_texture()
        texture.load_texture(canvas)
        texture.render()
        texture.deallocate()
            
    def setup_menus(self, m):
        GLView.setup_menus(self, m)
        super(TerminalPyGUIGLViewBase, self).setup_menus(m)

    def viewport_changed(self):
        width, height = self.size

        if width <= 0 or height <= 0:
            return

        GLView.viewport_changed(self)

        self.resized((1, 1))

    def _create_canvas_texture(self, width, height):
        pass

    def _paint_line_surface(self, v_context, line_surf, x, y):
        pass

    def _prepare_line_surface(self, line_surf):
        pass

    def _layout_line_text(self, line_context, t, font, col_width):
        pass

    def _fill_line_background(self, line_context, cur_b_color, l, t, w, h):
        pass

    def _draw_layouted_line_text(self, line_context, layout, cur_f_color, l, t, w, h):
        pass
    
    def _draw_canvas(self, v_context):
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
                self._paint_line_surface(v_context, line_surf, 0, y)

                y += line_height
                continue

            cached_line_surf.cached = True
            line_context = self._prepare_line_context(line_surf, width, line_height)

            def render_text(t, xxxx, wide_char):
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

                t_w, t_h, layout = self._layout_line_text(line_context, t, font, xxxx, 0, col_width, line_height, cur_f_color)

                if cur_b_color != self.session.cfg.default_background_color:
                    self._fill_line_background(line_context, cur_b_color, xxxx, 0,
                                                   max(t_w, col_width * 2 if wide_char else col_width),
                                                   t_h)

                self._draw_layouted_line_text(line_context, layout, cur_f_color, xxxx, 0, t_w, t_h)

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
                    for r_col in range(last_col, col):
                        wide_char = False
                        if r_col + 1 < len(line):
                            wide_char = line[r_col + 1] == '\000'
                        render_text(line[r_col], b_x, wide_char)
                        b_x += col_width

                last_col = col
                last_option = line_option[col]
                last_f_color, last_b_color, last_mode = n_f_color, n_b_color, n_mode

            if last_col < len(line):
                for r_col in range(last_col, len(line)):
                    wide_char = False
                    if r_col + 1 < len(line):
                        wide_char = line[r_col + 1] == '\000'
                        
                    render_text(line[r_col], b_x, wide_char)
                    b_x += col_width

            self._paint_line_surface(v_context, line_surf, 0, y)

            y += line_height
