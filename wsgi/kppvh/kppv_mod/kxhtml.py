#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
 kppvh - various checks on xhtml
"""

from lxml import etree
import cssselect
import tinycss
import re
import os

from helpers import k_unicode

# The xml: prefix is equivalent to the following
XMLNS = "{http://www.w3.org/XML/1998/namespace}"

# List of language, indexed on the language tag, from
#   http://www.iana.org/assignments/language-subtag-registry
# Its format is record-jar -- (TODO) May be one day use a converted
#   version by https://github.com/mattcg/language-subtag-registry
def load_languages():
    with open(os.path.dirname(__file__) + "/../kppv_misc/language-subtag-registry",
              "r", encoding='utf-8') as f:

        languages = {}
        current = {}

        for line in f:
            if line.startswith('  '):
                # Continuation of previous field on a new line
                continue

            line = line.strip()

            # End of record. Store it.
            if line == '%%':
                # Some record don't have subtags
                subtag = current.get('Subtag')
                if subtag:
                    languages[subtag] = current

                current = {}
                continue

            # Ignore lines that do not have "key: value"
            try:
                key, value = line.split(': ')
            except ValueError:
                continue

            if key == 'Description':
                # Some languages have several descriptions, so concat them
                desc = current.get('Description', None)
                if desc:
                    current[key] = desc + ', ' + value
                else:
                    current[key] = value
            elif key in ['Type', 'Subtag']:
                current[key] = value

        # Last record.
        subtag = current.get('Subtag')
        if subtag:
            languages[subtag] = current

        return languages


class KXhtml(object):

    def check_css(self, myfile):
        """Find unused CSS and undefined used CCS.
        """

        # Fails on a few corner cases, such as
        #  ".tdm > tbody > tr > td:first-child + td"
        #  ".onetable td"
        #
        # Ignores @media

        # Find the CCS style
        css = myfile.tree.find('head').find('style')

        if css == None:
            return

        # The CSS can be in a comment or not
        if len(css):
            # Not sure whether that covers all the comment cases. Maybe add
            # all the children
            css_text = etree.tostring(css[0]).decode("utf8")
        else:
            css_text = css.text

        stylesheet = tinycss.make_parser().parse_stylesheet(css_text)

        # retrieve the errors
        self.cssutils_errors = ["{0},{1}: {2}".format(err.line+css.sourceline-1, err.column, err.reason) for err in stylesheet.errors]

        css_selectors = []
        for rule in stylesheet.rules:

            if rule.at_keyword is None:
                # Regular rules.
                # Add the selector as a string
                css_selectors += rule.selector.as_css().split(',')

            elif rule.at_keyword == '@media':
                # Itself is a bunch of regular rules
                for rule2 in rule.rules:
                    if rule2.at_keyword is None:
                        # Regular rules.
                        # Add the selector as a string
                        css_selectors += rule2.selector.as_css().split(',')

        css_selectors = list(set(css_selectors))

        # Find the unused/undefined CSS. It is possible 2 rules will
        # match the same class (for instance "p.foo" and ".foo" will
        # match "class=foo"). That is not detected, and both rules
        # will be valid.
        self.sel_unchecked = []
        self.sel_unused = []
        for selector in css_selectors:

            # Get the selector (eg. "body", "p", ".some_class")
            try:
                sel_xpath = cssselect.GenericTranslator().css_to_xpath(selector)
            except (cssselect.xpath.ExpressionError, cssselect.parser.SelectorSyntaxError):
                self.sel_unchecked.append(selector)
                continue

            # Retrieve where it is used in the xhtml
            occurences = etree.XPath(sel_xpath)(myfile.tree)

            if len(occurences) == 0:
                self.sel_unused.append(selector)
                continue

            # If it's from a class, find the name. It should be the
            # last word starting with a dot (eg. "p.foo", ".foo",
            # "#toc .foo" => "foo")
            #
            # Remove a pseudo selector with rsplit, if there is one.
            m = re.search(r'\.([\w-]+)$', selector.rsplit(":", 1)[0])
            if m == None:
                continue

            cl = m.group(1)
            if len(cl) == 0:
                continue

            # Mark the class wherever it is used, in each element
            for item in occurences:
                item.attrib['__used_classes'] = item.attrib.get('__used_classes', '') + ' ' + cl

        # Look for unused classes
        self.classes_undefined = []
        find = etree.XPath("//*[@class]")
        for element in find(myfile.tree):
            classes = set(element.attrib['class'].split())

            used_classes = element.attrib.get('__used_classes', None)
            if used_classes:
                # Substract content of used_classes from classes
                # leaving classes that were not matched.
                classes -= set(used_classes.split())

            # Finally, create the warning
            for cl in classes:
                self.classes_undefined.append([element.sourceline, cl])


    def check_title(self, myfile):
        """Check whether the title is built according to PG or PGDP suggestion.
        """
        self.good_format = False
        self.title = None
        self.author = None

        # Find the title and sanitize it.
        title = myfile.tree.find('head').find('title')
        if title is None or title.text is None:
            # Title can be empty -- See book #43014
            title_str = ""
        else:
            title_str = ' '.join(title.text.splitlines())
            title_str = re.sub(r"\s+", " ", title_str).strip()

        # Try the recommended format
        for regex in [r'The Project Gutenberg eBook of (.*), by (.*)$',
                      r'(.*), by (.*)\s?&mdash;\s?A Project Gutenberg eBook\.?$',
                      r'(.*), by (.*)\s?—\s?A Project Gutenberg eBook\.?$',
                      r'(.*), by (.*)\s?--\s?A Project Gutenberg eBook\.?$']:

            m = re.match(regex, title_str)
            if m:
                self.good_format = True
                self.title = m.group(1)
                self.author = m.group(2)
                return

        # Try variations
        for regex in [r"The Project Gutenberg's eBook of (.*), by (.*)$",
                      r"The Project Gutenberg eBook of (.*), by (.*)$",
                      r"The Project Gutenberg eBook of (.*), par (.*)$",
                      r"The Project Gutenberg eBook of (.*), edited by (.*)$"]:

            m = re.match(regex, title_str, flags=re.I)
            if m:
                self.title = m.group(1)
                self.author = m.group(2)
                return

        self.title = title_str


    def epub_toc(self, myfile):
        """Build the ePub table of content.
        indent will be added in front of each line, once per level.
        """

        self.toc = []

        find = etree.XPath("//h1|//h2|//h3|//h4")
        elements = find(myfile.tree)
        for element in elements:
            # Compute an offset for future indent. h1=0, h2=1, h3=2, h4=3
            level = int(element.tag[1]) - 1

            # Attribute title overrides the content
            title = element.attrib.get('title', None)
            if title is not None:
                text = ' '.join(title.splitlines())
            else:
                text = element.xpath("string()")

                # Replace series of spaces with only one space
                text = re.sub(r'\s+', ' ', text).strip()

            # Print the title with an offset and indent
            if text != "":
                self.toc.append((level, text))


    def check_document(self, myfile):
        """Check for language
        """

        # May be this does not belong here
        self.iana_languages = load_languages()

        attr = myfile.tree.getroot().attrib

        # Get the document's language
        self.document_lang = attr.get('lang', None)
        self.document_xmllang = attr.get(XMLNS + 'lang', None)

        if myfile.xhtml == 0 and self.document_lang:
            languages = set([self.document_lang])
        elif myfile.xhtml != 0 and self.document_xmllang:
            languages = set([self.document_xmllang])
        else:
            languages = set()

        # Enumerate all languages found
        lang_set = set()
        xmllang_set = set()
        for element in myfile.tree.iter():
            # With the lang attribute
            lang = element.attrib.get('lang', None)
            if lang:
                languages.add(lang)
                lang_set.add(element)

            # With the xml:lang attribute
            lang = element.attrib.get(XMLNS+'lang')
            if lang:
                languages.add(lang)
                xmllang_set.add(element)

        self.languages = sorted(list(languages))

        # Find elements with lang but not xml:lang
        self.missing_xmllang = [(element.sourceline, element.tag)
                                for element in lang_set - xmllang_set]
        self.missing_xmllang.sort()

        # Find elements with xml:lang but not lang
        self.missing_lang = [(element.sourceline, element.tag)
                             for element in xmllang_set - lang_set]
        self.missing_lang.sort()

        # Find elements with different values for xml:lang and lang
        self.different_lang = []
        if myfile.xhtml != 0:
            for element in xmllang_set & lang_set: # intersection of both sets
                if element.attrib['lang'] != element.attrib[XMLNS+'lang']:
                    self.different_lang.append((element.sourceline, element.tag))
            self.different_lang.sort()

        # Misc errors

        # Encoding
        self.encoding_errors = []
        elements = myfile.tree.findall('/head/meta')
        self.meta_encoding = None
        for element in elements:
            if element.attrib.get('http-equiv', None) == 'Content-Type':
                content = element.attrib.get('content', None)
                if content:
                    # property-value, but use a regex instead.
                    m = re.match(r"\s*text/html;\s*charset=(.*)", content)
                    if m is not None:
                        self.meta_encoding = m.group(1).lower().strip()
                        break

        if self.meta_encoding is None:
            self.encoding_errors.append("Document has no encoding set in the http-equiv tag")
        else:
            if self.meta_encoding not in ['us-ascii', 'utf-8', 'iso-8859-1']:
                # Full list at https://www.iana.org/assignments/character-sets/character-sets.xhtml
                self.encoding_errors.append("Document encoding '{}' is unknown to this tool or invalid. See https://www.iana.org/assignments/character-sets/character-sets.xhtml".format(self.meta_encoding))

            if self.meta_encoding != myfile.encoding:
                badenc = True

                # Make an exception if the text in encoded is ascii,
                # because we'll always read the file as
                # utf-8. us-ascii is a subset of utf-8. We just need
                # to make sure that the file is really ascii.
                if self.meta_encoding == 'us-ascii' and myfile.encoding == 'utf-8':
                    text= " ".join(myfile.text)
                    try:
                        bytes(text, 'utf-8').decode('us-ascii')
                        badenc = False
                    except Exception as e:
                        # not ascii
                        pass

                if badenc:
                    self.encoding_errors.append("Document encoded with {} but declared encoding is {}".format(myfile.encoding, self.meta_encoding))

        # Ensure there is only one h1.
        elements = myfile.tree.findall('//h1')
        self.num_h1 = len(elements)

        # Ensure no * inside <sup>, because * is already superscript
        self.stars_in_sup = []
        elements = myfile.tree.findall('//sup')
        for element in elements:
            if element.text and '*' in element.text:
                self.stars_in_sup.append(element.sourceline)

        # No inline style
        self.inline_style = []
        image_position = frozenset(["figcenter", "figleft", "figright"])
        elements = myfile.tree.findall('//*[@style]')
        for element in elements:
            # Ignore if it's a div with a figcenter/figleft/figright class
            # It's used to position an image in some documents
            myclass = element.attrib.get('class', None)
            if element.tag == 'div' and myclass is not None and (image_position & set(myclass.split(' '))):
                # One of the image_position style was found
                continue

            self.inline_style.append((element.sourceline, element.tag, element.attrib['style']))

        # No empty td
#        elements = myfile.tree.findall('//td')
#        for element in elements:
#            # Check for no child and no text
#            if len(element) == 0 and not element.text:
#                print(str(element.sourceline) + ": found empty td")

        # Check what is just after a <sup> tag. It's likely an error.
        self.text_after_sup = []
        elements = myfile.tree.findall('//sup')
        for element in elements:
            # Check for no child and no text
            if element.tail and element.tail[0].isalpha():
                self.text_after_sup.append(element.sourceline)

        self.misc_regex_result = []

        # Try to find various strings in the text
        strings = [("unusual punctuation", "[,:;][!?]"),
                   ("[oE]->[oe], [OE] or œ", "[oE]"),
                   ("[Oe]->[oe], [OE] or Œ", "[Oe]"),
                   ("[ae]->æ", "[ae]"),
                   ("[AE]->Æ", "[AE]"),
                   ("[Blank Page]", "[Blank Page]"),
                   ("degré sign ?", "°"),
                   ("ordinal sign ?", "º"),
                   ("space then punctuation", " ."),
                   ("space then punctuation", " ,"),
                   ("space then punctuation", " ;"),
                   ("space then punctuation", " ]"),
                   ("space then punctuation", " ?"),
                   ("space then punctuation", " !"),
                   ("space then punctuation", " :"),
                   ("dp marker?", "-*")]

        if self.document_lang and (
                self.document_lang == 'de' or self.document_lang.startswith(('de_', 'de-'))):
            strings.append(["space then punctuation", " «"])
        else:
            strings.append(["space then punctuation", " »"])

        for element in myfile.tree.find('body').iter():
            for desc, string in strings:
                if element.text and string in element.text:
                    self.misc_regex_result.append((desc, element.text, element.sourceline))
                if element.tail and string in element.tail:
                    self.misc_regex_result.append((desc, element.tail, element.sourceline))

        # Try various regexes on the text
        text = etree.XPath("string(//body)")(myfile.tree)
        regexes = [("mdash->ndash(?)", r"\d+--\d+"),
                   ("mdash->ndash(?)", r"[rv]\.--\d+"), # recto/verso

                   ("dash->ndash(?)", r"\d+-\d+"),
                   ("mdash->ndash(?)", r"\b[rv]\.—\d+"), # recto/verso

                   ("mdash->ndash(?)", r"\d+—\d+"),
                   ("mdash->ndash(?)", r"\b[rv]\.—\d+"), # recto/verso

                   (",letter", r",[^\W\d_]+"),
                   ("bad guiguts find/replace?", r"\$\d[^\d][^ ]*\s"),

                   ("PP tag?", r"\n(/[CFQRPTUX\*#]|[CFQRPTUX\*#]/).*(?=\n)")]

        # Find all matches, and add them
        for desc, regex in regexes:
            m = re.findall(regex, text)
            if m is None:
                continue

            for match in m:
                self.misc_regex_result.append((desc, match, 0))


        # Ensure that quote types are not mixed. If straight quotes
        # are found, suggest curly quotes. Same for double quotes.
        self.misc_has_straight_quote = "'" in text
        self.misc_has_curly_quote = "’" in text
        self.misc_has_straight_dquote = '"' in text
        self.misc_has_curly_dquote = '“' in text or '”' in text


    def check_anchors(self, myfile):
        """Perform check on anchors: id must be equal to name, find
        undefined or unused anchors.
        """

        name_set = set()
        id_set = set()
        hrefs = set()

        self.different_id_name = []
        self.missing_name = []
        self.missing_id = []
        self.bad_hrefs = []

        # Ensure all 'a' have both a name and an id, and that they are identical
        # Inspect all 'a' for href/id/name and the other elements for id
        find = etree.XPath("/html/body//*")
        for element in find(myfile.tree):

            # Find id
            attr_id = element.attrib.get("id", None)
            if attr_id:
                id_set.add((element.sourceline, attr_id))

            if element.tag != 'a':
                # Not an anchor
                continue

            # Find href and name
            attr_href = element.attrib.get("href", None)
            if attr_href and attr_href[0] == '#':
                hrefs.add((element.sourceline, attr_href[1:]))

            attr_name = element.attrib.get("name", None)
            if attr_name:
                name_set.add((element.sourceline, attr_name))

            # Checks name and id present
            if attr_id and not attr_name:
                self.missing_name.append((element.sourceline, attr_id))

            if attr_name and not attr_id:
                self.missing_id.append((element.sourceline, attr_name))

            # If we have id and name, the must be the same
            if attr_id and attr_name and attr_id != attr_name:
                self.different_id_name.append((element.sourceline, attr_name, attr_id))

        if myfile.xhtml == 11:
            # XHTML 1.1 -- only id matters
            name_id_set = id_set
            self.missing_name = []

        elif myfile.xhtml == 10:
            # XHTML 1.0 -- id + name
            name_id_set = id_set

        else:
            # HTML - only name matters
            name_id_set = name_set
            self.missing_id = []


        # Find hrefs not referenced.
        # todo - There must be a more pythonic way to do that.
        for lineno, href in hrefs:
            for _, name in name_id_set:
                if name == href:
                    break
            else:
                # href was not found
                self.bad_hrefs.append((lineno, href))

        self.bad_hrefs = sorted(self.bad_hrefs)

        # todo - find anchor with name/id that have no corresponding href
        #  self.unused_anchors = name_id_set - hrefs
        self.unused_anchors = []


    def check_unicode(self, myfile):
        res = k_unicode.analyze_file(etree.XPath("string(/)")(myfile.tree))

        self.unicode_bad = []
        self.unicode_misc = []

        # Separate various categories
        for cat, ordl, l, name, num in res:

            # Tabs are ok in html. And no break space (nbsp) are
            # common too.
            if l in '\t\u00a0':
                continue

            # Control characters should not appear
            if cat[0] == 'C':
                self.unicode_bad.append((cat, ordl, l, name, num))
            else:
                self.unicode_misc.append((cat, ordl, l, name, num))




def test_html1():
    from sourcefile import SourceFile
    myfile = SourceFile()
    myfile.load_xhtml("data/testfiles/badcharset.html")
    assert myfile.tree
    x = KXhtml()
    x.check_document(myfile)
    assert x.meta_encoding == 'iso-8859-1'
    assert myfile.encoding == 'utf-8'
    assert len(x.encoding_errors) == 1
    assert myfile.ending_empty_lines == 1

def test_html2():
    from sourcefile import SourceFile
    myfile = SourceFile()
    myfile.load_xhtml("data/testfiles/nocharset.html")
    assert myfile.tree
    x = KXhtml()
    x.check_document(myfile)
    assert x.meta_encoding == None
    assert myfile.encoding == 'utf-8'
    assert len(x.encoding_errors) == 0

def test_html2():
    """Test all document errors, as long as the document is valid."""
    from sourcefile import SourceFile
    myfile = SourceFile()
    assert myfile
    myfile.load_xhtml("data/testfiles/miscerrors.html")
    assert myfile.tree
    x = KXhtml()
    x.check_css(myfile)
    x.check_title(myfile)
    x.check_document(myfile)
    x.epub_toc(myfile)
    x.check_anchors(myfile)
    x.check_unicode(myfile)

    # CSS
    assert x.cssutils_errors == []
    assert x.sel_unchecked == []
    assert len(x.sel_unused) == 2
    assert '.large' in x.sel_unused
    assert '.pagenum' in x.sel_unused
    assert x.classes_undefined == [[17, 'asdfgh']]

    # Title
    assert x.good_format == False
    assert x.title == 'no title — no author'
    assert x.author == None

    # Encoding
    assert myfile.encoding == 'utf-8'
    assert x.meta_encoding == myfile.encoding
    assert len(x.encoding_errors) == 0

    # TOC - not tested here
    assert len(x.toc) == 2

    # Languages
    assert x.document_lang == "fr"
    assert x.document_xmllang == "en"

    # h1
    assert x.num_h1 == 2

    # sup stars
    assert len(x.stars_in_sup) == 2

    # Inline style
    assert len(x.inline_style) == 2
    assert x.inline_style[0][1] == 'div'
    assert x.inline_style[0][2] == 'text-indent:2em'
    assert x.inline_style[1][1] == 'span'
    assert x.inline_style[1][2] == 'margin-left: 1em;'

    # Something after <sup> tag
    assert len(x.text_after_sup) == 2
    assert x.text_after_sup == [37, 38]

    # Empty lines at the end
    assert myfile.ending_empty_lines == 5

def test_html3():
    """Test document with no error."""
    from sourcefile import SourceFile
    myfile = SourceFile()
    assert myfile
    myfile.load_xhtml("data/testfiles/noerror.html")
    assert myfile.tree
    x = KXhtml()
    x.check_css(myfile)
    x.check_title(myfile)
    x.check_document(myfile)
    x.epub_toc(myfile)
    x.check_anchors(myfile)
    x.check_unicode(myfile)

    # CSS
    assert x.cssutils_errors == []
    assert x.sel_unchecked == []
    assert len(x.sel_unused) == 0
    assert len(x.classes_undefined) == 0

    # Title
    assert x.good_format == True
    assert x.title == 'Voyage à Cayenne, Vol. 1'
    assert x.author == 'L. A. Pitou'

    # Encoding
    assert myfile.encoding == 'utf-8'
    assert x.meta_encoding == myfile.encoding
    assert len(x.encoding_errors) == 0

    # TOC
    assert len(x.toc) == 10
    assert x.toc[0][0] == 0
    assert x.toc[0][1] == 'one header'
    assert x.toc[3][0] == 3
    assert x.toc[3][1] == 'lvl 4-1'
    assert x.toc[8][0] == 2
    assert x.toc[8][1] == 'other'
    assert x.toc[9][0] == 3
    assert x.toc[9][1] == 'lvl 4-3 on 2 lines'

    # Languages
    assert x.document_lang == "fr"
    assert x.document_xmllang == "fr"

    # h1
    assert x.num_h1 == 1

    # sup stars
    assert len(x.stars_in_sup) == 0

    # Inline style
    assert len(x.inline_style) == 0

    # Something after <sup> tag
    assert len(x.text_after_sup) == 0

    assert myfile.ending_empty_lines == 1

def test_encoding1():
    """No encoding."""
    from sourcefile import SourceFile
    myfile = SourceFile()
    assert myfile
    myfile.load_xhtml("data/testfiles/noencoding.html")
    assert myfile.tree
    x = KXhtml()
    x.check_document(myfile)

    # Encoding
    assert myfile.encoding == 'utf-8'
    assert x.meta_encoding == None

def test_encoding2():
    """validly declared us-ascii encoding, read as utf-8."""
    from sourcefile import SourceFile
    myfile = SourceFile()
    assert myfile
    myfile.load_xhtml("data/testfiles/asciiencoding.html")
    assert myfile.tree
    x = KXhtml()
    x.check_document(myfile)

    # Encoding
    assert myfile.encoding == 'utf-8'
    assert x.meta_encoding == 'us-ascii'
    assert len(x.encoding_errors) == 0

def test_encoding3():
    """declared ascii but contains unicode."""
    from sourcefile import SourceFile
    myfile = SourceFile()
    assert myfile
    myfile.load_xhtml("data/testfiles/notasciiencoding.html")
    assert myfile.tree
    x = KXhtml()
    x.check_document(myfile)

    # Encoding
    assert myfile.encoding == 'utf-8'
    assert x.meta_encoding == 'us-ascii'
    assert len(x.encoding_errors) == 1

def test_encoding4():
    """invalid encoding."""
    from sourcefile import SourceFile
    myfile = SourceFile()
    assert myfile
    myfile.load_xhtml("data/testfiles/inv-encoding.html")
    assert myfile.tree
    x = KXhtml()
    x.check_document(myfile)

    # Encoding
    assert myfile.encoding == 'utf-8'
    assert x.meta_encoding == 'ascii'
    assert len(x.encoding_errors) == 2 # invalid + different encodings
