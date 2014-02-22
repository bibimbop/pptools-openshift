#!/usr/bin/env python3

# kppvh - performs some checking on text files to submit to Project Gutenberg
# Copyright 2012-2013 bibimbop at pgdp, all rights reserved

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

from __future__ import print_function

# Various quotes and object that must (usually) be balanced.
quotes = [ { 'open' : '«', 'close' : '»' },
           { 'open' : '"', 'close' : '"' },
           { 'open' : '“', 'close' : '”' }, # rsquo, rdquo
           { 'open' : '‘', 'close' : '’' }, # lsquo, rsquo
           { 'open' : '(', 'close' : ')' },
           { 'open' : '{', 'close' : '}' },
#           { 'open' : '[', 'close' : ']' },
           ]

class check(object):

    def __init__(self):
        self.unbalanced = {}
        pass

    def check_quotes(self, myfile, q):
        """Check quotes
        """
        guillemet = 0      # attends un guillemet 0=ouvrant, 1=fermant

        prochain_paragraphe_guillemet = 0
        qkey = q['open'] + " ... " + q['close']
        self.unbalanced[qkey] = []

        for lnum, line in enumerate(myfile.text, start = myfile.start):

            # Cumule les lignes blanches
            if len(line) == 0:
                if guillemet == 1:
                    # Pas de fermant. Correct si le paragraphe suivant
                    # commence avec un guillemet ouvrant
                    prochain_paragraphe_guillemet = 1
                continue

            # Nouveau paragraphe et guillemet ouvrant
            if prochain_paragraphe_guillemet:
                if line[0] != q['open']:
                    self.unbalanced[qkey].append((lnum, "Missing " + q['open'] + " above", line))

                # On fait comme si on avait eu un fermant, afin
                # que le test suivant ne sorte pas une erreur
                guillemet = 0

                prochain_paragraphe_guillemet = 0

            # Vérifie les guillemets
            for char in line:

                if char == q['open']:
                    if q['open'] == q['close']:
                        # Special case of typewriter quotes
                        # (""). There's no open/close difference, so
                        # toggle the variable.
                        guillemet = 1 - guillemet
                    else:
                        if guillemet != 0:
                            self.unbalanced[qkey].append((lnum, "expected " + q['close'], line))
                        guillemet = 1
                elif char == q['close']:
                    if guillemet != 1:
                        self.unbalanced[qkey].append((lnum, "expected " + q['open'], line))
                    guillemet = 0

        if self.unbalanced[qkey] == []:
            # Nothing found
            del self.unbalanced[qkey]




def main():

    import argparse
    import sys

    sys.path.append("../helpers")
    import sourcefile

    parser = argparse.ArgumentParser(description='Quotes checker PGDP PP.')

    parser.add_argument('--encoding', dest='encoding',
                        help='force document encoding (latin1, utf-8, ...)',
                        default=None)
    parser.add_argument('filename', metavar='FILENAME', type=str,
                        help='input text file')

    help_string = 'Type of quotes to check:'
    for i, q in enumerate(quotes, start=1):
        help_string += "  " + str(i) + " = " + q['open'] + " ... " + q['close']

    parser.add_argument('type', type=int, help=help_string, default=0)

    args = parser.parse_args()

    myfile = sourcefile.SourceFile()

    myfile.load_text(args.filename)

    if myfile.text is None:
        print("Cannot read file", f)
        return

    x = check()

    if args.type == 0:
        for q in quotes:
            x.check_quotes(myfile, q)

    else:
        x.check_quotes(myfile, quotes[args.type-1])


    for qkey, errors in x.unbalanced.items():
        print (qkey)
        for err in errors:
            print(err[0], err[1], err[2])



if __name__ == '__main__':
    main()
