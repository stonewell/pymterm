import logging
import os
import select
import socket
import sys
import time
import traceback

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb, View
from GUI import application
from GUI.Files import FileType
from GUI.Geometry import pt_in_rect, offset_rect, rects_intersect
from GUI.StdColors import black, red, blue
from GUI.StdFonts import application_font

import cap.cap_manager
from session import create_session
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget
import term.term_keyboard
import term_pygui_key_translate

class TerminalPyGUIApp(Application):
    def __init__(self, cfg):
        Application.__init__(self)

        self.cfg = cfg
        self.current_tab = None
        self.conn_history = []

    def get_application_name(self):
        return  'Multi-Tab Terminal Emulator in Python & pyGUI'
        
    def connect_to(self, conn_str = None, port = None):
        cfg = self.cfg.clone()
        if conn_str:
            cfg.set_conn_str(conn_str)

        if port:
            cfg.port = port
            
        cfg.session_type = 'ssh'

        doc = self.make_new_document()
        doc.new_contents()
        doc.cfg = cfg

        self.make_window(doc)
                
    def create_terminal(self, cfg):
        return TerminalPyGUI(cfg)

    def start(self):
        self.run()

    def open_app(self):
        self.connect_to()
    
    def make_window(self, document):
        view = TerminalPyGUIView(model=document)
        w, h = view.get_prefered_size()

        view.size = (w, h)
        
        win = Window(size = (w, h), document = document)
        
        cfg = document.cfg
        session = create_session(cfg, self.create_terminal(cfg))
        session.term_widget = view
        session.terminal.term_widget = view
        view.session = session
        view.tab_width = session.get_tab_width()
        
        win.place(view, left = 0, top = 0, right = 0, bottom = 0, sticky = 'nsew')

        session.start()
        win.show()

        view.become_target()
        
    def make_document(self, fileref):
        doc = TerminalPyGUIDoc()
        doc.cfg = self.cfg.clone()
        doc.title = 'Multi-Tab Terminal Emulator in Python & pyGUI'

        return doc
    
class TerminalPyGUIDoc(Document):
    def new_contents(self):
        pass

    def read_contents(self, file):
        pass

    def write_contents(self, file):
        pass
        
class TerminalPyGUIView(View, TerminalWidget):
    def __init__(self, **kwargs):
        View.__init__(self, **kwargs)
        TerminalWidget.__init__(self, **kwargs)

        self.font_size = 17.5
        self.padding_x = 5
        self.padding_y = 5
        
    def draw(self, canvas, update_rect):
        canvas.erase_rect(update_rect)

        self._setup_canvas(canvas)        

        y = self.padding_y

        lines = [line[:] for line in self.lines]
        for line in lines:
            canvas.moveto(self.padding_x, y)
            canvas.set_textcolor(black)
            canvas.show_text(''.join(line))

            y += canvas.font.line_height

    def __refresh(self):
        self.invalidate()
        self.update()

    def refresh(self):
        application().schedule_idle(self.__refresh)

    def _setup_canvas(self, canvas):
        canvas.fillcolor = red
        canvas.pencolor = black

        canvas.set_font(self._get_font())

    def _get_font(self):
        return application_font.but(size=self.font_size)
    
    def get_prefered_size(self):
        f = self._get_font()
        w = int(f.width('ABCDabcd') / 8 * self.visible_cols + self.padding_x * 2 + 0.5)
        h = int(f.line_height * self.visible_rows + self.padding_y * 2 + 0.5)

        return (w, h)
    
    def key_down(self, e):
        key = term_pygui_key_translate.translate_key(e)
            
        keycode = (e.char, key)
        text = e.char if len(e.char) > 0 else None
        modifiers = []
        
        if e.option:
            modifiers.append('alt')
        if e.control:
            modifiers.append('ctrl')
        if e.shift:
            modifiers.append('shift')
        
        logging.getLogger('term_pygui').debug('view key_down:{}'.format(e))
        logging.getLogger('term_pygui').debug('view key_down:{}, {}, {}'.format(keycode, text, modifiers))
        if self.session.terminal.process_key(keycode,
                                             text,
                                             modifiers):
            return
    
        v, handled = term.term_keyboard.translate_key(self.session.terminal,
                                                 keycode,
                                                 text,
                                                 modifiers)

        if len(v) > 0:
            self.session.send(v)
        elif text:
            self.session.send(text)

        logging.getLogger('term_pygui').debug(' - translated %r, %d' % (v, handled))
        
        # Return True to accept the key. Otherwise, it will be used by
        # the system.
        return

    def destroy(self):
        self.session.stop()
        super(TerminalPyGUIView, self).destroy()
        
class TerminalPyGUI(TerminalGUI):
    def __init__(self, cfg):
        super(TerminalPyGUI, self).__init__(cfg)
        
    def prompt_login(self, t, username):
        pass

    def prompt_password(self, action):
        pass
