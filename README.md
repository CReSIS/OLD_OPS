OPS
===

OpenPolarServer Spatial Data Infrastructure

##About

The OpenPolarServer (OPS) is a complete spatial data infrastructure (SDI) built for The Center for Remote Sensing of Ice Sheets (CReSIS) at The University of Kansas. The SDI is a complete Linux server created using vagrant provisioning and Oracle VirtualBox. The server includes the following components:

* Apache HTTPD and Apache Tomcat6
* GeoServer Web Mapping Server
* PostgreSQL + PostGIS Spatial Database
* Django Web Framework
* ExtJS + GeoEXT + OpenLayers GeoPortal web application
* Optional CRON and SSMTP configuration
 
##Requirements

To install the OPS SDI you need to download and install the following:

Oracle VirtualBox (4.3.6+): https://www.virtualbox.org/wiki/Downloads

A VM WILL EVENTUALLY BE MADE AVAILBLE FOR DISTIBUTION. THIS IS CURRENTLY IN PROGRESS.

##Installation

COMING SOON.

### Public OPS Authentication

The distributed source code is meant for public use and therefore the username and password information is included here. Obviously these values have changed for the CReSIS hosted OPS system.

**Linux OS**

```username: ops
password: pubOps```


**GeoServer**

```username: admin
password: pubAdmin```

```username: root
password: pubMaster```


**PostgreSQL**

```username: admin
password: pubAdmin```

### Adding CReSIS data to the system

This can be done by placing CReSIS "data packs" into the /data/postgresql/ directory. Information on how and where to get these data packs is coming soon.

Documentation still in progress...
