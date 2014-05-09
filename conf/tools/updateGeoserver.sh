#!/bin/sh
#
# UPDATE GEOPORTAL FROM REPO

service tomcat6 stop
mv /cresis/snfs1/web/ops2/geoserver/data /tmp/data
rm -rf /cresis/snfs1/web/ops2/geoserver/*
cp -rf /vagrant/conf/geoserver/geoserver/* /cresis/snfs1/web/ops2/geoserver/
mv /tmp/data /cresis/snfs1/web/ops2/geoserver/data
chmod -R u=rwX,g=rwX,o=rX /cresis/snfs1/web/ops2/geoserver/
chown -R tomcat:tomcat /cresis/snfs1/web/ops2/geoserver/
service tomcat6 start