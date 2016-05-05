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

        self._line_labels = []
        
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
            if name == 'lines':
                pass
            elif name == 'font_size':
                self._label.options[name] = value
            else:
                self._label.options[name] = value

        self._trigger_texture()

    def _create_line_labels(self, c):
        if len(self._line_labels) == c:
            return

        if len(self._line_labels) > c:
            self._line_labels = self.line_labels[0:c]
        else:
            for i in range(len(self._line_labels), c):
                self._line_labels.append(self._create_line_label())
                 
    def texture_update(self, *largs):
        self._update_line_options()

        lines = [line[:] for line in self.lines]
        line_options = [line_option[:] for line_option in self.line_options]
        
        #self._create_line_labels(len(lines))
        
        self.canvas.clear()

        dy = self.line_height + self.line_spacing
        y = self.height
        x = 0

        last_f_color = self.cfg.default_foreground_color
        last_b_color = self.cfg.default_background_color
        last_mode = 0
        
        for i in range(len(lines)):
            x = 0
            b_x = 0
            #label = self._line_labels[i]
            line = lines[i]
            line_option = line_options[i] if i < len(line_options) else []

            col = 0
            last_col = 0
            text = ''
            text_parts = []

            def render_text(t, b_x):
                cur_f_color, cur_b_color = last_f_color, last_b_color
                    
                if last_mode % TextMode.REVERSE:
                    cur_f_color, cur_b_color = last_b_color, last_f_color
                        
                text = ''.join(['[color=',
                                self.get_color_hex(cur_f_color),
                                ']',
                                escape_markup(t),
                                '[/color]'])

                text_parts.append(text)

                return self.add_background(t,
                                        cur_b_color, b_x, y - (i + 1) * dy)

            last_option = None                
            for col in range(len(line_option)):
                if line_option[col] is None:
                    continue

                if last_option == line_option[col]:
                    continue

                if last_col < col:
                    b_x = render_text(''.join(line[last_col: col]), b_x)
                    
                last_col = col
                f_color, b_color, mode = line_option[col]
                last_option = line_option[col]

                # foreground
                if f_color and len(f_color) > 0:
                    last_f_color = f_color
                elif f_color is None:
                    last_f_color = self.cfg.default_foreground_color

                # background
                if b_color and len(b_color) > 0:
                    last_b_color = b_color
                elif b_color is None:
                    last_b_color = self.cfg.default_background_color

                #mode
                if mode:
                    last_mode = mode

            if last_col < len(line):
                b_x = render_text(''.join(line[last_col:]), b_x)

            #add background to fill empty cols
            if b_x < self.width:
                render_text(' ' * self.visible_cols, b_x)
                                
            try:
                self.add_text(''.join(text_parts), x, y - (i + 1) * dy)
            except:
                logging.exception('show text:{},x={},y={}'.format(''.join(text_parts), x, y - (i + 1) * dy))

    def get_color_hex(self, l_color):
        return '#%02x%02x%02x%02x' % (l_color[0], l_color[1], l_color[2], l_color[3])

    def add_background(self, text, color, x, y):
        if not text or len(text) == 0:
            return

        cid = '%s\0%02x%02x%02x%02x' % (text, color[0], color[1], color[2], color[3])

        t = Cache_get('termwidget.b', cid)

        if t is not None:
            logging.getLogger('term_widget').debug('reuse the background texture, pos={}, {}, size={}'.format(x, y, t.size))
            self.canvas.add(Rectangle(texture=t, pos=(x , y), size=t.size))        
            return x + t.size[0]
        
        from kivy.graphics import Color
        from kivy.graphics.instructions import InstructionGroup
        from kivy.graphics.texture import Texture

        size = Cache_get('termwidget.b_size', text)

        if size is None:
            text = text.replace('\t', ' ' * self.tab_width)
            size = self._label.get_extents(text)
            size = (size[0], size[1] + 1)
            Cache_append('termwidget.b_size', text, size)

        t = Texture.create(size=size)

        buf = color * size[0] * size[1]
        buf = b''.join(map(chr, buf))
        t.blit_buffer(buf, colorfmt='rgba', bufferfmt='ubyte')

        Cache_append('termwidget.b', cid, t)
        
        self.canvas.add(Rectangle(texture=t, pos=(x , y), size=size))        
        
        return x + size[0]
    
    def add_text(self, text, x, y):
        if not text or len(text) == 0:
            return

        label = Cache_get('termwidget.label', text)

        texture = None
        
        if label is None:
            label = self._create_line_label()
            text = text.replace('\t', ' ' * self.tab_width)
            label.text = text.decode('utf_8')
            label.refresh()

            if label.texture:
                label.texture.bind()

            texture = label.texture

            Cache_append('termwidget.label', text, label)
        else:
            texture = label.texture
            
        self.canvas.add(Rectangle(texture=texture, size=texture.size, pos=(x, y)))

    def _get_text_width(self, text):
        width = Cache_get('termwidget.width', text)

        if width is not None:
            return width
        
        txt = text.replace('\t', ' ' * self.tab_width)
        
        width = self._label.get_extents(txt)[0]

        Cache_append('termwidget.width', text, width)

        return width
    
    def refresh(self):
        self._trigger_texture()
        
    #
    # Properties
    #

    lines = ListProperty([])
    line_options = ListProperty([])
    font_name = StringProperty('WenQuanYi')
    font_size = NumericProperty('17.5sp')
    line_height = NumericProperty(1.0)
    line_spacing = NumericProperty(1.0)
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
                    
