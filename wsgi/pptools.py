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
import time
from flask import Flask, abort, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
from itertools import combinations
import subprocess
from wtforms import Form, BooleanField, TextField, validators, StringField, TextAreaField, SelectField

import sys
sys.path.append("../pptools")
from comp_pp import diff_css, CompPP, html_usage, DEFAULT_TRANSFORM_CSS

import kppvh
import find_langs

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
    # Validate the project id, and return its directory
    if len(project_id) != 16:
        return None

    if len(set(project_id)-hexnumbers):
        return None

    project_dir = os.path.join(os.environ.get('OPENSHIFT_DATA_DIR', ''), "projects", project_id)
    if not os.path.isdir(project_dir):
        return None

    return project_dir


@app.route('/comp_pp/diff-default-css.txt')
def send_diff_default_css():
    # Kind of a hack. */
    return "<html><pre>" + DEFAULT_TRANSFORM_CSS.replace("<br />", "&ltbr /&gt") + "</pre></html>"


@app.route('/static/<filename>')
def send_foo(filename):
    # Send back a static file
    return send_from_directory('static', secure_filename(filename))


@app.route('/project/<project_id>/delete', methods=['GET'])
def del_file(project_id):
    # Display the project page
    project_dir = check_project_id(project_id)
    if project_dir is None:
        abort(404)

    files_dir = os.path.join(project_dir, "files")

    # We don't really need to check, but ...
    myfile = os.path.join(files_dir, secure_filename(request.args.get('file', '')))
    if not os.path.isfile(myfile):
        abort(404)

    # Remove the file
    os.unlink(myfile)

    # Reload the project page
    return redirect(url_for('project', project_id=project_id))



@app.route('/project/<project_id>/', methods=['GET', 'POST'])
def project(project_id):
    # Display the project page

    project_dir = check_project_id(project_id)
    if project_dir is None:
        abort(404)

    if request.method == 'GET':

        # Find the files available
        files_dir = os.path.join(project_dir, "files")
        files = []
        for filename in os.listdir(files_dir):

            st = os.stat(os.path.join(files_dir, filename))
            files.append([filename, st.st_size, time.ctime(st.st_mtime)])

        # Sort by names first, then by reversed extension to put txt
        # befor html. Note that since sorting is stable since python
        # 2.2, the sorting by names is not lost during the second
        # sort.
        files.sort(key=lambda x: os.path.splitext(x[0])[0])
        files.sort(key=lambda x: os.path.splitext(x[0])[1], reverse=True)

        # Create all the possible diffs combinations
        filenames = [ x[0] for x in files ]
        combos = combinations(filenames, 2)

        # Sort them again by alphabetical order
        files.sort()

        return render_template('project.tmpl',
                               project_id=project_id,
                               files=files,
                               files_html=[ x for x in files if x[0].lower().endswith((".htm", ".html")) ],
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
    extract_footnotes = BooleanField('Extract and process footnotes separately')
    suppress_proofers_notes = BooleanField('In Px/Fx versions, remove [**proofreaders notes]')
    ignore_format = BooleanField('Silence formating differences')
    suppress_footnote_tags = BooleanField('Suppress "[Footnote:" marks')
    suppress_illustration_tags = BooleanField('Suppress "[Illustration:" marks')
    suppress_sidenote_tags = BooleanField('Suppress "[Sidenote:" marks')
    with_sidenote_tags = BooleanField('Add "[Sidenote:" marks')
    ignore_case = BooleanField('Ignore case when comparing')
    extract_footnotes = BooleanField('Extract and process footnotes separately')
    ignore_0_space = BooleanField('Suppress zero width space (U+200B)')
    suppress_nbsp_num = BooleanField("Suppress non-breakable spaces (U+00A0) between numbers")
    regroup_split_words = BooleanField("In Px/Fx versions, regroup split wo-* *rds")

    css = TextAreaField('Transformation CSS',
                        default="""
/* Add brackets around footnote anchor */
/*   .fnanchor:before { content: "["; }
     .fnanchor:after { content: "]"; } */

/* .tb {display: none;} */
"""
)
    css_smcap = SelectField('Transform small caps',
                            choices=[('n', "(no change)"),
                                     ('U', "uppercase"),
                                     ('L', "lowercase"),
                                     ('T', "title")],
                            default='U')
    css_greek_title_plus = BooleanField("Use greek transliteration in title attribute")
    css_add_illustration = BooleanField('Add "[Illustration:" marks')
    css_no_default = BooleanField("Do not use default transformation CSS")

    txt_cleanup_type = SelectField('Type of text cleaning',
                                   choices=[('n', "none"),
                                            ('p', "proofers only"),
                                            ('b', "best effort")],
                                   default='b')

#    css-bold', type=str, default=None,"HTML: Surround bold strings with this string")


@app.route('/project/<project_id>/diffs', methods=['GET', 'POST'])
def diffs(project_id):

    # Validate input
    project_dir = check_project_id(project_id)
    if project_dir is None:
        abort(404)

    files_dir = os.path.join(project_dir, "files")

    f1 = os.path.join(files_dir, secure_filename(request.args.get('f1', '')))
    if not os.path.isfile(f1):
        abort(404)

    f2 = os.path.join(files_dir, secure_filename(request.args.get('f2', '')))
    if not os.path.isfile(f2):
        abort(404)

    form = DiffForm(request.form)
    if request.method=='POST':
        if not form.validate():
            abort(404)

    # Create empty object to store our arguments
    # TODO: find an easier way than recopy all of them.
    args = lambda:0
    args.filename = [ f1, f2 ]
    args.extract_footnotes = form.extract_footnotes.data
    args.css_smcap = form.css_smcap.data
    args.css = form.css.data
    args.extract_footnotes = form.extract_footnotes.data
    args.suppress_proofers_notes = form.suppress_proofers_notes.data
    args.ignore_format = form.ignore_format.data
    args.suppress_footnote_tags = form.suppress_footnote_tags.data
    args.suppress_illustration_tags = form.suppress_illustration_tags.data
    args.suppress_sidenote_tags = form.suppress_sidenote_tags.data
    args.with_sidenote_tags = form.with_sidenote_tags.data
    args.ignore_case = form.ignore_case.data
    args.ignore_0_space = form.ignore_0_space.data
    args.suppress_nbsp_num = form.suppress_nbsp_num.data
    args.regroup_split_words = form.regroup_split_words.data
    args.css_greek_title_plus = form.css_greek_title_plus.data
    args.css_add_illustration = form.css_add_illustration.data
    args.css_no_default = form.css_no_default.data
    args.txt_cleanup_type = form.txt_cleanup_type.data

    # Default value - not in form yet
    args.css_bold = None

    # Do diff
    x = CompPP(args)
    err_message, html_content, fn1, fn2 = x.do_process()

    f1=os.path.basename(f1)
    f2=os.path.basename(f2)

    return render_template('diffs.tmpl',
                           project_id=project_id,
                           f1=f1,
                           f2=f2,
                           err_message=err_message,
                           diff=html_content,
                           usage=html_usage(f1, f2),
                           css=diff_css(),
                           form=form)


class LangForm(Form):
    with_lang_only = BooleanField('Show only tags with a lang attribute', default=True)

@app.route('/project/<project_id>/langs', methods=['GET', 'POST'])
def langs(project_id):

    # Validate input
    project_dir = check_project_id(project_id)
    if project_dir is None:
        abort(404)

    files_dir = os.path.join(project_dir, "files")
    filename = secure_filename(request.args.get('file', ''))
    f1 = os.path.join(files_dir, filename)
    if not os.path.isfile(f1):
        abort(404)

    form = LangForm(request.form)
    if request.method=='POST':
        if not form.validate():
            abort(404)

        # Workaround for boolean defaulting to True.
        form.with_lang_only.data = request.form.get('with_lang_only', False)

    # Do diff
    args = lambda:0
    args.with_lang_only = form.with_lang_only.data
    args.filename = f1

    x = find_langs.Languages()
    x.load_file(args)
    x.find_tags(args)

    return render_template('find_langs/find_langs.tmpl',
                           project_id=project_id,
                           filename=filename,
                           extracts1=sorted(x.extracts, key=lambda x: (x[1], x[0], x[2].lower())),
                           extracts2=sorted(x.extracts, key=lambda x: x[2].lower()),
                           extracts3=sorted(x.extracts, key=lambda x: (x[1], x[2].lower())),
                           form=form)


@app.route('/project/<project_id>/checks', methods=['GET'])
def checks(project_id):

    # Validate input
    project_dir = check_project_id(project_id)
    if project_dir is None:
        abort(404)

    files_dir = os.path.join(project_dir, "files")
    filename = secure_filename(request.args.get('file', ''))
    f1 = os.path.join(files_dir, filename)
    if not os.path.isfile(f1):
        abort(404)

    kppv = kppvh.Kppvh()

    return kppv.process(project_id, f1)


# Main page
@app.route("/", methods=['GET', 'POST', 'HEAD'])
def main_page():
    if request.method == 'GET':
        return render_template('main_page.tmpl')

    elif request.method == 'POST':
        project_id = create_new_project()
        return redirect(url_for('project', project_id=project_id))

    elif request.method == 'HEAD':
        return ""




# Main project page

if __name__ == '__main__':

    app.config['UPLOAD_FOLDER'] = 'temp/uploads'


    app.debug = True
    app.run()



