import logging

from terminal import Terminal
from term import TextAttribute, TextMode, reserve

class TerminalGUI(Terminal):
    def __init__(self, cfg):
        Terminal.__init__(self, cfg)

        self.term_widget = None
        self.session = None

        self.lines = []
        self.line_options = []
        self.col = 0
        self.row = 0
        self.remain_buffer = []

        self.last_line_option_row = -1
        self.last_line_option_col = -1
        self.cur_line_option = TextAttribute(None, None, None)
        self.saved_lines, self.saved_line_options, self.saved_cursor = [], [], (0, 0)
        self.bold_mode = False
        self.scroll_region = None

        self.view_history_begin = None
        self.history_lines = []
        self.history_line_options = []

    def get_line(self, row):
        reserve(self.lines, row + 1, [])

        self.get_line_option(row)

        return self.lines[row]

    def get_cur_line(self):
        line = self.get_line(self.row)

        reserve(line, self.col + 1, ' ')

        return line

    def save_buffer(self, c, insert = False, wrap = False):
        line = self.get_cur_line()

        self.get_cur_option()
        line_option = self.get_cur_line_option()

        #update line option
        line_option[self.col] = self.cur_line_option

        if self.cfg.debug_more:
            logging.getLogger('term_gui').debug('save buffer:{},{},{}'.format(self.col, self.row, c))

        #take care utf_8
        if not wrap:
            self.remain_buffer.append(c)

            c = ''.join(self.remain_buffer).decode('utf_8', errors='ignore')

            if len(c) == 0:
                logging.getLogger('term_gui').debug('remain_buffer found:{}'.format(map(ord, self.remain_buffer)))
                return

            self.remain_buffer = []

            if len(c.encode('utf_8')) > 1:
                c += '\000'

        def wrap_line():
            self.col = 0
            self.cursor_down(None)
            self.save_buffer(c, insert, True)

        if insert:
            line.insert(self.col, c[0])
            if len(c) > 1:
                line.insert(self.col + 1, c[1])

            if len(line) > self.get_cols():
                c = line[self.get_cols()]
                two_bytes = 0
                if c == '\000':
                    c = line[self.get_cols() - 1]
                    c += '\000'
                    two_bytes = 1

                line = line[:self.get_cols() - two_bytes]
                wrap_line()
                return
        else:
            if self.col == self.get_cols():
                #wrap
                #TODO: need to handle the double bytes
                wrap_line()
                return
            line[self.col] = c[0]
            self.col += 1
            if len(c) > 1:
                if self.col < len(line):
                    line[self.col] = c[1]
                else:
                    line.append(c[1])
                self.col += 1

    def get_rows(self):
        return self.term_widget.visible_rows

    def get_cols(self):
        cols = self.term_widget.visible_cols

        return cols

    def get_history_text(self):
        return self.history_lines + self.lines, self.history_line_options + self.line_options

    def get_text(self):
        if self.view_history_begin is not None:
            l, o = self.get_history_text()
            lines = l[self.view_history_begin: self.view_history_begin + self.get_rows()]
            line_options = o[self.view_history_begin: self.view_history_begin + self.get_rows()]
            return lines, line_options

        if len(self.lines) <= self.get_rows():
            return self.lines + [self.create_new_line()] * (self.get_rows() - len(self.lines)), self.line_options + [self.create_new_line_option()] * (self.get_rows() - len(self.lines))
        else:
            lines = self.lines[len(self.lines) - self.get_rows():]
            line_options = self.line_options[len(self.lines) - self.get_rows():]
            return lines, line_options

    def output_normal_data(self, c, insert = False):
        if c == '\x1b':
            logging.getLogger('term_gui').error('normal data has escape char')
            sys.exit(1)

        self.save_buffer(c, insert)

    def output_status_line_data(self, c):
        if c == '\x1b':
            logging.getLogger('term_gui').error('status line data has escape char')
            sys.exit(1)
        pass

    def get_cursor(self):
        if len(self.lines) <= self.get_rows():
            return (self.col, self.row)
        else:
            return (self.col, self.row - len(self.lines) + self.get_rows())

    def set_cursor(self, col, row):
        self.col = col
        if len(self.lines) <= self.get_rows():
            self.row = row
        else:
            self.row = row + len(self.lines) - self.get_rows()

        logging.getLogger('term_gui').debug('termianl cursor:{}, {}'.format(self.col, self.row));

    def cursor_right(self, context):
        if self.col < self.get_cols() - 1:
            self.col += 1

    def cursor_left(self, context):
        logging.getLogger('term_gui').debug('cursor left:{}, {}'.format(self.col, self.row));
        if self.col > 0:
            self.col -= 1

    def cursor_down(self, context):
        self.parm_down_cursor(context)

    def cursor_up(self, context):
        self.parm_up_cursor(context)

    def carriage_return(self, context):
        self.col = 0

    def set_foreground(self, light, color_idx):
        self.set_attributes(1 if light else 0, color_idx, -2)

    def set_background(self, light, color_idx):
        self.set_attributes(1 if light else 0, -2, color_idx)

    def origin_pair(self):
        self.set_attributes(-1, -1, -1)

    def clr_eol(self, context):
        line = self.get_cur_line()
        line_option = self.get_cur_line_option()

        begin = self.col
        if line[begin] == '\000':
            begin -= 1

        for i in range(begin, len(line)):
            line[i] = ' '

        for i in range(begin, len(line_option)):
            line_option[i] = TextAttribute(None, None, None)

    def delete_chars(self, count):
        line = self.get_cur_line()
        begin = self.col
        line_option = self.get_cur_line_option()

        if line[begin] == '\000':
            begin -= 1

        for i in range(begin, len(line)):
            if i + count < len(line):
                line[i] = line[i + count]
            else:
                line[i] = ' '

        for i in range(begin, len(line_option)):
            if i + count < len(line_option):
                line_option[i] = line_option[i + count]
            else:
                line_option[i] = TextAttribute(None, None, None)

    def refresh_display(self):
        lines, line_options = self.get_text()

        self.term_widget.lines = lines
        self.term_widget.line_options = line_options
        self.term_widget.term_cursor = self.get_cursor()
        self.term_widget.cursor_visible = self.view_history_begin is None
        self.term_widget.refresh()
        self.term_widget.focus = True

    def on_data(self, data):
        Terminal.on_data(self, data)

        self.refresh_display()

    def meta_on(self, context):
        logging.getLogger('term_gui').debug('meta_on')

    def get_color(self, mode, idx):
        if mode < 0:
            color_set = 0
        else:
            color_set = mode & 1

        if self.bold_mode:
            color_set = 1

        if idx < 8:
            return self.cfg.get_color(color_set * 8 + idx)
        elif idx < 16:
            return self.cfg.get_color(idx)
        elif idx < 256:
            return self.cfg.get_color(idx)
        else:
            logging.getLogger('term_gui').error('not implemented color:{} mode={}'.format(idx, mode))
            sys.exit(1)

    def set_attributes(self, mode, f_color_idx, b_color_idx):
        fore_color = None
        back_color = None

        if f_color_idx >= 0:
            logging.getLogger('term_gui').debug('set fore color:{} {} {}'.format(f_color_idx, ' at ', self.get_cursor()))
            fore_color = self.get_color(mode, f_color_idx)
        elif f_color_idx == -1:
            #reset fore color
            logging.getLogger('term_gui').debug('reset fore color:{} {} {}'.format(f_color_idx, ' at ', self.get_cursor()))
            fore_color = None
        else:
            #continue
            fore_color = []

        if b_color_idx >= 0:
            logging.getLogger('term_gui').debug('set back color:{} {} {}'.format(b_color_idx, ' at ', self.get_cursor()))
            back_color = self.get_color(mode, b_color_idx)
        elif b_color_idx == -1:
            #reset back color
            logging.getLogger('term_gui').debug('reset back color:{} {} {}'.format(b_color_idx, ' at ', self.get_cursor()))
            back_color = None
        else:
            back_color = []

        self.save_line_option(TextAttribute(fore_color, back_color, None))

    def get_line_option(self, row):
        reserve(self.line_options, row + 1, [])

        return self.line_options[row]

    def get_cur_line_option(self):
        return self.get_line_option(self.row)

    def get_option_at(self, row, col):
        line_option = self.get_line_option(row)
        reserve(line_option, col + 1, self.cur_line_option)

        return line_option[col]

    def get_cur_option(self):
        return self.get_option_at(self.row, self.col)

    def save_line_option(self, option):
        if self.cur_line_option is None:
            self.cur_line_option = option
        else:
            cur_option = self.cur_line_option
            f_color = option.f_color if option.f_color != [] else cur_option.f_color
            b_color = option.b_color if option.b_color != [] else cur_option.b_color
            if option.mode is None:
                mode = cur_option.mode
            elif option.mode == 0 or cur_option.mode is None:
                mode = option.mode
            else:
                mode = cur_option.mode | option.mode

            self.cur_line_option = TextAttribute(f_color, b_color, mode)
            logging.getLogger('term_gui').debug('set line option:{} {} {}'.format(f_color, b_color, mode))

    def cursor_address(self, context):
        logging.getLogger('term_gui').debug('cursor address:{}'.format(context.params))
        self.set_cursor(context.params[1], context.params[0])

    def cursor_home(self, context):
        self.set_cursor(0, 0)

    def clr_eos(self, context):
        self.get_cur_line()
        self.get_cur_line_option()

        self.clr_eol(context)

        for row in range(self.row + 1, len(self.lines)):
            line = self.get_line(row)
            line_option = self.get_line_option(row)

            for i in range(len(line)):
                line[i] = ' '

            for i in range(len(line_option)):
                line_option[i] = TextAttribute(None, None, None)

    def parm_right_cursor(self, context):
        self.col += context.params[0]

    def client_report_version(self, context):
        self.session.send('\033[>0;136;0c')

    def user7(self, context):
        if (context.params[0] == 6):
            col, row = self.get_cursor()
            self.session.send(''.join(['\x1B[', str(row + 1), ';', str(col + 1), 'R']))
        elif context.params[0] == 5:
            self.session.send('\033[0n')

    def tab(self, context):
        col = self.col / self.session.get_tab_width()
        col = (col + 1) * self.session.get_tab_width();

        if col >= self.get_cols():
            col = self.get_cols() - 1

        self.col = col

    def row_address(self, context):
        self.set_cursor(self.col, context.params[0])

    def delete_line(self, context):
        self.parm_delete_line(context)

    def parm_delete_line(self, context):
        begin, end = self.get_scroll_region()
        logging.getLogger('term_gui').debug('delete line:{} begin={} end={}'.format(context.params, begin, end))

        c_to_delete = context.params[0] if len(context.params) > 0 else 1

        for i in range(c_to_delete):
            if self.row <= end:
                self.lines = self.lines[:self.row] + self.lines[self.row + 1: end + 1] + [self.create_new_line()] +self.lines[end + 1:]

            if self.row <= end:
                self.line_options = self.line_options[:self.row] + self.line_options[self.row + 1: end + 1] + [self.create_new_line_option()] + self.line_options[end + 1:]

    def get_scroll_region(self):
        if self.scroll_region:
            return self.scroll_region

        self.set_scroll_region(0, self.get_rows() - 1)

        return self.scroll_region

    def set_scroll_region(self, begin, end):
        if len(self.lines) > self.get_rows():
            begin = begin + len(self.lines) - self.get_rows()
            end = end + len(self.lines) - self.get_rows()

        self.get_line(end)
        self.get_line(begin)

        self.scroll_region = (begin, end)

    def change_scroll_region(self, context):
        logging.getLogger('term_gui').debug('change scroll region:{} rows={}'.format(context.params, self.get_rows()))
        self.set_scroll_region(context.params[0], context.params[1])

    def insert_line(self, context):
        self.parm_insert_line(context)

    def parm_insert_line(self, context):
        begin, end = self.get_scroll_region()
        logging.getLogger('term_gui').debug('insert line:{} begin={} end={}'.format(context.params, begin, end))

        c_to_insert = context.params[0] if len(context.params) > 0 else 1

        for i in range(c_to_insert):
            if self.row <= end:
                self.lines = self.lines[:self.row] + [self.create_new_line()] + self.lines[self.row: end] +self.lines[end + 1:]

            if self.row <= end:
                self.line_options = self.line_options[:self.row] + [self.create_new_line_option()] + self.line_options[self.row: end] + self.line_options[end + 1:]

    def request_background_color(self, context):
        rbg_response = '\033]11;rgb:%04x/%04x/%04x/%04x\007' % (self.cfg.default_background_color[0], self.cfg.default_background_color[1], self.cfg.default_background_color[2], self.cfg.default_background_color[3])

        logging.getLogger('term_gui').debug("response background color request:{}".format(rbg_response.replace('\033', '\\E')))
        self.session.send(rbg_response)

    def user9(self, context):
        logging.getLogger('term_gui').debug('response terminal type:{} {}'.format(context.params, self.cap.cmds['user8'].cap_value))
        self.session.send(self.cap.cmds['user8'].cap_value)

    def enter_reverse_mode(self, context):
        self.set_mode(TextMode.REVERSE)

    def exit_standout_mode(self, context):
        self.set_mode(TextMode.STDOUT)

    def set_mode(self, mode):
        self.save_line_option(TextAttribute([], [], mode))

    def enter_ca_mode(self, context):
        self.saved_lines, self.saved_line_options, self.saved_col, self.saved_row, self.saved_bold_mode = self.lines, self.line_options, self.col, self.row, self.bold_mode
        self.lines, self.line_options, self.col, self.row, self.bold_mode = [], [], 0, 0, False

    def exit_ca_mode(self, context):
        self.lines, self.line_options, self.col, self.row, self.bold_mode = \
            self.saved_lines, self.saved_line_options, self.saved_col, self.saved_row, self.saved_bold_mode

    def key_shome(self, context):
        self.set_cursor(1, 0)

    def enter_bold_mode(self, context):
        self.bold_mode = True

    def keypad_xmit(self, context):
        logging.getLogger('term_gui').debug('keypad transmit mode')
        self.keypad_transmit_mode = True
    def keypad_local(self, context):
        logging.getLogger('term_gui').debug('keypad local mode')
        self.keypad_transmit_mode = False

    def cursor_invisible(self, context):
        self.term_widget.cursor_visible = False

    def cursor_normal(self, context):
        self.term_widget.cursor_visible = True

    def cursor_visible(self, context):
        self.cursor_normal(context)

    def parm_down_cursor(self, context):
        begin, end = self.get_scroll_region()

        count = context.params[0] if context and context.params and len(context.params) > 0 else 1

        logging.getLogger('term_gui').debug('before parm down cursor:{} {} {} {} {}'.format(begin, end, self.row, count, len(self.lines)))
        for i in range(count):
            self.get_cur_line()
            self.get_cur_line_option()

            if self.row == end:
                if begin == 0:
                    self.history_lines.append(self.lines[begin])
                    self.history_line_options.append(self.line_options[begin])
                self.lines = self.lines[:begin] + self.lines[begin + 1: end + 1] + [self.create_new_line()] + self.lines[end + 1:]
                self.line_options = self.line_options[:begin] + self.line_options[begin + 1: end + 1] + [self.create_new_line_option()] + self.line_options[end + 1:]
            else:
                self.row += 1

            self.get_cur_line()
            self.get_cur_line_option()
        logging.getLogger('term_gui').debug('after parm down cursor:{} {} {} {} {}'.format(begin, end, self.row, count, len(self.lines)))

    def exit_alt_charset_mode(self, context):
        self.exit_standout_mode(context)

    def enable_mode(self, context):
        logging.getLogger('term_gui').debug('enable mode:{}'.format(context.params))

        mode = context.params[0]

        if mode == 25:
            self.cursor_normal(context)

    def disable_mode(self, context):
        logging.getLogger('term_gui').debug('disable mode:{}'.format(context.params))

        mode = context.params[0]

        if mode == 25:
            self.cursor_invisible(context)

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
            self.view_history(key == 'pageup')
            handled = True
            view_history_key = True

        if (not view_history_key and
            not ((key == 'shift' or key == 'shift_L' or key == 'shift_R') and len(modifiers) == 0)):
            self.view_history_begin = None

        return handled

    def paste_data(self):
        logging.getLogger('term_gui').debug('paste data by default doing nothing')
        pass

    def has_selection(self):
        s_from, s_to = self.term_widget.get_selection()

        return not (s_from == s_to)

    def get_selection_text(self):
        lines, line_options = self.get_text()

        s_from, s_to = self.term_widget.get_selection()

        if s_from == s_to:
            return ''

        s_f_col, s_f_row = s_from
        s_t_col, s_t_row = s_to

        texts = []

        if s_f_row == s_t_row:
            line = lines[s_f_row]
            if not line:
                return ''

            if s_f_col >= len(line):
                return ''

            if s_t_col > len(line):
                s_t_col = len(line)

            return ''.join(line[s_f_col:s_t_col]).replace('\000', '')

        for line_num, line in enumerate(lines[s_f_row:s_t_row + 1], start=s_f_row):
            if not line:
                continue
            if line_num == s_f_row:
                if s_f_col < len(line):
                    texts.append(''.join(line[s_f_col:]))
            elif line_num == s_t_row:
                if s_t_col <= len(line):
                    texts.append(''.join(line[:s_t_col]))
            else:
                texts.append(''.join(line))

        d = '\r\n'

        if 'carriage_return' in self.cap.cmds:
            d = self.cap.cmds['carriage_return'].cap_value

        data = d.join(texts).replace('\000', '')

        return data

    def copy_data(self):
        logging.getLogger('term_gui').debug('copy data by default doing nothing')
        pass

    def column_address(self, context):
        col, row = self.get_cursor()
        self.set_cursor(context.params[0], row)

    def parm_up_cursor(self, context):
        begin, end = self.get_scroll_region()

        count = context.params[0] if context and context.params and len(context.params) > 0 else 1

        logging.getLogger('term_gui').debug('before parm up cursor:{} {} {} {} {}'.format(begin, end, self.row, count, len(self.lines)))
        for i in range(count):
            self.get_cur_line()
            self.get_cur_line_option()

            if self.row == begin:
                self.lines = self.lines[:begin] + [self.create_new_line()] + self.lines[begin: end] + self.lines[end + 1:]
                self.line_options = self.line_options[:begin] + [self.create_new_line_option()] + self.line_options[begin: end] + self.line_options[end + 1:]
            else:
                self.row -= 1

            self.get_cur_line()
            self.get_cur_line_option()
        logging.getLogger('term_gui').debug('after parm up cursor:{} {} {} {} {}'.format(begin, end, self.row, count, len(self.lines)))

    def view_history(self, pageup):
        lines, line_options = self.get_history_text()
        logging.getLogger('term_gui').debug('view history:pageup={}, lines={}, rows={}, view_history_begin={}'.format(pageup, len(lines), self.get_rows(), self.view_history_begin))

        if len(lines) <=  self.get_rows():
            return

        if self.view_history_begin is not None:
            self.view_history_begin -= self.get_rows() if pageup else self.get_rows() * -1
        elif pageup:
            self.view_history_begin = len(lines) - 2 * self.get_rows()
        else:
            return

        if self.view_history_begin < 0:
            self.view_history_begin = 0
        if self.view_history_begin > len(lines):
            self.view_history_begin = len(lines) - self.get_rows()

        self.refresh_display()

    def prompt_login(self, t, username):
        logging.getLogger('term_gui').warn('sub class must implement prompt login')
        pass

    def prompt_password(self, action):
        logging.getLogger('term_gui').warn('sub class must implement prompt password')
        pass

    def create_new_line(self):
        return []

    def create_new_line_option(self):
        return []

    def paste_data(self):
        data = ''
        if self.has_selection():
            data = self.get_selection_text()
            self.term_widget.cancel_selection()

        if len(data) == 0:
            data = self.term_widget.paste_from_clipboard()
        else:
            self.term_widget.copy_to_clipboard(data)

        if len(data) > 0:
            self.session.send(data)

    def copy_data(self):
        data = self.get_selection_text()

        if len(data) == 0:
            return

        self.term_widget.copy_to_clipboard(data)

        self.term_widget.cancel_selection()
