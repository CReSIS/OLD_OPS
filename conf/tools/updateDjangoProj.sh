#!/bin/sh
#
# UPDATE DJANGO FROM REPO

# Keep a copy of any existing eclipse project files.
cp -f /var/django/ops/.project /tmp/.project_tmp > /dev/null 2>&1
cp -f /var/django/ops/.pydevproject /tmp/.pydevproject_tmp > /dev/null 2>&1

cp -f /var/django/ops/ops/settings.py /tmp/DjangoSettings.old
rm -rf /var/django/*
cp -rf /vagrant/conf/django/* /var/django/

#Make updating settings.py optional.
while true; do
	read -p "Update settings.py?" yn
	case $yn in 
		[Yy]* ) 
			rm -f /tmp/DjangoSettings.old;
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
			
			#Set the OPS_DATA_PATH setting.  			
			echo "PLEASE ENTER THE OPS_DATA_PATH (e.g., /cresis/snfs1/web/ops(2)/ OR /db/)"
			read opsDataPath
			while true; do
					read -p "Is the following path correct: $opsDataPath?" yn
							case $yn in
							[Yy]* )
									read -p "ARE YOU SURE THIS IS THE CORRECT OPS BASE PATH: $opsDataPath?" yn
									case $yn in
											[Yy]* )
													sed -i "s,OPS_DATA_PATH = '',OPS_DATA_PATH = '$opsDataPath',g" /var/django/ops/ops/settings.py;
													break;;
											* ) echo "Please answer yes or no.";;
									esac;;
							[Nn]* )
									echo "Please enter the correct path for OPS_DATA_PATH:"
									read opsDataPath;;
							* ) echo "Please answer yes or no.";;
					esac
			done
			break;;	
					
		[Nn]* ) 
			cp -f /tmp/DjangoSettings.old /var/django/ops/ops/settings.py;
			rm -f /tmp/DjangoSettings.old;
			break;;
		* ) echo "Please answer yes or no.";;
	esac
done

#Move any existing eclipse project files back in place.
mv -f /tmp/.project_tmp /var/django/ops/.project > /dev/null 2>&1
mv -f /tmp/.pydevproject_tmp /var/django/ops/.pydevproject > /dev/null 2>&1