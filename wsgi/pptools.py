#!/usr/bin/env python3

#
# -*- coding: utf-8 -*-
#
# Copyright 2012-2014 bibimbop at pgdp, All rights reserved
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

import os
from flask import Flask, abort, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
from itertools import combinations
import subprocess
from wtforms import Form, BooleanField, TextField, validators, StringField, TextAreaField, SelectField

import sys
sys.path.append("../pptools")
from comp_pp import diff_css, CompPP

app = Flask(__name__)
app.debug = True

hexnumbers = set("abcdef0123456789")

ALLOWED_UPLOAD_EXTENSIONS = sorted(['.txt', '.htm', '.html'])
PROJECT_FILES = "files"



def check_extension(filename):
    ext = os.path.splitext(filename)[1]
    return ext.lower() in ALLOWED_UPLOAD_EXTENSIONS

def create_new_project():

    # Create an 16 hex characters ID
    project_id = "".join("{:02x}".format(i) for i in os.urandom(8))

    # Make the directory structure
    os.makedirs(os.path.join(os.environ.get('OPENSHIFT_DATA_DIR', ''), "projects", project_id, "files"))

    return project_id


def check_project_id(project_id):
    # Validate the project id
    if len(project_id) != 16:
        return False

    if len(set(project_id)-hexnumbers):
        return False

    return True


@app.route('/static/<filename>')
def send_foo(filename):
    return send_from_directory('static', secure_filename(filename))


@app.route('/project/<project_id>/', methods=['GET', 'POST'])
def project(project_id):
    # Display the project page

    if not check_project_id(project_id):
        abort(404)

    project_dir = os.path.join(os.environ.get('OPENSHIFT_DATA_DIR', ''), "projects", project_id)
    if not os.path.isdir(project_dir):
        abort(404)

    if request.method == 'GET':

        # Find the files available
        files_dir = os.path.join(project_dir, "files")
        files = []
        for filename in os.listdir(files_dir):

            st = os.stat(os.path.join(files_dir, filename))
            files.append([filename, st.st_size])

        # Create all the possible diffs combinations
        filenames = [ x[0] for x in files ]
        combos = combinations(filenames, 2)

        return render_template('project.tmpl',
                               project_id=project_id,
                               files=files,
                               allowed_ext=", ".join(ALLOWED_UPLOAD_EXTENSIONS),
                               combos=combos)

    elif request.method == 'POST':
        # Posting a new file
        upfile = request.files['file']

        if upfile:
            filename = secure_filename(upfile.filename)

            # Check extension
            if check_extension(filename):
                upfile.save(os.path.join(project_dir, "files", filename))

                # TODO: unzip

        return redirect(url_for('project', project_id=project_id))



class DiffForm(Form):
    extract_footnotes = BooleanField('Extract and process footnotes separately', [])
    suppress_proofers_notes = BooleanField('In Px/Fx versions, remove [**proofreaders notes]', [])
    css = TextAreaField('HTML: Transformation CSS',
                        default="""
/* Add brackets around footnote anchor */
/*   .fnanchor:before { content: "["; }
     .fnanchor:after { content: "]"; } */

/* Adds [Sidenote: ... ] */
/*   div.sidenote:before { content: "[Sidenote:"; }
     div.sidenote:after { content: "]"; }' */
"""
)
    css_smcap = SelectField('HTML: Transform small caps',
                            choices=[('n', "(no change)"),
                                     ('U', "uppercase"),
                                     ('L', "lowercase"),
                                     ('T', "title")],
                            default='n')


@app.route('/project/<project_id>/diffs', methods=['GET', 'POST'])
def diffs(project_id):

    # Validate input
    if not check_project_id(project_id):
        abort(404)

    project_dir = os.path.join(os.environ.get('OPENSHIFT_DATA_DIR', ''), "projects", project_id)
    if not os.path.isdir(project_dir):
        abort(404)

    files_dir = os.path.join(project_dir, "files")

    f1 = os.path.join(files_dir, secure_filename(request.args.get('f1', '')))
    if not os.path.isfile(os.path.join(f1)):
        abort(404)

    f2 = os.path.join(files_dir, secure_filename(request.args.get('f2', '')))
    if not os.path.isfile(f2):
        abort(404)

    form = DiffForm(request.form)
    if not form.validate():
       pass #  abort(404)

    # Create empty object to store our arguments
    # TODO: find an easier way than recopy all of them.
    args = lambda:0
    args.filename = [ f1, f2 ]
    args.extract_footnotes = form.extract_footnotes.data
    args.css_smcap = form.css_smcap.data
    args.css = form.css.data

    # Default value - not in form yet
    args.ignore_format = False
    args.suppress_footnote_tags = False
    args.suppress_illustration_tags = False
    args.with_sidenote_tags = False
    args.ignore_case = False
    args.extract_footnotes = False
    args.ignore_0_space = False
    args.suppress_nbsp_num = False
    args.css_bold = None
    args.suppress_proofers_notes = False
    args.regroup_split_words = False
    args.css_greek_title_plus = False
    args.css_add_illustration = False
    args.css_no_default = False
    args.without_html_header = False





    # Do diff
    x = CompPP(args)
    html_content, fn1, fn2 = x.do_process()

    return render_template('diffs.tmpl',
                           project_id=project_id,
                           f1=os.path.basename(f1),
                           f2=os.path.basename(f2),
                           diff=html_content,
                           css=diff_css(),
                           form=form)

# Main page
@app.route("/", methods=['GET', 'POST'])
def main_page():
    if request.method == 'GET':
        return render_template('main_page.tmpl')

    elif request.method == 'POST':
        project_id = create_new_project()
        return redirect(url_for('project', project_id=project_id))





# Main project page

if __name__ == '__main__':

    app.config['UPLOAD_FOLDER'] = 'temp/uploads'


    app.debug = True
    app.run()



