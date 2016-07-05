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


Builder.load_file(os.path.join(os.path.dirname(__file__), 'term_kivy_login.kv'))

class KeyFileChooserScreen(Screen):
    cancel = BooleanProperty(False)
    
    def do_cancel(self):
        self.cancel = True
        self.popup.dismiss()

    def do_select(self, p, f):
        self.cancel = False
        self.key_file.text = os.path.join(p, f[0])
        self.popup.dismiss()

class KeyFileChooser(FileChooser):
    pass

class Login(Screen):
    def __init__(self, session, t):
        super(Login, self).__init__()
        
        self.session = session
        self.t = t
        self.popup = None
        self.file_chooser = None
        
    def do_login(self, key_file, loginText, passwordText):
        if self.session.try_login(self.t, key_file,
                                  'RSA' if self.ids['rsa'].state == 'down' else 'DSS',
                                  loginText, passwordText):
            self.popup.dismiss()

    def resetForm(self):
        self.ids['login'].text = ""
        self.ids['password'].text = ""

    def do_key_file_select(self, old_file):
        user_path = ''
        
        if cross_platform.is_windows():
            user_path = dirname(expanduser('~')) + sep + '.ssh'
        else:
            user_path = expanduser('~') + sep + '.ssh'
            
        content = KeyFileChooserScreen()

        if os.path.exists(old_file):
            parts = os.path.split(old_file)
            content.ids['filechooser'].path = parts[0]
            content.ids['filechooser'].selection = parts[1:]
            
        elif os.path.exists(user_path):
            content.ids['filechooser'].path = user_path

        self.file_chooser = Popup(title='Select Key File',
            content=content,
            auto_dismiss=False)

        content.popup = self.file_chooser
        content.key_file = self.ids['keyfile']
        
        self.file_chooser.open()
    

def prompt_login(terminal, t, username):
    login = Login(terminal.session, t)
    login.ids['login'].text = username
    
    popup = Popup(title='Connect',
        content=login,
        size_hint=(None, None), size=(600, 480),
        auto_dismiss=False)

    login.popup = popup
    
    popup.open()
