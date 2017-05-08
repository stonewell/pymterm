import pyglet

class MyWindow(pyglet.window.Window):
    def __init__(self, *args, **kwargs):
        super(MyWindow, self).__init__(*args, **kwargs)
        print self.width, self.height

    def on_draw(self):
        self.clear()
        label = pyglet.text.Label('Hello, world',
                          font_name='Times New Roman',
                          font_size=36,
                          x=self.width//2, y=self.height//2,
                          anchor_x='center', anchor_y='center')

        label.draw()

window = MyWindow()

pyglet.app.run()
