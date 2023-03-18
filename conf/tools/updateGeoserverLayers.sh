#!/bin/sh
#
# UPDATE GEOPORTAL FROM REPO

service tomcat6 stop
rm -rf /db/geoserver/styles/*
cp -rf /opt/ops/conf/geoserver/geoserver/styles/* /db/geoserver/styles/
rm -rf /db/geoserver/workspaces/*
cp -rf /opt/ops/conf/geoserver/geoserver/workspaces/* /db/geoserver/workspaces/
chmod -R u=rwX,g=rwX,o=rX /db/geoserver/
chown -R tomcat:tomcat /db/geoserver/
service tomcat6 start

