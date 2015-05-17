#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
 furtif - a python version of lvl's furtif.pl
"""

import sys
import re
import os

import helpers.sourcefile

class Furtif(object):

    def load_config(self):
        """Load the configuration file."""
        self.regexes = []
        word_list1 = []
        word_list2 = []
        word_list3 = []

        filename = os.environ.get('OPENSHIFT_REPO_DIR', '')
        if filename:
            filename = os.path.join(filename, "wsgi")
        filename = os.path.join(filename, "furtif", "regles-furtif03.txt")

        with open(filename, "r", encoding='utf-8') as f:
            for line in f.readlines():

                # Get rid of comments
                line = line.partition('#')[0].strip()
                if not line:
                    continue

                if ((line[0] == '"' and line[-1] == '"') or
                    (line[0] == "'" and line[-1] == "'")):
                    # A string - remove quotes
                    line = line[1:-1]

                    if line[0] == ' ':
                        # Starts with a space. Replace with \b to
                        # denote start of word
                        line = r"\b" + line[1:]

                    if line[-1] == ' ':
                        # End with a space. Replace with \b to
                        # denote start of word
                        line = line[:-1] + r"\b"

                    word_list2.append(line.replace(".", r"\."))

                elif line.startswith('/') and line.endswith('/'):
                    # Regex
                    word_list3.append(line[1:-1])

                else:
                    # A simple word
                    word_list1.append(line)

        self.regexes.append(re.compile(r"\b(" + "|".join(word_list1) + r")\b"))
        self.regexes.append(re.compile(r"(" + "|".join(word_list2) + r")"))
        self.regexes.append(re.compile(r"(" + "|".join(word_list3) + r")"))


    def check_furtif(self, filename, start, end, to_html=False):
        """Search for regexes/expressions in the text. """

        def html_safe(string):
            if to_html:
                return string.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")
            else:
                return string

        myfile = helpers.sourcefile.SourceFile()
        myfile.load_text(filename)

        self.matching = []

        for lineno, line in enumerate(myfile.text, start=myfile.start+1):

            if not len(line):
                continue

            # Regex
            for regex in self.regexes:
                for g in regex.finditer(line):
                    # Found one. Tag it with the start/end markers
                    # given by the caller
                    self.matching.append((lineno,
                                          html_safe(line[:g.start()]) +
                                          start +
                                          html_safe(line[g.start():g.end()]) +
                                          end +
                                          html_safe(line[g.end():])))


if __name__ == '__main__':

    furtif = Furtif()
    furtif.load_config()
    furtif.check_furtif(sys.argv[1], "[", "]")

    for lineno, line in furtif.matching:
        print(lineno, line)
