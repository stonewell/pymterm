#coding=utf-8
import logging
import os
import select
import socket
import sys
import time
import traceback
import string

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb, TabView
from GUI import application
from GUI.Files import FileType
from GUI.Geometry import pt_in_rect, offset_rect, rects_intersect
from GUI.StdColors import black, red, blue
from GUI.StdFonts import application_font
from GUI.Colors import rgb
from GUI.Files import FileType, DirRef, FileRef
from GUI import FileDialogs
from GUI.GL import GLView, GLConfig
from OpenGL.GL import glClearColor, glClear, glBegin, glColor3f, glVertex2i, glEnd, \
    GL_COLOR_BUFFER_BIT, GL_TRIANGLES
import GUI.Font
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

from term_pygui_view_base import TerminalPyGUIViewBase

import pygame
from pygame.locals import *

try:
    pygame.font.init()
except:
    logging.getLogger('term_pygui').exception('draw failed')

from functools32 import lru_cache

class Texture(object):
    def __init__(self, data, w=0, h=0):
        """
        Initialize the texture from 3 diferents types of data:
        filename = open the image, get its string and produce texture
        surface = get its string and produce texture
        string surface = gets it texture and use w and h provided
        """
        if type(data) == pygame.Surface:
            texture_data = pygame.image.tostring(data, "RGBA", True)
            self.w, self.h = data.get_size()

        elif type(data) == bytes:
            self.w, self.h = w, h
            texture_data = data

        self.texID = 0
        self.load_texture(texture_data)

    def load_texture(self, texture_data):
        self.texID = glGenTextures(1)

        glPixelStorei(GL_UNPACK_ALIGNMENT,1)
        glBindTexture(GL_TEXTURE_2D, self.texID)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.w,
                     self.h, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                     texture_data)

    def render(self):
        glMatrixMode(GL_PROJECTION)

        glLoadIdentity()
        glRotatef(180, 1, 0, 0)
        glTranslate(-1, -1, 0)
        glScale(2.0/self.w, 2.0/self.h, 1)
        glDisable(GL_DEPTH_TEST)
        glDisable(GL_CULL_FACE)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        self.Draw(0, 0, self.h, self.w)

    def Draw(self, top, left, bottom, right):
        """
        Draw the image on the Opengl Screen
        """
        # Make sure he is looking at the position (0,0,0)
        glBindTexture(GL_TEXTURE_2D, self.texID)
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

        #pygame.display.flip()

#put View on right to make Base class method override happer
#because python resolve method from left to right
class TerminalPyGUIGLView(TerminalPyGUIViewBase, GLView):

    def __init__(self, **kwargs):
        pf = GLConfig(double_buffer = True)
        TerminalPyGUIViewBase.__init__(self, **kwargs)
        GLView.__init__(self, pf, **kwargs)

    def init_context(self):
        glClearColor(0.0, 0.0, 0.0, 0.0)

    def render(self):
        try:
            self._draw()
        except:
            logging.getLogger('term_pygui').exception('draw failed')

    def _draw(self):
        color = map(lambda x: x / 255, map(float, self.session.cfg.default_background_color))

        width , height = self.size

        background = pygame.Surface((width, height))
        background.fill(color)

        # Display some text
        self._draw2(background)

        texture = Texture(background, width, height)

        texture.render()

    def _draw2(self, v_surf):
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

        width, height = self.size

        for i in range(len(lines)):
            x = b_x = self.padding_x
            line = lines[i]
            line_option = line_options[i] if i < len(line_options) else []

            last_mode &= ~TextMode.CURSOR
            last_mode &= ~TextMode.SELECTION

            # temprary add cusor and selection mode
            if self.cursor_visible and i == c_row and c_col < len(line):
                reserve(line_option, c_col + 1, TextAttribute(None, None, None))
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

            line_surf = None

            @lru_cache(1000)
            def __get_surf(line, line_option):
                return line_surf

            line_surf = __get_surf(line, line_option)

            if line_surf is not None:
                print 'surf hit'
                v_surf.blit(line_surf, (0, y))

                y += line_height
                continue
            
            line_surf = pygame.Surface((width, line_height))
            color = map(lambda x: x / 255, map(float, self.session.cfg.default_background_color))
            line_surf.fill(color)

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

                text = font.render(t, 1, cur_f_color)
                text_pos = text.get_rect()
                text_pos.centery = line_surf.get_rect().centery
                text_pos.left = xxxx

                if cur_b_color != self.session.cfg.default_background_color:
                    line_surf.fill(cur_b_color, text_pos)

                line_surf.blit(text, text_pos)

                return text_pos.right

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
                    b_x = render_text(''.join(line[last_col: col]), b_x)

                last_col = col
                last_option = line_option[col]
                last_f_color, last_b_color, last_mode = n_f_color, n_b_color, n_mode

            if last_col < len(line):
                b_x = render_text(''.join(line[last_col:]), b_x)

            if self.cursor_visible and i == c_row and c_col >= len(line):
                last_mode |= TextMode.CURSOR
                b_x = render_text(' ', b_x)

            v_surf.blit(line_surf, (0, y))

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

    @lru_cache(1)
    def _get_font(self):
        font_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'fonts',
                                     #'wqy-microhei-mono.ttf'
                                     #'NotoSansMonoCJKsc-Regular.otf'
                                     'YaHei Consolas Hybrid 1.12.ttf'
                                     )
        font = pygame.font.Font(font_path,
                                    int(self.font_size))
        return font

    def get_prefered_size(self):
        f = self._get_font()
        w = self._get_width(f, 'ABCDabcd')
        w = int(w / 8 * self.visible_cols + self.padding_x * 2 + 0.5)
        h = int(self._get_line_height() * self.visible_rows + self.padding_y * 2 + 0.5)

        return (w, h)

    def _get_width(self, f = None, t = ''):
        w, h = self._get_size(f, t)
        return w

    @lru_cache(200)
    def _get_size(self, f = None, t = ''):
        if f is None:
            f = self._get_font()

        text = f.render(t, 1, (0,0,0,0))
        text_pos = text.get_rect()

        return (text_pos.width, text_pos.height)

    def _get_line_height(self):
        f = self._get_font()

        return f.get_linesize()
