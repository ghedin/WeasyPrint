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
Specific handling for some HTML elements, especially replaced elements.

Replaced elements (eg. <img> elements) are rendered externally and behave
as an atomic opaque box in CSS. They may or may not have intrinsic dimensions.

"""

from __future__ import division

from .formatting_structure import boxes
from .utils import get_url_attribute


# Maps HTML tag names to function taking an HTML element and returning a Box.
HTML_HANDLERS = {}


def handle_element(document, element, box):
    """Handle HTML elements that need special care.

    :returns: a (possibly empty) list of boxes.
    """
    if box.element_tag in HTML_HANDLERS:
        return HTML_HANDLERS[element.tag](document, element, box)
    else:
        return [box]


def handler(tag):
    """Return a decorator registering a function handling ``tag`` elements."""
    def decorator(function):
        """Decorator registering a function handling ``tag`` elements."""
        HTML_HANDLERS[tag] = function
        return function
    return decorator


def is_block_level(box):
    """Tell wether ``box`` is supposed to be block level.

    Return ``True`` if the element is block-level, ``False`` if it is
    inline-level, and raise ValueError if it is neither.

    """
    display = box.style.display

    if display in ('block', 'list-item', 'table'):
        return True
    elif display in ('inline', 'inline-table', 'inline-block'):
        return False
    else:
        raise ValueError('Unsupported display: ' + display)


def make_replaced_box(element, box, replacement):
    """Wrap a :class:`Replacement` object in either replaced box.

    That box is either block-level or inline-level, depending on what the
    element should be.

    """
    if is_block_level(box):
        type_ = boxes.BlockLevelReplacedBox
    else:
        type_ = boxes.InlineLevelReplacedBox
    return type_(element.tag, element.sourceline, box.style, replacement)


def make_text_box(element, box, text):
    """Make a text box.

    If the element should be block-level, wrap it in a block box.

    """
    text_box = boxes.TextBox(element.tag, element.sourceline,
                             box.style.inherit_from(), text)
    if is_block_level(box):
        type_ = boxes.BlockBox
    else:
        type_ = boxes.InlineBox
    return type_(element.tag, element.sourceline,
                 box.style, [text_box])


@handler('img')
def handle_img(document, element, box):
    """Handle ``<img>`` tags, return either an image or the alt-text.

    See: http://www.w3.org/TR/html5/embedded-content-1.html#the-img-element

    """
    src = get_url_attribute(element, 'src')
    alt = element.get('alt')
    if src:
        surface = document.get_image_surface_from_uri(src)
        if surface is not None:
            replacement = ImageReplacement(surface)
            return [make_replaced_box(element, box, replacement)]
        else:
            # Invalid image, use the alt-text.
            if alt:
                return [make_text_box(element, box, alt)]
            elif alt == '':
                # The element represents nothing
                return []
            else:
                assert alt is None
                # TODO: find some indicator that an image is missing.
                # For now, just remove the image.
                return []
    else:
        if alt:
            return [make_text_box(element, box, alt)]
        else:
            return []


@handler('br')
def handle_br(document, element, box):
    """Handle ``<br>`` tags, return a preserved new-line character."""
    newline = boxes.TextBox(element.tag, element.sourceline,
                            box.style, '\n')
    newline.style.white_space = 'pre'
    return [boxes.InlineBox(element.tag, element.sourceline,
                            box.style, [newline])]


def integer_attribute(element, box, name, minimum=1):
    """Read an integer attribute from the HTML element and set it on the box.

    """
    value = element.get(name, '').strip()
    try:
        value = int(value)
    except ValueError:
        pass
    else:
        if value >= minimum:
            setattr(box, name, value)


@handler('colgroup')
def handle_colgroup(document, element, box):
    """Handle the ``span`` attribute."""
    if isinstance(box, boxes.TableColumnGroupBox):
        if any(child.tag == 'col' for child in element):
            box.span = None  # sum of the children’s spans
        else:
            integer_attribute(element, box, 'span')
    return [box]


@handler('col')
def handle_col(document, element, box):
    """Handle the ``span`` attribute."""
    if isinstance(box, boxes.TableColumnBox):
        integer_attribute(element, box, 'span')
        if box.span > 1:
            # Generate multiple boxes
            # http://lists.w3.org/Archives/Public/www-style/2011Nov/0293.html
            return [box.copy() for i in xrange(box.span)]
    return [box]


@handler('th')
@handler('td')
def handle_td(document, element, box):
    """Handle the ``colspan``, ``rowspan`` attributes."""
    if isinstance(box, boxes.TableCellBox):
        # HTML 4.01 gives special meaning to colspan=0
        # http://www.w3.org/TR/html401/struct/tables.html#adef-rowspan
        # but HTML 5 removed it
        # http://www.w3.org/TR/html5/tabular-data.html#attr-tdth-colspan
        # rowspan=0 is still there though.
        integer_attribute(element, box, 'colspan')
        integer_attribute(element, box, 'rowspan', minimum=0)
    return [box]


class Replacement(object):
    """Abstract base class for replaced elements."""
    def intrinsic_width(self):
        """Intrinsic width if defined."""

    def intrinsic_height(self):
        """Intrinsic height if defined."""

    def intrinsic_ratio(self):
        """Intrinsic ratio if defined."""
        width = self.intrinsic_width()
        height = self.intrinsic_height()
        if (width is not None and height is not None and height != 0):
            return width / height


class ImageReplacement(Replacement):
    """Replaced ``<img>`` element.

    :param surface: a cairo :class:`ImageSurface` object.

    """
    def __init__(self, surface):
        assert surface
        self.surface = surface

    def intrinsic_width(self):
        return self.surface.get_width()

    def intrinsic_height(self):
        return self.surface.get_height()

    def draw(self, context):
        """Draw the element on the Cairo context."""
        context.set_source_surface(self.surface)
        context.paint()