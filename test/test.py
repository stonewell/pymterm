#!/usr/bin/python

import pygame
from pygame.locals import *
from OpenGL.GL import *
from OpenGL.GLU import *
from math import *

class Texture(object):
    def __init__(self, data, w=0, h=0):
        """
        Initialize the texture from 3 diferents types of data:
        filename = open the image, get its string and produce texture
        surface = get its string and produce texture
        string surface = gets it texture and use w and h provided
        """
        if type(data) == str:
            texture_data = self.load_image(data)

        elif type(data) == pygame.Surface:
            texture_data = pygame.image.tostring(data, "RGBA", True)
            self.w, self.h = data.get_size()

        elif type(data) == bytes:
            self.w, self.h = w, h
            texture_data = data

        self.texID = 0
        self.load_texture(texture_data)

    def load_image(self, data):
        texture_surface = pygame.image.load(data).convert_alpha()
        texture_data = pygame.image.tostring(texture_surface, "RGBA", True)
        self.w, self.h = texture_surface.get_size()

        return texture_data

    def load_texture(self, texture_data):
        self.texID = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self.texID)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, self.w,
                     self.h, 0, GL_RGBA, GL_UNSIGNED_BYTE,
                     texture_data)

    def render(self):
        glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        glTranslate(-1, -1, 0)
        glScale(2.0/75, 2.0/25.0, 1)
        glDisable(GL_LIGHTING)
        glEnable(GL_TEXTURE_2D)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0, 0, 0, 1.0)

        self.Draw(-0.5, -0.5, self.w, self.h)
    
    def Draw(self, top, left, bottom, right):
        """
        Draw the image on the Opengl Screen
        """
        # Make sure he is looking at the position (0,0,0)
        glBindTexture(GL_TEXTURE_2D, self.texID)
        glBegin(GL_QUADS)
    
        # The top left of the image must be the indicated position
        glTexCoord2f(0.0, 1.0)
        glVertex2f(left, top)
    
        glTexCoord2f(1.0, 1.0)
        glVertex2f(right, top)
    
        glTexCoord2f(1.0, 0.0)
        glVertex2f(right, bottom)
    
        glTexCoord2f(0.0, 0.0)
        glVertex2f(left, bottom)
    
        glEnd()

    
def next_power_of_2(v):
    return int(2**ceil(log(v, 2)))

def main():
    # Initialise screen
    pygame.init()
    screen = pygame.display.set_mode((150, 50), DOUBLEBUF | OPENGL)
    pygame.display.set_caption('Basic Pygame program')

    width, height = 150, 50
    print width, height

    # Fill background
    background = pygame.Surface((width, height))
    background = background.convert()
    background.fill((250, 250, 250))

    # Display some text
    font = pygame.font.Font(None, 36)
    text = font.render("Hello There", 1, (10, 10, 10))
    textpos = text.get_rect()
    textpos.centerx = background.get_rect().centerx
    background.blit(text, textpos)


    texture = Texture(background)
    texture.render()
    
    # Blit everything to the screen
    #screen.blit(background, (0, 0))
    pygame.display.flip()

    # Event loop
    while 1:
        for event in pygame.event.get():
            if event.type == QUIT:
                return

            #screen.blit(background, (0, 0))
            texture.render()
            pygame.display.flip()


if __name__ == '__main__': main()
