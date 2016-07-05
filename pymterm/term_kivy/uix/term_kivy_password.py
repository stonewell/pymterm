import os
from os.path import sep, expanduser, isdir, dirname

from kivy.lang import Builder
from kivy.properties import StringProperty, OptionProperty, \
    NumericProperty, BooleanProperty, ReferenceListProperty, \
    ListProperty, ObjectProperty, DictProperty
from kivy.uix.filechooser import FileChooser, FileChooserIconLayout, FileChooserListLayout
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition

import cross_platform


Builder.load_file(os.path.join(os.path.dirname(__file__), 'term_kivy_password.kv'))

class PasswordScreen(Screen):
    cancel = BooleanProperty(False)
    
    def do_cancel(self):
        self.cancel = True
        self.popup.dismiss()

        if self.action.next_action:
            self.action.next_action.execute()

    def do_action(self, p):
        self.cancel = False
        self.action.password = p
        self.popup.dismiss()
        self.action.execute()

def prompt_password(action):
    pass_screen = PasswordScreen()
    pass_screen.action = action
    
    popup = Popup(title=action.get_pass_desc(),
        content=pass_screen,
        size_hint=(None, None), size=(360, 240),
        auto_dismiss=False)

    pass_screen.popup = popup
    
    popup.open()
