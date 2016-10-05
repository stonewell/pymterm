
# -*- coding: utf8 -*- 
import pygame
import pygame.freetype

pygame.init()
#font = pygame.freetype.SysFont('Menlo Regular', 13)
font = pygame.freetype.Font('/Users/stone/Work/GitHub/pymterm/data/fonts/wqy-microhei-mono.ttf', 13)
font.ucs4 = True #should be useless. defaults to true
surf = font.render(u'黒 ♧')[0]
pygame.image.save(surf, 'image.png')
