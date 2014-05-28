#!/bin/sh
#
# UPDATE GEOPORTAL FROM REPO

service tomcat6 stop
rm -rf /cresis/snfs1/web/ops2/geoserver/styles/*
cp -rf /vagrant/conf/geoserver/geoserver/styles/* /cresis/snfs1/web/ops2/geoserver/styles/
rm -rf /cresis/snfs1/web/ops2/geoserver/workspaces/*
cp -rf /vagrant/conf/geoserver/geoserver/workspaces/* /cresis/snfs1/web/ops2/geoserver/workspaces/
chmod -R u=rwX,g=rwX,o=rX /cresis/snfs1/web/ops2/geoserver/
chown -R tomcat:tomcat /cresis/snfs1/web/ops2/geoserver/
service tomcat6 start

