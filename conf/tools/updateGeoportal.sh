#!/bin/sh
#
# UPDATE GEOPORTAL FROM REPO

while true; do
	read -p "Would you like to update the geoportal?" yn
	case $yn in 
		[Yy]* ) 
			service httpd stop
			rm -rf /var/www/html/*
			cp -rf /vagrant/conf/geoportal/* /var/www/html/
			service httpd start
			break;;

		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done

while true; do
	read -p "Would you like to enable the debug page?" yn
	case $yn in 
		[Yy]* ) 
			printf "		*****NOTE*****\n"
			printf "You must git clone the OPS-GEOPORTAL to /opt/OPS-GEOPORTAL/ for this to work.\n"
			printf "		*****NOTE*****\n"
			read -n1 -r -p "Press space to continue..." key
			rm /var/www/html/debug
			ln -s /opt/OPS-GEOPORTAL/ /var/www/html/debug
			rm /opt/OPS-GEOPORTAL/GeoExt
			ln -s /opt/OPS-GEOPORTAL/geoext/src/GeoExt  /opt/OPS-GEOPORTAL/GeoExt
			chmod -R a+rX /opt/OPS-GEOPORTAL/
			printf "http://192.168.111.222/debug/ should now point to the OPS-GEOPORTAL.\n"
			break;;

		[Nn]* )
			rm /var/www/html/debug
			rm /opt/OPS-GEOPORTAL/GeoExt
			break;;
		* ) echo "Please answer yes or no.";;
	esac
done

