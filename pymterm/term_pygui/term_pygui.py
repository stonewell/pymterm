import logging
import os
import select
import socket
import sys
import time
import traceback

from GUI import Application, ScrollableView, Document, Window, Cursor, rgb
from GUI.Files import FileType
from GUI.Geometry import pt_in_rect, offset_rect, rects_intersect
from GUI.StdColors import black, red, blue
from GUI.StdFonts import application_font

import cap.cap_manager
from session import create_session
from term.terminal_gui import TerminalGUI
from term.terminal_widget import TerminalWidget


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
        win = Window(size = (400, 400), document = document)
        view = TerminalPyGUIView(model=document,
                                     extent = (1000, 1000),
                                    scrolling = 'hv')

        cfg = document.cfg
        session = create_session(cfg, self.create_terminal(cfg))
        session.term_widget = view
        session.terminal.term_widget = view
        view.session = session
        view.tab_width = session.get_tab_width()
        
        win.place(view, left = 0, top = 0, right = 0, bottom = 0, sticky = 'nsew')
        
        session.start()
        win.show()
        
    def make_document(self, fileref):
        doc = TerminalPyGUIDoc()
        doc.cfg = self.cfg.clone()
        doc.title = 'Multi-Tab Terminal Emulator in Python & pyGUI'

        return doc
    
    def key_down(self, e):
        print 'key_down', e
        
class TerminalPyGUIDoc(Document):
    def new_contents(self):
        pass

    def read_contents(self, file):
        pass

    def write_contents(self, file):
        pass
        
class TerminalPyGUIView(ScrollableView, TerminalWidget):
    def __init__(self, **kwargs):
        ScrollableView.__init__(self, **kwargs)
        TerminalWidget.__init__(self, **kwargs)
        
    def draw(self, canvas, update_rect):
        canvas.erase_rect(update_rect)

        self._setup_canvas(canvas)        

        y = 0

        lines = [line[:] for line in self.lines]
        for line in lines:
            canvas.moveto(0, y)
            canvas.set_textcolor(black)
            canvas.show_text(''.join(line))

            y += canvas.font.line_height

    def refresh(self):
        self.invalidate()
        self.update()

    def _setup_canvas(self, canvas):
        canvas.fillcolor = red
        canvas.pencolor = black

        canvas.set_font(application_font.but(size=17.5))
        
    def key_down(self, e):
        print 'key_down', e
        
class TerminalPyGUI(TerminalGUI):
    def __init__(self, cfg):
        super(TerminalPyGUI, self).__init__(cfg)
        
    def prompt_login(self, t, username):
        pass

    def prompt_password(self, action):
        pass
