#!/bin/bash

ARGS=""

ARGS="$ARGS --log-to-terminal"
ARGS="$ARGS --port 8080"

export OPENSHIFT_REPO_DIR=/opt/app-root/src
export OPENSHIFT_DATA_DIR=/opt/app-root/src/data
export XML_CATALOG_FILES=$OPENSHIFT_DATA_DIR/w3c-sgml-lib/schema/dtd/catalog.xml

# Openshift is broken (?)
pip install --upgrade pip
pip install lxml

# Download extra stuff not present in RHEL
#wget http://dl.fedoraproject.org/pub/fedora/linux/releases/26/Everything/x86_64/os/Packages/d/dwdiff-2.0.9-11.fc26.x86_64.rpm

wget http://os.ghalkes.nl/dist/dwdiff-2.0.10.tar.bz2
tar xvf dwdiff-2.0.10.tar.bz2
cd dwdiff-2.0.10/
./configure --without-unicode
make
mkdir -p $OPENSHIFT_REPO_DIR/data/bin/
mv dwdiff $OPENSHIFT_REPO_DIR/data/bin/

#wget http://dl.fedoraproject.org/pub/fedora/linux/releases/26/Everything/x86_64/os/Packages/x/xhtml1-dtds-1.0-20020801.13.fc26.2.noarch.rpm

#wget http://dl.fedoraproject.org/pub/fedora/linux/releases/26/Everything/x86_64/os/Packages/h/html401-dtds-4.01-19991224.12.fc26.8.noarch.rpm

#mkdir -p rpms
#rpm2cpio ../html401-dtds-4.01-19991224.12.fc26.8.noarch.rpm | cpio -idmv
#rpm2cpio ../xhtml1-dtds-1.0-20020801.13.fc26.2.noarch.rpm | cpio -idmv

cd $OPENSHIFT_REPO_DIR/wsgi

exec mod_wsgi-express start-server $ARGS application
