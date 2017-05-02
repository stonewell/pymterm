import logging


class TerminalWidget(object):
    def __init__(self, **kwargs):
        super(TerminalWidget, self).__init__()

        self.visible_rows = 24
        self.visible_cols = 80
        self.lines = []
        self.line_options = []
        self.term_cursor = (0, 0)
        self.cursor_visible = True
        self._selection_from = self._selection_to = self.term_cursor
        self._selection = False
        self._selection_finished = True

    def refresh(self):
        logging.getLogger('term_widget').debug('default refresh do nothing')
        pass

    def norm_text(self, text, removeDoubleWidthPaddingChar = True):
        text = text.replace('\t', ' ' * self.tab_width)
        text = text.replace('\000', '' if removeDoubleWidthPaddingChar else '\000')

        return text

    def cancel_selection(self):
        '''Cancel current selection (if any).
        '''
        self._selection_from = self._selection_to = (0, 0)
        self._selection = False
        self._selection_finished = True

    def compare_cursor(self, a, b):
        a_col, a_row = a
        b_col, b_row = b

        if a == b:
            return False

        if a_row > b_row:
            return True

        if a_row < b_row:
            return False

        return a_col > b_col

    def get_selection(self):
        a, b = self._selection_from, self._selection_to
        if self.compare_cursor(a, b):
            a, b = b, a
        return (a, b)

    def copy_to_clipboard(self, data):
        pass

    def paste_from_clipboard(self):
        pass
