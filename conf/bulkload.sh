#!/bin/sh
#
# OpenPolarServer (Public) Build Tools
#
# CONTACT: cresis_data@cresis.ku.edu
#
# AUTHORS: Kyle W. Purdon, Trey Stafford

# =================================================================================
# ---------------------------------------------------------------------------------
# ****************** DO NOT MODIFY ANYTHING BELOW THIS LINE ***********************
# ---------------------------------------------------------------------------------
# =================================================================================

#notify-send "Now building OpenPolarServer"
#notify-send "Please watch for more prompts (there will be a few you need to act on). Thank you."

printf "\n\n"
printf "#########################################################################\n"
printf "#########################################################################\n"
printf "#\n"
printf "# Welcome to the OpenPolarServer (OPS)\n"
printf "#\n"
printf "# Bulkloading data.\n"
printf "#\n"
printf "# On completion instructions will be printed to the screen.\n"
printf "#\n"
printf "#########################################################################\n"
printf "#########################################################################\n"
printf "\n"

startTime=$(date -u);

# --------------------------------------------------------------------
#PROMPT TO OPTIONALLY LOAD IN DATA (DATA BULKLOAD)
installPgData=0;
while true; do
	read -p "Would you like to bulk load the OpenPolarServer with data? [y/n]" yn
	case $yn in 
		[Yy]* ) 
			installPgData=1;
			printf "		*****NOTE*****\n"
			printf "You must place the desired datapacks in \n/opt/ops/data/postgresql/ before continuing.\n"
			printf "		*****NOTE*****\n"
			read -n1 -r -p "Press space to continue..." key
			break;;

		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done

while true; do
	printf "\nWould you like to load in a sample dataset from CReSIS (useful for testing and upgrading the system)?\n"
	read -p "[y/n]" yn
	case $yn in 
		[Yy]* ) 
			installPgData=1;
			# DOWNLOAD A PREMADE DATA PACK FROM CReSIS (MINIMAL LAYERS)
			wget https://data.cresis.ku.edu/data/ops/SampleData.zip -P /opt/ops/data/postgresql/   
			unzip /opt/ops/data/postgresql/SampleData.zip -d /opt/ops/data/postgresql/
			rm /opt/ops/data/postgresql/SampleData.zip
			break;;
		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done

# --------------------------------------------------------------------
# BULKLOAD DATA TO POSTGRESQL 

if [ $installPgData -eq 1 ]; then
	fCount=$(ls -A /opt/ops/data/postgresql/ | wc -l);
	if [ $fCount -gt 1 ]; then
		# LOAD INITIAL DATA INTO THE DATABASE
		sh /opt/ops/conf/bulkload/initdataload.sh
	fi
fi

# --------------------------------------------------------------------
# PRINT OUT THE COMPLETION NOTICE

stopTime=$(date -u);

printf "\n"	
printf "BULKLOAD COMPLETE. INSTRUCTIONS BELOW.\n"
printf "\n"
echo "Started at:" $startTime
echo "Finished at:" $stopTime

#notify-send "OpenPolarServer build complete. See terminal for details."
