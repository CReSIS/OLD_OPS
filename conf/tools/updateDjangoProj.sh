#!/bin/sh
#
# UPDATE DJANGO FROM REPO

rm -rf /var/django/*
cp -rf /vagrant/conf/django/* /var/django/

#Add Django admins
while true; do
	if [[ -z "$adminStr" ]]; then
		read -p "Do you wish to add an admin to Django (receives error messages)?" yn
	else
		read -p "Would you like to add another admin to Django (also receives error messages)?" yn
	fi
	case $yn in 
		[Yy]* ) 
			echo "Type the admin's name, followed by [ENTER]:";
			read name;
			echo "Type the admin's email, followed by [ENTER]:";
			read email; 
			read -p "are the name ($name) and email ($email) correct?" yn
			case $yn in 
				[Yy]* )adminStr="$adminStr \('$name'\, '$email'\)\,";;
				* ) echo "Please answer yes or no.";;
			esac;;
		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done
sed -i "s,ADMINS = (),ADMINS = ($adminStr),g" /var/django/ops/ops/settings.py

#Optionally set the debug parameter in Django.  			
while true; do		

	read -p "Would you like to have Django operate in debug mode (DEVELOPMENT ENVIRONMENT ONLY!)?" yn
	case $yn in 
		[Yy]* ) 
			read -p "ARE YOU SURE YOU WANT DJANGO TO BE IN DEBUG MODE? THIS IS FOR DEVELOPMENT ENVIRONMENTS ONLY." yn
			case $yn in 
				[Yy]* ) 
					sed -i "s,DEBUG = False,DEBUG = True,g" /var/django/ops/ops/settings.py;
					break;;
				* ) echo "Please answer yes or no.";;
			esac;;
		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done