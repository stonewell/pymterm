import pygame, numpy
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
#import settings, data

fonts = {}
def getfont(fontname, size):
	key = fontname, size
	if key not in fonts:
		fontname = fontname and data.filepath("fonts", "%s.ttf" % fontname)
		fonts[key] = pygame.font.Font(fontname, size)
	return fonts[key]

renders = {}
def getrender(text, fontname, size, color):
	key = text, fontname, size, color
	if key not in renders:
		if "\n" in text:
			surfs = [getrender(t, fontname, size, color) for t in text.split("\n")]
			w = max(surf.get_width() for surf in surfs)
			lh = int(round(size * 1.5))
			surf = pygame.Surface((w, lh * len(surfs))).convert_alpha()
			surf.fill((0, 0, 0, 0))
			for j, s in enumerate(surfs):
				surf.blit(s, (int(0.5 * (w - s.get_width())), j * lh))
			renders[key] = surf
		else:
			renders[key] = getfont(fontname, size).render(text, True, color)
	return renders[key]

surfs = {}
def getsurf(sw, sh):
	size = sw, sh
	if size not in surfs:
		surfs[size] = pygame.Surface((sw, sh)).convert_alpha()
	return surfs[size]

class Texture(object):
	def __init__(self, text, fontname, size, color, bcolor):
		self.text = text
		render = getrender(text, fontname, size, color)
		self.rw, self.rh = render.get_size()
		self.d = round(0.03 * size) if bcolor else 0
		self.rw += self.d
		self.rh += self.d
		sw = 4
		while sw < max(self.rw, self.rh):
			sw <<= 1
		sh = sw
		self.sw = sw
		self.sh = sh
		surf = getsurf(sw, sh)
		surf.fill((0, 0, 0, 0))
		if bcolor:
			brender = getrender(text, fontname, size, bcolor)
			surf.blit(brender, (0, 0))
			surf.blit(brender, (2 * self.d, 0))
			surf.blit(brender, (0, 2 * self.d))
			surf.blit(brender, (2 * self.d, 2 * self.d))

		surf.blit(render, (self.d, self.d))
		self.maketexture(surf)

	def maketexture(self, surf):
		sw, sh = surf.get_size()
		data = numpy.hstack([
			numpy.reshape(pygame.surfarray.pixels3d(surf), [sw * sh, 3]),
			numpy.reshape(pygame.surfarray.pixels_alpha(surf), [sw * sh, 1])
		])
		self.texture = glGenTextures(1)
		glPixelStorei(GL_UNPACK_ALIGNMENT,1)
		glBindTexture(GL_TEXTURE_2D, self.texture)
		glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
		glTexParameter(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
		glTexImage2D(GL_TEXTURE_2D, 0, 4, sw, sh, 0, GL_RGBA, GL_UNSIGNED_BYTE, data)

	def draw(self, (x, y), hanchor, vanchor):
		x0 = round(x - hanchor * self.rw)
		y0 = round(y - self.sh + (1 - vanchor) * self.rh)
		glBindTexture(GL_TEXTURE_2D, self.texture)
		glBegin(GL_QUADS)
		glTexCoord(1, 0)
		glVertex(x0, y0, 0)
		glTexCoord(0, 0)
		glVertex(x0, y0 + self.sh, 0)
		glTexCoord(0, 1)
		glVertex(x0 + self.sw, y0 + self.sh, 0)
		glTexCoord(1, 1)
		glVertex(x0 + self.sw, y0, 0)
		glEnd()

	def clear(self):
		glDeleteTextures([self.texture])


class Button(Texture):
	fontname = "Homenaje"
	def __init__(self, text, size, color, boxcolor, boxcolor1, indent, width):
		self.text = text
		render = getrender(text, self.fontname, size, color)
		self.rw, self.rh = render.get_size()
		self.rw += indent
		self.rw = max(self.rw, width)
		ohang = int(size * 0.3)
		d = int(size * 0.1) if boxcolor1 else 0
		self.rw += ohang + d
#		self.rh += d
		sw = 4
		while sw < max(self.rw, self.rh):
			sw <<= 1
		sh = sw
		self.sw = sw
		self.sh = sh
		surf = getsurf(sw, sh)
		surf.fill((0, 0, 0, 0))
		if boxcolor1:
			ps = (0, d), (self.rw + ohang + d, d), (self.rw + d, self.rh + d), (0, self.rh + d)
			pygame.draw.polygon(surf, boxcolor1, ps)
		if boxcolor:
			ps = (0, 0), (self.rw + ohang, 0), (self.rw, self.rh), (0, self.rh)
			pygame.draw.polygon(surf, boxcolor, ps)
		surf.blit(render, (indent, 0))
		self.maketexture(surf)

	def draw(self, (x, y)):
		Texture.draw(self, (x, y), 0, 1)

textures = {}
def gettexture(text, fontname, size, color, bcolor):
	key = text, fontname, size, color, bcolor
	if key not in textures:
		textures[key] = Texture(text, fontname, size, color, bcolor)
	return textures[key]

btextures = {}
def getbtexture(text, size, color, boxcolor, boxcolor1, indent, width):
	key = text, size, color, boxcolor, boxcolor1, indent, width
	if key not in btextures:
		btextures[key] = Button(text, size, color, boxcolor, boxcolor1, indent, width)
	return btextures[key]

def clear():
	for t in list(textures.keys()):
		textures[t].clear()
		del textures[t]
	for t in list(btextures.keys()):
		btextures[t].clear()
		del btextures[t]


def setup():
	glMatrixMode(GL_PROJECTION)
	glLoadIdentity()
	glTranslate(-1, -1, 0)
	glScale(2.0/854.0, 2.0/560.0, 1)
	glDisable(GL_DEPTH_TEST)
	glDisable(GL_CULL_FACE)
	glDisable(GL_LIGHTING)
	glEnable(GL_TEXTURE_2D)
	glEnable(GL_BLEND)
	glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

def write(text, fontname, size, color, (x, y), bcolor=None, hanchor=0.5, vanchor=0.5, alpha=1):
	glColor(1, 1, 1, alpha)
	texture = gettexture(text, fontname, size, color, bcolor)
	texture.draw((x, y), hanchor, vanchor)

def drawbutton(text, size, color, (x, y), boxcolor=None, boxcolor1=None, indent=0, width=0):
	texture = getbtexture(text, size, color, boxcolor, boxcolor1, indent, width)
	texture.draw((x, y))


if __name__ == "__main__":
	from pygame.locals import *
	pygame.init()
	pygame.display.set_mode((800, 600), DOUBLEBUF | OPENGL)
	pygame.font.init()
	glClearColor(0, 0, 0, 1)
	clock = pygame.time.Clock()
	t = 0
	pygame.event.get()
	while not any(e.type == KEYDOWN for e in pygame.event.get()):
		dt = 0.001 * clock.tick(30)
		glClear(GL_COLOR_BUFFER_BIT)
		setup()
		write("test %s" % t, None, 400, (255, 255, 255), (400, 300))
		print t
		t += 1
		pygame.display.flip()
	


