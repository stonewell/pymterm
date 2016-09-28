
# -*- coding: utf8 -*-
import os
os.environ['PYGAME_FREETYPE'] = '1'
import pygame
import pygame.freetype

pygame.init()
#font = pygame.freetype.SysFont('Menlo Regular', 13)
font = pygame.freetype.Font('c:\\github\\pymterm\\data\\fonts\\wqy-microhei-mono.ttf', 13)
#font = pygame.font.Font('c:\\github\\pymterm\\data\\fonts\\wqy-microhei-mono.ttf', 13)
#font = pygame.font.Font('/home/stone/Work/personal/pymterm/data/fonts/wqy-microhei-mono.ttf', 13)
#font.ucs4 = True #should be useless. defaults to true
print font.get_sized_height(), font.get_sized_ascender(), font.get_sized_descender(), font.get_rect('ABCDabcd')
print font.get_rect('g').left, font.get_rect('g').top
print font.get_metrics('g'), font.get_metrics('s'), font.get_metrics('l'), font.get_metrics('ls'), font.get_metrics('lg') , font.get_metrics(' ')
print font.get_rect('l'), font.get_rect('ls'), font.get_rect('s'), font.get_rect('lg'), font.get_rect('g'), font.get_rect(' ')
print font.render(' ', (0,0,0,0))[1]
surf = font.render(u'黒 ♧', (255, 0, 0, 1))[0]
pygame.image.save(surf, 'image.png')
print 'image saved'
