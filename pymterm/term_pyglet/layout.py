from __future__ import division

import re
import sys

from OpenGL.GL import *

from pyglet import graphics
from pyglet.text import runlist


_is_epydoc = hasattr(sys, 'is_epydoc') and sys.is_epydoc

_distance_re = re.compile(r'([-0-9.]+)([a-zA-Z]+)')

col_width = 14

def _parse_distance(distance, dpi):
    '''Parse a distance string and return corresponding distance in pixels as
    an integer.
    '''
    if isinstance(distance, int):
        return distance
    elif isinstance(distance, float):
        return int(distance)

    match = _distance_re.match(distance)
    assert match, 'Could not parse distance %s' % (distance)
    if not match:
        return 0

    value, unit = match.groups()
    value = float(value)
    if unit == 'px':
        return int(value)
    elif unit == 'pt':
        return int(value * dpi / 72.0)
    elif unit == 'pc':
        return int(value * dpi / 6.0)
    elif unit == 'in':
        return int(value * dpi)
    elif unit == 'mm':
        return int(value * dpi * 0.0393700787)
    elif unit == 'cm':
        return int(value * dpi * 0.393700787)
    else:
        assert False, 'Unknown distance unit %s' % unit


class _Line(object):
    align = 'left'

    margin_left = 0
    margin_right = 0

    length = 0

    ascent = 0
    descent = 0
    width = 0
    paragraph_begin = False
    paragraph_end = False

    x = None
    y = None

    def __init__(self, start):
        self.vertex_lists = []
        self.start = start
        self.boxes = []

    def __repr__(self):
        return '_Line(%r)' % self.boxes

    def add_box(self, box):
        self.boxes.append(box)
        self.length += box.length
        self.ascent = max(self.ascent, box.ascent)
        self.descent = min(self.descent, box.descent)
        self.width += box.advance

    def delete(self, layout):
        for vertex_list in self.vertex_lists:
            vertex_list.delete()
        self.vertex_lists = []

        for box in self.boxes:
            box.delete(layout)


class _LayoutContext(object):
    def __init__(self, layout, document, colors_iter, background_iter):
        self.colors_iter = colors_iter
        underline_iter = document.get_style_runs('underline')
        self.decoration_iter = runlist.ZipRunIterator(
            (background_iter,
             underline_iter))
        self.baseline_iter = runlist.FilteredRunIterator(
            document.get_style_runs('baseline'),
            lambda value: value is not None, 0)


class _StaticLayoutContext(_LayoutContext):
    def __init__(self, layout, document, colors_iter, background_iter):
        super(_StaticLayoutContext, self).__init__(layout, document,
                                                  colors_iter, background_iter)
        self.vertex_lists = layout._vertex_lists
        self.boxes = layout._boxes

    def add_list(self, vertex_list):
        self.vertex_lists.append(vertex_list)

    def add_box(self, box):
        self.boxes.append(box)


class _AbstractBox(object):
    owner = None

    def __init__(self, ascent, descent, advance, length):
        self.ascent = ascent
        self.descent = descent
        self.advance = advance
        self.length = length

    def place(self, layout, i, x, y):
        raise NotImplementedError('abstract')

    def delete(self, layout):
        raise NotImplementedError('abstract')

    def get_position_in_box(self, x):
        raise NotImplementedError('abstract')

    def get_point_in_box(self, position):
        raise NotImplementedError('abstract')


class _GlyphBox(_AbstractBox):
    def __init__(self, owner, font, glyphs, advance):
        '''Create a run of glyphs sharing the same texture.

        :Parameters:
            `owner` : `pyglet.image.Texture`
                Texture of all glyphs in this run.
            `font` : `pyglet.font.base.Font`
                Font of all glyphs in this run.
            `glyphs` : list of (int, `pyglet.font.base.Glyph`)
                Pairs of ``(kern, glyph)``, where ``kern`` gives horizontal
                displacement of the glyph in pixels (typically 0).
            `advance` : int
                Width of glyph run; must correspond to the sum of advances
                and kerns in the glyph list.

        '''
        super(_GlyphBox, self).__init__(
            font.ascent, font.descent, advance, len(glyphs))
        assert owner
        self.owner = owner
        self.font = font
        self.glyphs = glyphs
        self.advance = advance

    def place(self, layout, i, x, y, context):
        assert self.glyphs
        try:
            group = layout.groups[self.owner]
        except KeyError:
            group = layout.groups[self.owner] = \
                TextLayoutTextureGroup(self.owner, layout.foreground_group)

        n_glyphs = self.length
        vertices = []
        tex_coords = []
        x1 = x
        for start, end, baseline in context.baseline_iter.ranges(i, i+n_glyphs):
            baseline = layout._parse_distance(baseline)
            assert len(self.glyphs[start - i:end - i]) == end - start
            for kern, glyph in self.glyphs[start - i:end - i]:
                x1 += kern
                v0, v1, v2, v3 = glyph.vertices
                v0 += x1
                v2 += x1
                v1 += y + baseline
                v3 += y + baseline
                vertices.extend(map(int, [v0, v1, v2, v1, v2, v3, v0, v3]))
                t = glyph.tex_coords
                tex_coords.extend(t)
                x1 += col_width if glyph.advance <= col_width else col_width * 2

        # Text color
        colors = []
        for start, end, color in context.colors_iter.ranges(i, i+n_glyphs):
            if color is None:
                color = (0, 0, 0, 255)
            colors.extend(color * ((end - start) * 4))

        vertex_list = layout.batch.add(n_glyphs * 4, GL_QUADS, group,
            ('v2f/dynamic', vertices),
            ('t3f/dynamic', tex_coords),
            ('c4B/dynamic', colors))
        context.add_list(vertex_list)

        # Decoration (background color and underline)
        #
        # Should iterate over baseline too, but in practice any sensible
        # change in baseline will correspond with a change in font size,
        # and thus glyph run as well.  So we cheat and just use whatever
        # baseline was seen last.
        background_vertices = []
        background_colors = []
        underline_vertices = []
        underline_colors = []
        y1 = y + self.descent + baseline
        y2 = y + self.ascent + baseline
        x1 = x
        for start, end, decoration in \
                context.decoration_iter.ranges(i, i+n_glyphs):
            bg, underline = decoration
            x2 = x1
            for kern, glyph in self.glyphs[start - i:end - i]:
                x2 += kern + (col_width if glyph.advance <= col_width else col_width * 2)

            if bg is not None:
                background_vertices.extend(
                    [x1, y1, x2, y1, x2, y2, x1, y2])
                background_colors.extend(bg * 4)

            if underline is not None:
                underline_vertices.extend(
                    [x1, y + baseline - 2, x2, y + baseline - 2])
                underline_colors.extend(underline * 2)

            x1 = x2

        if background_vertices:
            background_list = layout.batch.add(
                len(background_vertices) // 2, GL_QUADS,
                layout.background_group,
                ('v2f/dynamic', background_vertices),
                ('c4B/dynamic', background_colors))
            context.add_list(background_list)

        if underline_vertices:
            underline_list = layout.batch.add(
                len(underline_vertices) // 2, GL_LINES,
                layout.foreground_decoration_group,
                ('v2f/dynamic', underline_vertices),
                ('c4B/dynamic', underline_colors))
            context.add_list(underline_list)

    def delete(self, layout):
        pass

    def get_point_in_box(self, position):
        x = 0
        for (kern, glyph) in self.glyphs:
            if position == 0:
                break
            position -= 1
            x += kern + (col_width if glyph.advance <= col_width else col_width * 2)  # glyph.advance + kern
        return x

    def get_position_in_box(self, x):
        position = 0
        last_glyph_x = 0
        for kern, glyph in self.glyphs:
            last_glyph_x += kern
            # if last_glyph_x + glyph.advance // 2 > x:
            if last_glyph_x + (col_width if glyph.advance <= col_width else col_width * 2) // 2 > x:
                return position
            position += 1
            last_glyph_x += (col_width if glyph.advance <= col_width else col_width * 2)  # glyph.advance
        return position

    def __repr__(self):
        return '_GlyphBox(%r)' % self.glyphs


class _InlineElementBox(_AbstractBox):
    def __init__(self, element):
        '''Create a glyph run holding a single element.
        '''
        super(_InlineElementBox, self).__init__(
            element.ascent, element.descent, element.advance, 1)
        self.element = element
        self.placed = False

    def place(self, layout, i, x, y, context):
        self.element.place(layout, x, y)
        self.placed = True
        context.add_box(self)

    def delete(self, layout):
        # font == element
        if self.placed:
            self.element.remove(layout)
            self.placed = False

    def get_point_in_box(self, position):
        if position == 0:
            return 0
        else:
            return self.advance

    def get_position_in_box(self, x):
        if x < self.advance // 2:
            return 0
        else:
            return 1

    def __repr__(self):
        return '_InlineElementBox(%r)' % self.element


class _InvalidRange(object):
    def __init__(self):
        self.start = sys.maxsize
        self.end = 0

    def insert(self, start, length):
        if self.start >= start:
            self.start += length
        if self.end >= start:
            self.end += length
        self.invalidate(start, start + length)

    def delete(self, start, end):
        if self.start > end:
            self.start -= end - start
        elif self.start > start:
            self.start = start
        if self.end > end:
            self.end -= end - start
        elif self.end > start:
            self.end = start

    def invalidate(self, start, end):
        if end <= start:
            return
        self.start = min(self.start, start)
        self.end = max(self.end, end)

    def validate(self):
        start, end = self.start, self.end
        self.start = sys.maxsize
        self.end = 0
        return start, end

    def is_invalid(self):
        return self.end > self.start

# Text group hierarchy
#
# top_group                     [Scrollable]TextLayoutGroup(Group)
#   background_group            OrderedGroup(0)
#   foreground_group            TextLayoutForegroundGroup(OrderedGroup(1))
#     [font textures]           TextLayoutTextureGroup(Group)
#     [...]                     TextLayoutTextureGroup(Group)
#   foreground_decoration_group
#                       TextLayoutForegroundDecorationGroup(OrderedGroup(2))


class TextLayoutGroup(graphics.Group):
    '''Top-level rendering group for `TextLayout`.

    The blend function is set for glyph rendering (``GL_SRC_ALPHA`` /
    ``GL_ONE_MINUS_SRC_ALPHA``).  The group is shared by all `TextLayout`
    instances as it has no internal state.
    '''
    def set_state(self):
        glPushAttrib(GL_ENABLE_BIT | GL_CURRENT_BIT)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

    def unset_state(self):
        glPopAttrib()


class TextLayoutForegroundGroup(graphics.OrderedGroup):
    '''Rendering group for foreground elements (glyphs) in all text layouts.

    The group enables ``GL_TEXTURE_2D``.
    '''
    def set_state(self):
        glEnable(GL_TEXTURE_2D)

    # unset_state not needed, as parent group will pop enable bit


class TextLayoutForegroundDecorationGroup(graphics.OrderedGroup):
    '''Rendering group for decorative elements (e.g., glyph underlines) in all
    text layouts.

    The group disables ``GL_TEXTURE_2D``.
    '''
    def set_state(self):
        glDisable(GL_TEXTURE_2D)

    # unset_state not needed, as parent group will pop enable bit


class TextLayoutTextureGroup(graphics.Group):
    '''Rendering group for a glyph texture in all text layouts.

    The group binds its texture to ``GL_TEXTURE_2D``.  The group is shared
    between all other text layout uses of the same texture.
    '''
    def __init__(self, texture, parent):
        assert texture.target == GL_TEXTURE_2D
        super(TextLayoutTextureGroup, self).__init__(parent)

        self.texture = texture

    def set_state(self):
        glBindTexture(GL_TEXTURE_2D, self.texture.id)

    # unset_state not needed, as next group will either bind a new texture or
    # pop enable bit.

    def __hash__(self):
        return hash((self.texture.id, self.parent))

    def __eq__(self, other):
        return (self.__class__ is other.__class__ and
                self.texture.id == other.texture.id and
                self.parent is other.parent)

    def __repr__(self):
        return '%s(%d, %r)' % (self.__class__.__name__,
                               self.texture.id,
                               self.parent)


class TextLayout(object):
    '''Lay out and display documents.

    This class is intended for displaying documents that do not change
    regularly -- any change will cost some time to lay out the complete
    document again and regenerate all vertex lists.

    The benefit of this class is that texture state is shared between
    all layouts of this class.  The time to draw one `TextLayout` may be
    roughly the same as the time to draw one `IncrementalTextLayout`; but
    drawing ten `TextLayout` objects in one batch is much faster than drawing
    ten incremental or scrollable text layouts.

    `Label` and `HTMLLabel` provide a convenient interface to this class.

    :Ivariables:
        `content_width` : int
            Calculated width of the text in the layout.  This may overflow
            the desired width if word-wrapping failed.
        `content_height` : int
            Calculated height of the text in the layout.
        `top_group` : `Group`
            Top-level rendering group.
        `background_group` : `Group`
            Rendering group for background color.
        `foreground_group` : `Group`
            Rendering group for glyphs.
        `foreground_decoration_group` : `Group`
            Rendering group for glyph underlines.

    '''
    _document = None
    _vertex_lists = ()
    _boxes = ()

    top_group = TextLayoutGroup()
    background_group = graphics.OrderedGroup(0, top_group)
    foreground_group = TextLayoutForegroundGroup(1, top_group)
    foreground_decoration_group = \
        TextLayoutForegroundDecorationGroup(2, top_group)

    _update_enabled = True
    _own_batch = False
    _origin_layout = False  # Lay out relative to origin?  Otherwise to box.

    def __init__(self, document, width=None, height=None,
                 dpi=None, batch=None, group=None):
        '''Create a text layout.

        :Parameters:
            `document` : `AbstractDocument`
                Document to display.
            `width` : int
                Width of the layout in pixels, or None
            `height` : int
                Height of the layout in pixels, or None
            `dpi` : float
                Font resolution; defaults to 96.
            `batch` : `Batch`
                Optional graphics batch to add this layout to.
            `group` : `Group`
                Optional rendering group to parent all groups this text layout
                uses.  Note that layouts with different
                rendered simultaneously in a batch.

        '''
        self.content_width = 0
        self.content_height = 0

        self.groups = {}
        self._init_groups(group)

        if batch is None:
            batch = graphics.Batch()
            self._own_batch = True
        self.batch = batch

        self._width = width
        if height is not None:
            self._height = height

        if dpi is None:
            dpi = 96
        self._dpi = dpi
        self.document = document

    def _parse_distance(self, distance):
        if distance is None:
            return None
        return _parse_distance(distance, self._dpi)

    def begin_update(self):
        '''Indicate that a number of changes to the layout or document
        are about to occur.

        Changes to the layout or document between calls to `begin_update` and
        `end_update` do not trigger any costly relayout of text.  Relayout of
        all changes is performed when `end_update` is called.

        Note that between the `begin_update` and `end_update` calls, values
        such as `content_width` and `content_height` are undefined (i.e., they
        may or may not be updated to reflect the latest changes).
        '''
        self._update_enabled = False

    def end_update(self):
        '''Perform pending layout changes since `begin_update`.

        See `begin_update`.
        '''
        self._update_enabled = True
        self._update()

    dpi = property(lambda self: self._dpi,
                   doc='''Get DPI used by this layout.

    Read-only.

    :type: float
    ''')

    def delete(self):
        '''Remove this layout from its batch.
        '''
        for vertex_list in self._vertex_lists:
            vertex_list.delete()
        self._vertex_lists = []

        for box in self._boxes:
            box.delete(self)

    def draw(self):
        '''Draw this text layout.

        Note that this method performs very badly if a batch was supplied to
        the constructor.  If you add this layout to a batch, you should
        ideally use only the batch's draw method.
        '''
        if self._own_batch:
            self.batch.draw()
        else:
            self.batch.draw_subset(self._vertex_lists)

    def _init_groups(self, group):
        if group:
            self.top_group = TextLayoutGroup(group)
            self.background_group = graphics.OrderedGroup(0, self.top_group)
            self.foreground_group = \
                TextLayoutForegroundGroup(1, self.top_group)
            self.foreground_decoration_group = \
                TextLayoutForegroundDecorationGroup(2, self.top_group)
        # Otherwise class groups are (re)used.

    def _get_document(self):
        return self._document

    def _set_document(self, document):
        if self._document:
            self._document.remove_handlers(self)
            self._uninit_document()
        document.push_handlers(self)
        self._document = document
        self._init_document()

    document = property(_get_document, _set_document,
                       '''Document to display.

    For `IncrementalTextLayout` it is far more efficient to modify a document
    in-place than to replace the document instance on the layout.

    :type: `AbstractDocument`
    ''')

    def _get_lines(self):
        len_text = len(self._document.text)
        glyphs = self._get_glyphs()
        owner_runs = runlist.RunList(len_text, None)
        self._get_owner_runs(owner_runs, glyphs, 0, len_text)
        lines = [line for line in self._flow_glyphs(glyphs, owner_runs,
                                                    0, len_text)]
        self.content_width = 0
        self._flow_lines(lines, 0, len(lines))
        return lines

    def _update(self):
        if not self._update_enabled:
            return

        for _vertex_list in self._vertex_lists:
            _vertex_list.delete()
        for box in self._boxes:
            box.delete(self)
        self._vertex_lists = []
        self._boxes = []
        self.groups.clear()

        if not self._document or not self._document.text:
            return

        lines = self._get_lines()

        colors_iter = self._document.get_style_runs('color')
        background_iter = self._document.get_style_runs('background_color')

        if self._origin_layout:
            left = top = 0
        else:
            left = self._get_left()
            top = self._get_top(lines)

        context = _StaticLayoutContext(self, self._document,
                                       colors_iter, background_iter)
        for line in lines:
            self._create_vertex_lists(left + line.x, top + line.y,
                                      line.start, line.boxes, context)

    def _get_left(self):
        width = self.content_width

        if self._anchor_x == 'left':
            return self._x
        elif self._anchor_x == 'center':
            return self._x - width // 2
        elif self._anchor_x == 'right':
            return self._x - width
        else:
            assert False, 'Invalid anchor_x'

    def _get_top(self, lines):
        if self._height is None:
            height = self.content_height
            offset = 0
        else:
            height = self._height
            if self._content_valign == 'top':
                offset = 0
            elif self._content_valign == 'bottom':
                offset = max(0, self._height - self.content_height)
            elif self._content_valign == 'center':
                offset = max(0, self._height - self.content_height) // 2
            else:
                assert False, 'Invalid content_valign'

        if self._anchor_y == 'top':
            return self._y - offset
        elif self._anchor_y == 'baseline':
            return self._y + lines[0].ascent - offset
        elif self._anchor_y == 'bottom':
            return self._y + height - offset
        elif self._anchor_y == 'center':
            if len(lines) == 1 and self._height is None:
                # This "looks" more centered than considering all of the
                # descent.
                line = lines[0]
                return self._y + line.ascent // 2 - line.descent // 4
            else:
                return self._y + height // 2 - offset
        else:
            assert False, 'Invalid anchor_y'

    def _init_document(self):
        self._update()

    def _uninit_document(self):
        pass

    def on_insert_text(self, start, text):
        '''Event handler for `AbstractDocument.on_insert_text`.

        The event handler is bound by the text layout; there is no need for
        applications to interact with this method.
        '''
        self._init_document()

    def on_delete_text(self, start, end):
        '''Event handler for `AbstractDocument.on_delete_text`.

        The event handler is bound by the text layout; there is no need for
        applications to interact with this method.
        '''
        self._init_document()

    def on_style_text(self, start, end, attributes):
        '''Event handler for `AbstractDocument.on_style_text`.

        The event handler is bound by the text layout; there is no need for
        applications to interact with this method.
        '''
        self._init_document()

    def _get_glyphs(self):
        glyphs = []
        runs = runlist.ZipRunIterator((
            self._document.get_font_runs(dpi=self._dpi),
            self._document.get_element_runs()))
        text = self._document.text
        for start, end, (font, element) in runs.ranges(0, len(text)):
            if element:
                glyphs.append(_InlineElementBox(element))
            else:
                glyphs.extend(font.get_glyphs(text[start:end]))
        return glyphs

    def _get_owner_runs(self, owner_runs, glyphs, start, end):
        owner = glyphs[start].owner
        run_start = start
        # TODO avoid glyph slice on non-incremental
        for i, glyph in enumerate(glyphs[start:end]):
            if owner != glyph.owner:
                owner_runs.set_run(run_start, i + start, owner)
                owner = glyph.owner
                run_start = i + start
        owner_runs.set_run(run_start, end, owner)

    def _flow_glyphs(self, glyphs, owner_runs, start, end):
        # TODO change flow generator on self, avoiding this conditional.
        for line in self._flow_glyphs_single_line(glyphs, owner_runs,
                                                  start, end):
            yield line

    def _flow_glyphs_single_line(self, glyphs, owner_runs, start, end):
        owner_iterator = owner_runs.get_run_iterator().ranges(start, end)
        font_iterator = self.document.get_font_runs(dpi=self._dpi)
        kern_iterator = runlist.FilteredRunIterator(
            self.document.get_style_runs('kerning'),
            lambda value: value is not None, 0)

        line = _Line(start)
        font = font_iterator[0]

        for start, end, owner in owner_iterator:
            font = font_iterator[start]
            width = 0
            owner_glyphs = []
            for kern_start, kern_end, kern in kern_iterator.ranges(start, end):
                gs = glyphs[kern_start:kern_end]
                # width += sum([g.advance for g in gs])
                width += sum([(col_width if glyph.advance <= col_width else col_width * 2) for glyph in gs])
                width += kern * (kern_end - kern_start)
                owner_glyphs.extend(zip([kern] * (kern_end - kern_start), gs))
            if owner is None:
                # Assume glyphs are already boxes.
                for kern, glyph in owner_glyphs:
                    line.add_box(glyph)
            else:
                line.add_box(_GlyphBox(owner, font, owner_glyphs, width))

        if not line.boxes:
            line.ascent = font.ascent
            line.descent = font.descent

        line.paragraph_begin = line.paragraph_end = True

        yield line

    def _flow_lines(self, lines, start, end):
        margin_top_iterator = runlist.FilteredRunIterator(
            self._document.get_style_runs('margin_top'),
            lambda value: value is not None, 0)
        margin_bottom_iterator = runlist.FilteredRunIterator(
            self._document.get_style_runs('margin_bottom'),
            lambda value: value is not None, 0)
        line_spacing_iterator = self._document.get_style_runs('line_spacing')
        leading_iterator = runlist.FilteredRunIterator(
            self._document.get_style_runs('leading'),
            lambda value: value is not None, 0)

        if start == 0:
            y = 0
        else:
            line = lines[start - 1]
            line_spacing = \
                self._parse_distance(line_spacing_iterator[line.start])
            leading = \
                self._parse_distance(leading_iterator[line.start])

            y = line.y
            if line_spacing is None:
                y += line.descent
            if line.paragraph_end:
                y -= self._parse_distance(margin_bottom_iterator[line.start])

        line_index = start
        for line in lines[start:]:
            if line.paragraph_begin:
                y -= self._parse_distance(margin_top_iterator[line.start])
                line_spacing = \
                    self._parse_distance(line_spacing_iterator[line.start])
                leading = self._parse_distance(leading_iterator[line.start])
            else:
                y -= leading

            if line_spacing is None:
                y -= line.ascent
            else:
                y -= line_spacing
            if line.align == 'left' or line.width > self.width:
                line.x = line.margin_left
            elif line.align == 'center':
                line.x = (self.width - line.margin_left - line.margin_right
                          - line.width) // 2 + line.margin_left
            elif line.align == 'right':
                line.x = self.width - line.margin_right - line.width

            self.content_width = max(self.content_width,
                                     line.width + line.margin_left)

            if line.y == y and line_index >= end:
                # Early exit: all invalidated lines have been reflowed and the
                # next line has no change (therefore subsequent lines do not
                # need to be changed).
                break
            line.y = y

            if line_spacing is None:
                y += line.descent
            if line.paragraph_end:
                y -= self._parse_distance(margin_bottom_iterator[line.start])

            line_index += 1
        else:
            self.content_height = -y

        return line_index

    def _create_vertex_lists(self, x, y, i, boxes, context):
        for box in boxes:
            box.place(self, i, x, y, context)
            x += box.advance
            i += box.length

    _x = 0

    def _set_x(self, x):
        if self._boxes:
            self._x = x
            self._update()
        else:
            dx = x - self._x
            l_dx = lambda x: int(x + dx)
            for vertex_list in self._vertex_lists:
                vertices = vertex_list.vertices[:]
                vertices[::2] = list(map(l_dx, vertices[::2]))
                vertex_list.vertices[:] = vertices
            self._x = x

    def _get_x(self):
        return self._x

    x = property(_get_x, _set_x,
                 doc='''X coordinate of the layout.

    See also `anchor_x`.

    :type: int
    ''')

    _y = 0

    def _set_y(self, y):
        if self._boxes:
            self._y = y
            self._update()
        else:
            dy = y - self._y
            l_dy = lambda y: int(y + dy)
            for vertex_list in self._vertex_lists:
                vertices = vertex_list.vertices[:]
                vertices[1::2] = list(map(l_dy, vertices[1::2]))
                vertex_list.vertices[:] = vertices
            self._y = y

    def _get_y(self):
        return self._y

    y = property(_get_y, _set_y,
                 doc='''Y coordinate of the layout.

    See also `anchor_y`.

    :type: int
    ''')


    _width = None
    def _set_width(self, width):
        self._width = width
        self._update()

    def _get_width(self):
        return self._width

    width = property(_get_width, _set_width,
                     doc='''Width of the layout.

    This property has no effect if `multiline` is False or `wrap_lines` is False.

    :type: int
    ''')

    _height = None
    def _set_height(self, height):
        self._height = height
        self._update()

    def _get_height(self):
        return self._height

    height = property(_get_height, _set_height,
                      doc='''Height of the layout.

    :type: int
    ''')

    _anchor_x = 'left'
    def _set_anchor_x(self, anchor_x):
        self._anchor_x = anchor_x
        self._update()

    def _get_anchor_x(self):
        return self._anchor_x

    anchor_x = property(_get_anchor_x, _set_anchor_x,
                      doc='''Horizontal anchor alignment.

    This property determines the meaning of the `x` coordinate.  It is one of
    the enumerants:

    ``"left"`` (default)
        The X coordinate gives the position of the left edge of the layout.
    ``"center"``
        The X coordinate gives the position of the center of the layout.
    ``"right"``
        The X coordinate gives the position of the right edge of the layout.

    For the purposes of calculating the position resulting from this
    alignment, the width of the layout is taken to be `width` if `multiline`
    is True and `wrap_lines` is True, otherwise `content_width`.

    :type: str
    ''')

    _anchor_y = 'bottom'
    def _set_anchor_y(self, anchor_y):
        self._anchor_y = anchor_y
        self._update()

    def _get_anchor_y(self):
        return self._anchor_y

    anchor_y = property(_get_anchor_y, _set_anchor_y,
                      doc='''Vertical anchor alignment.

    This property determines the meaning of the `y` coordinate.  It is one of
    the enumerants:

    ``"top"``
        The Y coordinate gives the position of the top edge of the layout.
    ``"center"``
        The Y coordinate gives the position of the center of the layout.
    ``"baseline"``
        The Y coordinate gives the position of the baseline of the first
        line of text in the layout.
    ``"bottom"`` (default)
        The Y coordinate gives the position of the bottom edge of the layout.

    For the purposes of calculating the position resulting from this
    alignment, the height of the layout is taken to be the smaller of
    `height` and `content_height`.

    See also `content_valign`.

    :type: str
    ''')

    _content_valign = 'top'
    def _set_content_valign(self, content_valign):
        self._content_valign = content_valign
        self._update()

    def _get_content_valign(self):
        return self._content_valign

    content_valign = property(_get_content_valign, _set_content_valign,
                              doc='''Vertical alignment of content within
    larger layout box.

    This property determines how content is positioned within the layout
    box when ``content_height`` is less than ``height``.  It is one
    of the enumerants:

    ``top`` (default)
        Content is aligned to the top of the layout box.
    ``center``
        Content is centered vertically within the layout box.
    ``bottom``
        Content is aligned to the bottom of the layout box.

    This property has no effect when ``content_height`` is greater
    than ``height`` (in which case the content is aligned to the top) or when
    ``height`` is ``None`` (in which case there is no vertical layout box
    dimension).

    :type: str
    ''')
