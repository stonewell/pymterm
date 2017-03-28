#coding=utf-8
import logging
import string
import threading

from GUI import Task
from GUI import application
from GUI.Colors import rgb
from functools32 import lru_cache

import cap.cap_manager
from session import create_session
from term import TextAttribute, TextMode, set_attr_mode, reserve
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import term_pygui_key_translate


SINGLE_WIDE_CHARACTERS =	\
					" !\"#$%&'()*+,-./" \
					"0123456789" \
					":;<=>?@" \
					"ABCDEFGHIJKLMNOPQRSTUVWXYZ" \
					"[\\]^_`" \
					"abcdefghijklmnopqrstuvwxyz" \
					"{|}~" \
					""

def boundary(value, minvalue, maxvalue):
    '''Limit a value between a minvalue and maxvalue.'''
    return min(max(value, minvalue), maxvalue)

_color_map = {}

class __cached_line_surf(object):
    pass

create_line_surface = None

@lru_cache(maxsize=1000)
def _get_surf(k, width, line_height):
    cached_line_surf = __cached_line_surf()
    cached_line_surf.cached = False
    cached_line_surf.surf = create_line_surface(width, line_height)

    return cached_line_surf

class TerminalPyGUIViewBase(TerminalWidget):

    def __init__(self, **kwargs):
        self.padding_x = 5
        self.padding_y = 5
        self.session = None
        self.selection_color = [0.1843, 0.6549, 0.8313, .5]
        self._width_cache = {}
        self._lock = threading.Lock()
        self._refresh_task = Task(self.__refresh, .02, False, False)

        TerminalWidget.__init__(self, **kwargs)
        
        self._generic_tabbing = False

    def _get_color(self, color_spec):
        key = repr(color_spec)
        if key in _color_map:
            return _color_map[key]

        c = map(lambda x: x / 255, map(float, color_spec))

        _color_map[key] = r = rgb(*c)

        return r

    def __refresh(self):
        if self.session and not self.session.stopped:
            logging.getLogger('term_pygui').debug('refresh called')
            self.invalidate()
            self.update()

    def refresh(self):
        self._refresh_task.start()

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
            logging.getLogger('term_pygui').debug(' processed by term_gui')
            return

        v, handled = term.term_keyboard.translate_key(self.session.terminal,
                                                 keycode,
                                                 text,
                                                 modifiers)

        if len(v) > 0:
            self.session.send(v)
        elif len(e.char) > 0:
            self.session.send(e.char)
        elif text:
            self.session.send(text)

        logging.getLogger('term_pygui').debug(' - translated %r, %d' % (v, handled))

        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        return

    def destroy(self):
        self.session.stop()
        super(TerminalPyGUIViewBase, self).destroy()

    def resized(self, delta):
        w, h = self.size

        if w <= 0 or h <=0:
            return

        w -= self.padding_x * 2
        h -= self.padding_y * 2
        h -= (self._get_line_height() / 3)

        self._calculate_visible_rows(h)
        self._calculate_visible_cols(w)

        logging.getLogger('term_pygui').debug('on size: cols={} rows={} width={} height={} size={} pos={}'.format(self.visible_cols, self.visible_rows, w, h, self.size, self.position))
        if self.session:
            self.session.resize_pty(self.visible_cols, self.visible_rows, w, h)
            self.session.terminal.resize_terminal()
            logging.getLogger('term_pygui').debug('on size done: cols={} rows={} width={} height={} size={} pos={}'.format(self.visible_cols, self.visible_rows, w, h, self.size, self.position))

    def _calculate_visible_rows(self, h):
        self.visible_rows = int(h / self._get_line_height())
        if self.visible_rows <= 0:
            self.visible_rows = 1

    def _calculate_visible_cols(self, w):
        self.visible_cols = int(w / self._get_col_width())

        if self.visible_cols <= 0:
            self.visible_cols = 1

    def copy_to_clipboard(self, data):
        application().set_clipboard(data.encode('utf-8'))

    def paste_from_clipboard(self):
        a = [chr(ord(c)) for c in application().get_clipboard()]
        s = ''.join(a).decode('utf-8')
        return s

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
        dy = self._get_line_height()
        cx = x
        cy = y - padding_top
        cy = int(boundary(round(cy / dy - 0.5), 0, len(l) - 1))

        if cy >= len(l) or cy < 0:
            return 0, 0

        text = self.norm_text(''.join(l[cy]), False)#reserve double width padding char to calculate width
        width_before = 0

        for i in range(0, len(text)):
            if text[i] == '\000':
                continue

            self_width = self._get_col_width()

            if i + 1 < len(text) and text[i + 1] == '\000':
                self_width += self._get_col_width()

            if width_before + self_width * 0.6 + padding_left > cx:
                return i, cy

            width_before += self_width

        return len(l[cy]), cy

    def _merge_color(self, c1, c2):
        return [c1[i] * c2[i] for i in range(len(c1))]

    def setup_menus(self, m):
        if self.session and self.session.terminal:
            m.copy_cmd.enabled = self.session.terminal.has_selection()
            m.paste_cmd.enabled = self.session.terminal.has_selection() or application().query_clipboard()
            m.clear_cmd.enabled = self.session.terminal.has_selection()
            m.transfer_file_cmd.enabled = hasattr(self.session, "transfer_file")
        else:
            m.transfer_file_cmd.enabled = False
            m.copy_cmd.enabled = False
            m.paste_cmd.enabled = False
            m.clear_cmd.enabled = False

    def next_handler(self):
        return application().target_window

    def copy_cmd(self):
        if self.session and self.session.terminal:
            self.session.terminal.copy_data()

    def paste_cmd(self):
        if self.session and self.session.terminal:
            self.session.terminal.paste_data()

    @lru_cache(1)
    def _get_col_width(self):
        f = self._get_font()

        col_width = max(map(lambda x:self._get_width(f, x), SINGLE_WIDE_CHARACTERS))

        logging.getLogger('term_pygui').info('col_width:{}'.format(col_width))

        return col_width

    def get_prefered_size(self):
        w = int(self._get_col_width() * self.visible_cols + self.padding_x * 2 + 0.5)
        h = int(self._get_line_height() * self.visible_rows + self.padding_y * 2 + 0.5)

        return (w, h)

    def _get_width(self, f = None, t = ''):
        w, h = self._get_size(f, t)
        return w

    def _get_cache_key(self, line, line_option):
        line_key = self._get_line_cache_key(line)
        line_option_key = self._get_line_option_cache_key(line_option)

        return '{}_{}'.format(line_key, line_option_key)

    def _get_line_cache_key(self, line):
        return repr(line)

    def _get_line_option_cache_key(self, line_option):
        return repr(line_option)

    def _refresh_font(self, cfg):
        self.font_file, self.font_name, self.font_size = cfg.get_font_info()


    @lru_cache(1)
    def _get_line_height(self):
        f = self._get_font()

        w, h = self._get_size(f, SINGLE_WIDE_CHARACTERS)

        return h + 1


    def _paint_line_surface(self, v_context, line_surf, x, y):
        pass

    def _prepare_line_context(self, line_surf, x, y, width, height):
        pass

    def _layout_line_text(self, context, text, font, l, t, w, h, cur_f_color):
        pass

    def _fill_line_background(self, line_context, cur_b_color, l, t, w, h):
        pass

    def _draw_layouted_line_text(self, line_context, layout, cur_f_color, l, t, w, h):
        pass

    def _do_cache(self):
        return True

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

            if self._do_cache():
                key = self._get_cache_key(line, line_option)
                cached_line_surf = _get_surf(key, width, line_height)
                line_surf = cached_line_surf.surf

                if cached_line_surf.cached:
                    self._paint_line_surface(v_context, line_surf, 0, y)

                    y += line_height
                    continue

                cached_line_surf.cached = self._do_cache()
            else:
                line_surf = create_line_surface(width, line_height)

            line_context = self._prepare_line_context(line_surf, x, y, width, line_height)

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

                t_w, t_h, layout = self._layout_line_text(line_context, t, font,
                                                              xxxx, y, col_width * 2 if wide_char else col_width, line_height,
                                                              cur_f_color)

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
                        if r_col >= len(line):
                            continue

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
