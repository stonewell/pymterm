import logging

from term import reserve
from term import Line, Cell

LOGGER = logging.getLogger('screen_buffer')

class ScreenBuffer(object):
    def __init__(self, max_lines = 1000):
        super(ScreenBuffer, self).__init__()

        self._max_lines = max_lines
        self._lines = []
        self._scrolling_region = None
        self._row_count = 0
        self._col_count = 0

        self._line_index_fix_before_scrolling_region = 0
        self._line_index_scrolling_region = 0
        self._line_index_fix_after_scrolling_region = 0

        self._viewing_history = False
        self._line_index_view_history = 0

        self._selected_lines = []

    def resize_buffer(self, row_count, col_count):
        self._row_count, self._col_count = row_count, col_count
        self._update_buffer_data()

    def get_scrolling_region(self):
        return self._scrolling_region if self._scrolling_region else (0, self._row_count - 1)

    def set_scrolling_region(self, scrolling_region):
        #reset old scrolling region
        if self._scrolling_region:
            begin, end = self._scrolling_region

            #clean up saved scroll buffer
            del self._lines[self._line_index_fix_before_scrolling_region + begin:self._line_index_scrolling_region]
            del self._lines[self._line_index_scrolling_region + end - begin + 1:self._line_index_fix_after_scrolling_region]

            self._line_index_fix_after_scrolling_region = \
              self._line_index_fix_before_scrolling_region + self._row_count

        self._scrolling_region = scrolling_region

        if self._scrolling_region == (0, self._row_count - 1):
            #reset
            self._scrolling_region = None

        if self._scrolling_region:
            begin, end = self._scrolling_region

            self._line_index_scrolling_region = \
              self._line_index_fix_before_scrolling_region + begin
            self._line_index_fix_after_scrolling_region = \
              self._line_index_fix_before_scrolling_region + end + 1

        self._update_buffer_data()

    def scroll_up(self, count = 1):
        for i in range(count):
            if self._scrolling_region:
                begin, end = self._scrolling_region

                if (self._line_index_scrolling_region + end - begin + 1 <
                    self._line_index_fix_after_scrolling_region):
                    #there is line can scroll up
                    self._line_index_scrolling_region += 1
                else:
                    #there is no line can scroll up
                    #add new line at scrolling region end
                    self._lines.insert(self._line_index_scrolling_region + end - begin + 1,
                                           Line())
                    self._line_index_fix_after_scrolling_region += 1
                    self._line_index_scrolling_region += 1
            else:
                self._line_index_fix_before_scrolling_region += 1

        self._update_buffer_data()

    def scroll_down(self, count = 1):
        for i in range(count):
            if self._scrolling_region:
                begin, end = self._scrolling_region

                if (self._line_index_scrolling_region >
                    self._line_index_fix_before_scrolling_region + begin):
                    #there is line can scroll down
                    self._line_index_scrolling_region -= 1
                else:
                    #there is no line can scroll down
                    #add new line at scrolling region begin
                    self._lines.insert(self._line_index_scrolling_region,
                                           Line())
                    self._line_index_fix_after_scrolling_region += 1
            else:
                if self._line_index_fix_before_scrolling_region > 0:
                    self._line_index_fix_before_scrolling_region -= 1
                else:
                    self._lines.insert(0, Line())
                    self._line_index_fix_after_scrolling_region += 1

        self._update_buffer_data()

    def _update_buffer_data(self):
        #make sure all line existing
        min_buffer_size = self._line_index_fix_before_scrolling_region + self._row_count

        if self._scrolling_region:
            begin, end = self._scrolling_region
            min_buffer_size = self._line_index_fix_after_scrolling_region + self._row_count - end - 1

        reserve(self._lines, min_buffer_size, Line())

        #fix the buffer to max size
        if len(self._lines) > self._max_lines:
            delta = len(self._lines) - self._max_lines

            for i in range(delta):
                #remove lines before fixed line first
                if self._line_index_fix_before_scrolling_region > 0:
                    del self._lines[0]
                    self._line_index_fix_before_scrolling_region -= 1
                    self._line_index_fix_after_scrolling_region -= 1
                    self._line_index_scrolling_region -= 1
                else:
                    if self._scrolling_region:
                        begin, end = self._scrolling_region
                        #remove lines between fixed lines and scrolling region
                        if (self._line_index_fix_before_scrolling_region + begin <
                            self._line_index_scrolling_region):
                            del self._lines[self._line_index_fix_before_scrolling_region + begin]
                            self._line_index_fix_after_scrolling_region -= 1
                            self._line_index_scrolling_region -= 1
                        elif (self._line_index_scrolling_region + end - begin + 1 <
                                  self._line_index_fix_after_scrolling_region):
                            #remove lines between scrolling region and fixed lines
                            del self._lines[self._line_index_scrolling_region + end - begin + 1]
                            self._line_index_fix_after_scrolling_region -= 1
                        elif (self._line_index_fix_after_scrolling_region + self._row_count - end - 1
                                  < len(self._lines)):
                            #remove lines after fixed lines
                            del self._lines[self._line_index_fix_after_scrolling_region + self._row_count - end - 1]
                    elif  (self._line_index_fix_before_scrolling_region + self._row_count < len(self._lines)):
                        #remove lines after fixed lines
                        del self._lines[self._line_index_fix_before_scrolling_region + self._row_count]

    def get_line(self, row):
        lines = self.get_visible_lines()

        if row >= len(lines):
            LOGGER.error('get line out of range:{}, {}'.format(row, len(lines)))
        return lines[row]

    def get_visible_lines(self):
        self._update_buffer_data()

        if self._viewing_history:
            return self._lines[self._line_index_view_history : self._line_index_view_history + self._row_count]

        if self._scrolling_region:
            begin, end = self._scrolling_region

            return self._lines[self._line_index_fix_before_scrolling_region : self._line_index_fix_before_scrolling_region + begin] \
              + self._lines[self._line_index_scrolling_region : self._line_index_scrolling_region + end - begin + 1] \
              + self._lines[self._line_index_fix_after_scrolling_region : self._line_index_fix_after_scrolling_region + self._row_count - end - 1]
        else:
            return self._lines[self._line_index_fix_before_scrolling_region : self._line_index_fix_before_scrolling_region + self._row_count]

    def delete_lines(self, start, count):
        if start < 0 or start >= self._row_count:
            LOGGER.warning('delete lines, start:{} out of range:({}, {})'.format(start, 0, self._row_count))
            return

        self._update_buffer_data()

        begin = self._line_index_fix_before_scrolling_region
        end = self._line_index_fix_before_scrolling_region + self._row_count

        start_row = self._line_index_fix_before_scrolling_region + start

        if self._scrolling_region:
            begin, end = self._scrolling_region

            if start < begin or start > end:
                LOGGER.warning('delete lines, start:{} out of range:({}, {})'.format(start, begin, end))
                return

            begin = self._line_index_scrolling_region
            end += self._line_index_scrolling_region - begin
            end += 1
            start_row = self._line_index_scrolling_region
            start_row += start - self._scrolling_region[0]

        for i in range(count):
            self._lines.insert(end, Line())
            del self._lines[start_row]

    def insert_lines(self, start, count):
        if start < 0 or start >= self._row_count:
            LOGGER.warning('insert lines, start:{} out of range:({}, {})'.format(start, 0, self._row_count))
            return

        self._update_buffer_data()

        begin = self._line_index_fix_before_scrolling_region
        end = self._line_index_fix_before_scrolling_region + self._row_count - 1

        start_row = self._line_index_fix_before_scrolling_region + start

        if self._scrolling_region:
            begin, end = self._scrolling_region

            if start < begin or start > end:
                LOGGER.warning('insert lines, start:{} out of range:({}, {})'.format(start, begin, end))
                return

            begin = self._line_index_scrolling_region
            end += self._line_index_scrolling_region - begin
            start_row = self._line_index_scrolling_region
            start_row += start - self._scrolling_region[0]

        for i in range(count):
            del self._lines[end]
            self._lines.insert(start_row, Line())

    def view_history(self, view_history):
        self._viewing_history = view_history

        if view_history:
            if self._scrolling_region:
                begin, end = self._scrolling_region
                self._line_index_view_history = self._line_index_scrolling_region - begin
            else:
                self._line_index_view_history = self._line_index_fix_before_scrolling_region

    def is_view_history(self):
        return self._viewing_history

    def view_history_pageup(self):
        self._view_history_update(-1 * self._row_count)

    def view_history_pagedown(self):
        self._view_history_update(self._row_count)

    def view_history_lineup(self):
        self._view_history_update(-1)

    def view_history_linedown(self):
        self._view_history_update(1)

    def _view_history_update(self, delta):
        self._line_index_view_history += delta

        if self._line_index_view_history < 0:
            self._line_index_view_history = 0

        if self._line_index_view_history > len(self._lines) - self._row_count:
            self._line_index_view_history = len(self._lines) - self._row_count

    def set_selection(self, s_from, s_to):
        self.clear_selection()

        if s_from == s_to:
            return

        s_f_col, s_f_row = s_from
        s_t_col, s_t_row = s_to

        lines = self.get_visible_lines()

        for i in range(s_f_row, s_t_row + 1):
            line = lines[i]
            line.select_cells(s_f_col if i == s_f_row else 0,
                            s_t_col if i == s_t_row else self._col_count)
            self._selected_lines.append(line)

    def clear_selection(self):
        for line in self._selected_lines:
            line.clear_selection()

        self._selected_lines = []

    def get_selection_text(self):
        return self._selected_lines

    def has_selection(self):
        return len(self._selected_lines) > 0
