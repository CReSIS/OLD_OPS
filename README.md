OPS
===

OpenPolarServer Spatial Data Infrastructure

## About

The OpenPolarServer (OPS) is a complete spatial data infrastructure (SDI) built for The Center for Remote Sensing of Ice Sheets (CReSIS) at The University of Kansas. The SDI is a complete Linux server created using vagrant provisioning and Oracle VirtualBox. The server includes the following components:

* Apache HTTPD and Apache Tomcat6
* GeoServer Web Mapping Server
* PostgreSQL + PostGIS Spatial Database
* Django Web Framework
* ExtJS + GeoEXT + OpenLayers GeoPortal web application
* Optional CRON and SSMTP configuration

## To cite usage of the Open Polar Server please use the following:

    CReSIS. 2023. Open Polar Server [computer software], Lawrence,  Kansas, USA. Retrieved from https://github.com/CReSIS/.

## To acknowledge the use of the CReSIS Toolbox, please note Kansas, NSF and NASA contributions. For example:

    We acknowledge the use of the CReSIS Open Polar Server from CReSIS generated with support from the University of Kansas, NASA Operation IceBridge grant NNX16AH54G, and NSF grants ICER-2126503.

## Requirements

A Centos 7 Linux server or virtual machine. We test the setup using Oracle VirtualBox at https://www.virtualbox.org/wiki/Downloads.

Provisioned Virtual Machines are available at:
https://data.cresis.ku.edu/data/temp/ct/ops/

## Installation

On a clean centos 7.9 VM:

```bash
yum install -y git
git clone https://github.com/cresis/ops.git /opt/ops
cd /opt/ops

sh conf/provisions.sh

# Answer prompts and watch for errors
# At the half-way point, a reboot is required. After the reboot, resume the script:
cd /opt/ops
sh conf/provisions.sh
```

After install, edit `/var/django/ops/ops/settings.py` and add the URL/IP that points to the VM to the `ALLOWED_HOSTS` list.

## Endpoints

Assuming the VM's IP is `192.168.111.222`:

`192.168.111.222`: The geoportal for accessing OPS

`192.168.111.222/git`: A local Gitlab server with copies of a few OPS-related repos

`192.168.111.222/geoserver`: The geoserver which hosts map data


### Public OPS Authentication

The username and password for the default setup are included here.

**Linux OS**

```
username: root
password: pubMaster
```

```
username: ops
password: pubOps
```

**Gitlab**

```
username: root
password: pubMaster
```

**GeoServer**

```
username: admin
password: pubAdmin
```

**PostgreSQL**

```
username: admin
password: pubAdmin
```

### Adding CReSIS data to the system

This can be done by placing CReSIS "data packs" into the /data/postgresql/ directory. Information on how and where to get these data packs can be found [here.](https://github.com/CReSIS/OPS/wiki/Data-bulkload)

Documentation still in progress...
