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

from kivy.core.text import Label
from kivy.graphics import Color, Rectangle, PushMatrix, PopMatrix, Callback
from kivy.graphics.context_instructions import Transform
from kivy.graphics.texture import Texture

from kivy.uix.widget import Widget
from kivy.uix.bubble import Bubble
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.image import Image

from kivy.properties import StringProperty, NumericProperty, \
    BooleanProperty, AliasProperty, \
    ListProperty, ObjectProperty, VariableListProperty

Cache_register = Cache.register
Cache_append = Cache.append
Cache_get = Cache.get
Cache_remove = Cache.remove
Cache_register('textinput.label', timeout=60.)
Cache_register('textinput.width', timeout=60.)

FL_IS_LINEBREAK = 0x01
FL_IS_WORDBREAK = 0x02
FL_IS_NEWLINE = FL_IS_LINEBREAK | FL_IS_WORDBREAK

# late binding
Clipboard = None
CutBuffer = None
MarkupLabel = None
_platform = platform

# for reloading, we need to keep a list of textinput to retrigger the rendering
_textinput_list = []

# cache the result
_is_osx = sys.platform == 'darwin'

# When we are generating documentation, Config doesn't exist
_is_desktop = False
if Config:
    _is_desktop = Config.getboolean('kivy', 'desktop')

class TerminalWidgetKivy(FocusBehavior, Widget):
    def __init__(self, **kwargs):
        self.is_focusable = kwargs.get('is_focusable', True)
        self._cursor = [0, 0]
        self._selection = False
        self._selection_finished = True
        self._selection_touch = None
        self.selection_text = u''
        self._selection_from = None
        self._selection_to = None
        self._selection_callback = None
        self._handle_left = None
        self._handle_right = None
        self._handle_middle = None
        self._bubble = None
        self._lines_flags = []
        self._lines_labels = []
        self._lines_rects = []
        self._hint_text_flags = []
        self._hint_text_labels = []
        self._hint_text_rects = []
        self._label_cached = None
        self._line_options = None
        self._keyboard_mode = Config.get('kivy', 'keyboard_mode')
        self._command_mode = False
        self._command = ''

        super(TerminalWidgetKivy, self).__init__(**kwargs)

        fbind = self.fbind
        refresh_line_options = self._trigger_refresh_line_options
        update_text_options = self._update_text_options

        fbind('font_size', refresh_line_options)
        fbind('font_name', refresh_line_options)
        fbind('padding', update_text_options)
        fbind('tab_width', update_text_options)
        fbind('font_size', update_text_options)
        fbind('font_name', update_text_options)
        fbind('size', update_text_options)
        fbind('password', update_text_options)
        fbind('password_mask', update_text_options)

        fbind('pos', self._trigger_update_graphics)
        fbind('readonly', handle_readonly)
        fbind('focus', self._on_textinput_focused)
        
        handles = self._trigger_position_handles = Clock.create_trigger(
            self._position_handles)
        self._trigger_show_handles = Clock.create_trigger(
            self._show_handles, .05)
        self._trigger_cursor_reset = Clock.create_trigger(
            self._reset_cursor_blink)
        self._trigger_update_cutbuffer = Clock.create_trigger(
            self._update_cutbuffer)
        refresh_line_options()
        self._trigger_refresh_text()

        fbind('pos', handles)
        fbind('size', handles)

        # when the gl context is reloaded, trigger the text rendering again.
        _textinput_list.append(ref(self, TextInput._reload_remove_observer))

        if platform == 'linux':
            self._ensure_clipboard()
