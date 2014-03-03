OPS
===

OpenPolarServer Spatial Data Infrastructure

##About

The OpenPolarServer (OPS) is a complete spatial data infrastructure (SDI) built for The Center for Remote Sensing of Ice Sheets (CReSIS) at The University of Kansas. The SDI is a comlete linux server created using vagrant provisioning and Oracle VirtualBox. The server includes the following components:

* Apache HTTPD and Apache Tomcat6
* GeoServer Web Mapping Server
* PostgreSQL + PostGIS Spatial Database
* Django Web Framework
* ExtJS + GeoEXT + OpenLayers GeoPortal web application
* Optional CRON and SSMTP configuration
* Vagrant SHELL provisioning script
 
##Requirements

To install the OPS SDI you need to download and install the following:

Oracle VirtualBox (4.3.6+): https://www.virtualbox.org/wiki/Downloads

Vagrant(1.4.3+): http://www.vagrantup.com/downloads.html

##Installation

Creating your own standalone installation of the OPS system is simple!

1. Install VirtualBox and Vagrant (See Requirements above)
2. Download a release or pull a GitHub branch
2. Open a Command Prompt / Terminal and move (cd) into the root directory of the project
3. Type ```vagrant up``` to start the installation process (~30 minutes)
4. Visit 192.168.111.222 in your browser when it's done!


### Modifying the installation settings

Some basic parameters can be modified before installation. For now it is reccomended that you only change the hardware options and not any of the network parameters. To do this edit the ```Vagrantfile```

```ruby
config.vm.provider :virtualbox do |vb|

	# BOOT INTO A GUI
	vb.gui = true

	# CHANGE THE NAME
	vb.name = "OpenPolarServer"

	# CHANGE THE HARDWARE ALLOTMENT
	vb.customize ["modifyvm", :id, "--memory", "2048"]
	vb.customize ["modifyvm", :id, "--cpus", "2"]

end
```
	
You can change the memory and/or cpu allocations by editing the ```--memory``` and ```--cpus``` parameters. You can also boot in "headless" mode (with no GUI) by setting ```vb.gui = false```.

### Adding CReSIS data to the system

This can be done by plasing CReSIS "data packs" into the /data/postgresql/ directroy. Information on how and where to get these data packs is coming soon.

Documentation still in progress...
