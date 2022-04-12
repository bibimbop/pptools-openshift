"""
ppcomp.py - compare text from 2 files, ignoring html and formatting differences, for use by users
of Distributed Proofreaders (https://www.pgdp.net)

Applies various transformations according to program options before passing the files to the Linux
program dwdiff.

Copyright (C) 2012-2013, 2021 bibimbop at pgdp

Modified March 2022 by Robert Tonsing, per GPL section 5

Originally written as the standalone program comp_pp.py by bibimbop at PGDP as part of his PPTOOLS
program. It is used as part of the PP Workbench with permission.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

import argparse
import os
import re
import subprocess
import tempfile
import warnings

import cssselect
import tinycss
from lxml import etree
from lxml.html import html5parser

PG_EBOOK_START = '*** START OF'
PG_EBOOK_END = '*** END OF'
DEFAULT_TRANSFORM_CSS = '''
  /* Italics */
  i::before, cite::before, em::before,
  i::after, cite::after, em::after { content: "_"; }

  /* Add spaces around td tags */
  td::before, td::after { content: " "; }
  
  /* Remove thought breaks */
  .tb { display: none; }

  /* Add space before br tags */
  br::before { content: " "; }

  /* Remove page numbers. It seems every PP has a different way. */
  span[class^="pagenum"],
  p[class^="pagenum"],
  div[class^="pagenum"],
  span[class^="pageno"],
  p[class^="pageno"],
  div[class^="pageno"],
  p[class^="page"],
  span[class^="pgnum"],
  div[id^="Page_"] { display: none }

  /* Superscripts, subscripts */
  sup { text-transform:superscript; }
  sub { text-transform:subscript; }
'''
# CSS used to display the diffs
DIFF_CSS = '''
body {
  margin-left: 5%;
  margin-right: 5%;
}
ins, del {
  text-decoration: none;
  border: 1px solid black;
  background-color: whitesmoke;
  font-size: larger;
}
ins, .second { color: green; }
del, .first { color: purple; }
.lineno { margin-right: 1em; }
.bbox {
  margin-left: auto;
  margin-right: auto;
  border: 1px dashed;
  padding: 0 1em;
  background-color: lightcyan;
  width: 90%;
  max-width: 50em;
}
h1, .center { text-align: center; }
/* Use a CSS counter to number each diff. */
body { counter-reset: diff; } /* set diff counter to 0 */
hr::before {
  counter-increment: diff; /* inc the diff counter ... */
  content: "Diff " counter(diff) ": "; /* ... and display it */
}
.error-border {
  border-style: double;
  border-color: red;
  border-width: 15px;
}
'''
"""Note that 'º' and 'ª' are ordinals, assume they would be entered as-is, not superscript"""
SUPERSCRIPTS = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ',
    'A': 'ᴬ', 'B': 'ᴮ', 'D': 'ᴰ', 'E': 'ᴱ', 'G': 'ᴳ',
    'H': 'ᴴ', 'I': 'ᴵ', 'J': 'ᴶ', 'K': 'ᴷ', 'L': 'ᴸ',
    'M': 'ᴹ', 'N': 'ᴺ', 'O': 'ᴼ', 'P': 'ᴾ', 'R': 'ᴿ',
    'T': 'ᵀ', 'U': 'ᵁ', 'V': 'ⱽ', 'W': 'ᵂ', 'Æ': 'ᴭ', 'œ': 'ꟹ'
}
SUBSCRIPTS = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
    'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
    'v': 'ᵥ', 'x': 'ₓ'
}


def to_superscript(text):
    """Convert to unicode superscripts"""
    result = ''
    for char in text:
        try:
            result += SUPERSCRIPTS[char]
        except KeyError:
            return text  # can't convert, just leave it
    return result


def to_subscript(text):
    """Convert to unicode subscripts"""
    result = ''
    for char in text:
        try:
            result += SUBSCRIPTS[char]
        except KeyError:
            return text  # can't convert, just leave it
    return result


class PgdpFile:
    """Base class: Store and process a DP text or html file"""

    def __init__(self, args):
        self.args = args
        self.basename = ''
        self.text = ''  # file text
        self.start_line = 0  # line text started, before stripping boilerplate and/or head
        self.footnotes = ''  # footnotes text, if extracted

    def load(self, filename):
        """Load a file (text or html)
        Args:
            filename: file pathname
        Vars:
            self.text = contents of file
            self.basename = file base name
        Raises:
            IOError: unable to open file
            SyntaxError: file too short
        """
        self.basename = os.path.basename(filename)
        try:
            with open(filename, 'r', encoding='utf-8') as file:
                self.text = file.read()
        except UnicodeError:
            with open(filename, 'r', encoding='latin-1') as file:
                self.text = file.read()
        except FileNotFoundError as ex:
            raise FileNotFoundError("Cannot load file: " + filename) from ex
        if len(self.text) < 10:
            raise SyntaxError("File is too short: " + filename)

    def strip_pg_boilerplate(self):
        """Remove the PG header and footer from the text if present."""
        raise NotImplementedError("Override this method")

    def cleanup(self):
        """Remove tags from the file"""
        raise NotImplementedError("Override this method")


class PgdpFileText(PgdpFile):
    """Store and process a DP text file"""

    def __init__(self, args):
        super().__init__(args)
        self.from_pgdp_rounds = False  # THIS file is from proofing rounds

    def load(self, filename):
        """Load the file"""
        if not filename.lower().endswith('.txt'):
            raise SyntaxError("Not a text file: " + filename)
        super().load(filename)

    def strip_pg_boilerplate(self):
        """Remove the PG header and footer from the text if present."""
        new_text = []
        start_found = False
        for lineno, line in enumerate(self.text.splitlines(), start=1):
            # Find the markers. Unfortunately PG lacks consistency
            if line.startswith(PG_EBOOK_START):
                start_found = True
            if start_found and line.endswith("***"):  # may take multiple lines
                new_text = []  # PG found, remove previous lines
                self.start_line = lineno + 1
                start_found = False
            elif line.startswith(PG_EBOOK_END):
                break  # ignore following lines
            else:
                new_text.append(line)
        self.text = '\n'.join(new_text)

    def remove_paging(self):
        """Remove page markers & blank pages"""
        self.text = re.sub(r"-----File: \w+.png.*", '', self.text)
        self.text = self.text.replace("[Blank Page]", '')

    def remove_block_markup(self):
        """Remove block markup"""
        for markup in ['/*', '*/', '/#', '#/', '/P', 'P/', '/F', 'F/', '/X', 'X/']:
            self.text = self.text.replace('\n' + markup + '\n', '\n\n')

    def remove_formatting(self):
        """Ignore or replace italics and bold tags in file from rounds"""
        if self.args.ignore_format:
            for tag in ['<i>', '</i>', '<b>', '</b>']:
                self.text = self.text.replace(tag, '')
        else:
            for tag in ['<i>', '</i>']:
                self.text = self.text.replace(tag, '_')
            for tag in ['<b>', '</b>']:
                self.text = self.text.replace(tag, self.args.css_bold)
        # remove other markup
        self.text = re.sub('<.*?>', '', self.text)

    def suppress_proofers_notes(self):
        """suppress proofers notes in file from rounds"""
        if self.args.suppress_proofers_notes:
            self.text = re.sub(r"\[\*\*[^]]*?]", '', self.text)

    def regroup_split_words(self):
        """Regroup split words, must run remove page markers 1st"""
        if self.args.regroup_split_words:
            word_splits = {r"(\w+)-\*(\n+)\*": r"\n\1",  # followed by 0 or more blank lines
                           r"(\w+)-\*(\w+)": r"\1\2"}  # same line
            for key, value in word_splits.items():
                self.text = re.sub(key, value, self.text)

    def ignore_format(self):
        """Remove italics and bold markers in proofed file"""
        if self.args.ignore_format:
            self.text = re.sub(r"_((.|\n)+?)_", r'\1', self.text)
            self.text = re.sub(r"=((.|\n)+?)=", r'\1', self.text)

    def remove_thought_breaks(self):
        """Remove thought breaks (5 spaced asterisks)"""
        self.text = re.sub(r"\n\s+\*\s+\*\s+\*\s+\*\s+\*\s+\n", '\n\n', self.text)
        self.text = re.sub(r"\n\s+•\s+•\s+•\s+•\s+•\s+", '\n\n', self.text)

    def suppress_footnote_tags(self):
        """Remove footnote tags"""
        if self.args.ignore_format or self.args.suppress_footnote_tags:
            self.text = re.sub(r"[\[]*Footnote ([\d\w]+):\s([^]]*?)[\]]*", r"\1 \2", self.text,
                               flags=re.MULTILINE)
            self.text = re.sub(r"\*\[Footnote:\s([^]]*?)]", r'\1', self.text, flags=re.MULTILINE)

    def suppress_illustration_tags(self):
        """Remove illustration tags"""
        if self.args.ignore_format or self.args.suppress_illustration_tags:
            self.text = re.sub(r"\[Illustration?:([^]]*?)]", r'\1', self.text, flags=re.MULTILINE)
            self.text = self.text.replace("[Illustration]", '')

    def suppress_sidenote_tags(self):
        """Remove sidenote tags"""
        if self.args.ignore_format or self.args.suppress_sidenote_tags:
            self.text = re.sub(r"\[Sidenote:([^]]*?)]", r'\1', self.text, flags=re.MULTILINE)

    @staticmethod
    def match_to_superscript(match):
        """Convert regex match to subscript"""
        return to_superscript(match.group(1))

    def superscripts(self):
        """Convert ^{} tagged text"""
        self.text = re.sub(r"\^{?([\w\d]+)}?", PgdpFileText.match_to_superscript, self.text)

    @staticmethod
    def match_to_subscript(match):
        """Convert regex match to subscript"""
        return to_subscript(match.group(1))

    def subscripts(self):
        """Convert _{} tagged text"""
        self.text = re.sub(r"_{([\w\d]+)}", PgdpFileText.match_to_subscript, self.text)

    def cleanup(self):
        """Perform cleanup for this type of file"""
        if self.from_pgdp_rounds:
            if self.args.txt_cleanup_type == 'n':  # none
                return
            # remove page markers & blank pages
            self.remove_paging()
            if self.args.txt_cleanup_type == 'p':  # proofers, all done
                return
            # else 'b' best effort
            self.remove_block_markup()
            self.remove_formatting()
            self.suppress_proofers_notes()
            self.regroup_split_words()
        else:  # processed text file
            self.strip_pg_boilerplate()
            self.ignore_format()
            self.remove_thought_breaks()

        # all text files
        if self.args.extract_footnotes:
            if self.from_pgdp_rounds:  # always [Footnote 1: text]
                self.extract_footnotes_pgdp()
            else:  # probably [1] text
                self.extract_footnotes_pp()
        else:
            self.suppress_footnote_tags()
        self.suppress_illustration_tags()
        self.suppress_sidenote_tags()
        self.superscripts()
        self.subscripts()

    def extract_footnotes_pgdp(self):
        """ Extract the footnotes from an F round text file
        Start with [Footnote #: and finish with ] at the end of a line
        """
        in_footnote = False  # currently processing a footnote
        text = []  # new text without footnotes
        footnotes = []

        for line in self.text.splitlines():
            if '[Footnote' in line:  # New footnote?
                in_footnote = True
                if '*[Footnote' not in line:  # Join to previous?
                    footnotes.append('')  # start new footnote
                line = re.sub(r'\*?\[Footnote\s?[\w\d]*:\s?', '', line)
            if in_footnote:  # Inside a footnote?
                footnotes[-1] = '\n'.join([footnotes[-1], line])
                if line.endswith(']'):  # End of footnote?
                    footnotes[-1] = footnotes[-1][:-1]
                    in_footnote = False
                elif line.endswith(']*'):  # Footnote continuation
                    footnotes[-1] = footnotes[-1][:-2]
                    in_footnote = False
            else:
                text.append(line)

        self.text = '\n'.join(text)  # Rebuild text, now without footnotes
        self.footnotes = '\n'.join(footnotes)

    def extract_footnotes_pp(self):
        """Extract footnotes from a PP text file. Text is iterable. Returns the text as an iterable,
        without the footnotes, and footnotes as a list of (footnote string id, line number of the
        start of the footnote, list of strings comprising the footnote). fn_regexes is a list of
        (regex, fn_type) that identify the beginning and end of a footnote. The fn_type is 1 when
        a ] terminates it, or 2 when a new block terminates it.
        """
        fn_regexes = [(r"\s*\[([\w-]+)\]\s*(.*)", 1),
                      (r"(\s*)\[Note (\d+):( .*|$)", 2),
                      (r"(      )Note (\d+):( .*|$)", 1)]
        regex_count = [0] * len(fn_regexes)  # i.e. [0, 0, 0]
        text_lines = self.text.splitlines()
        for block, empty_lines in self.get_block(text_lines):
            if not block:
                continue
            for i, (regex, fn_type) in enumerate(fn_regexes):
                matches = re.match(regex, block[0])
                if matches:
                    regex_count[i] += 1
                    break
        # Pick the regex with the most matches
        fn_regexes = [fn_regexes[regex_count.index(max(regex_count))]]

        # Different types of footnote. 0 means not in footnote.
        cur_fn_type, cur_fn_indent = 0, 0
        footnotes = []
        text = []
        prev_block = None

        for block, empty_lines in self.get_block(text_lines):
            # Is the block a new footnote?
            next_fn_type = 0
            if len(block):
                for (regex, fn_type) in fn_regexes:
                    matches = re.match(regex, block[0])
                    if matches:
                        if matches.group(2).startswith('Illustration'):
                            # An illustration, possibly inside a footnote. Treat
                            # as part of text or footnote.
                            continue
                        next_fn_type = fn_type
                        # Update first line of block, because we want the number outside.
                        block[0] = matches.group(3)
                        break

            # Try to close previous footnote
            next_fn_indent = None
            if cur_fn_type:
                if next_fn_type:
                    # New block is footnote, so it ends the previous footnote
                    footnotes += prev_block + ['']
                    text += [''] * (len(prev_block) + 1)
                    cur_fn_type, cur_fn_indent = next_fn_type, next_fn_indent
                elif block[0].startswith(cur_fn_indent):
                    # Same indent or more. This is a continuation. Merge with one empty line.
                    block = prev_block + [''] + block
                else:
                    # End of footnote - current block is not a footnote
                    footnotes += prev_block + ['']
                    text += [''] * (len(prev_block) + 1)
                    cur_fn_type = 0
            if not cur_fn_type and next_fn_type:
                # Account for new footnote
                cur_fn_type, cur_fn_indent = next_fn_type, next_fn_indent
            if cur_fn_type and (empty_lines >= 2 or
                                (cur_fn_type == 2 and block[-1].endswith("]"))):
                # End of footnote
                if cur_fn_type == 2 and block[-1].endswith("]"):
                    # Remove terminal bracket
                    block[-1] = block[-1][:-1]
                footnotes += block
                text += [''] * (len(block))
                cur_fn_type = 0
                block = None
            if not cur_fn_type:
                # Add to text, with white lines
                text += (block or []) + [''] * empty_lines
                footnotes += [''] * (len(block or []) + empty_lines)

            prev_block = block
        # Rebuild text, now without footnotes
        self.text = '\n'.join(text)
        self.footnotes = '\n'.join(footnotes)

    @staticmethod
    def get_block(pp_text):
        """Generator to get a block of text, followed by the number of empty lines."""
        empty_lines = 0
        block = []
        for line in pp_text:
            if len(line):
                if empty_lines:  # one or more empty lines will stop a block
                    yield block, empty_lines
                    block = []
                    empty_lines = 0
                block += [line]
            else:
                empty_lines += 1
        yield block, empty_lines


class PgdpFileHtml(PgdpFile):
    """Store and process a DP html file."""

    def __init__(self, args):
        super().__init__(args)
        self.tree = None
        self.mycss = ''

    def parse_html5(self):
        """Parse an HTML5 doc"""
        # ignore warning caused by "xml:lang"
        warnings.filterwarnings('ignore', message='Coercing non-XML name: xml:lang')
        # don't include namespace in elements
        myparser = html5parser.HTMLParser(namespaceHTMLElements=False)
        # without parser this works for all html, but we have to remove namespace
        # & don't get the errors list
        tree = html5parser.document_fromstring(self.text, parser=myparser)
        return tree.getroottree(), myparser.errors

    def parse_html(self):
        """Parse a non-HTML5 doc"""
        myparser = etree.HTMLParser()
        tree = etree.fromstring(self.text, parser=myparser)
        # HTML parser rejects tags with both id and name: (513 == DTD_ID_REDEFINED)
        # even though https://www.w3.org/TR/html4/struct/links.html#edef-A says it is OK
        errors = [x for x in myparser.error_log
                  if myparser.error_log[0].type != 513]
        return tree.getroottree(), errors

    def load(self, filename):
        """Load the file. If parsing succeeded, then self.tree is set, and parser.errors is []"""
        if not filename.lower().endswith(('.html', '.htm', '.xhtml')):
            raise SyntaxError('Not an html file: ' + filename)
        super().load(filename)
        try:
            if 0 <= self.text.find('<!DOCTYPE html>', 0, 100):  # limit search
                self.tree, errors = self.parse_html5()
            else:
                self.tree, errors = self.parse_html()
        except Exception as ex:
            raise SyntaxError('File cannot be parsed: ' + filename) from ex
        if errors:
            for error in errors:
                print(error)
            raise SyntaxError('Parsing errors in document: ' + filename)

        # save line number of <body> tag - actual text start
        # html5parser does not fill in the source line number
        for lineno, line in enumerate(self.text.splitlines(), start=-1):
            if '<body' in line:
                self.start_line = lineno
                break

        # remove the head - we only want the body
        head = self.tree.find('head')
        if head is not None:
            head.getparent().remove(head)

    def strip_pg_boilerplate(self):
        """Remove the PG header and footer from the text if present."""
        if -1 == self.text.find(PG_EBOOK_START):
            return
        # start: from <body to <div>*** START OF THE ...</div>
        # end: from <div>*** END OF THE ...</div> to </body
        start_found = False
        end_found = False
        for node in self.tree.find('body').iter():
            if node.tag == 'div' and node.text and node.text.startswith(PG_EBOOK_START):
                start_found = True
                node.text = ''
                node.tail = ''
            elif node.tag == 'div' and node.text and node.text.startswith(PG_EBOOK_END):
                end_found = True
            if end_found or not start_found:
                node.text = ''
                node.tail = ''
        # we need the start line, html5parser does not save source line
        for lineno, line in enumerate(self.text.splitlines(), start=1):
            if PG_EBOOK_START in line:
                self.start_line = lineno + 1
                break

    def css_smallcaps(self):
        """Transform small caps"""
        transforms = {'U': 'uppercase',
                      'L': 'lowercase',
                      'T': 'capitalize'}
        if self.args.css_smcap in transforms:
            self.mycss += f".smcap {{ text-transform:{transforms[self.args.css_smcap]}; }}"

    def css_bold(self):
        """Surround bold strings with this string"""
        self.mycss += 'b::before, b::after { content: "' + self.args.css_bold + '"; }'

    def css_illustration(self):
        """Add [Illustration: ...] markup"""
        if self.args.css_add_illustration:
            for figclass in ['figcenter', 'figleft', 'figright']:
                self.mycss += '.' + figclass + '::before { content: "[Illustration: "; }'
                self.mycss += '.' + figclass + '::after { content: "]"; }'

    def css_sidenote(self):
        """Add [Sidenote: ...] markup"""
        if self.args.css_add_sidenote:
            self.mycss += '.sidenote::before { content: "[Sidenote: "; }'
            self.mycss += '.sidenote::after { content: "]"; }'

    def css_greek_title_plus(self):
        """Greek: if there is a title, use it to replace the (grc=ancient) Greek."""
        if self.args.css_greek_title_plus:
            self.mycss += '*[lang=grc] { content: "+" attr(title) "+"; }'

    def css_custom_css(self):
        """--css can be present multiple times, so it's a list"""
        for css in self.args.css:
            self.mycss += css

    def remove_nbspaces(self):
        """Remove non-breakable spaces between numbers. For instance, a
        text file could have 250000, and the html could have 250 000.
        """
        # Todo: &nbsp;, &#160;, &#x00A0;?
        if self.args.suppress_nbsp_num:
            self.text = re.sub(r"(\d)\u00A0(\d)", r"\1\2", self.text)

    def remove_soft_hyphen(self):
        """Suppress shy (soft hyphen)"""
        # Todo: &#173;, &#x00AD;?
        self.text = re.sub(r"\u00AD", r"", self.text)

    def cleanup(self):
        """Perform cleanup for this type of file - build up a list of CSS transform rules,
        process them against tree, then convert to text.
        """
        self.strip_pg_boilerplate()
        # load default CSS for transformations
        if not self.args.css_no_default:
            self.mycss = DEFAULT_TRANSFORM_CSS
        self.css_smallcaps()
        self.css_bold()
        self.css_illustration()
        self.css_sidenote()
        self.css_custom_css()
        self.process_css()  # process transformations

        self.extract_footnotes()

        # Transform html into text for character search.
        self.text = etree.XPath("string(/)")(self.tree)

        self.remove_nbspaces()
        self.remove_soft_hyphen()

    @staticmethod
    def _text_transform(val, errors: list):
        """Transform smcaps"""
        if len(val.value) != 1:
            errors += [(val.line, val.column, val.name + " takes 1 argument")]
        else:
            value = val.value[0].value
            if value == 'uppercase':
                return lambda x: x.upper()
            if value == 'lowercase':
                return lambda x: x.lower()
            if value == 'capitalize':
                return lambda x: x.title()
            if value == 'superscript':
                return lambda x: to_superscript(x)
            if value == 'subscript':
                return lambda x: to_subscript(x)
            errors += [(val.line, val.column,
                        val.name + " accepts only 'uppercase', 'lowercase', 'capitalize',"
                                   " 'superscript', or 'subscript'")]
        return None

    @staticmethod
    def _text_replace(val, errors: list):
        """Skip S (spaces) tokens"""
        values = [v for v in val.value if v.type != "S"]
        if len(values) != 2:
            errors += [(val.line, val.column, val.name + " takes 2 string arguments")]
            return None
        return lambda x: x.replace(values[0].value, values[1].value)

    @staticmethod
    def _text_move(val, errors: list):
        """Move a node"""
        values = [v for v in val.value if v.type != "S"]
        if len(values) < 1:
            errors += [(val.line, val.column, val.name + " takes at least one argument")]
            return None
        f_move = []
        for value in values:
            if value.value == 'parent':
                f_move.append(lambda el: el.getparent())
            elif value.value == 'prev-sib':
                f_move.append(lambda el: el.getprevious())
            elif value.value == 'next-sib':
                f_move.append(lambda el: el.getnext())
            else:
                errors += [(val.line, val.column, val.name + " invalid value " + value.value)]
                f_move = None
                break
        return f_move

    def process_css(self):
        """Process each rule from our transformation CSS"""
        stylesheet = tinycss.make_parser().parse_stylesheet(self.mycss)
        property_errors = []

        def _move_element(elem, move_list):
            """Move elem in tree"""
            parent = elem.getparent()
            new = elem
            for item in move_list:
                new = item(new)
            # move the tail to the sibling or the parent
            if elem.tail:
                sibling = elem.getprevious()
                if sibling:
                    sibling.tail = (sibling.tail or '') + elem.tail
                else:
                    parent.text = (parent.text or '') + elem.tail
                elem.tail = None
            # prune and graft
            parent.remove(elem)
            new.append(elem)

        def _process_element(elem, val):
            """replace text with content of an attribute."""
            if val.name == 'content':
                v_content = self.new_content(elem, val)
                if selector.pseudo_element == 'before':
                    elem.text = v_content + (elem.text or '')  # opening tag
                elif selector.pseudo_element == 'after':
                    elem.tail = v_content + (elem.tail or '')  # closing tag
                else:  # replace all content
                    elem.text = self.new_content(elem, val)
            elif f_replace_with_attr:
                elem.text = f_replace_with_attr(elem)
            elif f_transform:
                self.text_apply(elem, f_transform)
            elif f_element_func:
                f_element_func(elem)
            elif f_move:
                _move_element(elem, f_move)

        for rule in stylesheet.rules:
            # extract values we care about
            f_transform = None
            f_replace_with_attr = None
            f_element_func = None
            f_move = []

            for value in rule.declarations:
                if value.name == 'content':
                    pass  # result depends on element and pseudo elements
                elif value.name == 'text-transform':
                    f_transform = self._text_transform(value, property_errors)
                elif value.name == 'text-replace':
                    f_transform = self._text_replace(value, property_errors)
                elif value.name == '_replace_with_attr':
                    def f_replace_with_attr(elem):
                        return elem.attrib[value.value[0].value]
                elif value.name == 'display':
                    # support display none only. So ignore "none" argument
                    f_element_func = PgdpFileHtml.clear_element
                elif value.name == '_graft':
                    f_move = self._text_move(value, property_errors)
                else:
                    property_errors += [(value.line, value.column, "Unsupported property "
                                         + value.name)]
                    continue

                # iterate through each selector in the rule
                for selector in cssselect.parse(rule.selector.as_css()):
                    xpath = cssselect.HTMLTranslator().selector_to_xpath(selector)
                    find = etree.XPath(xpath)
                    # find each matching elem in the HTML document
                    for element in find(self.tree):
                        _process_element(element, value)

        return self.css_errors(stylesheet.errors, property_errors)

    def css_errors(self, stylesheet_errors, property_errors):
        """Collect transformation CSS errors"""
        css_errors = ''
        if stylesheet_errors or property_errors:
            css_errors = "<div class='error-border bbox'><p>Error(s) in the" \
                         "  transformation CSS:</p><ul>"
            i = 0
            # if the default css is included, take the offset into account
            if not self.args.css_no_default:
                i = DEFAULT_TRANSFORM_CSS.count('\n')
            for err in stylesheet_errors:
                css_errors += f"<li>{err.line - i},{err.column}: {err.reason}</li>"
            for err in property_errors:
                css_errors += f"<li>{err[0] - i},{err[1]}: {err[2]}</li>"
            css_errors += "</ul>"
        return css_errors

    @staticmethod
    def new_content(elem, val):
        """Process the "content:" property"""

        def _escaped_unicode(element):
            try:
                return bytes(element.group(0), 'utf8').decode('unicode-escape')
            except UnicodeDecodeError:
                return element.group(0)

        escaped_unicode_re = re.compile(r"\\u[0-9a-fA-F]{4}")
        result = ""
        for token in val.value:
            if token.type == "STRING":  # e.g. { content: "xyz" }
                result += escaped_unicode_re.sub(_escaped_unicode, token.value)
            elif token.type == "FUNCTION":
                if token.function_name == 'attr':  # e.g. { content: attr(title) }
                    result += elem.attrib.get(token.content[0].value, "")
            elif token.type == "IDENT":
                if token.value == "content":  # identity, e.g. { content: content }
                    result += elem.text
        return result

    @staticmethod
    def text_apply(tree_elem, func):
        """Apply a function to every sub-element's .text and .tail, and element's .text"""
        if tree_elem.text:
            tree_elem.text = func(tree_elem.text)
        for sub in tree_elem.iter():
            if sub == tree_elem:
                continue
            if sub.text:
                sub.text = func(sub.text)
            if sub.tail:
                sub.tail = func(sub.tail)

    @staticmethod
    def clear_element(element):
        """In an XHTML tree, remove all sub-elements of a given element"""
        tail = element.tail
        element.clear()
        element.tail = tail

    def extract_footnotes(self):
        """Extract the footnotes"""

        def strip_note_tag(string):
            """Remove note tag and number. "Note 123: lorem ipsum" becomes "lorem ipsum"."""
            for regex in [r"\s*\[([\w-]+)\](.*)",
                          r"\s*([\d]+)\s+(.*)",
                          r"\s*([\d]+):(.*)",
                          r"\s*Note ([\d]+):\s+(.*)"]:
                match = re.match(regex, string, re.DOTALL)
                if match:
                    return match.group(2)
            return string  # That may be bad

        if not self.args.extract_footnotes:
            return
        footnotes = []
        # Special case for PPers who do not keep the marking around
        # the whole footnote. They only mark the first paragraph.
        elements = etree.XPath("//div[@class='footnote']")(self.tree)
        if len(elements) == 1:
            # remove footnote number & remove footnote from main document
            footnotes += [strip_note_tag(elements[0].xpath("string()"))]
            elements[0].getparent().remove(elements[0])
        else:
            for find in ["//div[@class='footnote']",
                         "//div[@id[starts-with(.,'FN_')]]",
                         "//p[a[@id[starts-with(.,'Footnote_')]]]",
                         "//div/p[span/a[@id[starts-with(.,'Footnote_')]]]",
                         "//p[@class='footnote']"]:
                for element in etree.XPath(find)(self.tree):
                    # remove footnote number & remove footnote from main document
                    footnotes += [strip_note_tag(element.xpath("string()"))]
                    element.getparent().remove(element)
                if footnotes:  # found them, stop now
                    break
        self.footnotes = "\n".join(footnotes)  # save as text string


class PPComp:
    """Compare two files."""

    def __init__(self, args):
        self.args = args

    def do_process(self):
        """Main routine: load & process the files"""
        files = [None, None]
        for i, fname in enumerate(self.args.filename):
            if fname.lower().endswith(('.html', '.htm', '.xhtml')):
                files[i] = PgdpFileHtml(self.args)
            else:
                files[i] = PgdpFileText(self.args)
            files[i].load(fname)
            files[i].cleanup()  # perform cleanup for each type of file

        # perform common cleanup for both files
        self.check_characters(files)

        # Compare the two versions
        main_diff = self.compare_texts(files[0].text, files[1].text)
        if self.args.extract_footnotes:
            fnotes_diff = self.compare_texts(files[0].footnotes, files[1].footnotes)
        else:
            fnotes_diff = ""
        html_content = self.create_html(files, main_diff, fnotes_diff)
        return html_content, files[0].basename, files[1].basename

    def compare_texts(self, text1, text2):
        """Compare two sources, using dwdiff"""
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8') as temp1, \
                tempfile.NamedTemporaryFile(mode='w', encoding='utf-8') as temp2:
            temp1.write(text1)
            temp1.flush()
            temp2.write(text2)
            temp2.flush()
            repo_dir = os.environ.get('OPENSHIFT_DATA_DIR', '')
            if repo_dir:
                dwdiff_path = os.path.join(repo_dir, 'bin', 'dwdiff')
            else:
                dwdiff_path = 'dwdiff'

            # -P Use punctuation characters as delimiters.
            # -R Repeat the begin and end markers at the start and end of line if a change crosses
            #    a newline.
            # -C 2 Show <num> lines of context before and after each changes.
            # -L Show line numbers at the start of each line.
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
                cmd += ["--ignore-case"]
            cmd += [temp1.name, temp2.name]
            with subprocess.Popen(cmd, stdout=subprocess.PIPE) as process:
                return process.stdout.read().decode('utf-8')

    def create_html(self, files, text, footnotes):
        """Create the output html file"""

        def massage_input(txt, start0, start1):
            # Massage the input
            replacements = {"&": "&amp;",
                            "<": "&lt;",
                            ">": "&gt;",
                            "]COMPPP_START_DEL[": "<del>",
                            "]COMPPP_STOP_DEL[": "</del>",
                            "]COMPPP_START_INS[": "<ins>",
                            "]COMPPP_STOP_INS[": "</ins>"}
            newtext = txt
            for key, value in replacements.items():
                newtext = newtext.replace(key, value)
            if newtext:
                newtext = "<hr /><pre>\n" + newtext
            newtext = newtext.replace("\n--\n", "\n</pre><hr /><pre>\n")
            newtext = re.sub(r"^\s*(\d+):(\d+)",
                             lambda m: f"<span class='lineno'>{int(m.group(1)) + start0}"
                                       f" : {int(m.group(2)) + start1}</span>",
                             newtext, flags=re.MULTILINE)
            if newtext:
                newtext += "</pre>\n"
            return newtext

        # Find the number of diff sections
        diffs_text = 0
        if text:
            diffs_text = len(re.findall("\n--\n", text)) + 1
            # Text, with correct (?) line numbers
            text = massage_input(text, files[0].start_line, files[1].start_line)
        html_content = "<div>"
        if diffs_text == 0:
            html_content += "<p>There is no diff section in the main text.</p>"
        elif diffs_text == 1:
            html_content += "<p>There is 1 diff section in the main text.</p>"
        else:
            html_content += f"<p>There are <b>{diffs_text}</b> diff sections in the main text.</p>"

        if footnotes:
            diffs_footnotes = len(re.findall("\n--\n", footnotes or "")) + 1
            # Footnotes - line numbers are meaningless right now. We could fix that.
            footnotes = massage_input(footnotes, 0, 0)
            html_content += "<p>Footnotes are diff'ed separately <a href='#footnotes'>here</a></p>"
            if diffs_footnotes == 0:
                html_content += "<p>There is no diff section in the footnotes.</p>"
            elif diffs_footnotes == 1:
                html_content += "<p>There is 1 diff section in the footnotes.</p>"
            else:
                html_content += f"<p>There are {diffs_footnotes}" \
                                " diff sections in the footnotes.</p>"
        else:
            if self.args.extract_footnotes:
                html_content += "<p>There is no diff section in the footnotes.</p>"

        if diffs_text:
            html_content += "<h2>Main text</h2>"
            html_content += text
        if footnotes:
            html_content += "<h2 id='footnotes'>Footnotes</h2>"
            html_content += "<pre>" + footnotes + "</pre>"
        html_content += "</div>"
        return html_content

    def simple_html(self):
        """Debugging only, transform the html and print the text output"""
        if not self.args.filename[0].lower().endswith(('.html', '.htm')):
            print('Error: 1st file must be an html file')
            return
        html_file = PgdpFileHtml(self.args)
        html_file.load(self.args.filename[0])
        html_file.cleanup()
        print(html_file.text)
        with open('outhtml.txt', 'w', encoding='utf-8') as file:
            file.write(html_file.text)

    @staticmethod
    def check_characters(files):
        """Check whether each file has the 'best' character. If not, convert.
        This is used for instance if one version uses curly quotes while the other uses straight.
        In that case, we need to convert one into the other, to get a smaller diff.
        """
        character_checks = {
            '’': "'",  # close curly single quote to straight
            '‘': "'",  # open curly single quote to straight
            '”': '"',  # close curly double quote to straight
            '“': '"',  # open curly double quote to straight
            '–': '-',  # en dash to hyphen
            '—': '--',  # em dash to double hyphen
            '⁄': '/',  # fraction slash
            "′": "'",  # prime
            '″': "''",  # double prime
            '‴': "'''",  # triple prime
            '½': '-1/2',
            '¼': '-1/4',
            '¾': '-3/4'
        }
        for char_best, char_other in character_checks.items():
            finds_0 = files[0].text.find(char_best)
            finds_1 = files[1].text.find(char_best)
            if finds_0 >= 0 and finds_1 >= 0:  # Both have it
                continue
            if finds_0 == -1 and finds_1 == -1:  # Neither has it
                continue
            # Downgrade one version
            if finds_0 >= 0:
                files[0].text = files[0].text.replace(char_best, char_other)
            else:
                files[1].text = files[1].text.replace(char_best, char_other)
        if files[0].footnotes and files[1].footnotes:
            for char_best, char_other in character_checks.items():
                finds_0 = files[0].footnotes.find(char_best)
                finds_1 = files[1].footnotes.find(char_best)
                if finds_0 >= 0 and finds_1 >= 0:  # Both have it
                    continue
                if finds_0 == -1 and finds_1 == -1:  # Neither has it
                    continue
                if finds_0 >= 0:
                    files[0].footnotes = files[0].footnotes.replace(char_best, char_other)
                else:
                    files[1].footnotes = files[1].footnotes.replace(char_best, char_other)


# noinspection PyPep8
def html_usage(filename1, filename2):
    """Describe how to use the diffs"""
    # noinspection PyPep8
    return f"""
    <div class="bbox">
      <p class="center">— Note —</p>
      <p>The first number is the line number in the first file (<b>{filename1}</b>)<br />
        The second number is the line number in the second file (<b>{filename2}</b>)<br />
        Line numbers can sometimes be very approximate.</p>
      <p>Deleted words that were in the first file but not in the second will appear <del>like
         this</del>.<br />
        Inserted words that were in the second file but not in the first will appear <ins>like
         this</ins>.</p>
    </div>
    """


def output_html(html_content, filename1, filename2, css):
    """Outputs a complete HTML file"""
    print("""
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
<head>
  <meta charset="UTF-8" />
  <title>Compare""" + filename1 + " and " + filename2 + """</title>
  <style type="text/css">
""")
    print(DIFF_CSS)
    print("""
  </style>
</head>
<body>
""")
    print(f'<h1>Diff of <span class="first">{filename1}</span> and'
          f' <span class="second">{filename2}</span></h1>')
    print(html_usage(filename1, filename2))
    if css:
        print('<p>Custom CSS added on command line: ' + " ".join(css) + '</p>')
    print(html_content)
    print("""
</body>
</html>
""")


def main():
    """Main program"""
    parser = argparse.ArgumentParser(description='Diff text/HTML documents for PGDP'
                                                 ' Post-Processors.')
    parser.add_argument('filename', metavar='FILENAME', type=str,
                        help='input files', nargs=2)
    parser.add_argument('--ignore-case', action='store_true', default=False,
                        help='Ignore case when comparing')
    parser.add_argument('--extract-footnotes', action='store_true', default=False,
                        help='Extract and process footnotes separately')
    parser.add_argument('--suppress-footnote-tags', action='store_true', default=False,
                        help='TXT: Suppress "[Footnote #:" marks')
    parser.add_argument('--suppress-illustration-tags', action='store_true', default=False,
                        help='TXT: Suppress "[Illustration:" marks')
    parser.add_argument('--suppress-sidenote-tags', action='store_true', default=False,
                        help='TXT: Suppress "[Sidenote:" marks')
    parser.add_argument('--ignore-format', action='store_true', default=False,
                        help='In Px/Fx versions, silence formatting differences')
    parser.add_argument('--suppress-proofers-notes', action='store_true', default=False,
                        help="In Px/Fx versions, remove [**proofreaders notes]")
    parser.add_argument('--regroup-split-words', action='store_true', default=False,
                        help="In Px/Fx versions, regroup split wo-* *rds")
    parser.add_argument('--txt-cleanup-type', type=str, default='b',
                        help="TXT: In Px/Fx versions, type of text cleaning -- (b)est effort,"
                             " (n)one, (p)roofers")
    parser.add_argument('--css-add-illustration', action='store_true', default=False,
                        help="HTML: add [Illustration ] tag")
    parser.add_argument('--css-add-sidenote', action='store_true', default=False,
                        help="HTML: add [Sidenote: ...]")
    parser.add_argument('--css-smcap', type=str, default=None,
                        help="HTML: Transform small caps into uppercase (U), lowercase (L) or"
                             " title case (T)")
    parser.add_argument('--css-bold', type=str, default='=',
                        help="HTML: Surround bold strings with this string")
    parser.add_argument('--css', type=str, default=[], action='append',
                        help="HTML: Insert transformation CSS")
    parser.add_argument('--css-no-default', action='store_true', default=False,
                        help="HTML: do not use default transformation CSS")
    parser.add_argument('--suppress-nbsp-num', action='store_true', default=False,
                        help="HTML: Suppress non-breakable spaces between numbers")
    parser.add_argument('--ignore-0-space', action='store_true', default=False,
                        help='HTML: suppress zero width space (U+200b)')
    parser.add_argument('--css-greek-title-plus', action='store_true', default=False,
                        help="HTML: use greek transliteration in title attribute")
    parser.add_argument('--simple-html', action='store_true', default=False,
                        help="HTML: Process just the html file and print the output (debug)")
    args = parser.parse_args()

    if args.extract_footnotes and args.suppress_footnote_tags:
        raise SyntaxError("Cannot use both --extract-footnotes and --suppress-footnote-tags")

    compare = PPComp(args)
    if args.simple_html:
        compare.simple_html()
    else:
        html_content, file1, file2 = compare.do_process()
        output_html(html_content, file1, file2, args.css)


def dumptree(tree):
    """Save tree for debug"""
    with open('tmptree.txt', 'w', encoding='utf-8') as file:
        for node in tree.iter():
            if node.text:
                file.write(node.tag + ': ' + node.text + '\n')
            else:
                file.write(node.tag + '\n')


if __name__ == '__main__':
    main()
