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
from term import TextAttribute, TextMode, reserve, get_default_text_attribute
import term.term_keyboard
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import term_pygui_key_translate
import pymterm

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

    def gen_render_color(self, color_spec):
        c = map(lambda x: x / 255, map(float, color_spec))

        return r

    def __refresh(self):
        if self.session and not self.session.stopped:
            if pymterm.debug_log:
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

        if pymterm.debug_log:
            logging.getLogger('term_pygui').debug('view key_down:{}'.format(e))
            logging.getLogger('term_pygui').debug('view key_down:{}, {}, {}'.format(keycode, text, modifiers))

        if self.session.terminal.process_key(keycode,
                                             text,
                                             modifiers):
            if pymterm.debug_log:
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

        if pymterm.debug_log:
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

        self._calculate_visible_rows(h)
        self._calculate_visible_cols(w)

        if pymterm.debug_log:
            logging.getLogger('term_pygui').debug('on size: cols={} rows={} width={} height={} size={} pos={}'.format(self.visible_cols, self.visible_rows, w, h, self.size, self.position))
        if self.session:
            self.session.resize_pty(self.visible_cols, self.visible_rows, w, h)
            self.session.terminal.resize_terminal()
            if pymterm.debug_log:
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
        return application().get_clipboard().decode('utf-8')

    def mouse_down(self, event):
        self.become_target()

        self.cancel_selection()

        self._selection_from = self._selection_to = self._get_cursor_from_xy(*event.position)

        mouse_tracker = self.track_mouse()
        while True:
            event = mouse_tracker.next()
            to = self._get_cursor_from_xy(*event.position)

            if to != self._selection_to:
                self._selection_to = to
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

        text = self.norm_text(l[cy].get_text(raw=True), False)#reserve double width padding char to calculate width
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

        return l[cy].cell_count(), cy

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

        if pymterm.debug_log:
            logging.getLogger('term_pygui').debug('col_width:{}'.format(col_width))

        return col_width

    def get_prefered_size(self):
        w = int(self._get_col_width() * self.visible_cols + self.padding_x * 2 + 0.5)
        h = int(self._get_line_height() * self.visible_rows + self.padding_y * 2 + 0.5)

        return (w, h)

    def _get_width(self, f = None, t = ''):
        w, h = self._get_size(f, t)
        return w

    def _get_cache_key(self, line):
        return line.get_hash_value()

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
        def locked_draw_canvas():
            self._real_draw_canvas(v_context)

        self.session.terminal.lock_display_data_exec(locked_draw_canvas)

    def _real_draw_canvas(self, v_context):
        x = self.padding_x
        b_x = self.padding_x
        y = self.padding_y

        lines = self.lines

        c_col, c_row = self.term_cursor

        s_f, s_t = self.get_selection()

        s_f_c, s_f_r = s_f
        s_t_c, s_t_r = s_t


        font = self._get_font();

        line_height = self._get_line_height()
        col_width = int(self._get_col_width())

        width, height = self.size

        for i in range(len(lines)):
            x = b_x = self.padding_x
            line = lines[i]

            #clean up temp cursor and selection mode
            for cell in line.get_cells():
                cell.get_attr().unset_mode(TextMode.CURSOR)
                cell.get_attr().unset_mode(TextMode.SELECTION)

            # temprary add cusor and selection mode
            if self.cursor_visible and i == c_row:
                line.alloc_cells(c_col + 1)
                line.get_cell(c_col).get_attr().set_mode(TextMode.CURSOR)

            if s_f != s_t:
                if s_f_r == s_t_r and i == s_f_r:
                    line.alloc_cells(s_t_c)
                    for mm in range(s_f_c, s_t_c):
                        line.get_cell(mm).get_attr().set_mode(TextMode.SELECTION)
                else:
                    if i == s_f_r:
                        line.alloc_cells(s_f_c + 1)
                        for mm in range(s_f_c, len(line.get_cells())):
                            line.get_cell(mm).get_attr().set_mode(TextMode.SELECTION)
                    elif i == s_t_r:
                        line.alloc_cells(s_t_c)
                        for mm in range(0, s_t_c):
                            line.get_cell(mm).get_attr().set_mode(TextMode.SELECTION)
                    elif i > s_f_r and i < s_t_r:
                        for cell in line.get_cells():
                            cell.get_attr().set_mode(TextMode.SELECTION)

            col = 0
            last_col = 0
            text = ''

            if self._do_cache():
                key = self._get_cache_key(line)
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

            def render_text(xxxx, cell):
                t = cell.get_char()

                if len(t) == 0:
                    return xxxx

                t = self.norm_text(t)

                if len(t) == 0:
                    return xxxx

                cur_f_color, cur_b_color = self.session.terminal.determin_colors(cell.get_attr())

                wide_char = cell.is_widechar()

                t_w, t_h, layout = self._layout_line_text(line_context, t, font,
                                                              xxxx, y, col_width * 2 if wide_char else col_width, line_height,
                                                              cur_f_color)

                if cur_b_color != self.session.cfg.default_background_color:
                    self._fill_line_background(line_context, cur_b_color, xxxx, 0,
                                                   max(t_w, col_width * 2 if wide_char else col_width),
                                                   t_h)

                self._draw_layouted_line_text(line_context, layout, cur_f_color, xxxx, 0, t_w, t_h)

                if cell.get_attr().has_mode(TextMode.BOLD):
                    self._draw_layouted_line_text(line_context, layout, cur_f_color, xxxx + 1, 1, t_w, t_h)

                return xxxx + t_w

            for cell in line.get_cells():
                if cell.need_draw():
                    render_text(b_x, cell)

                b_x += col_width

            self._paint_line_surface(v_context, line_surf, 0, y)

            y += line_height
