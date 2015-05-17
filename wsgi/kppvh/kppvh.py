#!/usr/bin/env python3
# -*- coding: utf-8 -*-

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

"""
 kppvh - performs some checking on PGDP or Project Gutenberg files.
"""

import os
from flask import render_template

import helpers.sourcefile as sourcefile

import kppvh.kppv_mod.duplicates as duplicates
import kppvh.kppv_mod.footnotes as footnotes
import kppvh.kppv_mod.kxhtml as kxhtml
import kppvh.kppv_mod.furtif as furtif
import kppvh.kppv_mod.images as images
import kppvh.kppv_mod.pages as pages
import kppvh.kppv_mod.pptxt as pptxt
import kppvh.kppv_mod.points as points
import kppvh.kppv_mod.greek as greek


class Kppvh(object):

    def __init__(self):
        pass

    def process_pgdp(self, myfile, project_id):
        """Process a text file."""

        dup = duplicates.DuplicateLines()
        dup.check_duplicates(myfile)

        return render_template("kppv_templates/kppvh-pgdp.tmpl",
                               myfile=myfile, project_id=project_id,
                               dup=dup)


    def process_text(self, myfile, project_id):
        """Process a text file."""

        dup = duplicates.DuplicateLines()
        dup.check_duplicates(myfile)

        fn = footnotes.FootNotes()
        fn.check_footnotes(myfile)

        misc = pptxt.MiscChecks()
        misc.check_misc(myfile)

        return render_template("kppv_templates/kppvh-text.tmpl",
                               myfile=myfile, project_id=project_id,
                               dup=dup, fn=fn, misc=misc)


    def process_html(self, myfile, project_id):
        """Process an html file."""

        x = kxhtml.KXhtml()
        if myfile.tree:
            x.check_document(myfile)
            x.check_title(myfile)
            x.epub_toc(myfile)
            x.check_anchors(myfile)
            x.check_unicode(myfile)

            css = kxhtml.KXhtml()
            css.check_css(myfile)

            img = images.KImages()
            img.check_images(myfile)

            pgs = pages.KPages()
            pgs.check_pages_links(myfile)
            pgs.check_footnotes(myfile)
            pgs.check_pages_sequence(myfile)

            pts = points.KPoints()
            pts.check_points(myfile)

            grc = greek.KGreekTrans()
            grc.check_greek_trans(myfile)
        else:
            css = None
            img = None
            pgs = None
            pts = None
            grc = None

        return render_template("kppv_templates/kppvh-html.tmpl",
                               myfile=myfile, project_id=project_id,
                               x=x, css=css, img=img, pages=pgs,
                               points=pts, greek=grc)


    def process(self, project_id, fname):
        """Process the file given and return an xhtml page"""

        myfile = sourcefile.SourceFile()

        basename = os.path.basename(fname)
        if basename.startswith("projectID") and basename.lower().endswith(".txt"):
            myfile.load_text(fname)
            return self.process_pgdp(myfile, project_id)
        elif basename.lower().endswith((".txt", ".ltn")):
            myfile.load_text(fname)
            return self.process_text(myfile, project_id)
        elif basename.lower().endswith((".htm", ".html")):
            try:
                myfile.load_xhtml(fname)
            except Exception:
                pass
            return self.process_html(myfile, project_id)
        else:
            abort(404)
