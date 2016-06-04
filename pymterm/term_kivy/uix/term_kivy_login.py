import os

from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.lang import Builder
from kivy.uix.popup import Popup

Builder.load_file(os.path.join(os.path.dirname(__file__), 'term_kivy_login.kv'))

class Login(Screen):
    def do_login(self, loginText, passwordText):
        pass

    def resetForm(self):
        self.ids['login'].text = ""
        self.ids['password'].text = ""

def prompt_login(username):
    popup = Popup(title='',
        content=Login(),
        size_hint=(.8, .5))

    popup.open()
