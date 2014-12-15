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
 kppvh - file loading
"""

import os
from lxml import etree
import re

def clear_element(element):
    """In an XHTML tree, remove all sub-elements of a given element.

    We can't properly remove an XML element while traversing the
    tree. But we can clean it. Remove its text and children. However
    the tail must be preserved because it belongs to the next element,
    so re-attach.
    """
    tail = element.tail
    element.clear()
    element.tail = tail

class SourceFile(object):
    """Represent a file in memory.
    """

    def load_file(self, fname, encoding=None):
        """Load a file (text ot html) and finds its encoding.
        """

        # Keep the full name, the file name and its path
        self.fullname = fname
        self.basename = os.path.basename(fname)
        self.dirname = os.path.dirname(fname)

        with open(fname, "rb") as f:
            raw = f.read()

        if raw is None or len(raw) < 10:
            return None, None, None

        # Remove BOM if present
        if raw[0] == 0xef and raw[1] == 0xbb and raw[2] == 0xbf:
            raw = raw[3:]

        # Try various encodings. Much faster than using chardet
        if encoding is None:
            encodings = [ 'utf-8', 'latin1' ]
        else:
            encodings = [ encoding ]

        for enc in encodings:
            try:
                # Encode the raw data string into an internal unicode
                # string, according to the discovered encoding.
                text = raw.decode(enc)
            except Exception:
                continue
            else:
                return raw, text, enc

        # Encoding couldn't be found
        return None, None, None

    def count_ending_empty_lines(self, text):
        """Count the number of ending empty lines."""
        self.ending_empty_lines = 0
        for mychar in text[::-1]:
            if mychar == "\n":
                self.ending_empty_lines += 1
            elif mychar == "\r":
                continue
            else:
                break

    def strip_pg_boilerplate(self):
        """Remove the PG header and footer from a text version if present.
        """
        new_text = []
        self.start = 0
        for lineno, line in enumerate(self.text, start=1):
            # Find the markers. Unfortunately PG lacks consistency
            if line.startswith(("*** START OF THIS PROJECT GUTENBERG EBOOK",
                                "*** START OF THE PROJECT GUTENBERG EBOOK",
                                "***START OF THE PROJECT GUTENBERG EBOOK")):
                new_text = []
                self.start = lineno
            elif line.startswith(("*** END OF THIS PROJECT GUTENBERG EBOOK",
                                  "***END OF THIS PROJECT GUTENBERG EBOOK",
                                  "*** END OF THE PROJECT GUTENBERG EBOOK",
                                  "End of the Project Gutenberg EBook of",
                                  "End of Project Gutenberg's",
                                  "***END OF THE PROJECT GUTENBERG EBOOK")):
                break
            else:
                new_text.append(line)

        self.text = new_text


    def parse_html_xhtml(self, raw, text, relax=False):
        """Parse a byte array. Find the correct parser. Returns both the
        parser, which contains the error log, and the resulting tree,
        if the parsing was successful.

        If relax is True, then the lax html parser is used, even for
        XHTML, so the parsing will almost always succeed.
        """

        parser = None
        tree = None

        # Get the first 5 lines and find the DTD
        header = text.splitlines()[:5]

        if any(["DTD XHTML" in x for x in header]):
            parser = etree.XMLParser(dtd_validation=True)
        if any(["DTD HTML" in x for x in header]):
            parser = etree.HTMLParser()

        if parser is None:
            return None, None

        # Try the decoded file first.
        try:
            tree = etree.fromstring(text, parser)
        except etree.XMLSyntaxError:
            if relax == False:
                return parser, tree
        except Exception:
            pass
        else:
            return parser, tree

        # Try raw string. This will decode files with <?xml ...
        try:
            tree = etree.fromstring(raw, parser)
        except etree.XMLSyntaxError:
            if relax == False:
                return parser, tree
        except Exception:
            pass
        else:
            return parser, tree

        # The XHTML file may have some errors. If the caller really
        # wants a result then use the HTML parser.
        if relax and any(["DTD XHTML" in x for x in header]):
            parser = etree.HTMLParser()
            try:
                tree = etree.fromstring(text, parser)
            except etree.XMLSyntaxError:
                return parser, tree
            except Exception:
                pass
            else:
                return parser, tree

        return None, None


    def load_xhtml(self, name, encoding=None, relax=False):
        """Load an html/xhtml file. If it is an XHTML file, get rid of the
        namespace since that makes things much easier later.

        If parsing fails, then self.parser_errlog is not empty.

        If parsing succeeded, then self.tree is set, and
        self.parser_errlog is [].
        """
        self.parser_errlog = None
        self.tree = None
        self.text = None

        raw, text, encoding = self.load_file(name, encoding)
        if raw is None:
            return

        parser, tree = self.parse_html_xhtml(raw, text, relax)
        if parser == None:
            return

        self.parser_errlog = parser.error_log
        self.encoding = encoding
        self.count_ending_empty_lines(text)

        if len(self.parser_errlog):
            # Cleanup some errors
            #print(parser.error_log[0].domain_name)
            #print(parser.error_log[0].type_name)
            #print(parser.error_log[0].level_name)

            if type(parser) == etree.HTMLParser:
                # HTML parser rejects tags with both id and name
                #   (513 == DTD_ID_REDEFINED)
                self.parser_errlog = [
                    x for x in parser.error_log if parser.error_log[0].type != 513 ]

        if len(self.parser_errlog):
            return

        self.tree = tree.getroottree()
        self.text = text.splitlines()

        # Find the namespace - HOW ?
        # self.tree.getroot().nsmap -> {None: 'http://www.w3.org/1999/xhtml'}
        xmlns = self.tree.getroot().nsmap.get(None, None)
        if xmlns:
            self.xmlns = '{' + xmlns + '}'
        else:
            self.xmlns = ""

        # Remove the namespace from the tags
        # (eg. {http://www.w3.org/1999/xhtml})
        for element in self.tree.iter(tag=etree.Element):
            element.tag = element.tag.replace(self.xmlns, "")

        # Find type of xhtml (10 or 11 for 1.0 and 1.1). 0=html or
        # unknown. So far, no need to differentiate 1.0 strict and
        # transitional.
        if "DTD/xhtml1-strict.dtd" in self.tree.docinfo.doctype or "DTD/xhtml1-transitional.dtd" in self.tree.docinfo.doctype:
            self.xhtml=10
        elif "http://www.w3.org/TR/xhtml11/DTD/xhtml11.dtd" in self.tree.docinfo.doctype:
            self.xhtml=11
        else:
            self.xhtml=0

        # Remove PG boilerplate. These are kept in a <pre> tag.
        find = etree.XPath("//pre")
        for element in find(self.tree):
            if element.text is None:
                continue

            text = element.text.strip()

            if re.match(".*?\*\*\* START OF THIS PROJECT GUTENBERG EBOOK.*?\*\*\*(.*)", text, flags=re.MULTILINE | re.DOTALL):
                clear_element(element)

            elif text.startswith("End of the Project Gutenberg") or text.startswith("End of Project Gutenberg"):
                clear_element(element)


    def load_text(self, fname, encoding=None):
        """Load the file as text."""
        raw, text, encoding = self.load_file(fname, encoding)

        if raw is None:
            return

        self.count_ending_empty_lines(text)

        self.text = text.splitlines()
        self.encoding = encoding

        self.strip_pg_boilerplate()


def test_load_file1():
    myfile = SourceFile()
    raw, text, encoding = myfile.load_file("data/testfiles/file1.txt")
    assert(myfile.basename == 'file1.txt')

    assert(raw != None)
    assert(text != None)
    assert(encoding == 'utf-8')

def test_load_file2():
    myfile = SourceFile()
    raw, text, encoding = myfile.load_file("data/testfiles/file2.txt")
    assert(myfile.basename == 'file2.txt')

    assert(raw != None)
    assert(text != None)
    assert(encoding == 'latin1')

def test_load_text1():
    myfile = SourceFile()
    myfile.load_text("data/testfiles/file2.txt")
    assert(myfile.encoding == 'latin1')
    assert(myfile.basename == 'file2.txt')
    assert(myfile.text)
    assert(len(myfile.text) == 7)
    assert(myfile.start == 0)
    assert(myfile.ending_empty_lines == 1)

def test_load_text2():
    myfile = SourceFile()
    myfile.load_text("data/testfiles/pg34332.txt")
    assert(myfile.encoding == 'latin1')
    assert(myfile.basename == 'pg34332.txt')
    assert(myfile.text)
    assert(len(myfile.text) == 76)
    assert(myfile.start == 21)
    assert(myfile.ending_empty_lines == 1)

def test_load_html_text1():
    myfile = SourceFile()
    myfile.load_xhtml("data/testfiles/34332-h.htm")
    assert(myfile.encoding == 'latin1')
    assert(myfile.basename == '34332-h.htm')
    assert(myfile.text)
    assert(len(myfile.text) == 489)
    assert(myfile.tree)
    assert(myfile.xhtml == 0)               # html 4
    assert(len(myfile.parser_errlog) == 0)
    assert(myfile.ending_empty_lines == 4)

def test_load_xhtml_text1():
    myfile = SourceFile()
    myfile.load_xhtml("data/testfiles/41307-h.htm")
    assert(myfile.encoding == 'utf-8')
    assert(myfile.basename == '41307-h.htm')
    assert(myfile.text)
    assert(len(myfile.text) == 442)
    assert(myfile.tree)
    assert(myfile.xhtml == 10)            # xhtml 1.0
    assert(myfile.parser_errlog == [])

def test_load_xhtml_text1():
    myfile = SourceFile()
    myfile.load_xhtml("data/testfiles/badxhtml.html")
    assert(myfile.encoding == 'utf-8')
    assert(myfile.basename == 'badxhtml.html')
    assert(myfile.tree == None)
    assert(myfile.text == None)
    assert(len(myfile.parser_errlog) == 3)
