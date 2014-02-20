#!/usr/bin/env python3

# -*- coding: utf-8 -*-

# comp_pp - compare 2 files

# Copyright (C) 2012-2013 bibimbop at pgdp

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
import os
import sys
import argparse
import tempfile
import subprocess
from lxml import etree
import tinycss
import cssselect
#from functools import partial

from helpers import sourcefile

DEFAULT_TRANSFORM_CSS =  '''
                i:before, cite:before, em:before, abbr:before, dfn:before,
                i:after, cite:after, em:after, abbr:after, dfn:after      { content: "_"; }

                /* line breaks with <br /> will be ignored by
                 *  normalize-space(). Add a space in all of them to work
                 *  around. */
                br:before { content: " "; }

                /* Add spaces around td tags. */
                td:after, td:after { content: " "; }

                /* Remove page numbers. It seems every PP has a different way. */
                span[class^="pagenum"] { display: none }
                p[class^="pagenum"] { display: none }
                p[class^="page"] { display: none }
                span[class^="pgnum"] { display: none }
                div[id^="Page_"] { display: none }
                div[class^="pagenum"] { display: none }
            '''

def clear_element(element):
    """In an XHTML tree, remove all sub-elements of a given element.

    We can't properly remove an XML element while traversing the
    tree. But we can clean it. Remove its text and children. However
    the tail must be preserved because it belongs to the next element,
    so re-attach."""
    tail = element.tail
    element.clear()
    element.tail = tail


class pgdp_file(object):
    """Stores and process a DP/text/html file.
    """

    def __init__(self, args):
        self.text = None
        self.words = None
        self.myfile = sourcefile.SourceFile()
        self.args = args

        # œ ligature - has_oe_ligature and has_oe_dp are mutually
        # exclusive
        self.has_oe_ligature = False # the real thing
        self.has_oe_dp = False       # DP type: [oe]

        # Conversion to latin1 ?
        self.convert_to_latin1 = False

        self.transform_func = []

        # Footnotes, if extracted
        self.footnotes = []

        # First line of the text. This is where <body> is for html.
        self.start_line = 0


    def load(self, filename):
        pass

    def process_args(self, args):
        """Process command line arguments"""
        pass

    def analyze(self):
        pass

    def extract_footnotes(self):
        """Extract the footnotes."""
        pass

    def transform(self):
        """Final transformation pass."""
        pass




class pgdp_file_text(pgdp_file):

    def __init__(self, args):
        super().__init__(args)
        self.from_pgdp_rounds = False
        self.char_text = None

    def load(self, filename):
        """Load the file"""
        self.myfile.load_text(filename)
        self.from_pgdp_rounds = self.myfile.basename.startswith('projectID')

    def analyze(self):
        """Clean then analyse the content of a file. Decides if it is PP version,
        a DP version, ..."""

        # Remember which line the text started
        self.start_line = self.myfile.start

        # Unsplit lines
        self.text = '\n'.join(self.myfile.text)

        # Keep a copy to search for characters
        self.char_text = self.text

        # Check for œ, or [oe]
        if self.text.find('œ') != -1 or self.text.find('Œ') != -1:
            self.has_oe_ligature = True
        elif self.text.find('[oe]') != -1 or self.text.find('[OE]') != -1:
            self.has_oe_dp = True


    def convert(self):
        """Remove markers from the text."""

        if self.args.txt_cleanup_type == "n":
            return

        if self.from_pgdp_rounds:

            # Px or Fx From PGDP
            self.text = re.sub(r"-----File: \w+.png.*", '', self.text)

            if self.args.txt_cleanup_type == "p":
                # Proofers only. Done.
                return

            self.text = self.text.replace("\n/*\n", '\n\n')
            self.text = self.text.replace("\n*/\n", '\n\n')
            self.text = self.text.replace("\n/#\n", '\n\n')
            self.text = self.text.replace("\n#/\n", '\n\n')
            self.text = self.text.replace("\n/P\n", '\n\n')
            self.text = self.text.replace("\nP/\n", '\n\n')

            if self.args.ignore_format:
                self.text = self.text.replace("<i>", "")
                self.text = self.text.replace("</i>", "")
            else:
                self.text = self.text.replace("<i>", "_")
                self.text = self.text.replace("</i>", "_")

            self.text = re.sub("<.*?>", '', self.text)
            self.text = re.sub("</.*?>", '', self.text)
            self.text = re.sub("\[Blank Page\]", '', self.text)

            if self.args.ignore_format or self.args.suppress_footnote_tags:
                self.text = re.sub(r"\[Footnote (\d+): ", r'\1 ', self.text)
                self.text = re.sub(r"\*\[Footnote: ", '', self.text)

            if self.args.ignore_format or self.args.suppress_illustration_tags:
                self.text = re.sub(r"\[Illustrations?:([^]]*?)\]", r'\1', self.text, flags=re.MULTILINE)
                self.text = re.sub(r"\[Illustration\]", '', self.text)

            if self.args.ignore_format: #or self.args.suppress_sidenote_tags:
                self.text = re.sub(r"\[Sidenote:([^]]*?)\]", r'\1', self.text, flags=re.MULTILINE)

            if self.args.suppress_proofers_notes:
                self.text = re.sub(r"\[\*\*[^]]*?\]", '', self.text)

            if self.args.regroup_split_words:
                self.text = re.sub(r"(\w+)-\*(\n+)\*", r'\2\1', self.text)
                self.text = re.sub(r"(\w+)-\*_(\n\n)_\*", r"\2\1", self.text)
                self.text = re.sub(r"(\w+)-\*(\w+)", r"\1\2", self.text)

        else:
            if self.args.txt_cleanup_type == "p":
                # Proofers only. None here. Bail.
                return

            if self.args.ignore_format:
                self.text = self.text.replace("_", "")

            # Horizontal separation
            self.text = self.text.replace("*       *       *       *       *", "")
            self.text = self.text.replace("*     *     *     *     *", "")

        # Temp - ndash between numbers
        #self.text = re.sub("\d\-\-\d", '-', self.text)
        #self.text = self.text.replace("_", ' ')

        # Replace -- with real mdash
        self.text = self.text.replace("--", "—")


        # temp
        #self.text = self.text.replace("–", "-")

        transtab = str.maketrans("ª₁²₂₃₄₅₆₇",
                                 "a12234567")
        self.text = self.text.translate(transtab)


    def extract_footnotes_pgdp(self):
        # Extract the footnotes from an F round
        # Start with [Footnote ... and finish with ] at the end of a line

        in_fnote = False        # currently processing a footnote
        cur_fnote = []          # keeping current footnote
        text = []               # new text without footnotes

        for lineno, line in enumerate(self.text.splitlines()):

            # New footnote
            if "[Footnote" in line:

                if in_fnote:
#                    print("Error in text -- manual cleanup is needed around line %d" % (lineno), file=sys.stderr)
                    sys.exit()

                if "*[Footnote" in line:
                    # Join to previous - Remove the last from the existing
                    # footnotes.
                    line = line.replace("*[Footnote: ", "")
                    cur_fnote, self.footnotes = self.footnotes[-1], self.footnotes[:-1]
                else:
                    cur_fnote = [-1, ""]

                in_fnote = True

            if in_fnote:
                cur_fnote[1] = "\n".join([cur_fnote[1], line])

                # Footnote continuation: ] or ]*
                # We don't try to regroup yet
                if line.endswith((']', "]*")):
                    self.footnotes.append(cur_fnote)
                    in_fnote = False

            else:
                text.append(line)

        # Rebuild text, now without footnotes
        self.text = '\n'.join(text)


    def extract_footnotes_pp(self):
        # Extract the footnotes from a PP text version
        # Convert to lines and back
        in_fnote = False        # currently processing a footnote
        cur_fnote = []          # keeping current footnote
        text = []               # new text without footnotes
        blanc_cur = False       # current line is empty
        indent_fnote = 0        # indentation of current footnote

        for line in self.text.splitlines():

            blanc_prev = blanc_cur
            blanc_cur = len(line) == 0

            if line.startswith("——-File:") and in_fnote:
                self.footnotes.append(cur_fnote)
                text.append(line)
                in_fnote = False
                continue

            if line.endswith((".]", "]]", "»]", " ]", ")]", "_]", "-]", "—]")) and in_fnote:
                cur_fnote[1] += "\n" + line
                text.append("")
                self.footnotes.append(cur_fnote)
                in_fnote = False
                continue

            # Check for new footnote
            m = re.match("(\s*)\[([\w-]+)\](.*)", line)
            if not m:
                m = re.match("(\s*)\[Note (\d+): (.*)", line)

            if m and (m.group(2) == 'Illustration' or m.group(2) == "Décoration"):
                # An illustration, possibly inside a footnote. Treat
                # as part of text or footnote.
                m = None

            if m and blanc_prev:
                # It matches, and the previous line was empty

                if in_fnote:
                    # New footnote - Append current one to footnotes
                    self.footnotes.append(cur_fnote)
                    text.append("")

                in_fnote = True
                cur_fnote = [ m.group(2), m.group(3) ]
                indent_fnote = len(m.group(1))

                if line.endswith((".]", "]]", "»]", " ]", ")]", "_]", "-]", "—]")) and in_fnote:
                    self.footnotes.append(cur_fnote)
                    in_fnote = False

                continue

            if in_fnote:
                if ((blanc_prev and blanc_cur) or
                    (not blanc_cur and not line.startswith(' '*indent_fnote))):
                    # Two empty lines
                    # or
                    # Not a blank line, but indentation is less than
                    # when the footnote was open
                    #
                    #  -> end of footnote
                    in_fnote = False

                    if blanc_prev:
                        text.append("")

                    # Append to footnotes
                    self.footnotes.append(cur_fnote)

                else:
                    # still in footnote
                    cur_fnote[1] += "\n" + line
                    text.append("")
                    continue


            # Not a footnote - regular text
            text.append(line)

        # Last footnote
        if in_fnote:
            self.footnotes.append(cur_fnote)

        # Rebuild text, now without footnotes
        self.text = '\n'.join(text)


    def extract_footnotes(self):
        if self.from_pgdp_rounds:
            self.extract_footnotes_pgdp()
        else:
            self.extract_footnotes_pp()


    def transform(self):
        """Final cleanup."""
        for func in self.transform_func:
            self.text = func(self.text)

        # Apply transform function to the footnotes
        for fn in self.footnotes:
            for func in self.transform_func:
                fn[1] = func(fn[1])


class pgdp_file_html(pgdp_file):

    def __init__(self, args):
        super().__init__(args)

        self.mycss = ""
        self.char_text = None


    def load(self, filename):
        """Load the file"""
        self.myfile.load_xhtml(filename)


    def process_args(self, args):
        # Load default CSS for transformations
        if args.css_no_default is False:
            self.mycss = DEFAULT_TRANSFORM_CSS

        # Process command line arguments
        if self.args.css_smcap == 'U':
            self.mycss += ".smcap { text-transform:uppercase; }"
        elif self.args.css_smcap == 'L':
            self.mycss += ".smcap { text-transform:lowercase; }"
        elif self.args.css_smcap == 'T':
            self.mycss += ".smcap { text-transform:capitalize; }"

        if self.args.css_bold:
            self.mycss += "b:before, b:after { content: " + self.args.css_bold + "; }"

        if self.args.css_greek_title_plus:
            # greek: if there is a title, use it to replace the greek. */
            self.mycss += 'body *[lang=grc] { _replace_with_attr: "title"; }'
            self.mycss += 'body *[lang=grc]:before, body *[lang=grc]:after { content: "+"; }'

        if self.args.css_add_illustration:
            for figclass in [ 'figcenter', 'figleft', 'figright' ]:
                self.mycss += '.' + figclass + ':before { content: "[Illustration: "; }'
                self.mycss += '.' + figclass + ':after { content: "]"; }'

        # --css can be present multiple times, so it's a list.
        for css in self.args.css:
            self.mycss += css


    def analyze(self):
        """Clean then analyse the content of a file."""
        # Empty the head - we only want the body
        self.myfile.tree.find('head').clear()

        # Remember which line <body> was.
        self.start_line = self.myfile.tree.find('body').sourceline - 2

        # Remove PG footer, 1st method
        clear_after = False
        for element in self.myfile.tree.find('body').iter():
            if clear_after:
                element.text = ""
                element.tail = ""
            elif element.tag == "p" and element.text and element.text.startswith("***END OF THE PROJECT GUTENBERG EBOOK"):
                element.text = ""
                element.tail = ""
                clear_after = True

        # Remove PG header and footer, 2nd method
        find = etree.XPath("//pre")
        for element in find(self.myfile.tree):
            if element.text is None:
                continue

            text = element.text.strip()

            # Header - Remove everything until start of book.
            m = re.match(".*?\*\*\* START OF THIS PROJECT GUTENBERG EBOOK.*?\*\*\*(.*)", text, flags=re.MULTILINE | re.DOTALL)
            if m:
                # Found the header. Keep only the text after the
                # start tag (usually the credits)
                element.text = m.group(1)
                continue

            if text.startswith("End of the Project Gutenberg") or text.startswith("End of Project Gutenberg"):
                clear_element(element)

        # Remove PG footer, 3rd method -- header and footer are normal
        # html, not text in <pre> tag.
        try:
            # Look for one element
            (element,) = etree.XPath("//p[@id='pg-end-line']")(self.myfile.tree)
            while element is not None:
                clear_element(element)
                element = element.getnext()
        except ValueError:
            pass

        # Cleaning is done.

        # Transform html into text for character search.
        self.char_text = etree.XPath("normalize-space(/)")(self.myfile.tree)

        # HTML doc should have oelig by default.
        self.has_oe_ligature = True


    def text_apply(self, element, func):
        """Apply a function to every sub element's .text and .tail,
        and element's .text."""
        if element.text:
            element.text = func(element.text)
        for el in element.iter():
            if el == element:
                continue
            if el.text:
                el.text = func(el.text)
            if el.tail:
                el.tail = func(el.tail)


    def convert(self):
        """Remove HTML and PGDP marker from the text."""

        # Process each rule from our transformation CSS
        stylesheet = tinycss.make_parser().parse_stylesheet(self.mycss)
        for rule in stylesheet.rules:

            # Extract values we care about
            v_content = None
            f_transform = None
            f_replace_with_attr = None
            f_replace_regex = None
            f_text_replace = None
            f_element_func = None

            for val in rule.declarations:

                if val.name == 'content':
                    v_content = val.value[0].value

                elif val.name == "text-transform":
                    v = val.value[0].value
                    if v == "uppercase":
                        f_transform = lambda x: x.upper()
                    elif v == "lowercase":
                        f_transform = lambda x: x.lower()
                    elif v == "capitalize":
                        f_transform = lambda x: x.title()

                elif val.name == "_replace_with_attr":
                    f_replace_with_attr = lambda el: el.attrib[val.value[0].value]

                elif val.name == "text-replace":
                    v1 = val.value[0].value
                    v2 = val.value[2].value
                    f_text_replace = lambda x: x.replace(v1, v2)

                elif val.name == "display":
                    # Support display none only. So ignore "none" argument.
                    f_element_func = clear_element

#                elif val.name == "_replace_regex":
#                    f_replace_regex = partial(re.sub, r"(\d)\u00A0(\d)", r"\1\2")
#                    f_replace_regex = partial(re.sub, val.value[0].value, val.value[1].value)

                # Iterate through each selectors in the rule
                for selector in cssselect.parse(rule.selector.as_css()):

                    pseudo_element = selector.pseudo_element

                    xpath = cssselect.HTMLTranslator().selector_to_xpath(selector)
                    find = etree.XPath(xpath)

                    # Find each matching element in the HTML/XHTML document
                    for element in find(self.myfile.tree):

                        # Replace text with content of an attribute.
                        if f_replace_with_attr:
                            element.text = f_replace_with_attr(element)

                        if pseudo_element == "before":
                            element.text = v_content + (element.text or '') # opening tag
                        elif pseudo_element == "after":
                            element.tail = v_content + (element.tail or '') # closing tag

                        if f_transform:
                            self.text_apply(element, f_transform)

                        if f_text_replace:
                            self.text_apply(element, f_text_replace)

                        if f_element_func:
                            f_element_func(element)

                       # if f_replace_regex and element.text:
                       #     element.text = f_replace_regex(element.text)


        css_errors = ""
        if stylesheet.errors:
            # There is transformation CSS errors. If the default css
            # is included, take the offset into account.
            i = 0
            if self.args.css_no_default is False:
                i = DEFAULT_TRANSFORM_CSS.count('\n')
            print (stylesheet.errors)
            css_errors = "<div class='error-border bbox'><p>Error(s) in the transformation CSS:</p><ul>"
            for err in stylesheet.errors:
                css_errors += "<li>{0},{1}: {2}</li>".format(err.line-i, err.column, err.reason)
            css_errors += "</ul>"

        return css_errors





        # Transform footnote anchors to [..]
        find = etree.XPath("//a")
        for element in find(self.myfile.tree):
            href = element.attrib.get('href', None)
            if not href or not href.startswith("#Footnote_"):
                continue

            if element.text and not element.text.startswith('['):
                # Some PP have [xx], other have just xx for a page
                # number. Do not add [ ] if they are already there.
                element.text = '[' + (element.text or '') # opening tag
                element.tail = ']' + (element.tail or '') # closing tag

        # Add illustration tag, wherever we find it
        for figclass in [ 'figcenter', 'figleft', 'figright', 'caption' ]:
            find = etree.XPath("//div[contains(concat(' ', normalize-space(@class), ' '), ' " + figclass + " ')]")
            for element in find(self.myfile.tree):
                if element.text and len(element.text) > 1:
                    element.text = '[Illustration:' + element.text # opening tag
                else:
                    element.text = '[Illustration' + (element.text or '') # opening tag
                element.tail = ']' + (element.tail or '') # closing tag

#        for figclass in [ 'caption' ]:
#            find = etree.XPath("//p[contains(concat(' ', normalize-space(@class), ' '), ' " + figclass + " ')]")
#            for element in find(self.myfile.tree):
#                element.text = '[Illustration:' + (element.text or '')  # opening tag
#                element.tail = ']' + (element.tail or '') # closing tag

        # Add sidenote tag
        if self.args.with_sidenote_tags:
            for sntag in [ 'sidenote' ]:
                for find in [ "//p[contains(concat(' ', normalize-space(@class), ' '), ' " + sntag + " ')]",
                              "//div[starts-with(@class, 'sidenote')]" ]:
                    for element in etree.XPath(find)(self.myfile.tree):
                        element.text = '[Sidenote:' + (element.text or '') # opening tag
                        element.tail = ']' + (element.tail or '') # closing tag


    def extract_footnotes(self):
        # Find footnotes, then remove them
        if self.args.extract_footnotes:
            for find in [ "//div[@id[starts-with(.,'FN_')]]",
                          "//div[p/a[@id[starts-with(.,'Footnote_')]]]",
                          "//p[a[@id[starts-with(.,'Footnote_')]]]",
                          "//div/p[span/a[@id[starts-with(.,'Footnote_')]]]",
                          #"//p[a[@id[not(starts-with(.,'footnotetag')) and starts-with(.,'footnote')]]]",
                          #"//p[a[@id[starts-with(.,'footnote')]]]",
                          ]:
                for element in etree.XPath(find)(self.myfile.tree):

                    # Grab the text and remove the footnote number
                    m = re.match("\s*\[([\w-]+)\](.*)", element.xpath("string()"), re.DOTALL)
                    if not m:
                        m = re.match("\s*([\d]+)\s+(.*)", element.xpath("string()"), re.DOTALL)
                    if not m:
                        m = re.match("\s*([\d]+):(.*)", element.xpath("string()"), re.DOTALL)
                    if not m:
                        m = re.match("\s*Note ([\d]+):\s+(.*)", element.xpath("string()"), re.DOTALL)

                    if not m:
                        # That's probably bad
                        print("BAD? " , element.sourceline)
                        print("*" + element.xpath("string()") + "*")
                        #continue
                        raise

                    #print("*" + element.xpath("string()") + "*")

                    self.footnotes.append([ m.group(1), m.group(2) ])

                    clear_element(element)

                if len(self.footnotes):
                    # Found them. Stop now.
                    break

            #for fn in self.footnotes:
            #    print(fn[0])
            #raise


    def transform(self):
        """Transform html into text. Do a final cleanup."""
        self.text = etree.XPath("string(/)")(self.myfile.tree)

#        ff=open("compfilehtml.txt", "w")
#        ff.write(self.text)
#        ff.close()

        # Apply transform function to the main text
        for func in self.transform_func:
            self.text = func(self.text)

        # Apply transform function to the footnotes
        for fn in self.footnotes:
            for func in self.transform_func:
                fn[1] = func(fn[1])

        # zero width space
        if self.args.ignore_0_space:
            self.text = self.text.replace(chr(0x200b), "")


class CompPP(object):
    """Compare two files.
    """

    def __init__(self, args):
        self.args = args

    def oelig_convert(self, convert_oelig, text):
        # Do the required oelig conversion
        if convert_oelig == 1:
            text = text.replace(r"[oe]", "oe")
            text = text.replace(r"[OE]", "OE")

        elif convert_oelig == 2:
            text = text.replace(r"[oe]", "œ")
            text = text.replace(r"[OE]", "Œ")

        elif convert_oelig == 3:
            text = text.replace("œ", "oe")
            text = text.replace("Œ", "OE")

        return text

    def latin1_convert(self, text):
        # Convert some UTF8 characters to latin1
        text = text.replace("’", "'")
        text = text.replace("‘", "'")
        text = text.replace('“', '"')
        text = text.replace('”', '"')

    #    text = text.replace('in-4º', 'in-4o')
    #    text = text.replace('in-8º', 'in-8o')
    #    text = text.replace('in-fº', 'in-fo')
        text = text.replace('º', 'o')

        return text


    def convert_to_words(self, text):
        """Split the text into a list of words from the text."""

        # Split into list of words
        words = []

        for line in re.findall(r'([\w-]+|\W)', text):
            line = line.strip()

            if line != '':
                words.append(line)

        return words


    def compare_texts(self, text1, text2, debug=False):
        # Compare two sources
        # We could have used the difflib module, but it's too slow:
        #    for line in difflib.unified_diff(f1.words, f2.words):
        #        print(line)
        # Use diff instead.

        # Some debug code
        if False and debug:
            f = open("/tmp/text1", "wb")
            f.write(text1.encode('utf-8'))
            f.close()
            f = open("/tmp/text2", "wb")
            f.write(text2.encode('utf-8'))
            f.close()

        with tempfile.NamedTemporaryFile(mode='wb') as t1, tempfile.NamedTemporaryFile(mode='wb') as t2:

            t1.write(text1.encode('utf-8'))
            t2.write(text2.encode('utf-8'))

            t1.flush()
            t2.flush()

            repo_dir = os.environ.get("OPENSHIFT_REPO_DIR", "")
            if repo_dir:
                dwdiff_path = os.path.join(repo_dir, "bin", "dwdiff")
            else:
                dwdiff_path = "dwdiff"

            cmd = [dwdiff_path,
                   "-P",
                   "-R",
                   "-C 2",
                   "-L",
                   "-w ]COMPPP_START_DEL[",
                   "-x ]COMPPP_STOP_DEL[",
                   "-y ]COMPPP_START_INS[",
                   "-z ]COMPPP_STOP_INS["]

            if self.args.ignore_case:
                cmd += [ "--ignore-case" ]

            cmd += [ t1.name, t2.name ]

            # That shouldn't be needed if openshift was utf8 by default.
            env = os.environ.copy()
            env["LANG"] = "en_US.UTF-8"

            p = subprocess.Popen(cmd,
                                 stdout=subprocess.PIPE,
                                 env=env)

            # The output is raw, so we have to decode it to UTF-8, which
            # is the default under Ubuntu.
            return p.stdout.read().decode('utf-8')


    def create_html(self, files, text, footnotes, footnotes_errors):

        def massage_input(text, start0, start1):
            # Massage the input
            text = text.replace("&", "&amp;")
            text = text.replace("<", "&lt;")
            text = text.replace(">", "&gt;")

            text = text.replace("]COMPPP_START_DEL[", "<del>")
            text = text.replace("]COMPPP_STOP_DEL[", "</del>")
            text = text.replace("]COMPPP_START_INS[", "<ins>")
            text = text.replace("]COMPPP_STOP_INS[", "</ins>")

            if text:
                text = "<hr /><pre>\n" + text
            text = text.replace("\n--\n", "\n</pre><hr /><pre>\n")

            text = re.sub(r"^\s*(\d+):(\d+)",
                          lambda m: "<span class='lineno'>{0} : {1}</span>".format(int(m.group(1)) + start0,
                                                                                   int(m.group(2)) + start1),
                          text, flags=re.MULTILINE)
            if text:
                text = text + "</pre>\n"


            return text

        # Find the number of diff sections
        nb_diffs_text = 0
        if text:
            nb_diffs_text = len(re.findall("\n--\n", text)) + 1

        nb_diffs_footnotes = 0
        if footnotes:
            nb_diffs_footnotes = len(re.findall("\n--\n", footnotes or "")) + 1

        # Text, with correct (?) line numbers
        text = massage_input(text, files[0].start_line, files[1].start_line)

        # Footnotes - line numbers are meaningless right now. We could fix
        # that.
        footnotes = massage_input(footnotes, 0, 0)

        html_content = "<div>"

        if nb_diffs_text == 0:
            html_content += "<p>There is no diff section in the main text.</p>"
        elif nb_diffs_text == 1:
            html_content += "<p>There is " + str(nb_diffs_text) + " diff section in the main text.</p>"
        else:
            html_content += "<p>There are " + str(nb_diffs_text) + " diff sections in the main text.</p>"

        if footnotes:
            html_content += "<p>Footnotes are diff'ed separately <a href='#footnotes'>here</a></p>"
            if nb_diffs_footnotes == 0:
                html_content += "<p>There is no diff section in the footnotes.</p>"
            elif nb_diffs_footnotes == 1:
                html_content += "<p>There is " + str(nb_diffs_footnotes) + " diff section in the footnotes.</p>"
            else:
                html_content += "<p>There are " + str(nb_diffs_footnotes) + " diff sections in the footnotes.</p>"
        else:
            if self.args.extract_footnotes:
                html_content += "<p>There is no diff section in the footnote.</p>"

        if footnotes_errors:
            html_content += "<p>Error with footnotes numbering:</p>"
            html_content += "<ul>"
            for err in footnotes_errors:
                html_content += "<li>" + err + "</li>"
            html_content += "</ul>"

        if nb_diffs_text:
            html_content += "<h2 class='sep4'>Main text</h2>"
            html_content += text

        if footnotes:
            html_content += "<h2 id='footnotes' class='sep4'>Footnotes</h2>"
            html_content += "<pre class='sep4'>"
            html_content += footnotes
            html_content += "</pre>"

        html_content += "</div>"

        return html_content


    def check_char(self, files, char_best, char_other):
        """Check whether each file has a the best character. If not, add a
        conversion request.

        This is used for instance if one version uses ’ while the other
        uses '. In that case, we need to convert one into the other, to
        get a smaller diff.
        """

        in_0 = files[0].char_text.find(char_best)
        in_1 = files[1].char_text.find(char_best)

        if in_0 >= 0 and in_1 >= 0:
            # Both have it
            return

        if in_0 == -1 and in_1 == -1:
            # None have it
            return

        # Downgrade one version
        if in_0 > 0:
            files[0].transform_func.append(lambda text: text.replace(char_best, char_other))
        else:
            files[1].transform_func.append(lambda text: text.replace(char_best, char_other))


    def check_oelig(self, files):
        """Similar to check_char, but for oe ligatures."""
        if files[0].has_oe_ligature and files[1].has_oe_ligature:
            pass
        elif files[0].has_oe_dp and files[1].has_oe_dp:
            pass
        elif files[0].has_oe_ligature and files[1].has_oe_dp:
            files[1].transform_func.append(lambda text: text.replace("[oe]", "œ"))
            files[1].transform_func.append(lambda text: text.replace("[OE]", "Œ"))
        elif files[1].has_oe_ligature and files[0].has_oe_dp:
            files[0].transform_func.append(lambda text: text.replace("[oe]", "œ"))
            files[0].transform_func.append(lambda text: text.replace("[OE]", "Œ"))
        else:
            if files[0].has_oe_ligature:
                files[0].transform_func.append(lambda text: text.replace("œ", "oe"))
                files[0].transform_func.append(lambda text: text.replace("Œ", "OE"))
            elif files[1].has_oe_ligature:
                files[1].transform_func.append(lambda text: text.replace("œ", "oe"))
                files[1].transform_func.append(lambda text: text.replace("Œ", "OE"))

            if files[0].has_oe_dp:
                files[0].transform_func.append(lambda text: text.replace("[oe]", "oe"))
                files[0].transform_func.append(lambda text: text.replace("[OE]", "OE"))
            elif files[1].has_oe_dp:
                files[1].transform_func.append(lambda text: text.replace("[oe]", "oe"))
                files[1].transform_func.append(lambda text: text.replace("[OE]", "OE"))


    def do_process(self):

        files = [ None, None ]

        # Load files
        for i, fname in enumerate(self.args.filename):

            # Look for file type.
            if fname.endswith(('.html', '.htm')):
                files[i] = pgdp_file_html(self.args)
            else:
                files[i] = pgdp_file_text(self.args)

            f = files[i]

            f.load(fname)

            if f.myfile is None:
                print("Couldn't load file:", fname)
                return

            f.process_args(self.args)
            f.analyze()


        # How to process oe ligature
        self.check_oelig(files)

        # How to process punctuation
        self.check_char(files, "’", "'") # curly quote to straight
        self.check_char(files, "‘", "'") # curly quote to straight
        self.check_char(files, "º", "o") # ordinal to letter o
        self.check_char(files, "–", "-") # ndash to regular dash
        self.check_char(files, "½", "-1/2")
        self.check_char(files, "¼", "-1/4")
        self.check_char(files, "¾", "-3/4")
        self.check_char(files, '”', '"')
        self.check_char(files, '“', '"')
        self.check_char(files, '⁄', '/') # fraction
        self.check_char(files, "′", "'") # prime
        self.check_char(files, "″", "''") # double prime
        self.check_char(files, "‴", "'''") # triple prime

        # Remove non-breakable spaces between numbers. For instance, a
        # text file could have 250000, and the html could have 250 000.
        if self.args.suppress_nbsp_num:
            func = lambda text: re.sub(r"(\d)\u00A0(\d)", r"\1\2", text)
            files[0].transform_func.append(func)
            files[1].transform_func.append(func)

        # Suppress shy (soft hyphen)
        func = lambda text: re.sub(r"\u00AD", r"", text)
        files[0].transform_func.append(func)
        files[1].transform_func.append(func)

        # If the original encoding of them is latin1, we must convert a
        # few UTF8 characters. We assume the default is utf-8. No
        # provision for any other format.
        if files[0].myfile.encoding == "latin1" or files[1].myfile.encoding == "latin1":
            for f in files:
                if f.myfile.encoding != "latin1":
                    f.convert_to_latin1 = True

        err_message = ""

        # Apply the various convertions
        for f in files:
            err_message += f.convert() or ""

        # Extract footnotes
        if self.args.extract_footnotes:
            for f in files:
                f.extract_footnotes()

        # Transform the final document into a diffable format
        for f in files:
            f.transform()


        # Compare the two versions
        main_diff = self.compare_texts(files[0].text, files[1].text)

    #    for fn1, fn2 in zip(files[0].footnotes, files[1].footnotes):
    #        print()
    #        print("==========================================")
    #        print(fn1[1])
    #        print()
    #        print(fn2[1])

        fnotes_diff = ""
        fnotes_errors = []
        if self.args.extract_footnotes:
            if len(files[0].footnotes) != len(files[1].footnotes):
                fnotes_errors += [ "FOOTNOTE ERRORS: uneven number of footnotes: {0} and {1}. Footnotes diffs WILL NOT be displayed.".format(len(files[0].footnotes), len(files[1].footnotes)) ]

            else:
                fnotes1 = []
                fnotes2 = []
                for fn1, fn2 in zip(files[0].footnotes, files[1].footnotes):
                    if fn1[0] != fn2[0] and fn1[0] != -1 and fn2[0] != -1:
                        fnotes_errors += [ "FOOTNOTE ERROR: different footnote numbers: {0} and {1}".format(fn1[0], fn2[0]) ]

                    fnotes1 += [ fn1[1] ]
                    fnotes2 += [ fn2[1] ]

                fnotes_diff = self.compare_texts("\n".join(fnotes1), "\n".join(fnotes2))

        html_content = self.create_html(files, main_diff, fnotes_diff, fnotes_errors)

        return err_message, html_content, files[0].myfile.basename, files[1].myfile.basename

######################################

# Sample CSS used to display the diffs.
def diff_css():
    return """
body {
    margin-left: 5%;
    margin-right: 5%;
}

del {
    text-decoration: none;
    border: 1px solid black;
    color: #700000 ;
    background-color: #f4f4f4;
    font-size: larger;
}
ins {
    text-decoration: none;
    border: 1px solid black;
    color: green;
    background-color: #f4f4f4;
    font-size: larger;
}
.lineno { margin-right: 3em; }
.sep4 { margin-top: 4em; }
.bbox { margin-left: auto;
    margin-right: auto;
    border: 1px dashed;
    padding: 0em 1em 0em 1em;
    background-color: #F0FFFF;
    width: 90%;
    max-width: 50em;
}
.center { text-align:center; }

/* Use a CSS counter to number each diff. */
body {
  counter-reset: diff;  /* set diff counter to 0 */
}
hr:before {
  counter-increment: diff; /* inc the diff counter ... */
  content: "Diff " counter(diff) ": "; /* ... and display it */
}

.error-border { border-style:double; border-color:red; border-width:15px; }
"""

# Describe how to use the diffs
def html_usage(filename1, filename2):
    return """
    <div class="bbox">
      <p class="center">— Usage —</p>
      <p>
        The first number is the line number in the first file (""" + filename1 + """)<br />
        The second number is the line number in the second file (""" + filename2 + """)<br />
      </p>
      <p>
        Deleted words that were in the first file but not in the second will appear <span class='start_del'>like this</span>.<br />
        Inserted words that were in the second file but not in the first will appear <span class='start_ins'>like this</span>.<br />
      </p>
    </div>
    """


def output_html(args, html_content, filename1, filename2):
    # Outputs a complete HTML file
    print("""
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"
  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
    <meta http-equiv="Content-Style-Type" content="text/css" />
    <title>
      Compare """ + filename1 + " and " + filename2 + """
    </title>
    <style type="text/css">
""")

    print(diff_css())

    print("""
    </style>
  </head>
<body>
""")

    print("<h1>" + filename1 + " and " + filename2 + "</h1>")
    print(html_usage(filename1, filename2))
    print('<p>Custom CSS added on command line: ' + " ".join(args.css) + '</p>')

    print(html_content)
    print("""
  </body>
</html>
""")

def main():

    parser = argparse.ArgumentParser(description='Diff text document for PGDP PP.')

    parser.add_argument('filename', metavar='FILENAME', type=str,
                        help='input text file', nargs=2)
    parser.add_argument('--ignore-format', action='store_true', default=False,
                        help='Silence formating differences')
    parser.add_argument('--suppress-footnote-tags', action='store_true', default=False,
                        help='Suppress "[Footnote ?:" marks')
    parser.add_argument('--suppress-illustration-tags', action='store_true', default=False,
                        help='Suppress "[Illustration:" marks')
    parser.add_argument('--with-sidenote-tags', action='store_true', default=False,
                        help="HTML: add [Sidenote: ...]")
    parser.add_argument('--ignore-case', action='store_true', default=False,
                        help='Ignore case when comparing')
    parser.add_argument('--extract-footnotes', action='store_true', default=False,
                        help='Extract and process footnotes separately')
    parser.add_argument('--ignore-0-space', action='store_true', default=False,
                        help='HTML: suppress zero width space (U+200b)')
    parser.add_argument('--suppress-nbsp-num', action='store_true', default=False,
                        help="Suppress non-breakable spaces between numbers")
    parser.add_argument('--css-smcap', type=str, default=None,
                        help="HTML: Transform small caps into uppercase (U), lowercase (L) or title (T)")
    parser.add_argument('--css-bold', type=str, default=None,
                        help="HTML: Surround bold strings with this string")
    parser.add_argument('--css', type=str, default=[], action='append',
                        help="HTML: Insert transformation CSS")
    parser.add_argument('--suppress-proofers-notes', action='store_true', default=False,
                        help="In Px/Fx versions, remove [**proofreaders notes]")
    parser.add_argument('--regroup-split-words', action='store_true', default=False,
                        help="In Px/Fx versions, regroup split wo-* *rds")
    parser.add_argument('--css-greek-title-plus', action='store_true', default=False,
                        help="HTML: use greek transliteration in title attribute")
    parser.add_argument('--css-add-illustration', action='store_true', default=False,
                        help="HTML: add [Illustration ] tag")
    parser.add_argument('--css-no-default', action='store_true', default=False,
                        help="HTML: do not use default transformation CSS")
    parser.add_argument('--without-html-header', action='store_true', default=False,
                        help="HTML: do not output html header and footer")
    parser.add_argument('--txt-cleanup-type', type=str, default='b',
                        help="TXT: Type of text cleaning -- (b)est effort, (n)one, (p)roofers")

    args = parser.parse_args()

    x = CompPP(args)
    html_content, fn1, fn2 = x.do_process()

    output_html(args, html_content, fn1, fn2)

if __name__ == '__main__':
    main()
