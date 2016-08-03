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
import GUI.Font

import cap.cap_manager
from session import create_session
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import term.term_keyboard
import term_pygui_key_translate
from term import TextAttribute, TextMode, set_attr_mode, reserve
from term_menu import basic_menus

def boundary(value, minvalue, maxvalue):
    '''Limit a value between a minvalue and maxvalue.'''
    return min(max(value, minvalue), maxvalue)

class TerminalPyGUIApp(Application):
    def __init__(self, cfg):
        Application.__init__(self)

        self.cfg = cfg
        self.current_tab = None
        self.conn_history = []
        self.menus = basic_menus(self.cfg.get_session_names())

    def get_application_name(self):
        return  'Multi-Tab Terminal Emulator in Python & pyGUI'

    def setup_menus(self, m):
        Application.setup_menus(self, m)
        m.paste_cmd.enabled = application().query_clipboard()
        m.new_window_cmd.enabled = 1
        m.open_session_cmd.enabled = 1

    def connect_to(self, conn_str = None, port = None, session_name = None, win = None):
        cfg = self.cfg.clone()
        if conn_str:
            cfg.set_conn_str(conn_str)
        elif session_name:
            cfg.session_name = session_name
            cfg.config_session()

        if port:
            cfg.port = port

        cfg.session_type = 'ssh'

        doc = self.make_new_document()
        doc.new_contents()
        doc.cfg = cfg

        if win:
            view = TerminalPyGUIView(model=doc)
            self._create_new_tab(win, view)
        else:
            self.make_window(doc)

    def create_terminal(self, cfg):
        return TerminalPyGUI(cfg)

    def start(self):
        self.run()

    def open_app(self):
        self.connect_to()

    def open_window_cmd(self):
        self.connect_to()

    def make_window(self, document):
        view = TerminalPyGUIView(model=document)
        w, h = view.get_prefered_size()

        win = Window(bounds = (0, 0, w + 10, h + 50), document = document)
        win.tabview = tabview = TermTabView()
        win.auto_position = False

        self._create_new_tab(win, view)

        win.place(tabview, left = 0, top = 0, right = 0, bottom = 0, sticky = 'nsew')

        win.show()
        view.become_target()

    def _create_new_tab(self, win, view):
        win.tabview.add_item(view)

        cfg = view.model.cfg
        session = create_session(cfg, self.create_terminal(cfg))
        session.term_widget = view
        session.terminal.term_widget = view
        view.session = session
        view.tab_width = session.get_tab_width()

        session.start()

        win.tabview.selected_index = len(win.tabview.items) - 1

    def make_document(self, fileref):
        doc = TerminalPyGUIDoc()
        doc.cfg = self.cfg.clone()
        doc.title = 'Multi-Tab Terminal Emulator in Python & pyGUI'

        return doc

    def new_window_cmd(self):
        self.connect_to()

    def new_cmd(self):
        self.connect_to(win = self.get_target_window())

    def open_session_cmd(self, *args):
        index, = args
        self.connect_to(session_name=self.cfg.get_session_names()[index], win=self.get_target_window())

class TerminalPyGUIDoc(Document):
    def new_contents(self):
        pass

    def read_contents(self, file):
        pass

    def write_contents(self, file):
        pass

_color_map = {}

class TerminalPyGUIView(View, TerminalWidget):

    def __init__(self, **kwargs):
        View.__init__(self, **kwargs)
        TerminalWidget.__init__(self, **kwargs)

        self.font_size = 17.5
        self.padding_x = 5
        self.padding_y = 5
        self.session = None
        self.selection_color = [0.1843, 0.6549, 0.8313, .5]
        self._width_cache = {}

    def _get_color(self, color_spec):
        key = repr(color_spec)
        if key in _color_map:
            return _color_map[key]

        c = map(lambda x: x / 255, map(float, color_spec))

        _color_map[key] = r = rgb(*c)

        return r

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
                    canvas.fill_frame_rect((xxxx, y, right, y + canvas.font.line_height))

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

            y += canvas.font.line_height

    def __refresh(self):
        self.invalidate()
        self.update()

    def refresh(self):
        application().schedule_idle(self.__refresh)

    def _setup_canvas(self, canvas):
        canvas.set_font(self._get_font())

    def _get_font(self):
        return GUI.Font(family='Noto Sans Mono CJK SC Regular',
                                    #u'文泉驿等宽微米黑',
                                    #'YaHei Consolas Hybrid',
                                    #'WenQuanYi Micro Hei Mono',
                                    size=self.font_size)

    def get_prefered_size(self):
        f = self._get_font()
        w = int(self._get_width(f, 'ABCDabcd') / 8 * self.visible_cols + self.padding_x * 2 + 0.5)
        h = int(f.line_height * self.visible_rows + self.padding_y * 2 + 0.5)

        return (w, h)

    def key_down(self, e):
        key = term_pygui_key_translate.translate_key(e)

        keycode = (e.char, key)
        text = key if len(key) == 1 and key[0] in string.printable else e.char if len(e.char) > 0 else None
        modifiers = []

        if e.option:
            modifiers.append('alt')
        if e.control:
            modifiers.append('ctrl')
        if e.shift:
            modifiers.append('shift')

        logging.getLogger('term_pygui').debug('view key_down:{}'.format(e))
        logging.getLogger('term_pygui').debug('view key_down:{}, {}, {}'.format(keycode, text, modifiers))
        if self.session.terminal.process_key(keycode,
                                             text,
                                             modifiers):
            return

        v, handled = term.term_keyboard.translate_key(self.session.terminal,
                                                 keycode,
                                                 text,
                                                 modifiers)

        if len(v) > 0:
            self.session.send(v)
        elif text:
            self.session.send(text)

        logging.getLogger('term_pygui').debug(' - translated %r, %d' % (v, handled))

        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        return

    def destroy(self):
        self.session.stop()
        super(TerminalPyGUIView, self).destroy()

    def resized(self, delta):
        super(TerminalPyGUIView, self).resized(delta)

        w, h = self.size

        if w <= 0 or h <=0:
            return

        w -= self.padding_x * 2
        h -= self.padding_y * 2
        h -= (self._get_font().line_height / 3)

        self._calculate_visible_rows(h)
        self._calculate_visible_cols(w)

        logging.getLogger('term_pygui').debug('on size: cols={} rows={} width={} height={} size={} pos={}'.format(self.visible_cols, self.visible_rows, w, h, self.size, self.position))
        if self.session:
            self.session.resize_pty(self.visible_cols, self.visible_rows, w, h)
            self.session.terminal.resize_terminal()

    def _calculate_visible_rows(self, h):
        f = self._get_font()
        self.visible_rows = int(h / f.line_height)
        if self.visible_rows <= 0:
            self.visible_rows = 1

    def _calculate_visible_cols(self, w):
        f = self._get_font()
        self.visible_cols = int(w / self._get_width(f, 'ABCDabcd') * 8)

        if self.visible_cols <= 0:
            self.visible_cols = 1

    def copy_to_clipboard(self, data):
        application().set_clipboard(data.encode('utf-8'))

    def paste_from_clipboard(self):
        return application().get_clipboard().decode('utf-8')

    def mouse_down(self, event):
        self.become_target()

        self.cancel_selection()

        self._selection_from = self._selection_to = self._get_cursor_from_xy(*event.position)

        mouse_tracker = self.track_mouse()
        while True:
            event = mouse_tracker.next()
            self._selection_to = self._get_cursor_from_xy(*event.position)

            self.refresh()

            if event.kind == 'mouse_up':
                try:
                    mouse_tracker.next()
                except StopIteration:
                    pass
                break

    def _get_cursor_from_xy(self, x, y):
        '''Return the (row, col) of the cursor from an (x, y) position.
        '''
        padding_left = self.padding_x
        padding_top = self.padding_y
        l = self.lines
        f = self._get_font()
        dy = f.line_height
        cx = x
        cy = y - padding_top
        cy = int(boundary(round(cy / dy - 0.5), 0, len(l) - 1))

        if cy >= len(l) or cy < 0:
            return 0, 0

        text = self.norm_text(''.join(l[cy]))
        for i in range(0, len(text)):
            if self._get_width(f, text[:i]) + self._get_width(f, text[i]) * 0.6 + padding_left > cx:
                for ii in range(len(l[cy])):
                    if l[cy][ii] == '\000':
                        continue
                    i -= 1
                    if i < 0:
                        while ii < len(l[cy]) and l[cy][ii] == '\000':
                            ii += 1
                        return ii, cy

        return len(l[cy]), cy

    def _merge_color(self, c1, c2):
        return [c1[i] * c2[i] for i in range(len(c1))]

    def setup_menus(self, m):
        View.setup_menus(self, m)
        if self.session and self.session.terminal:
            m.copy_cmd.enabled = self.session.terminal.has_selection()
            m.paste_cmd.enabled = self.session.terminal.has_selection() or application().query_clipboard()
            m.clear_cmd.enabled = self.session.terminal.has_selection()

    def next_handler(self):
        return application().target_window

    def copy_cmd(self):
        if self.session and self.session.terminal:
            self.session.terminal.copy_data()

    def paste_cmd(self):
        if self.session and self.session.terminal:
            self.session.terminal.paste_data()

    def _get_width(self, f = None, t = ''):
        if t in self._width_cache:
            return self._width_cache[t]

        if f is None:
            f = self._get_font()

        self._width_cache[t] = w = f.width(t)

        return w

class TermTabView(TabView):
    def tab_changed(self, tab_index):
        v = self.items[tab_index]

        v.become_target()

class TerminalPyGUI(TerminalGUI):
    def __init__(self, cfg):
        super(TerminalPyGUI, self).__init__(cfg)

    def prompt_login(self, t, username):
        pass

    def prompt_password(self, action):
        pass
