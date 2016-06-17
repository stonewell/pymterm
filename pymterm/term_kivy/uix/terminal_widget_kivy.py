# -*- encoding: utf-8 -*-

import re
import sys
import logging

from os import environ
from weakref import ref

from kivy.animation import Animation
from kivy.base import EventLoop
from kivy.cache import Cache
from kivy.clock import Clock
from kivy.config import Config
from kivy.metrics import inch
from kivy.utils import boundary, platform
from kivy.uix.behaviors import FocusBehavior

from kivy.graphics import Color, Rectangle, PushMatrix, PopMatrix, Callback
from kivy.graphics.context_instructions import Transform
from kivy.graphics.texture import Texture

from kivy.uix.widget import Widget
from kivy.uix.bubble import Bubble
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image
from kivy.uix.label import Label

from kivy.properties import StringProperty, OptionProperty, \
    NumericProperty, BooleanProperty, ReferenceListProperty, \
    ListProperty, ObjectProperty, DictProperty

from kivy.core.text import Label as CoreLabel
from kivy.core.text.markup import MarkupLabel as CoreMarkupLabel
from kivy.utils import escape_markup

from collections import namedtuple

Cache_register = Cache.register
Cache_append = Cache.append
Cache_get = Cache.get
Cache_remove = Cache.remove
Cache_register('termwidget.label', timeout=60.)
Cache_register('termwidget.width', timeout=60.)
Cache_register('termwidget.b', timeout=60.)
Cache_register('termwidget.b_size', timeout=60.)

TextAttribute = namedtuple('TextAttributes', ['f_color', 'b_color', 'mode'])
class TextMode:
    STDOUT = 0
    REVERSE = 1 << 0

class TerminalWidgetKivy(FocusBehavior, Widget):
    _font_properties = ('lines', 'font_size', 'font_name', 'bold', 'italic',
                        'underline', 'strikethrough', 
                        'halign', 'valign', 'padding_left', 'padding_top',
                        'padding_right', 'padding_bottom',
                        'shorten', 'mipmap', 
                        'line_height', 'max_lines', 'strip',
                        'split_str', 'unicode_errors',
                        'font_hinting', 'font_kerning', 'font_blended')
        
    def __init__(self, **kwargs):
        self._trigger_texture = Clock.create_trigger(self.texture_update, -1)

        super(TerminalWidgetKivy, self).__init__(**kwargs)
        
        # bind all the property for recreating the texture
        d = TerminalWidgetKivy._font_properties
        fbind = self.fbind
        update = self._trigger_texture_update
        fbind('disabled', update, 'disabled')
        for x in d:
            fbind(x, update, x)

        self._label = None
        self._create_label()

        self.cursor = (0, 0)
        self.line_rects = {}
        self._touch_count = 0
        self.cancel_selection()
        
        # force the texture creation
        self._trigger_texture()
        
    def _create_label(self):
        # create the core label class according to markup value
        if self._label is not None:
            cls = self._label.__class__
        else:
            cls = None

        if cls is not CoreMarkupLabel:
            # markup have change, we need to change our rendering method.
            d = TerminalWidgetKivy._font_properties
            dkw = dict(list(zip(d, [getattr(self, x) for x in d])))
            self._label = CoreMarkupLabel(**dkw)

        self._update_line_options()

    def _create_line_label(self):
        d = TerminalWidgetKivy._font_properties
        dkw = dict(list(zip(d, [getattr(self, x) for x in d])))
        return CoreMarkupLabel(**dkw)
        
    def _update_line_options(self):
        min_line_ht = self._label.get_extents('_')[1]
        self.line_height = min_line_ht
        self._label.options['color'] = [1,1,1,1]

    def _trigger_texture_update(self, name=None, source=None, value=None):
        # check if the label core class need to be switch to a new one
        if source:
            if name == 'font_size':
                self._label.options[name] = value
            else:
                self._label.options[name] = value

        if name != 'lines':
            self._trigger_texture()

    def texture_update(self, *largs):
        self._update_line_options()

        lines = [line[:] for line in self.lines]
        line_options = [line_option[:] for line_option in self.line_options]
        c_col, c_row = self.cursor

        self.canvas.clear()

        dy = self.line_height + self.line_spacing
        y = self.height
        x = 0

        last_f_color = self.session.cfg.default_foreground_color
        last_b_color = self.session.cfg.default_background_color
        last_mode = 0
        
        for i in range(len(lines)):
            x = 0
            b_x = 0

            line = lines[i]
            line_option = line_options[i] if i < len(line_options) else []

            col = 0
            last_col = 0
            text = ''
            text_parts = []

            def render_text(t, xxxx):
                cur_f_color, cur_b_color = last_f_color, last_b_color
                    
                if last_mode & TextMode.REVERSE:
                    cur_f_color, cur_b_color = last_b_color, last_f_color
                        
                text = ''.join(['[color=',
                                self.get_color_hex(cur_f_color),
                                ']',
                                escape_markup(t),
                                '[/color]'])

                text_parts.append(text)

                return self.add_background(t,
                                        cur_b_color, xxxx, y - (i + 1) * dy)

            last_option = None                
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

                if (n_f_color, n_b_color, n_mode) == (last_f_color, last_b_color, last_mode):
                    continue
                
                if last_col < col:
                    if self.cursor_visible and i == c_row and last_col <= c_col and c_col < col:
                        b_x = render_text(''.join(line[last_col: c_col]), b_x)

                        tmp_l_f, last_f_color, tmp_l_b, last_b_color = \
                          last_f_color, last_b_color, last_b_color, self.session.cfg.default_cursor_color
                        b_x = render_text(''.join(line[c_col: c_col + 1]), b_x)
                        last_f_color, last_b_color = tmp_l_f, tmp_l_b
                        
                        b_x = render_text(''.join(line[c_col + 1: col]), b_x)
                    else:
                        b_x = render_text(''.join(line[last_col: col]), b_x)
                    
                last_col = col
                last_option = line_option[col]
                last_f_color, last_b_color, last_mode = n_f_color, n_b_color, n_mode

            if last_col < len(line):
                if self.cursor_visible and i == c_row and last_col <= c_col and c_col < len(line):
                    b_x = render_text(''.join(line[last_col: c_col]), b_x)

                    tmp_l_f, last_f_color, tmp_l_b, last_b_color = \
                          last_f_color, last_b_color, last_b_color, self.session.cfg.default_cursor_color
                    b_x = render_text(''.join(line[c_col: c_col + 1]), b_x)
                    last_f_color, last_b_color = tmp_l_f, tmp_l_b
                    
                    b_x = render_text(''.join(line[c_col + 1:]), b_x)
                else:
                    b_x = render_text(''.join(line[last_col:]), b_x)

            if self.cursor_visible and i == c_row and c_col >= len(line):
                tmp_l_f, last_f_color, tmp_l_b, last_b_color = \
                          last_f_color, last_b_color, last_b_color, self.session.cfg.default_cursor_color
                b_x = render_text(' ', b_x)
                last_f_color, last_b_color = tmp_l_f, tmp_l_b

            #add background to fill empty cols
            if b_x < self.width:
                tmp_b_c, last_b_color = last_b_color, self.session.cfg.default_background_color
                render_text(' ' * (self.visible_cols + 1), b_x)
                last_b_color = tmp_b_c
                                
            try:
                self.add_text(i, ''.join(text_parts), x, y - (i + 1) * dy)
            except:
                logging.exception('show text:{},x={},y={}'.format(''.join(text_parts), x, y - (i + 1) * dy))

    def get_color_hex(self, l_color):
        return '#%02x%02x%02x%02x' % (l_color[0], l_color[1], l_color[2], l_color[3])

    def add_background(self, text, color, x, y):
        if not text or len(text) == 0:
            return x

        cid = '%s\0%02x%02x%02x%02x' % (text, color[0], color[1], color[2], color[3])

        t = Cache_get('termwidget.b', cid)

        if t is not None:
            if self.session.cfg.debug_more:
                logging.getLogger('term_widget').debug('reuse the background texture, pos={}, {}, size={}'.format(x, y, t.size))
            self.canvas.add(Rectangle(texture=t, pos=(x , y), size=t.size))        
            return x + t.size[0]
        
        from kivy.graphics import Color
        from kivy.graphics.instructions import InstructionGroup
        from kivy.graphics.texture import Texture

        size = Cache_get('termwidget.b_size', text)

        if size is None:
            text = self.norm_text(text)
            size = self._label.get_extents(text)
            size = (size[0], size[1] + 1)
            Cache_append('termwidget.b_size', text, size)

        t = Texture.create(size=size)

        buf = color * size[0] * size[1]
        buf = b''.join(map(chr, buf))
        t.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')

        Cache_append('termwidget.b', cid, t)

        self.canvas.add(Rectangle(texture=t, pos=(x , y), size=size, group='background'))        
        
        return x + size[0]
    
    def add_text(self, line_num, text, x, y):
        self.line_rects[line_num] = Rectangle(size=(0,0), pos=(x, y))
        
        if not text or len(text) == 0:
            return

        label = Cache_get('termwidget.label', text)

        texture = None
        
        if label is None:
            label = self._create_line_label()
            text = self.norm_text(text)
            label.text = text#.decode('utf_8', errors='ignore')
            label.refresh()

            if label.texture:
                label.texture.bind()

            texture = label.texture

            Cache_append('termwidget.label', text, label)
            if self.session.cfg.debug_more:
                logging.getLogger('term_widget').debug('cache the foreground texture, pos={}, {}, size={}'.format(x, y, texture.size))
        else:
            texture = label.texture
            if self.session.cfg.debug_more:
                logging.getLogger('term_widget').debug('reuse the foreground texture, pos={}, {}, size={}'.format(x, y, texture.size))

        self.line_rects[line_num] = Rectangle(texture=texture, size=texture.size, pos=(x, y), group='foreground')
        self.canvas.add(self.line_rects[line_num])

    def _get_text_width(self, text):
        width = Cache_get('termwidget.width', text)

        if width is not None:
            return width
        
        txt = self.norm_text(text)
        
        width = self._label.get_extents(txt)[0]

        Cache_append('termwidget.width', text, width)

        return width
    
    def refresh(self):
        self._trigger_texture()

    def norm_text(self, text):
        text = text.replace('\t', ' ' * self.tab_width)
        text = text.replace('\000', '')

        return text
        
    def on_touch_down(self, touch):
        touch_pos = touch.pos
        
        if not self.collide_point(*touch_pos):
            return super(TerminalWidgetKivy, self).on_touch_down(touch)

        touch.grab(self)
        self._touch_count += 1

        cursor = self.get_cursor_from_xy(*touch_pos)
        if not self._selection_touch:
            self.cancel_selection()
            self._selection_touch = touch
            self._selection_from = self._selection_to = cursor
            self._update_selection()

        self.focus = True
        return super(TerminalWidgetKivy, self).on_touch_down(touch)

    def on_touch_move(self, touch):
        if touch.grab_current is not self:
            return super(TerminalWidgetKivy, self).on_touch_move(touch)

        if self._selection_touch is touch:
            self._selection_to = self.get_cursor_from_xy(touch.x, touch.y)
            self._update_selection()

        return super(TerminalWidgetKivy, self).on_touch_move(touch)

    def on_touch_up(self, touch):
        if touch.grab_current is not self:
            return super(TerminalWidgetKivy, self).on_touch_up(touch)

        touch.ungrab(self)
        self._touch_count -= 1

        if self._selection_touch is touch:
            self._selection_to = self.get_cursor_from_xy(touch.x, touch.y)
            self._update_selection(True)

        self.focus = True
        return super(TerminalWidgetKivy, self).on_touch_up(touch)
        
    def get_cursor_from_xy(self, x, y):
        '''Return the (row, col) of the cursor from an (x, y) position.
        '''
        padding_left = self.padding[0]
        padding_top = self.padding[1]
        l = self.lines
        dy = self.line_height + self.line_spacing
        cx = x - self.x
        cy = (self.top - padding_top) - y
        cy = int(boundary(round(cy / dy - 0.5), 0, len(l) - 1))
        _get_text_width = self._get_text_width
        for i in range(0, len(l[cy])):
            if _get_text_width(''.join(l[cy][:i])) + \
                  _get_text_width(l[cy][i]) * 0.6 + \
                  padding_left > cx:
                return i, cy

        return len(l[cy]), cy

    #
    # Selection control
    #
    def cancel_selection(self):
        '''Cancel current selection (if any).
        '''
        self._selection_from = self._selection_to = (0, 0)
        self._selection = False
        self._selection_finished = True
        self._selection_touch = None

    def _update_selection(self, finished=False):
        self._selection_finished = finished

        if not finished:
            self._selection = True
        else:
            self._selection = True
            self._selection_touch = None

        self._update_graphics_selection()

    def _update_graphics_selection(self):
        if not self._selection:
            return
        self.canvas.remove_group('selection')
        dy = self.line_height + self.line_spacing

        padding_top = self.padding[1]
        padding_bottom = self.padding[3]
        _top = self.top
        y = _top - padding_top
        miny = self.y + padding_bottom
        maxy = _top - padding_top
        draw_selection = self._draw_selection

        a, b = self.get_selection()
        s1c, s1r = a
        s2c, s2r = b
        s2r += 1
        # pass only the selection lines[]
        # passing all the lines can get slow when dealing with a lot of text
        y -= s1r * dy
        _lines = self.lines
        _get_text_width = self._get_text_width
        width = self.width
        padding_left = self.padding[0]
        padding_right = self.padding[2]
        x = self.x
        canvas_add = self.canvas.add
        selection_color = self.selection_color
        for line_num, value in enumerate(_lines[s1r:s2r], start=s1r):
            r = self.line_rects[line_num]
            if miny <= y <= maxy + dy:
                draw_selection(r.pos, r.size, line_num, (s1c, s1r),
                               (s2c, s2r - 1), _lines, _get_text_width,
                               width,
                               padding_left, padding_right, x,
                               canvas_add, selection_color)
            y -= dy

    def _draw_selection(self, *largs):
        pos, size, line_num, (s1c, s1r), (s2c, s2r),\
            _lines, _get_text_width, width,\
            padding_left, padding_right, x, canvas_add, selection_color = largs
        # Draw the current selection on the widget.
        if line_num < s1r or line_num > s2r or line_num >= len(_lines):
            return
        x, y = pos
        w, h = size
        x1 = x
        x2 = x + w
        if line_num == s1r:
            lines = _lines[line_num]
            if not lines:
                return
            s1c = s1c if s1c <= len(lines) else len(lines)
            x1 += _get_text_width(''.join(lines[:s1c]))
        if line_num == s2r:
            lines = _lines[line_num]
            if not lines:
                return
            s2c = s2c if s2c <= len(lines) else len(lines)
            x2 = x + _get_text_width(''.join(lines[:s2c]))
        width_minus_padding = width - (padding_right + padding_left)
        maxx = x + width_minus_padding
        if x1 > maxx:
            return
        x1 = max(x1, x)
        x2 = min(x2, x + width_minus_padding)
        canvas_add(Color(*selection_color, group='selection'))
        canvas_add(Rectangle(
            pos=(x1, pos[1]), size=(x2 - x1, size[1] + 1), group='selection'))


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
        
    #
    # Properties
    #

    selection_color = ListProperty([0.1843, 0.6549, 0.8313, .5])
    lines = ListProperty([])
    line_options = ListProperty([])
    font_name = StringProperty('NotoSans')
    font_size = NumericProperty('17.5sp')
    line_height = NumericProperty(1.0)
    line_spacing = NumericProperty(1.0)
    cursor_visible = BooleanProperty(True)
    bold = BooleanProperty(False)
    italic = BooleanProperty(False)
    underline = BooleanProperty(False)
    strikethrough = BooleanProperty(False)
    padding_left = NumericProperty(0)
    padding_top = NumericProperty(0)
    padding_right = NumericProperty(0)
    padding_bottom = NumericProperty(0)
    padding = ReferenceListProperty(padding_left, padding_top, padding_right, padding_bottom)
    halign = OptionProperty('left', options=['left', 'center', 'right',
                            'justify'])
    valign = OptionProperty('top',
                            options=['bottom', 'middle', 'center', 'top'])
    texture = ObjectProperty(None, allownone=True)
    texture_size = ListProperty([0, 0])
    mipmap = BooleanProperty(False)
    shorten = BooleanProperty(False)
    split_str = StringProperty('')
    unicode_errors = OptionProperty(
        'replace', options=('strict', 'replace', 'ignore'))
    max_lines = NumericProperty(0)
    strip = BooleanProperty(False)
    font_hinting = OptionProperty(
        'mono', options=[None, 'normal', 'light', 'mono'], allownone=True)
    font_kerning = BooleanProperty(True)
    font_blended = BooleanProperty(True)

if __name__ == '__main__':
    from kivy.app import App
    from kivy.uix.label import Label
    from kivy.clock import Clock
    from kivy.graphics import Color, Rectangle


    class TestApp(App):

        def build(self):
            label = Label(
                text='[color=#ff00ffff]a\\\\nChars [/color]b\\n[ref=myref]ref[/ref]',
                markup=True)

            def update(dt):
                print label.texture, label.texture_size
            Clock.schedule_once(update)
            return label

    TestApp().run()
