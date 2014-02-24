#!/usr/bin/env python3

# kppvh - performs some checking on text files to submit to Project Gutenberg
# Copyright (C) 2013 bibimbop at pgdp

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

# -*- coding: utf-8 -*-

from lxml import etree
import sys
import re
import argparse
import tempfile
import subprocess
import os

import helpers.sourcefile

class Languages(object):

    def init(self):
        self.myfile = None

    def load_file(self, args):
        self.myfile = helpers.sourcefile.SourceFile()
        self.myfile.load_xhtml(args.filename)

    def find_tags(self, args):

        # Indexed by tag then lang
        self.extracts = set()

        if self.myfile.xhtml == 11:
            lang_attr = "{http://www.w3.org/XML/1998/namespace}lang"
        else:
            lang_attr = "lang"

        # Transform </br> to space because normalize-space doesn't do it
        find = etree.XPath("//br")
        for element in find(self.myfile.tree):
            element.tail = ' ' + (element.tail or '')

        for element in self.myfile.tree.iter(tag=etree.Element):

            tag = element.tag

            if tag == 'html':
                doc_lang = "(" + element.attrib.get(lang_attr, '_doc_') + ")"
                continue

            # Check whether we want a lang attribute
            if args.with_lang_only and lang_attr not in element.attrib:
                continue

            if tag in [ 'i', 'cite', 'em', 'span' ]:

                # Set the language to _doc_ if there is no lang tag
                lang = element.attrib.get(lang_attr, doc_lang)

                # Ignore span in main document language
                if tag == 'span' and lang == doc_lang:
                    continue

                self.extracts.add((tag, lang, etree.XPath("normalize-space()")(element)))




if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Language tag finder in HTML for PGDP PP.')

    parser.add_argument('filename', metavar='FILENAME', type=str,
                        help='input text file')
    parser.add_argument('--encoding', dest='encoding',
                        help='force document encoding (latin1, utf-8, ...)',
                        default=None)
    parser.add_argument('--verbose', dest='verbose',
                        help='verbose', action='store_true',
                        default=None)
    parser.add_argument('--with-lang-only', dest='with_lang_only',
                        help='verbose', action='store_true',
                        default=None)

    args = parser.parse_args()

    x = Languages()
    x.load(args)
    x.find_tags(args)

    # Display sorted by lang + tag
    print("====\nSorted by tag + language\n====\n\n")
    for (tag, lang, string) in sorted(x.extracts, key=lambda x: (x[1], x[0], x[2].lower())):
        print ("%-6s %-8s" % (tag, lang), string)

    # Display sorted by text
    print("====\nSorted by content\n====\n\n")
    for (tag, lang, string) in sorted(x.extracts, key=lambda x: x[2].lower()):
        print ("%-6s %-8s" % (tag, lang), string)

    # Display sorted by language
    print("====\nSorted by language\n====\n\n")
    for (tag, lang, string) in sorted(x.extracts, key=lambda x: (x[1], x[2].lower())):
        print ("%-6s %-8s" % (tag, lang), string)

