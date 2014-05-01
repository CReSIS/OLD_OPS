#!/bin/sh
#
# UPDATE GEOPORTAL FROM REPO

service httpd stop
rm -rf /var/www/html/*
cp -rf /vagrant/conf/geoportal/* /var/www/html/
service httpd start