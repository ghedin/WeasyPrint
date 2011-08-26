# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Various classes to break text lines and draw them.

"""

import cairo
import pangocairo
import pango

from .css.values import get_single_keyword, get_keyword, get_single_pixel_value


ALIGN_PROPERTIES = {'left': pango.ALIGN_LEFT,
                    'right': pango.ALIGN_RIGHT,
                    'center': pango.ALIGN_CENTER}

STYLE_PROPERTIES = {'normal': pango.STYLE_NORMAL,
                    'italic': pango.STYLE_ITALIC,
                    'oblique': pango.STYLE_OBLIQUE}

VARIANT_PROPERTIES = {'normal': pango.VARIANT_NORMAL,
                      'small-caps': pango.VARIANT_SMALL_CAPS}


class TextFragment(object):
    """Text renderer using Pango.

    This class is mainly used to render the text from a TextBox.

    """
    def __init__(self, text='', width=-1, context=None):
        if context is None:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 400)
            context = cairo.Context(surface)
        self.pango_context = pangocairo.CairoContext(context)
        self.pango_context.set_antialias(cairo.ANTIALIAS_SUBPIXEL)
        self.layout = self.pango_context.create_layout()
        self._font = None
        self.set_text(text)
        self.set_width(width)
        # If fallback is True other fonts on the system can be used to provide
        # characters missing from the current font. Otherwise, only characters
        # from the closest matching font can be used.
        # See : http://www.pygtk.org/docs/pygtk/class-pangoattribute.html
        self._set_attribute(pango.AttrFallback(True, 0, -1))
        # Other properties
        self.layout.set_wrap(pango.WRAP_WORD)

    def set_textbox(self, textbox):
        """Set the textbox properties in the layout."""
        self.set_text(textbox.text)
        font = ', '.join(v.value for v in textbox.style['font-family'])
        self.set_font_family(font)
        self.set_font_size(get_single_pixel_value(textbox.style.font_size))
        self.set_alignment(get_single_keyword(textbox.style.text_align))
        self.set_font_variant(get_single_keyword(textbox.style.font_variant))
        self.set_font_weight(int(textbox.style.font_weight[0].value))
        self.set_font_style(get_single_keyword(textbox.style.font_style))
        letter_spacing = get_single_pixel_value(textbox.style.letter_spacing)
        if letter_spacing is not None:
            self.set_letter_spacing(letter_spacing)
        self.set_foreground(textbox.style.color[0])
        # Have the draw package draw backgrounds like for blocks, do not
        # set the background with Pango.

    def show_layout(self):
        """Draw the text to the ``context`` given at construction."""
        self.pango_context.update_layout(self.layout)
        self.pango_context.show_layout(self.layout)

    @classmethod
    def from_textbox(cls, textbox, context=None):
        """Create a TextFragment from a TextBox."""
        if context is None:
            surface = textbox.document.surface
            context = cairo.Context(surface)
        object_cls = cls('', -1, context)
        object_cls.set_textbox(textbox)
        return object_cls

    def _update_font(self):
        """Update the font used by the layout."""
        self.layout.set_font_description(self._font)

    def _get_attributes(self):
        """Get the layout attributes."""
        return self.layout.get_attributes() or pango.AttrList()

    def _set_attribute(self, value):
        """Set the ``value`` attribute in the layout."""
        attributes = self.layout.get_attributes()
        if attributes:
            attributes.change(value)
        else:
            attributes = pango.AttrList()
            attributes.insert(value)
        self.layout.set_attributes(attributes)

    def get_layout(self):
        """Get a copy of the layout."""
        return self.layout.copy()

    @property
    def font(self):
        """Get the layout font."""
        self._font = self.layout.get_font_description()
        if self._font is None:
            self._font = self.layout.get_context().get_font_description()
        return self._font

    @font.setter
    def font(self, font_desc):
        """Set the layout font."""
        self.layout.set_font_description(pango.FontDescription(font_desc))

    def get_text(self):
        """Get the unicode text of the layout."""
        return self.layout.get_text().decode('utf-8')

    def set_text(self, text):
        """Set the layout unicode ``text``."""
        self.layout.set_text(text.encode('utf-8'))

    def get_size(self):
        """Get the real text area size in pixels."""
        return self.layout.get_pixel_size()

    def set_width(self, width):
        """Set the layout ``width``.

        The ``width`` value can be ``-1`` to indicate that no wrapping should
        be performed.

        """
        if width != -1:
            width = pango.SCALE * width
        self.layout.set_width(int(width))

    def set_spacing(self, value):
        """Set the spacing ``value`` between the lines of the layout."""
        self.layout.set_spacing(pango.SCALE * value)

    def set_alignment(self, alignment):
        """Set the default alignment of text in layout.

        The value of alignment must be ``'left'``, ``'center'``, ``'right'`` or
        ``'justify'``.

        """
        if alignment == 'justify':
            self.layout.set_alignment(ALIGN_PROPERTIES['left'])
            self.layout.set_justify(True)
        else:
            self.layout.set_alignment(ALIGN_PROPERTIES[alignment])

    def set_font_family(self, font):
        """Set the ``font`` used by the layout.

        ``font`` can be a unicode comma-separated list of font names, as in
        CSS.

        >>> set_font_family('Al Mawash Bold, Comic sans MS')

        """
        self.font.set_family(font.encode('utf-8'))
        self._update_font()

    def set_font_style(self, style):
        """Set the font style of the layout text.

        The value must be ``'normal'``, ``'italic'`` or ``'oblique'``, as in
        CSS.

        """
        if style in STYLE_PROPERTIES.keys():
            self.font.set_style(STYLE_PROPERTIES[style])
            self._update_font()
        else:
            raise ValueError(
                'The style property must be in %s' % STYLE_PROPERTIES.keys())

    def set_font_size(self, size):
        """Set the layout font size in pixels."""
        self.font.set_size(pango.SCALE * int(size))
        self._update_font()

    def set_font_variant(self, variant):
        """Set the layout font variant.

        The value of ``variant`` must be ``'normal'`` or ``'small-caps'``.

        """
        if variant in VARIANT_PROPERTIES.keys():
            self.font.set_variant(VARIANT_PROPERTIES[variant])
            self._update_font()
        else:
            raise ValueError(
                'The style property must be in %s' % VARIANT_PROPERTIES.keys())

    def set_font_weight(self, weight):
        """Set the layout font weight.

        The value of ``weight`` must be an integer in a range from 100 to 900.

        """
        self.font.set_weight(weight)
        self._update_font()

    def set_foreground(self, color):
        """Set the foreground ``color``."""
        self._set_attribute(
            # Pange colors channels take values in 0..65535,
            # while cssutils values are in 0..255
            # TODO: somehow handle color.alpha
            pango.AttrForeground(color.red * 256, color.green * 256,
                                 color.blue * 256, 0, -1))

    def set_letter_spacing(self, value):
        """Set the letter spacing ``value``."""
        self._set_attribute(
            pango.AttrLetterSpacing(int(value * pango.SCALE), 0, -1))

    def set_rise(self, value):
        """Set the text displacement ``value`` from the baseline."""
        self._set_attribute(pango.AttrRise(value * pango.SCALE, 0, 1))


class TextLineFragment(TextFragment):
    """Text renderer splitting lines."""
    def get_layout_line(self):
        """Create a new layout from the one line text."""
        layout = self.get_layout()
        layout.set_text(self.get_text())
        return layout

    def get_remaining_text(self):
        """Get the unicode text that can't be on the line."""
        # Do not use the length of the first line here.
        # Preserved new-line characters are between get_line(0).length
        # and get_line(1).start_index
        second_line = self.layout.get_line(1)
        if second_line is not None:
            text = self.layout.get_text()[second_line.start_index:]
            return text.decode('utf-8')
        else:
            return None

    def get_text(self):
        """Get all the unicode text can be on the line."""
        first_line = self.layout.get_line(0)
        return self.layout.get_text()[:first_line.length].decode('utf-8')

    def get_size(self):
        """Get the real text area dimensions for this line in pixels."""
        first_line = self.layout.get_line(0)
        return self.get_layout_line().get_pixel_size()

    def get_logical_extents(self):
        """Get the size of the logical area occupied by the text."""
        return self.layout.get_line(0).get_pixel_extents()[0]

    def get_ink_extents(self):
        """Get the size of the ink area occupied by the text."""
        return self.layout.get_line(0).get_pixel_extents()[1]

    def get_baseline(self):
        """Get the baseline of the text."""
        descent = pango.DESCENT(self.layout.get_line(0).get_pixel_extents()[1])
        height = self.get_size()[1]
        return height - descent