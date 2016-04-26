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
    _font_properties = ('text', 'font_size', 'font_name', 'bold', 'italic',
                        'underline', 'strikethrough', 
                        'halign', 'valign', 'padding_left', 'padding_top',
                        'padding_right', 'padding_bottom',
                        'text_size', 'shorten', 'mipmap', 
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

    def _update_line_options(self):
        min_line_ht = self._label.get_extents('_')[1]
        self.line_height = min_line_ht
        self._label.options['color'] = [1,1,1,1]

    def _trigger_texture_update(self, name=None, source=None, value=None):
        # check if the label core class need to be switch to a new one
        if source:
            if name == 'text':
                self._label.text = value
            elif name == 'text_size':
                self._label.usersize = value
            elif name == 'font_size':
                self._label.options[name] = value
            else:
                self._label.options[name] = value
                
        self._trigger_texture()

    def texture_update(self, *largs):
        self.texture = None
        
        self._update_line_options()

        if False:
            pass
        else:
            text = self.text
            # we must strip here, otherwise, if the last line is empty,
            # markup will retain the last empty line since it only strips
            # line by line within markup
            if self.halign == 'justify' or self.strip:
                text = text.strip()
            self._label.text = ''.join(('[color=',
                                            get_hex_from_color([1,0,0,1]),
                                            ']', text, '[/color]'))
            self._label.refresh()
            # force the rendering to get the references
            if self._label.texture:
                self._label.texture.bind()
            texture = self._label.texture
            if texture is not None:
                self.texture = self._label.texture
                self.texture_size = list(self.texture.size)

            print 'texture size:', self.texture_size, self.size, texture

        self.canvas.clear()
        r = Rectangle(size=self.texture.size)
        r.texture = texture
        self.canvas.add(r)

    def _get_text_width(self, text, tab_width, _label_cached):
        txt = text.replace('\t', ' ' * tab_width)
        
        return self._label.get_extents(txt)[0]
    #
    # Properties
    #

    text = StringProperty('')
    text_size = ListProperty([None, None])
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
                    
