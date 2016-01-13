#!/bin/sh
#
# UPDATE GEOPORTAL FROM REPO

service tomcat6 stop
mv /var/lib/tomcat6/webapps/geoserver/data /tmp/data
rm -rf /var/lib/tomcat6/webapps/geoserver/*
cp -rf /vagrant/conf/geoserver/* /var/lib/tomcat6/webapps/geoserver/
mv /tmp/data /var/lib/tomcat6/webapps/geoserver/data
chmod -R u=rwX,g=rwX,o=rX /var/lib/tomcat6/webapps/geoserver/
chown -R tomcat:tomcat /var/lib/tomcat6/webapps/geoserver
service tomcat6 start