#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# sourcefile -

# Copyright 2012, 2014, bibimbop at pgdp, All rights reserved

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

"""
 kppvh - unicode analysis
"""

from lxml import etree
from collections import Counter
import unicodedata

def analyze_file(text):
    """From a unicode text, return a list of unusual unicode codes."""

    all_letters = Counter(text)
    #print(all_letters)

    res = []
    for l, num in all_letters.items():

        # End of line, common characters
        if l in '\u000a +-=/*<>°_':
            continue

        # Skip some categories: letter, numbers, some spaces
        #
        # List of categories:
        #   http://www.fileformat.info/info/unicode/category/index.htm
        cat = unicodedata.category(l)
        if cat[0] in ['L', 'N']:
            continue

        if cat in ['Po', 'Ps', 'Pe', 'Pi', 'Pf', 'Pd']:
            continue

        if cat in ['Sk', 'Mn']:
            continue

        # Some codes don't exists (like those in the Cc category.)
        try:
            name = unicodedata.name(l)
        except ValueError:
            name = ""

        res.append((cat, "\\u" + hex(ord(l)), l, name, num))

    return res
