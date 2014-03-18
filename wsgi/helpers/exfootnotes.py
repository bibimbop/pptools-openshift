#!/usr/bin/env python3

# -*- coding: utf-8 -*-

# Footnote extraction. Part of comp_pp

# Copyright (C) 2014 bibimbop at pgdp

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

import re

def extract_footnotes_pp(pp_text):
    """Extract footnotes from a text file. text is iterable. Returns
    the text as an iterable, without the footnotes, and footnotes as a
    list of (footnote string id, line number of the start of the
    footnote, list of strings comprising the footnote)."""

    def get_block():
        """Get a block of text, followed by the number of empty lines"""
        empty_lines = 0
        block = []

        for lineno, line in enumerate(pp_text):

            if len(line):
                # One or more empty lines will stop a block
                if empty_lines:
                    yield block, empty_lines
                    block = []
                    empty_lines = 0

                block += [ line ]

            else:
                empty_lines += 1

        yield block, empty_lines


    # Different types of footnote. 0 means not in footnote.
    cur_fn_type, cur_fn_indent, cur_fn_num = 0, 0, 0
    footnotes = []
    text = []
    prev_block = None

    for block, empty_lines in get_block():

        # Is the block a new footnote?
        next_fn_type = 0
        if len(block):
            for (regex, fn_type) in [ (r"(\s*)\[([\w-]+)\](.*)", 1),
                                      (r"(\s*)\[Note (\d+): (.*)", 2),
                                      (r"(      )Note (\d+): (.*)", 1),
                                      ]:
                m = re.match(regex, block[0])
                if m:
                    if m and m.group(2).startswith(("Illustration", "Décoration")):
                        # An illustration, possibly inside a footnote. Treat
                        # as part of text or footnote.
                        m = None
                        continue

                    next_fn_type = fn_type
                    next_fn_indent = m.group(1)
                    next_fn_num = m.group(2)

                    # Update first line of block, because we want the
                    # number outside.
                    block[0] = m.group(3)
                    break

        # Try to close previous footnote
        if cur_fn_type:
            if next_fn_type:
                # New block is footnote, so it ends the previous footnote
                footnotes += prev_block + [ "" ]
                text += [""] * (len(prev_block) + 1)
                prev_block = None
                cur_fn_type, cur_fn_indent, cur_fn_num = next_fn_type, next_fn_indent, next_fn_num
            elif block[0].startswith(cur_fn_indent):
                # Same indent or more. This is a continuation. Merge with
                # one empty line.
                block = prev_block + [ "" ] + block
            else:
                # End of footnote - current block is not a footnote
                footnotes += prev_block + [ "" ]
                text += [""] * (len(prev_block) + 1)
                prev_block = None
                cur_fn_type = 0

        if not cur_fn_type and next_fn_type:
            # Account for new footnote
            cur_fn_type, cur_fn_indent, cur_fn_num = next_fn_type, next_fn_indent, next_fn_num

        if cur_fn_type and (empty_lines >= 2 or
                            (cur_fn_type == 2 and block[-1].endswith("]"))):
            # End of footnote
            if cur_fn_type == 2 and block[-1].endswith("]"):
                # Remove terminal bracket
                block[-1] = block[-1][:-1]

            footnotes += block
            text += [""] * (len(block))
            cur_fn_type = 0
            block = None

        if not cur_fn_type:
            # Add to text, with white lines
            text += (block or []) + [""] * empty_lines
            footnotes += [""] * (len(block or []) + empty_lines)

        prev_block = block

    return text, footnotes





if __name__ == '__main__':

    import sys
    import sourcefile

    f = sourcefile.SourceFile()
    f.load_text(sys.argv[1])

#    mytext, myfootnotes = extract_footnotes_pp(f.text)

#    print("\n".join(mytext))

#    print("\n".join(myfootnotes))

#    for x in myfootnotes:
#        print(x[0], "\n".join(x[2]))
#        print()


