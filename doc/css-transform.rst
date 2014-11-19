.. highlight:: css

==============================
comp_pp — comparing files easy
==============================


Introduction
------------

Comparing file is useful to ensure the various version of a document
(latin1, utf-8 and html) are consistent, and have not deviated during
the PP phase.

This diff tool (comp_pp) is based on dwdiff. At the base, it compares
2 different text files while ignoring all the spacing differences.

To be able to compare an HTML file some another file (either text
itself or HTML), that file has to be transformed into a regular text
file, without all the HTML tags.

Internally, comp_pp will transform both files to make them closer to
each other. This transformation is driven by a CSS like language,
using selectors, classes,... This CSS only affects the HTML file(s)
given as input.

comp_pp includes a default set of CSS to perform sane transformations
that follow DP usual PPing. For instance, **<i>...</i>** in the html
version will be transformed to **_..._** so that will not generate a
diff with another file. That should be enough for a normal project,
without having to define some specialized CSS rules.


Handling of files
-----------------

Depending on certain criteria, the internal handling of files will be
different.

Files which name ends with *.html* or *.htm* are recognized as HTML
files. Files starting with *ProjectID* and ending with *.txt* will be
considered as P1/2/3 or F1/2, and files ending with *.txt* are
regular text files. Files not matching these criteria will be rejected.

The encoding (either ASCII/latin1 or UTF-8) is autodetected.


Options
-------

Extract and process footnotes separately
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the two versions have footnotes, but they are not placed in the
same spot (i.e. after each paragraph for the text, and at the end of
the book for the html), they can be extracted and compared separately
with this option.

There is a best effort done with the files coming from th
rounds. However they are usually broken, thus finding all the
footnotes will fail, and the diff for the footnotes will not be done
at all.


Transform small caps
~~~~~~~~~~~~~~~~~~~~~~~~~~

Usually small caps in the text version are transformed in
uppercase. This transformation has to be done in the html too, so
these section will not generate a diff.

The default is to do nothing. The options are *"uppercase"*, *"lowercase"*
and *"title"*. *"title"* means capitalizing the first letter of each word
*"Like This"*.


HTML: add [Sidenote: ...]
~~~~~~~~~~~~~~~~~~~~~~~~~

To use when the text version has "[Sidenote: ...]", and not the
html. This will add a "[Sidenote: ...]" in the HTML version, thus
suppressing the diff.


HTML: add [Illustration: ...] tag
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

See above.


Ignore case when comparing
~~~~~~~~~~~~~~~~~~~~~~~~~~

If there is too many unfixable case differences, use this option to
ignore them.


Suppress non-breakable spaces between numbers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some numbers can be written with an unbreakable space between them
(eg. 2_000). This removes them.


HTML: use greek transliteration in title attribute
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the greek text in the html also includes the transliteration in the
title attribute, the diff will use it to compare with a latin1
version.


HTML: suppress zero width space
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some HTML contain zero-width spaces. Select this to remove them.


HTML: do not use default transformation CSS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

comp_pp include a set of relatively sane defaults, but they can create
issues with some documents. For instance **<i>** might be **+** instead of
the regular **_**. This option tells comp_pp to ignore that predefined
CSS. The downside is that more diffs may appear until a new
transformational CSS is in place.

There is a link on the diff page to see the existing default CSS. This
can be cut and pasted in the transformation CSS box, and adapted.


Transformational CSS
--------------------

This is what drives the transformation of the html in a usable text
version ressembling the real text version produced by the PP.

For instance, here's how **<i>...</i>** is tranformed into **_..._**.
::

  i:before, i:after   { content: "_"; }

This tells comp_pp to insert an underscore before and after the string
delimited by the <i> tag. On the left side is regular CSS selector. On
the right side is more or less standard CSS 3 property/value, although
only a few are implemented.

The removal of page numbers is done with this::

  span[class^="pagenum"] { display: none }

This selects every span with a class starting with the string pagenum,
and suppresses it.


Selectors
~~~~~~~~~

Most CSS 3 selectors should be supported. See
http://www.w3schools.com/cssref/css_selectors.asp


Properties/Values
~~~~~~~~~~~~~~~~~

Only a limited set of properties make sense for comp_pp. Some are from
CSS, some are new.


content
.......

Insert some content in a tag. Used on the element, or in conjonction
with the **:before** and **:after** pseudo selector. If no
pseudo-element is used, then the existing content is replaced.

Supports multiple parameters, such as a string, the *attr()* function
(insert the content of the attribute), *content* (the identity,
ie. the original content).

The original content is only the first string in the html until either
the closing of the matched element or the opening of a sub
element. For instance, if the matched html is
*"<span>abc<i>def</i></span>", then the content is only *abc*.

For instance::

  br:before { content: " "; }

  *[lang=grc] { content: "+" attr(title) "+"; }

  .dumb { content: "abc" attr(title) "def" content; }


The *"use greek transliteration in title attribute"* option is
implemented with this::

  *[lang=grc] { content: "+" attr(title) "+"; }


text-transform
..............

Transform the content inside the selected tags. The options are:

  * "uppercase":  *Lorem ipsum dolor*  -->  *LOREM IPSUM DOLOR*
  * "lowercase":  *Lorem ipsum dolor*  -->  *lorem ipsum dolor*
  * "capitalize": *Lorem ipsum dolor*  -->  *Lorem Ipsum Dolor*

For instance::

  .smcap { text-transform:uppercase; }


_replace_with_attr
..................

**OBSOLETE**. Use *content* instead.


display
.......

How to display some content. Right now only "none" is supported, which
simply suppresses the content.

For instance::

  span[class^="pagenum"] { display: none }


text-replace
............

Replaces the first string with the second. All instances will be
replaced.

For instance, to replace a divide symbol with a slash::

  p { text-replace: "⁄" "/"; }

With "1⁄2 + 1⁄2 = 1", this will result in "1/2 + 1/2 = 1".

It is also possible to use unicode numbers (with 2 backslashes)::

  p { text-replace: "Z" "\\u1234"; }
  [id^=Footnote_]:before { content: "\\u200C"; }

_graft
......

Prune and graft an element to another element. The element to graft to
is relative to the element to prune. The path to the new position is
created with 3 parameters:

  * parent: a parent
  * prev-sib: the previous sibling
  * next-sib: the next sibling

The path can be as long as necessary. For instance, the following CSS
will move all span elements with the class "sidenote" to the 2nd
previous sibling of the parent::

  span.sidenote { _graft: parent prev-sib prev-sib; }

For every element, comp_pp will find the parent, then its previous
sibling, then its previous sibling. It will detach the element and
attach it to this new element.

The elements must exist; i.e. all the elements in the path, for all
element matching the selector, must exist.


Expectations in default transformational CSS
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


Footnotes
.........

In many document, the semantic of a footnote in html is lost because
they are put at the end of the file and look like any other
paragraph. Ideally, a document should include each footnote in a tag,
for instance a div with a footnote class. If this is not present,
comp_pp cannot find the end of the footnote, and sometimes not even
the start.


Page numbers
............

The default CSS includes several selectors to strip the page numbers::

  span[class^="pagenum"] { display: none }
  p[class^="pagenum"] { display: none }
  p[class^="page"] { display: none }
  span[class^="pgnum"] { display: none }
  div[id^="Page\_"] { display: none }
  div[class^="pagenum"] { display: none }


Italics
.......

Italics are surrounded by underscores. Same for cite, abbr, ...


Some CSS examples
~~~~~~~~~~~~~~~~~


Anchors
.......

By default anchors are expected to be surrounded by brackets. If it is
not the case in the html, this can be easily fixed with the following::

  .fnanchor:before { content: "["; } .fnanchor:after { content: "]"; }


Miscellaneous
.............

Just a few more CSS examples::

  sup:before { content:"^"; } /* 1<sup>st</sup> --> 1^st */
  table[summary="Table of Cases"] td[class="lt"]:after { content: ","; }
  li { text-replace: "--" "—"; }
  h4:before, h4:after { content: "_"; }
  a[id^=FNanchor_]:before { content: "[" } a[id^=FNanchor_]:after{ content: "]" }
  span[lang]:before { content: "_" }
