import logging

class TerminalWidget(object):
    def __init__(self, **kwargs):
        self.visible_rows = 25
        self.visible_cols = 80
        self.lines = []
        self.line_options = []
        self.cursor = (0, 0)
        self.cursor_visible = True
        self._selection_from = self._selection_to = self.cursor
        self._selection = False
        
    def refresh(self):
        logging.getLogger('term_widget').debug('default refresh do nothing')
        pass

    def norm_text(self, text):
        text = text.replace('\t', ' ' * self.tab_width)
        text = text.replace('\000', '')

        return text

    def get_selection(self):
        def compare_cursor(a, b):
            a_col, a_row = a
            b_col, b_row = b

            if a == b:
                return False

            if a_row > b_row:
                return True

            if a_row < b_row:
                return False

            return a_col > b_col
        
        a, b = self._selection_from, self._selection_to
        if compare_cursor(a, b):
            a, b = b, a
        return (a, b)
