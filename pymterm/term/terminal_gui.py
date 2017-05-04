import logging
import sys
import threading

from term import TextAttribute, TextMode, reserve, clone_attr, get_default_text_attribute, DEFAULT_FG_COLOR_IDX, DEFAULT_BG_COLOR_IDX
from term import Cell, Line
from term_char_width import char_width
from terminal import Terminal
from charset_mode import translate_char, translate_char_british
from screen_buffer import ScreenBuffer

class TerminalGUI(Terminal):
    def __init__(self, cfg):
        Terminal.__init__(self, cfg)

        self.term_widget = None
        self.session = None

        self.col = 0
        self.row = 0 #always from 0 to row_count
        self._cursor_buffer_row = 0 #save any value from cursor_address ctrl sequence

        self.remain_buffer = []

        self.cur_line_option = get_default_text_attribute()
        self.saved_screen_buffer, self.saved_cursor, self.saved_cur_line_option = ScreenBuffer(), (0, 0), get_default_text_attribute()

        self.status_line = []
        self.status_line_mode = 0

        self.charset_modes_translate = [None, None]
        self.charset_mode = 0

        self._saved_charset_modes_translate = [None, None]
        self._saved_charset_mode = 0

        self._data_lock = threading.RLock()
        self._screen_buffer = ScreenBuffer()

        self._dec_mode = False
        self._force_column = False
        self._force_column_count = 80

        self._origin_mode = False
        self._saved_origin_mode = False

        self._tab_stops = {}
        self._set_default_tab_stops()

    def _set_default_tab_stops(self):
        tab_width = self.get_tab_width()

        for i in range(0, 999, tab_width):
            self._tab_stops[i] = True

    def _translate_char(self, c):
        if self.charset_modes_translate[self.charset_mode]:
            return self.charset_modes_translate[self.charset_mode](c)
        else:
            return c

    def get_line(self, row):
        line = self._screen_buffer.get_line(row)

        line.alloc_cells(self.get_cols(), True)

        return line

    def get_cur_line(self):
        line = self.get_line(self.row)

        return line

    def wrap_line(self, chars, insert):
        save_col, save_row, save_cursor_buffer_row = self.col, self.row, self._cursor_buffer_row

        self.col = 0
        self.cursor_down(None)
        for c in chars:
            if c == '\000':
                continue
            self._save_buffer(c, insert)
        if insert:
            self.col, self.row, self._cursor_buffer_row = save_col, save_row, save_cursor_buffer_row

    def save_buffer(self, c, insert = False):
        line = self.get_cur_line()

        #take care utf_8
        self.remain_buffer.append(c)

        c = ''.join(self.remain_buffer).decode('utf_8', errors='ignore')

        if len(c) == 0:
            if self.cfg.debug:
                logging.getLogger('term_gui').debug('remain_buffer found:{}'.format(map(ord, self.remain_buffer)))
            return

        self.remain_buffer = []

        #translate g0, g1 charset
        c = self._translate_char(c)

        w = char_width(c)

        if w == 0 or w == -1:
            logging.getLogger('term_gui').warning(u'save buffer get a invalid width char: w= {}, c={}'.format(w, c))

        if len(c.encode('utf_8')) > 1 and w > 1:
            c += '\000'

        if self.cfg.debug_more:
            logging.getLogger('term_gui').debug(u'save buffer width:{},{},{},len={}, line_len={}, cols={}'.format(self.col, self.row, w, len(c), line.cell_count(), self.get_cols()))

        if insert:
            if self.col + len(c) > self.get_cols():
                wrap_c = line.get_cells()[self.get_cols() - self.col - len(c):]

                if wrap_c[0].get_char() == '\000':
                    wrap_c = line.get_cells()[self.get_cols() - self.col - len(c) - 1:]

                two_bytes = len(wrap_c)

                if self.cfg.debug_more:
                    logging.getLogger('term_gui').debug(u'save buffer wrap:c=[{}], wrap=[{}]'.format(c, wrap_c))

                self._save_buffer(c, insert)
                self.wrap_line(''.join([c.get_char() for c in wrap_c]), insert)
            else:
                self._save_buffer(c, insert)
        else:
            if self.col + len(c) > self.get_cols():
                #wrap
                self.wrap_line(c, insert)
            else:
                self._save_buffer(c, insert)


    def _save_buffer(self, c, insert):
        line = self.get_cur_line()

        if self.cfg.debug_more:
            logging.getLogger('term_gui').debug(u'save buffer:{},{},{},len={}'.format(self.col, self.row, c, len(c)))

        if insert:
            line.insert_cell(self.col, Cell(c[0], self.cur_line_option, len(c) > 1))

            if len(c) > 1:
                line.insert_cell(self.col, Cell(c[1], self.cur_line_option, len(c) > 1))
        else:
            line.alloc_cells(self.col + len(c))
            if self.cfg.debug_more:
                logging.getLogger('term_gui').debug(u'save buffer option:{},{},{},option={}'.format(self.col, self.row,
                                                                                                            c, self.cur_line_option))
            line.get_cell(self.col).set_char(c[0])
            line.get_cell(self.col).set_attr(self.cur_line_option)
            line.get_cell(self.col).set_is_wide_char(len(c) > 1)

            self.col += 1
            if len(c) > 1:
                line.get_cell(self.col).set_char(c[1])
                line.get_cell(self.col).set_attr(self.cur_line_option)
                line.get_cell(self.col).set_is_wide_char(len(c) > 1)
                self.col += 1

    def get_rows(self):
        if self._force_column:
            return self.cap.flags['lines']
        return self.term_widget.visible_rows

    def get_cols(self):
        if self._force_column:
            return self._force_column_count

        cols = self.term_widget.visible_cols

        return cols

    def get_text(self):
        return self._screen_buffer.get_visible_lines()

    def output_normal_data(self, c, insert = False):
        if c == '\x1b':
            logging.getLogger('term_gui').error('normal data has escape char')
            sys.exit(1)

        try:
            for cc in c:
                self.save_buffer(cc, insert)
        except:
            logging.getLogger('term_gui').exception('save buffer failed')

    def output_status_line_data(self, c):
        if c == '\x1b':
            logging.getLogger('term_gui').error('status line data has escape char')
            sys.exit(1)

        self.status_line.append(c)

    def save_cursor(self, context):
        self.saved_cursor = self.get_cursor()

        self._saved_charset_modes_translate = self.charset_modes_translate[:]
        self._saved_charset_mode = self.charset_mode

        self._saved_origin_mode = self._origin_mode

        if self.cfg.debug:
            logging.getLogger('term_gui').debug('{} {} {} {} {} {}'.format( 'save', self.saved_cursor, self.row, self.col, self.get_rows(), self.get_cols()))

    def restore_cursor(self, context):
        col, row = self.saved_cursor

        if self.cfg.debug:
            logging.getLogger('term_gui').debug('{} {} {}'.format( 'restore', row, col))

        self._origin_mode = self._saved_origin_mode

        self.charset_modes_translate = self._saved_charset_modes_translate[:]
        self.charset_mode = self._saved_charset_mode

        self.set_cursor(col, row)

    def get_cursor(self):
        return (self.col, self.row)

    def set_cursor(self, col, row):
        old_col, self.col = self.col, col

        if self._origin_mode:
            begin, end = self.get_scroll_region()
            row += begin

        count = row - self._cursor_buffer_row

        #in case the program didn't care about terminal size,
        #like windows openssh from powershell
        #they use continuours row number start from 0,
        #never go back
        old_row = self.row

        if self.row + count >= self.get_rows() or self.row + count < 0:
            if count < 0:
                for i in range(count * -1):
                    self.parm_up_cursor(None)
            elif count > 0:
                for i in range(count):
                    self.parm_down_cursor(None)
        else:
            self.row += count

        old_cursor_buffer_row, self._cursor_buffer_row = self._cursor_buffer_row, row

        if self.cfg.debug:
            logging.getLogger('term_gui').debug('terminal cursor:old:{}, new:{}, cursor_buffer_row:{}'.format((old_col, old_row),
                                                                                                                  (self.col, self.row),
                                                                                                                  (old_cursor_buffer_row, self._cursor_buffer_row)))

    def cursor_right(self, context):
        self.parm_right_cursor(context)

    def cursor_left(self, context):
        self.parm_left_cursor(context)

    def cursor_down(self, context):
        self.parm_down_cursor(context)

    def cursor_up(self, context):
        self.parm_up_cursor(context)

    def carriage_return(self, context):
        self.col = 0
        self.refresh_display()

    def set_foreground(self, light, color_idx):
        self.set_attributes(1 if light else -1, color_idx, -2)

    def set_background(self, light, color_idx):
        self.set_attributes(1 if light else -1, -2, color_idx)

    def origin_pair(self):
        self.cur_line_option.reset_mode()
        self.cur_line_option.reset_fg_idx()
        self.cur_line_option.reset_bg_idx()

    def clr_line(self, context):
        line = self.get_cur_line()

        for cell in line.get_cells():
            cell.reset(self.cur_line_option)

        self.refresh_display()

    def clr_eol(self, context):
        line = self.get_cur_line()

        begin = self.col
        if line.get_cell(begin).get_char() == '\000':
            begin -= 1

        for i in range(begin, line.cell_count()):
            line.get_cell(i).reset(self.cur_line_option)

        self.refresh_display()

    def clr_bol(self, context):
        line = self.get_cur_line()

        end = self.col
        if end + 1 < line.cell_count() and line.get_cell(end + 1).get_char() == '\000':
            end = end + 1

        for i in range(end + 1):
            line.get_cell(i).reset(self.cur_line_option)

        self.refresh_display()

    def delete_chars(self, count, overwrite = False):
        line = self.get_cur_line()
        begin = self.col

        if line.get_cell(begin).get_char() == '\000':
            begin -= 1

        end = line.cell_count() if not overwrite or begin + count > line.cell_count() else begin + count

        for i in range(begin, end):
            if not overwrite and i + count < line.cell_count():
                line.get_cell(i).copy(line.get_cell(i + count))
            else:
                line.get_cell(i).reset(self.cur_line_option)

        self.refresh_display()

    def refresh_display(self):
        self.term_widget.refresh()

    def lock_display_data_exec(self, func):
        try:
            #self._data_lock.acquire()

            lines = self.get_text()

            self.term_widget.lines = lines
            self.term_widget.term_cursor = self.get_cursor()
            self.term_widget.cursor_visible = not self._screen_buffer.is_view_history()
            self.term_widget.focus = True

            func()
        except:
            logging.getLogger('term_gui').exception('lock display data exec')
        finally:
            #self._data_lock.release()
            pass

    def on_data(self, data):
        try:
            self._data_lock.acquire()
            Terminal.on_data(self, data)
        except:
            logging.getLogger('term_gui').exception('on data')
        finally:
            self._data_lock.release()

        self.refresh_display()

    def meta_on(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('meta_on')

    def set_attributes(self, mode, f_color_idx, b_color_idx):
        fore_color = None
        back_color = None

        text_mode = None

        if (mode > 0):
            if mode & (1 << 1):
                self.cur_line_option.set_mode(TextMode.BOLD)
            if mode & (1 << 2):
                self.cur_line_option.set_mode(TextMode.DIM)
            if mode & (1 << 7):
                self.cur_line_option.set_mode(TextMode.REVERSE)
            if mode & (1 << 21) or mode & (1 << 22):
                self.cur_line_option.unset_mode(TextMode.BOLD)
                self.cur_line_option.unset_mode(TextMode.DIM)
            if mode & (1 << 27):
                self.cur_line_option.unset_mode(TextMode.REVERSE)
        elif mode == 0:
            self.cur_line_option.reset_mode()
            if self.cfg.debug:
                logging.getLogger('term_gui').debug('reset mode')

        if f_color_idx >= 0:
            self.cur_line_option.set_fg_idx(f_color_idx)
            if self.cfg.debug:
                logging.getLogger('term_gui').debug('set fore color:{} {} {}, cur_option:{}'.format(f_color_idx, ' at ', self.get_cursor(), self.cur_line_option))
        elif f_color_idx == -1:
            #reset fore color
            self.cur_line_option.reset_fg_idx()
            if self.cfg.debug:
                logging.getLogger('term_gui').debug('reset fore color:{} {} {}, cur_option:{}'.format(f_color_idx, ' at ', self.get_cursor(), self.cur_line_option))

        if b_color_idx >= 0:
            if self.cfg.debug:
                logging.getLogger('term_gui').debug('set back color:{} {} {}, cur_option:{}'.format(b_color_idx, ' at ', self.get_cursor(), self.cur_line_option))
            self.cur_line_option.set_bg_idx(b_color_idx)
        elif b_color_idx == -1:
            #reset back color
            if self.cfg.debug:
                logging.getLogger('term_gui').debug('reset back color:{} {} {}, cur_option:{}'.format(b_color_idx, ' at ', self.get_cursor(), self.cur_line_option))
            self.cur_line_option.reset_bg_idx()

        if self.cfg.debug:
            logging.getLogger('term_gui').debug('set attribute:{}'.format(self.cur_line_option))

    def cursor_address(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('cursor address:{}'.format(context.params))
        self.set_cursor(context.params[1], context.params[0])

        self.refresh_display()

    def cursor_home(self, context):
        self.set_cursor(0, 0)
        self.refresh_display()

    def clr_eos(self, context):
        self.get_cur_line()

        begin = 0
        end = self.get_rows()

        if context:
            if len(context.params) == 0 or context.params[0] == 0:
                self.clr_eol(context)

                begin = self.row + 1
            elif context.params[0] == 1:
                self.clr_bol(context)

                end = self.row

        for row in range(begin, end):
            line = self.get_line(row)

            for cell in line.get_cells():
                cell.reset(self.cur_line_option)

        self.refresh_display()

    def parm_right_cursor(self, context):
        #same as xterm, if cursor out of screen, moving start from last col
        if self.col >= self.get_cols():
            self.col = self.get_cols() - 1

        self.col += context.params[0] if len(context.params) > 0 and context.params[0] > 0 else 1

        if self.col > self.get_cols():
            self.col = self.get_cols() - 1
        self.refresh_display()

    def parm_left_cursor(self, context):
        #same as xterm, if cursor out of screen, moving start from last col
        if self.col >= self.get_cols():
            self.col = self.get_cols() - 1

        self.col -= context.params[0] if len(context.params) > 0 and context.params[0] > 0 else 1
        if self.col < 0:
            self.col = 0
        self.refresh_display()

    def client_report_version(self, context):
        self.session.send('\033[>0;136;0c')

    def user7(self, context):
        if (context.params[0] == 6):
            col, row = self.get_cursor()

            if self._origin_mode:
                begin, end = self.get_scroll_region()
                row -= begin

            self.session.send(''.join(['\x1B[', str(row + 1), ';', str(col + 1), 'R']))
        elif context.params[0] == 5:
            self.session.send('\033[0n')

    def clear_tab(self, context):
        action = 0
        if context.params and len(context.params) > 0:
            action = context.params[0]

        if action == 0:
            self._tab_stops.pop(self.col, 0)
        elif action == 3:
            self._tab_stops.clear()

    def clear_all_tabs(self, context):
        self._tab_stops.clear()

    def set_tab(self, context):
        self._tab_stops[self.col] = True

    def tab(self, context):
        #col = self.col / self.session.get_tab_width()
        #col = (col + 1) * self.session.get_tab_width();

        tab_width = self.get_tab_width()
        col = self.col

        if len(self._tab_stops) > 0:
            for c in range(self.col+1, self.get_cols() + 1):
                if c in self._tab_stops:
                    col = c
                    break

        if col >= self.get_cols():
            col = self.get_cols() - 1

        self.col = col
        self.refresh_display()

    def row_address(self, context):
        self.set_cursor(self.col, context.params[0])

    def delete_line(self, context):
        self.parm_delete_line(context)

    def parm_delete_line(self, context):
        if self.cfg.debug:
            begin, end = self.get_scroll_region()
            logging.getLogger('term_gui').debug('delete line:{} begin={} end={}'.format(context.params, begin, end))

        c_to_delete = context.params[0] if len(context.params) > 0 else 1

        self._screen_buffer.delete_lines(self.row, c_to_delete)

        self.refresh_display()

    def get_scroll_region(self):
        return self._screen_buffer.get_scrolling_region()

    def set_scroll_region(self, begin, end):
        self._screen_buffer.set_scrolling_region( (begin, end) )

    def change_scroll_region(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('change scroll region:{} rows={}'.format(context.params, self.get_rows()))
        if len(context.params) == 0:
            self._screen_buffer.set_scrolling_region(None)
        else:
            self.set_scroll_region(context.params[0], context.params[1])
        self.cursor_home(None)
        self.refresh_display()

    def change_scroll_region_from_start(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('change scroll region from start:{} rows={}'.format(context.params, self.get_rows()))
        self.set_scroll_region(0, context.params[0])
        self.cursor_home(None)
        self.refresh_display()

    def change_scroll_region_to_end(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('change scroll region to end:{} rows={}'.format(context.params, self.get_rows()))
        self.set_scroll_region(context.params[0], self.get_rows() - 1)
        self.cursor_home(None)
        self.refresh_display()

    def insert_line(self, context):
        self.parm_insert_line(context)

    def parm_insert_line(self, context):
        if self.cfg.debug:
            begin, end = self.get_scroll_region()
            logging.getLogger('term_gui').debug('insert line:{} begin={} end={}'.format(context.params, begin, end))

        c_to_insert = context.params[0] if len(context.params) > 0 else 1

        self._screen_buffer.insert_lines(self.row, c_to_insert)

        self.refresh_display()

    def request_background_color(self, context):
        rbg_response = '\033]11;rgb:%04x/%04x/%04x/%04x\007' % (self.cfg.default_background_color[0], self.cfg.default_background_color[1], self.cfg.default_background_color[2], self.cfg.default_background_color[3])

        if self.cfg.debug:
            logging.getLogger('term_gui').debug("response background color request:{}".format(rbg_response.replace('\033', '\\E')))
        self.session.send(rbg_response)

    def user9(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('response terminal type:{} {}'.format(context.params, self.cap.cmds['user8'].cap_value))
        self.session.send(self.cap.cmds['user8'].cap_value)

    def enter_reverse_mode(self, context):
        self.cur_line_option.set_mode(TextMode.REVERSE)
        self.refresh_display()

    def exit_standout_mode(self, context):
        self.cur_line_option.reset_mode()
        self.refresh_display()

    def enter_ca_mode(self, context):
        self.saved_screen_buffer, self.saved_col, self.saved_row, self.saved_cur_line_option = \
          self._screen_buffer, self.col, self.row, self.cur_line_option
        self._screen_buffer, self.col, self.row, self.cur_line_option = \
          ScreenBuffer(), 0, 0, get_default_text_attribute()
        self._screen_buffer.resize_buffer(self.get_rows(), self.get_cols())
        self._screen_buffer.clear_selection()
        self.refresh_display()

    def exit_ca_mode(self, context):
        self._screen_buffer, self.col, self.row, self.cur_line_option = \
            self.saved_screen_buffer, self.saved_col, self.saved_row, self.saved_cur_line_option
        self._screen_buffer.clear_selection()
        self.refresh_display()

    def key_shome(self, context):
        self.set_cursor(1, 0)
        self.refresh_display()

    def enter_bold_mode(self, context):
        self.cur_line_option.set_mode(TextMode.BOLD)
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('set bold mode:attr={}'.format(self.cur_line_option))

    def keypad_xmit(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('keypad transmit mode')
        self.keypad_transmit_mode = True

    def keypad_local(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('keypad local mode')
        self.keypad_transmit_mode = False

    def cursor_invisible(self, context):
        self.term_widget.cursor_visible = False
        self.refresh_display()

    def cursor_normal(self, context):
        self.term_widget.cursor_visible = True
        self.refresh_display()

    def cursor_visible(self, context):
        self.cursor_normal(context)

    def next_line(self, context):
        self.col = 0
        self.parm_down_cursor(context)

    def parm_down_cursor(self, context, do_refresh = True):
        begin, end = self.get_scroll_region()

        count = context.params[0] if context and context.params and len(context.params) > 0 else 1

        if self.cfg.debug:
            logging.getLogger('term_gui').debug('before parm down cursor:{} {} {} {}'.format(begin, end, self.row, count))
        for i in range(count):
            self.get_cur_line()

            if self.row == end:
                self._screen_buffer.scroll_up()
                self._cursor_buffer_row += 1
            else:
                self.row += 1
                self._cursor_buffer_row += 1

            self.get_cur_line()

        if self.cfg.debug:
            logging.getLogger('term_gui').debug('after parm down cursor:{} {} {} {}'.format(begin, end, self.row, count))

        if do_refresh:
            self.refresh_display()

    def exit_alt_charset_mode(self, context):
        self.charset_modes_translate[0] = None
        self.exit_standout_mode(context)
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('exit alt:{} {}'.format(' at ', self.get_cursor()))

    def enter_alt_charset_mode(self, context):
        self.charset_modes_translate[0] = translate_char
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('enter alt:{} {}'.format(' at ', self.get_cursor()))

    def enter_alt_charset_mode_british(self, context):
        self.charset_modes_translate[0] = translate_char_british

    def enter_alt_charset_mode_g1(self, context):
        self.charset_modes_translate[1] = translate_char

    def enter_alt_charset_mode_g1_british(self, context):
        self.charset_modes_translate[1] = translate_char_british

    def exit_alt_charset_mode_g1_british(self, context):
        self.charset_modes_translate[1] = None
        self.exit_standout_mode(context)

    def shift_in_to_charset_mode_g0(self, context):
        self.charset_mode = 0
        self.refresh_display()

    def shift_out_to_charset_mode_g1(self, context):
        self.charset_mode = 1
        self.refresh_display()

    def enable_mode(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('enable mode:{}'.format(context.params))

        mode = context.params[0]

        if mode == 25:
            self.cursor_normal(context)
        elif mode == 40:
            self._dec_mode = True
            self._force_column = True
            self.resize_terminal()
        elif mode == 3:
            if self._dec_mode:
                self._force_column = True
                self._force_column_count = 132

                self.clr_eos(None)
                self.cursor_home(None)
                self.resize_terminal()
        elif mode == 6:
            self._origin_mode = True
            self.cursor_home(None)

    def disable_mode(self, context):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('disable mode:{}'.format(context.params))

        mode = context.params[0]

        if mode == 25:
            self.cursor_invisible(context)
        elif mode == 40:
            self._dec_mode = False
            self._force_column = False
            self.resize_terminal()
        elif mode == 3:
            if self._dec_mode:
                self._force_column = True
                self._force_column_count = 80

                self.clr_eos(None)
                self.cursor_home(None)
                self.resize_terminal()
        elif mode == 6:
            self._origin_mode = False
            self.cursor_home(None)

    def process_key(self, keycode, text, modifiers):
        handled = False
        code, key = keycode
        view_history_key = False

        if ('shift' in modifiers or 'shift_L' in modifiers or 'shift_R' in modifiers ) and key == 'insert':
            #paste
            self.paste_data()
            handled = True
        elif ('ctrl' in modifiers or 'ctrl_L' in modifiers or 'ctrl_R' in modifiers) and key == 'insert':
            #copy
            self.copy_data()
            handled = True
        elif ('shift' in modifiers or 'shift_L' in modifiers or 'shift_R' in modifiers ) and (key == 'pageup' or key == 'pagedown'):
            if not self._screen_buffer.is_view_history():
                self._screen_buffer.view_history(True)
            if key == 'pageup':
                self._screen_buffer.view_history_pageup()
            else:
                self._screen_buffer.view_history_pagedown()
            handled = True
            view_history_key = True
            self.refresh_display()

        if (not view_history_key and
            not ((key == 'shift' or key == 'shift_L' or key == 'shift_R') and len(modifiers) == 0)):
            self._screen_buffer.view_history(False)

        return handled

    def has_selection(self):
        return self._screen_buffer.has_selection()

    def get_selection_text(self):
        if not self.has_selection():
            return ''

        lines = self._screen_buffer.get_selection_text()

        texts = map(lambda x:''.join(x.get_selection_text()), lines)

        d = '\r\n'

        if 'carriage_return' in self.cap.cmds:
            d = self.cap.cmds['carriage_return'].cap_value

        data = d.join(texts).replace('\000', '')

        return data

    def column_address(self, context):
        col, row = self.get_cursor()
        self.set_cursor(context.params[0], row)
        self.refresh_display()

    def parm_up_cursor(self, context, do_refresh = True):
        begin, end = self.get_scroll_region()

        count = context.params[0] if context and context.params and len(context.params) > 0 else 1

        if self.cfg.debug:
            logging.getLogger('term_gui').debug('before parm up cursor:{} {} {} {}'.format(begin, end, self.row, count))
        for i in range(count):
            self.get_cur_line()

            if self.row == begin:
                self._screen_buffer.scroll_down()
                self._cursor_buffer_row -= 1
            else:
                self.row -= 1
                self._cursor_buffer_row -= 1

            self.get_cur_line()

        if self.cfg.debug:
            logging.getLogger('term_gui').debug('after parm up cursor:{} {} {} {}'.format(begin, end, self.row, count))

        if do_refresh:
            self.refresh_display()

    def prompt_login(self, t, username):
        logging.getLogger('term_gui').warn('sub class must implement prompt login')
        pass

    def prompt_password(self, action):
        logging.getLogger('term_gui').warn('sub class must implement prompt password')
        pass

    def create_new_line(self):
        return Line()

    def paste_data(self):
        data = ''
        if self.has_selection():
            data = self.get_selection_text()
            self._screen_buffer.clear_selection()

        if len(data) == 0:
            data = self.term_widget.paste_from_clipboard()
        else:
            self.term_widget.copy_to_clipboard(data)

        if len(data) > 0:
            self.session.send(data.encode('utf-8'))

    def copy_data(self):
        data = self.get_selection_text()

        if len(data) == 0:
            return

        self.term_widget.copy_to_clipboard(data)

        self._screen_buffer.clear_selection()

    def resize_terminal(self):
        self._screen_buffer.resize_buffer(self.get_rows(), self.get_cols())

        self.set_scroll_region(0, self.get_rows() - 1)

        if self.row >= self.get_rows():
            self.row = self.get_rows() - 1
            self._cursor_buffer_row = self.row

        if self.col >= self.get_cols():
            self.col = self.get_cols() - 1

    def enter_status_line(self, mode, enter):
        if not enter:
            status_line = ''.join(self.status_line)
            if len(status_line) > 0:
                self.process_status_line(mode, status_line)
        else:
            self.status_line = []
            self.status_line_mode = mode

        Terminal.enter_status_line(self, mode, enter)

    def process_status_line(self, mode, status_line):
        if self.cfg.debug:
            logging.getLogger('term_gui').debug('status line:mode={}, {}'.format(mode, status_line))
        self.session.on_status_line(mode, status_line)

    def determin_colors(self, attr):
        if self.cfg.debug_more:
            logging.getLogger('term_gui').debug('determin_colors:attr={}'.format(attr))
        def _get_color(idx):
            color = None

            if idx < 8:
                color = self.cfg.get_color(8 + idx if attr.has_mode(TextMode.BOLD) else idx)
            elif idx < 16:
                color = self.cfg.get_color(idx)
            elif idx < 256:
                color = self.cfg.get_color(idx)
            elif idx == DEFAULT_FG_COLOR_IDX:
                color = self.cfg.default_foreground_color
            elif idx == DEFAULT_BG_COLOR_IDX:
                color = self.cfg.default_background_color
            else:
                logging.getLogger('term_gui').error('not implemented color:{} mode={}'.format(idx, mode))
                sys.exit(1)

            if attr.has_mode(TextMode.DIM):
                color = map(lambda x: int(float(x) * 2 / 3), color)
            return color

        f_color = _get_color(attr.get_fg_idx())
        b_color = _get_color(attr.get_bg_idx())

        if attr.has_mode(TextMode.REVERSE):
            f_color, b_color = b_color, f_color

        if attr.has_mode(TextMode.SELECTION):
            f_color, b_color = b_color, f_color

        if attr.has_mode(TextMode.CURSOR):
            f_color, b_color = b_color, self.cfg.default_cursor_color

        return (f_color, b_color)

    def send_primary_device_attributes(self, context):
        self.session.send('\033[?62;c')

    def screen_alignment_test(self, context):
        self.save_cursor(context)
        self.get_line(self.get_rows() - 1)

        for i in range(self.get_rows()):
            self.set_cursor(0, i)
            line = self.get_cur_line()
            line.alloc_cells(self.get_cols(), True)

            for cell in line.get_cells():
                cell.set_char('E')

        self.restore_cursor(context)
        self.refresh_display()

    def set_selection(self, s_f, s_t):
        self._screen_buffer.set_selection(s_f, s_t)
