# pptools

This is a collection of tools to help to check the ebooks produced by
[Distributed Proofreader](pgdp.net), before they are submitted to
[Project Gutenberg](gutenberg.org).

The frontend for the tools is a web service that can be run locally on
a Linux system, or on RedHat's Openshift.

It is currently available for everyone to use at
[http://pptools-pptools.rhcloud.com](http://pptools-pptools.rhcloud.com)


## Local installation

### Requirements

This is for a local installation on Ubuntu. Several packages have to
be installed with the following command line:

>  sudo apt-get install python3-flask python3-lxml python3-roman w3c-sgml-lib dwdiff

The cssselect package is now available in Ubunto 15.04:

>  sudo apt-get install python3-cssselect

The flask-wtf and tinycss are available in Ubuntu 17.04:
   sudo apt-get install python3-flaskext.wtf

If not available, install them with pip:

>  sudo pip3 install cssselect
>  sudo pip3 install tinycss
>  sudo pip3 install flask-wtf
>  sudo pip3 install tinycss

To run the application locally, cd into wsgi/, and run:

>  ./pptools.py


### Installation on OpenShift 2

(Note: OpenShift 2 will be shutdown on September 2017.)

OpenShift can host pptools. The setup is a bit more complex.

First create your OpenShift account, a project, then push the pptools git tree.

Then copy dwdiff to the virtual machine in ./app-root/data/bin/. Since
binaries are compatible amongst distributions, any can be used. Make
sure the version is at least 2.0.7. Log on the VM and execute it to
ensure it can run there. Otherwise download the sources from
http://os.ghalkes.nl/dwdiff.html and compile and install on the VM.

The Openshift VM doesn't provide the w3c DTDs. Ubuntu provides the
w3c-sgml-lib package. Copy the /usr/share/xml/w3c-sgml-lib/ to the VM
in ./app-root/data/ (so you have files like
./app-root/data/w3c-sgml-lib/schema/dtd/REC-xhtml-modularization-20100729).

Once that is done, the application should be running. Compare with the
existing demo at
[http://pptools-pptools.rhcloud.com](http://pptools-pptools.rhcloud.com)


### Installation on OpenShift 3

Sort of broken. app.sh has to install pip 9.3, to be able to install
lxml. Normally lxml should be in the requirements file, but the VM
just stops when trying to install them. Also the VM is using an
ancient version of pip (7.1).
