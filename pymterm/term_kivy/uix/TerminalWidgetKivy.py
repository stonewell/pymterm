# -*- encoding: utf-8 -*-

import re
import sys
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
from kivy.utils import get_hex_from_color

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

        lines = self.lines[:]
        line_options = self.line_options[:]
        
        self._create_line_labels(len(lines))
        
        self.canvas.clear()

        dy = self.line_height + self.line_spacing
        y = self.height
        x = 0
        
        for i in range(len(lines)):
            x = 0
            label = self._line_labels[i]
            line = lines[i]
            line_option = line_options[i]

            col = 0
            last_col = 0
            text = ''
            for col in range(len(line_option)):
                if line_option[col] is None:
                    continue

                if last_col < col:
                    text += ''.join(line[last_col:col])
                    text += '[/color]' if text.find('[color=') == 0 else ''

                    self.add_text(text, x, y - (i + 1) * dy)
                    x += self._get_text_width(''.join(line[last_col:col]))
                    text = ''
                    
                last_col = col
                text = ''.join(['[color=', get_hex_from_color(line_option[col][0]), ']'])

            if last_col < len(line):
                text += ''.join(line[last_col:])
                text += '[/color]' if text.find('[color=') == 0 else ''

                self.add_text(text, x, y - (i + 1) * dy)
                
    def add_text(self, text, x, y):
        if not text or len(text) == 0:
            return

        label = self._create_line_label()
        text = text.replace('\t', ' ' * self.tab_width)
        label.text = text
        label.refresh()

        if label.texture:
            label.texture.bind()

        r = Rectangle(size=label.texture.size, pos=(x, y))
        r.texture = label.texture
        self.canvas.add(r)

    def _get_text_width(self, text):
        txt = text.replace('\t', ' ' * self.tab_width)
        
        return self._label.get_extents(txt)[0]

    def refresh(self):
        self._trigger_texture()
        
    #
    # Properties
    #

    lines = ListProperty([])
    line_options = ListProperty([])
    cursor = ListProperty([0,0])
    font_name = StringProperty('Roboto')
    font_size = NumericProperty('15sp')
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
                    