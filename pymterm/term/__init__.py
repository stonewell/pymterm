#__init__.py

class TextMode:
    STDOUT = 0
    REVERSE = 1
    SELECTION = 2
    CURSOR = 3
    BOLD = 4
    DIM = 5

def reserve(l, size, default=None):
    import copy

    while size > len(l):
        if default is not None:
            if hasattr(default, '__clone__'):
                l.append(getattr(default, '__clone__')())
            else:
                l.append(copy.deepcopy(default))
        else:
            l.append(None)

DEFAULT_FG_COLOR_IDX = 256
DEFAULT_BG_COLOR_IDX = 257

class TextAttribute(object):
    def __init__(self, f_color_idx, b_color_idx, mode = {}):
        super(TextAttribute, self).__init__()

        self._f_color_idx = f_color_idx
        self._b_color_idx = b_color_idx
        self._mode = {}
        self._mode.update(mode)

        self._hashed_value = (None, None, None)
        self._hash = None
        self.get_hash_value()

    def need_calc_hash(self):
        return not (self._hashed_value[0] == self._f_color_idx and
                        self._hashed_value[1] == self._b_color_idx and
                        self._hashed_value[2] == self._mode)

    def get_hash_value(self):
        if not self.need_calc_hash():
            return self._hash

        mode = {}
        mode.update(self._mode)
        
        self._hashed_value = (self._f_color_idx, self._b_color_idx, mode)
        self._hash = str(self)

        return self._hash

    def set_mode(self, text_mode):
        self._mode[text_mode] = True

    def reset_mode(self):
        self._mode.clear()

    def get_mode(self):
        return self._mode

    def unset_mode(self, text_mode):
        self._mode[text_mode] = False

    def has_mode(self, text_mode):
        try:
            return self._mode[text_mode]
        except:
            self.unset_mode(text_mode)
            return False

    def set_fg_idx(self, fg_idx):
        self._f_color_idx = fg_idx

    def reset_fg_idx(self):
        self._f_color_idx = DEFAULT_FG_COLOR_IDX

    def set_bg_idx(self, bg_idx):
        self._b_color_idx = bg_idx

    def reset_bg_idx(self):
        self._b_color_idx = DEFAULT_BG_COLOR_IDX

    def get_fg_idx(self):
        return self._f_color_idx

    def get_bg_idx(self):
        return self._b_color_idx

    def equals(self, attr):
        return (self._f_color_idx == attr._f_color_idx and
                    self._b_color_idx == attr._b_color_idx and
                    self._mode == attr._mode)

    def to_print_str(self):
        m = 'bold:{}, dim:{}, selection:{}, reverse:{}, cursor:{}, default:{}'.format(
            self.has_mode(TextMode.BOLD),
            self.has_mode(TextMode.DIM),
            self.has_mode(TextMode.SELECTION),
            self.has_mode(TextMode.REVERSE),
            self.has_mode(TextMode.CURSOR),
            self.has_mode(TextMode.STDOUT))

        return ','.join([str(self.get_fg_idx()), str(self.get_bg_idx()), m])

    def __str__(self):
        return ''.join([str(self.get_fg_idx()), str(self.get_bg_idx()), str(self._mode)])

    def __clone__(self):
        return clone_attr(self)

def get_default_text_attribute():
    return TextAttribute(DEFAULT_FG_COLOR_IDX,
                             DEFAULT_BG_COLOR_IDX,
                             {})
def clone_attr(attr):
    mode = {}
    mode.update(attr.get_mode())
    
    return TextAttribute(attr.get_fg_idx(), attr.get_bg_idx(), mode)

class Cell(object):
    def __init__(self, c = ' ', attr = get_default_text_attribute(), wide_char = False):
        super(Cell, self).__init__()

        self._char = c
        self._attr = clone_attr(attr)
        self._is_wide_char = wide_char

        self._hashed_value = None
        self._hash = None
        self.get_hash_value()

    def __clone__(self):
        return Cell(self._char, self._attr, self._is_wide_char)

    def need_calc_hash(self):
        return (self._hashed_value != self._char) or self._attr.need_calc_hash()

    def get_hash_value(self):
        if not self.need_calc_hash():
            return self._hash

        self._hashed_value = self._char
        self._hash = '_'.join([self._char, self._attr.get_hash_value()])

        return self._hash

    def set_char(self, c):
        self._char = c

    def get_char(self):
        return self._char

    def set_attr(self, attr):
        self._attr = clone_attr(attr)
        self._hashed_value = None

    def get_attr(self):
        return self._attr

    def reset(self, attr=get_default_text_attribute()):
        self.set_char(' ')
        self.set_attr(attr)

    def copy(self, cell):
        self.set_char(cell.get_char())
        self.set_attr(cell.get_attr())

    def is_widechar(self):
        return self._is_wide_char

    def set_is_wide_char(self, wide_char):
        self._is_wide_char = wide_char

    def need_draw(self):
        return self._char != ' ' \
          or self._attr.has_mode(TextMode.CURSOR) \
          or self._attr.has_mode(TextMode.SELECTION) \
          or self._attr.get_bg_idx != DEFAULT_BG_COLOR_IDX

class Line(object):
    def __init__(self):
        super(Line, self).__init__()

        self._cells = []
        self._hash_calc_done = False
        self._hash = None

    def __clone__(self):
        l = Line()

        l._cells = [Cell(c.get_char(), c.get_attr(), c.is_widechar()) for c in self._cells]

        return l

    def c(self):
        return self.__clone__()

    def need_calc_hash(self):
        return (not self._hash_calc_done) or any([cell.need_calc_hash() for cell in self._cells])

    def get_hash_value(self):
        if not self.need_calc_hash():
            return self._hash

        self._hash_calc_done = True
        self._hash = '|'.join([cell.get_hash_value() for cell in self._cells])

        return self._hash

    def alloc_cells(self, cols, fit=False):
        reserve(self._cells, cols, Cell())

        if fit and self.cell_count() > cols:
            self._cells = self._cells[:cols]

    def insert_cell(self, col, cell):
        self._cells.insert(col, cell)

    def get_cell(self, col):
        self.alloc_cells(col + 1)
        return self._cells[col]

    def get_text(self, begin_col = 0, end_col = -1, raw = False):
        if end_col < 0 or end_col > self.cell_count():
            end_col = self.cell_count()
        if begin_col < 0:
            begin_col = 0
        if begin_col > self.cell_count():
            begin_col = self.cell_count()

        if begin_col >= end_col:
            return ''

        raw_text = ''.join([self._cells[i].get_char() for i in range(begin_col, end_col)])

        return raw_text if raw else raw_text.replace('\000', '')

    def get_cells(self):
        return self._cells

    def cell_count(self):
        return len(self._cells)

    def select_cells(self, begin_col = 0, end_col = -1):
        if end_col < 0 or end_col > self.cell_count():
            end_col = self.cell_count()
        if begin_col < 0:
            begin_col = 0
        if begin_col > self.cell_count():
            begin_col = self.cell_count()

        if begin_col >= end_col:
            return

        self.alloc_cells(end_col)
        
        for i in range(begin_col, end_col):
            self._cells[i].get_attr().set_mode(TextMode.SELECTION)

    def clear_selection(self):
        for cell in self._cells:
            cell.get_attr().unset_mode(TextMode.SELECTION)

    def get_selection_text(self):
        selected_cells = filter(lambda x: x.get_attr().has_mode(TextMode.SELECTION), self._cells)
        return map(lambda x:x.get_char(), selected_cells)
