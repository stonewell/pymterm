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
from GUI.Alerts import stop_alert, ask

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

from term_pygui_glview_base import TerminalPyGUIGLViewBase, TextureBase
import term_pygui_view_base

import pygame
from pygame.locals import *

use_freetype = True

try:
    import pygame.freetype
    pygame.freetype.init()
except:
    use_freetype = False
    pygame.font.init()
    logging.getLogger('term_pygui').exception('pygame font initialize failed')

from functools32 import lru_cache

term_pygui_view_base.create_line_surface = lambda w,h: pygame.Surface((w, h))

class Texture(TextureBase):
    def __init__(self):
        super(Texture, self).__init__()

    def _decode_texture_data(self, data):
        w, h = data.get_size()
        texture_data = pygame.image.tostring(data, "RGBA", True)

        return w, h, texture_data, GL_RGBA

    def _pre_render(self):
        glRotatef(180, 1, 0, 0)
        glTranslate(-1, -1, 0)
        glScale(2.0/self.w, 2.0/self.h, 1)

class TerminalPyGUIGLView(TerminalPyGUIGLViewBase):

    def __init__(self, **kwargs):
        TerminalPyGUIGLViewBase.__init__(self, **kwargs)

    def _get_texture(self):
        return Texture()

    def _create_canvas_texture(self, width, height):
        background = pygame.Surface((width, height))
        background.fill(self.session.cfg.default_background_color)

        # Display everything on background
        self._draw_canvas(background)

        return background

    def _paint_line_surface(self, v_context, line_surf, x, y):
        v_context.blit(line_surf, (x, y))

    def _prepare_line_context(self, line_surf, x, y, w, h):
        line_surf.fill(self.session.cfg.default_background_color)
        return line_surf

    def _layout_line_text(self, line_context, text_data, font, l, t, width, height, cur_f_color):
        right_adjust = 0
        if use_freetype:
            text, text_pos = font.render(text_data, cur_f_color)
            for turple in font.get_metrics(text_data):
                if turple:
                    right_adjust += turple[4]
            text_pos.top = font.get_sized_ascender() - text_pos.top
        else:
            text = font.render(text_data, 1, cur_f_color)
            text_pos = text.get_rect()
            right_adjust = text_pos.width
            text_pos.centery = line_surf.get_rect().centery

        text_pos.left += l
        right_adjust = right_adjust if right_adjust >= width else width

        return right_adjust, self._get_line_height(), (text, text_pos)

    def _fill_line_background(self, line_context, cur_b_color, l, t, w, h):
        line_context.fill(cur_b_color, (l, t, w, h))

    def _draw_layouted_line_text(self, context, layout, cur_f_color, l, t, w, h):
        text, text_pos = layout

        context.blit(text, text_pos)

    @lru_cache(1)
    def _get_font(self):
        font_path = self.font_file

        if not font_path:
            stop_alert("render pygame unable to find a valid font file, please use --font_file or pymterm.json to set font file")
            sys.exit(1)

        if use_freetype:
            font = pygame.freetype.Font(font_path,
                                                self.font_size)
        else:
            font = pygame.font.Font(font_path,
                                            int(self.font_size))
        return font

    @lru_cache(200)
    def _get_size(self, f = None, t = ''):
        if f is None:
            f = self._get_font()

        if use_freetype:
            width = 0
            for turple in f.get_metrics(t):
                width += turple[4]

            return (width, f.get_sized_height())
        else:
            text = f.render(t, 1, (0,0,0,0))
            text_pos = text.get_rect()

        return (text_pos.width, f.get_linesize())
