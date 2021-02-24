# pptools

This is a collection of tools to help to check the ebooks produced by
[Distributed Proofreader](pgdp.net), before they are submitted to
[Project Gutenberg](gutenberg.org).

The frontend for the tools is a web service that can be run locally on
a Linux system, or online.

It is currently available for everyone to use at
[https://pptools.tangledhelix.com](https://pptools.tangledhelix.com)


## Local installation

### Requirements

This is for a local installation on Ubuntu. Several packages have to
be installed with the following command line:

>  sudo apt-get install python3-flask python3-lxml python3-roman w3c-sgml-lib dwdiff python3-flaskext.wtf python3-tinycss python3-cssselect

On older versions of Ubuntu, some of these packages are not available,
they can be installed through pip:

>  sudo pip3 install cssselect
>  sudo pip3 install flask-wtf
>  sudo pip3 install tinycss

To run the application, cd into wsgi, and run:

>  ./pptools.py

Then point a web browser to the displayed URL, usually http://127.0.0.1:5000/
