#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
 kppvh - points checking
"""

from lxml import etree
import re

class KPoints(object):
    """ Check combination where a comma is more warranted than a
    dot. Returns a sorted list of matching combinations. Duplicates
    are removed. """

    def check_points(self, myfile):

        # Transform html into text - get rid of <head> content first.
        head = myfile.tree.find('head')
        tail = head.tail
        head.clear()
        head.tail = tail
        text = etree.XPath("normalize-space(/)")(myfile.tree)

        self.point_matches = []

        for m in re.finditer("(\w+\.)»? [a-z]\w+", text):

            string = m.group(1)

            # Remove all uppercase letter. They usually are initials.
            if len(string) == 2 and string[0].isupper():
                continue

            # Skip some common abbreviations
            if m.group(1) in [ 'Voy.', 'voy.',            # voyez
                               'Biblioth.', 'Bibl.', 'biblioth.',     # bibliothèque
                               'man.', 'Man.', 'manusc.', # manuscript
                               'vol.',                    # volume
                               'fr.',                     # francs
                               'traduct.',                # traduction
                               'photo.', 'photogr.',      # photographie
                               'Rech.',                   # Recherches
                               'orig.',                   # origine, original
                               'Inst.',                   # catalogue
                               'éd.',                     # édition
                               'Collect.',                # collection
                               'Cf.', 'cf.',
                               'impr.',                   # imprimerie, impression
                               'Arch.',                   # archives
                               'hist.',                   # histoire
                               'Mém.',                    # Mémoire
                               'ff.',                     # digramme latin
                               'édit.',                   # édition
                               'MM.',                     # messieurs
                               'mm.',                     # millimètre
                               'Acad.',
                               'Anc.',
                               'Antiq.',
                               'Archiv.',
                               'Bibliog.',
                               'Bibliogr.',
                               'Catal.',
                               'Chron.',
                               'Chronol.',
                               'Corresp.',
                               'Curios.',
                               'Descript.',
                               'Dict.',
                               'Edit.',
                               'Fragm.',
                               'Hist.',
                               'Interprét.',
                               'Journ.',
                               'Nouv.',
                               'Ordonn.',
                               'Suppl.',
                               'antiq.',
                               'histor.',
                               'loc.',
                               'nouv.',
                               'trad.',
                               'Éd.',
                               'Édit.',
                               'chap.',
                               'lbs.',
                               'viz.',
                               'vols.',
                               'pick',
                               'Mr.',
                               'p.',
                               'pp.',
                               'Pron.',
                               'etc.',
                               ]:
                continue

            self.point_matches.append(m.group(0))

        self.point_matches = sorted(set(self.point_matches))


def test_kpoints():

    import argparse
    import os
    import sys

    sys.path.append("../../helpers")
    import sourcefile

    myfile = sourcefile.SourceFile()
    myfile.load_xhtml("../../../data/testfiles/kpoints.html")

    assert(myfile.tree)

    kp = KPoints()
    kp.check_points(myfile)

    # There should be 2 strings to check
    assert("centimes. traduct" in kp.point_matches)
    assert("dot. or" in kp.point_matches)
    assert(len(kp.point_matches) == 2)


if __name__ == '__main__':

    import argparse
    import os

    import sys
    sys.path.append("../../helpers")
    import sourcefile

    parser = argparse.ArgumentParser(description='Diff text document for PGDP PP.')

    parser.add_argument('filename', metavar='FILENAME', type=str,
                        help='input text file')

    args = parser.parse_args()

    kp = KPoints()

    myfile = sourcefile.SourceFile()
    myfile.load_xhtml(args.filename)

    kp.check_points(myfile)

    for x in sorted(kp.point_matches):
        print (x)
