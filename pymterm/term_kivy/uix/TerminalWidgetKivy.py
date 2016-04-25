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
