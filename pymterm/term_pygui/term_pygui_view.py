#coding=utf-8
import logging
import os
import select
import socket
import sys
import time
import traceback
import string

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb, View, TabView
from GUI import application
from GUI.Files import FileType
from GUI.Geometry import pt_in_rect, offset_rect, rects_intersect
from GUI.StdColors import black, red, blue
from GUI.StdFonts import application_font
from GUI.Colors import rgb
from GUI.Files import FileType, DirRef, FileRef
from GUI import FileDialogs

import GUI.Font

import cap.cap_manager
from session import create_session
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import term.term_keyboard
import term_pygui_key_translate
from term import TextAttribute, TextMode, set_attr_mode, reserve
from term_menu import basic_menus

from term_pygui_view_base import TerminalPyGUIViewBase

from functools32 import lru_cache

#put View on right to make Base class method override happer
#because python resolve method from left to right
class TerminalPyGUIView(TerminalPyGUIViewBase, View):

    def __init__(self, **kwargs):
        TerminalPyGUIViewBase.__init__(self, **kwargs)
        View.__init__(self, **kwargs)

    def draw(self, canvas, update_rect):
        try:
            self._draw(canvas, update_rect)
        except:
            logging.getLogger('term_pygui').exception('draw failed')

    def _draw(self, canvas, update_rect):
        self._setup_canvas(canvas)

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

        canvas.fillcolor = self._get_color(self.session.cfg.default_background_color)
        canvas.fill_frame_rect(update_rect)

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

                tmp_t_c, canvas.textcolor = canvas.textcolor, self._get_color(cur_f_color)
                tmp_b_c, canvas.backcolor = canvas.backcolor, self._get_color(cur_b_color)
                tmp_f_c, canvas.fillcolor = canvas.fillcolor, self._get_color(cur_b_color)
                tmp_p_c, canvas.pencolor = canvas.pencolor, canvas.backcolor

                right = xxxx + self._get_width(canvas.font, t)
                if cur_b_color != self.session.cfg.default_background_color:
                    canvas.fill_frame_rect((xxxx, y, right, y + self._get_line_height()))

                canvas.moveto(xxxx, y + canvas.font.ascent)
                canvas.show_text(t)

                canvas.textcolor, canvas.backcolor, canvas.fillcolor, canvas.pencolor = tmp_t_c, tmp_b_c, tmp_f_c, tmp_p_c

                return right

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

            y += self._get_line_height()

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
        return GUI.Font(family='Noto Sans Mono CJK SC Regular',
                                    #u'文泉驿等宽微米黑',
                                    #'YaHei Consolas Hybrid',
                                    #'WenQuanYi Micro Hei Mono',
                                    size=self.font_size)

    def get_prefered_size(self):
        f = self._get_font()
        w = int(self._get_width(f, 'ABCDabcd') / 8 * self.visible_cols + self.padding_x * 2 + 0.5)
        h = int(self._get_line_height() * self.visible_rows + self.padding_y * 2 + 0.5)

        return (w, h)

    @lru_cache(200)
    def _get_width(self, f = None, t = ''):
        if f is None:
            f = self._get_font()
            
        return w
    
    def _get_line_height(self):
        f = self._get_font()

        return f.line_height
