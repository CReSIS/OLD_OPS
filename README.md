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

A Centos 6 Linux server or virtual machine. We test the setup using Oracle VirtualBox at https://www.virtualbox.org/wiki/Downloads.

Provisioned Virtual Machines are available at:
https://data.cresis.ku.edu/data/temp/ct/ops/

**NOTE: We are currently updating all the packages to the latest releases on a Centos 7 virtual box which we aim to distribute in April 2021.**

##Installation

Check https://github.com/CReSIS/OPS/wiki for instructions.

###Public OPS Authentication

The username and password for the default setup are included here.

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

This can be done by placing CReSIS "data packs" into the /data/postgresql/ directory. Information on how and where to get these data packs can be found [here.](https://github.com/CReSIS/OPS/wiki/Data-bulkload)

Documentation still in progress...
