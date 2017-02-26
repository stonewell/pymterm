#coding=utf-8
import array
import logging
import os
import select
import socket
import string
import sys
import threading
import time
import traceback

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb, TabView
from GUI import FileDialogs
from GUI import application
from GUI.Alerts import stop_alert
from GUI.Colors import rgb
from GUI.Files import FileType
from GUI.Files import FileType, DirRef, FileRef
from GUI.GL import GLView, GLConfig
from GUI.GLTextures import Texture as GTexture
from GUI.Geometry import pt_in_rect, offset_rect, rects_intersect
from OpenGL.GL import *
from OpenGL.GL import glClearColor, glClear, glBegin, glColor3f, glVertex2i, glEnd, \
    GL_COLOR_BUFFER_BIT, GL_TRIANGLES
from OpenGL.GLU import *
import cap.cap_manager
from session import create_session
from term import TextAttribute, TextMode, set_attr_mode, reserve
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
from term_menu import basic_menus
import term_pygui_key_translate
from term_pygui_view_base import TerminalPyGUIViewBase, SINGLE_WIDE_CHARACTERS


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

