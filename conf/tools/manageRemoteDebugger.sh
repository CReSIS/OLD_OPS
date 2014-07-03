#!/bin/sh
#
# Tool for activating and deactivating Eclipse's Remote Debugger for the OPS Django application. 
# Example use: sh manageRemoteDebugger.sh
# For more information, see: https://github.com/CReSIS/OPS/wiki/Using-Eclipse#using-the-remote-debugger-in-eclipse

#Make sure the user wants to proceed. 
while true; do
	echo "WARNING: THIS FEATURE IS INTENDED FOR USE WITH DEVELOPMENT ENVIRONMENTS ONLY. THIS IS NOT CONSIDERED SUITABLE FOR USE IN A PRODUCTION SETTING."
	printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
	read -p "Are you sure you want to start or stop an Eclipse Remote Debugging Session?" yn
	case $yn in 
		[Yy]* ) 
			while [[ $choice != '1' ]] && [[ $choice != '2' ]] && [[ $choice != '3' ]]; do
				printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
				echo "Enter an option (1,2, or 3): (1) Start Remote Debugger; (2) Stop Remote Debugger; (3) Quit without changes";
				read choice;
				if [[ $choice = '1' ]]
				then
					#Start Remote Debugging
					#Append location of the PyDev debugging module to the python path in wsgi.py
					echo "sys.path.append('"$(find /opt/eclipse/plugins/ -type d -name 'pysrc')"')" >> /var/django/ops/ops/wsgi.py

					#Ensure Eclipse has access to the applicaiton code:
					sed -i "s,PATHS_FROM_ECLIPSE_TO_PYTHON = \[\],PATHS_FROM_ECLIPSE_TO_PYTHON = \[\(r\'/var/django/ops\'\,r\'/var/django/ops\'\)\],g" /opt/eclipse/plugins/org.python.pydev_*/pysrc/pydevd_file_utils.py
					
					#Prompt to start the debug server and then reload apache.
					printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
					echo "Please start the eclipse pydev server within the debug perspective (can be found under Pydev -> Start Debug Server)."
					while [[ $debugReady != '1' ]]; do
						echo "Enter '1' once the pydev debugger has started."
						read debugReady;
						if [[ $debugReady = '1' ]]
						then
							printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
							service httpd reload
							echo "You can now start remote debugging! Please use this tool to end your debugging session when you are done."
							exit
						else
							echo "Please Enter 1 When Ready!"
						fi
					done
				elif [[ $choice = '2' ]]
					then
					#Roll back above changes
					while true; do
						printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
						read -p "Have you ended the pydev debugging server?" yn
						printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
						case $yn in 
							[Yy]* )
								#Remove the pydevd module from the pythonpath.
								sed -i '/org.python.pydev/d' /var/django/ops/ops/wsgi.py;
								
								#Have the user remove any calls to pydevd
								while true; do
									find /var/django/ops/ -type f -name '*py' | xargs grep 'pydevd' | while read -r line; do
										if [[ -z "$filesExist" ]]; then
											echo -e "**THERE ARE FILES WITH 'pdevd' AND/OR 'settrace()' IN THEM: "
											filesExist=1
										fi
										echo $line
									done
									printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
									read -p "Have you removed ALL 'import pydevd' AND/OR 'pydevd.settrace()' calls in the ops Django application code?" yn
									case $yn in 
										[Yy]* )
											printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -
											#Reload apache
											service httpd reload;
											#Tell the user that the process has finished.
											echo "The pydev debugging session has been cleaned up.";
											exit;;
										[Nn]* ) 
											echo "PLEASE REMOVE ANY 'import pydevd' AND/OR 'pydevd.settrace()' CALLS IN THE OPS DJANGO APPLICATION CODE.";
											printf '%*s\n' "${COLUMNS:-$(tput cols)}" '' | tr ' ' -;;
										* ) echo "Please answer yes or no.";;
									esac
								done;;
							[Nn]* ) echo "Please end the pydev debugging server (Pydev -> End Debug Server)";;
							* ) echo "Please answer yes or no.";;
						esac
					done
				elif [[ $choice = '3' ]]
					then
					#Quit without any changes
					exit
				else
					#The user entered a non-supported value. 
					echo "MUST CHOOSE 1, 2, or 3!"
				fi		
			done;;
		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done