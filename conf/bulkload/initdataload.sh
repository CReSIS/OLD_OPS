#!/bin/bash

STATUS_COLOR='\033[1;35m';
NC='\033[0m' # No Color

#KEEP TIME
START=$(date +%s)

pgdir='/db/pgsql/12/'
pgconfdir=$pgdir"postgresql.conf"

#MODIFY POSTGRESQL.CONF
printf "${STATUS_COLOR}Updating postgresql.conf${NC}\n";
# sed -i "s,#checkpoint_segments = 3,checkpoint_segments = 100,g" $pgconfdir  # This setting has been deprecated for (min/)max_wal_size
sed -i "s,#checkpoint_timeout = 5min,checkpoint_timeout = 1h,g" $pgconfdir
sed -i "s,#checkpoint_completion_target = 0.5,checkpoint_completion_target = 0.9,g" $pgconfdir

#RESTART POSTGRESQL
printf "${STATUS_COLOR}Restarting postgresql${NC}\n";
su - postgres -c '/usr/pgsql-12/bin/pg_ctl restart -m fast -D '$pgdir
sleep 2

# PREPARE DB FOR DATA LOAD
printf "${STATUS_COLOR}Preparing db for dataload${NC}\n";
psql -U postgres -d ops -c "SET maintenance_work_mem TO '1024MB';"

#Make a temporary directory and unpack initial data files to it.
printf "${STATUS_COLOR}Creating temp dir${NC}\n";
mkdir /tmp/pgdata/;

#Find all selected initial data files then unpack and load
printf "${STATUS_COLOR}Finding, unpacking, and unloading data files${NC}\n";
(
cd /opt/ops/data/postgresql/
for pack in *.tar.gz
do
    printf "${STATUS_COLOR}Unpacking ${pack}${NC}\n";
	tar -zxf /opt/ops/data/postgresql/$pack -C /tmp/pgdata/;
	#Use pg_bulkload to load initial data into the database.
	cd /tmp/pgdata/
    printf "${STATUS_COLOR}Loading files from ${pack}${NC}\n";

	# Make corrections to datapacks if they are from an old version of OPS
	for file in *_segments;
	do
		# Check if file has expected 6 columns or is missing the crossover_calc column (as with older versions of OPS)
		num_commas=`head -n 1 $file | grep -o ',' | wc -l`
		if [ "$num_commas" -lt 5 ]; then
			printf "${STATUS_COLOR}Adding default to crossover_calc to ${file} from ${pack}${NC}\n";
			awk -F"," 'BEGIN { OFS = "," } {$6="true"; print}' $file > "new_${file}"
			rm -f $file;
			mv "new_${file}" $file
		fi
	done
	for file in *_point_paths;
	do
		# Check if file has expected 10 columns or is missing the key_point column (as with older versions of OPS)
		num_commas=`head -n 1 $file | grep -o ',' | wc -l`
		if [ "$num_commas" -lt 10 ]; then
			printf "${STATUS_COLOR}Adding default to key_point to ${file} from ${pack}${NC}\n";
			awk -F"," 'BEGIN { OFS = "," } {$11="true"; print}' $file > "new_${file}"
			rm -f $file;
			mv "new_${file}" $file
		fi
	done

	# Load the files
	for file in *;
	do
        printf "${STATUS_COLOR}Loading ${file} from ${pack}${NC}\n";
		/usr/pgsql-12/bin/pg_bulkload -d ops -U admin -i /tmp/pgdata/$file -O $file;
		rm -f $file;
	done
done
)
printf "${STATUS_COLOR}Removing temp dir${NC}\n";
rmdir /tmp/pgdata/;

# CALL SQL TO RESUME NORMAL DATABASE
printf "${STATUS_COLOR}Cleanup bulkload${NC}\n";
su - postgres -c "psql -d ops -f /opt/ops/conf/bulkload/pg_bulkload_cleanup.sql"

# RE-SET POSTGRESQL.CONF
printf "${STATUS_COLOR}Resetting postgresql.conf${NC}\n";
# sed -i "s,checkpoint_segments = 100,#checkpoint_segments = 3,g" $pgconfdir
sed -i "s,checkpoint_timeout = 1h,#checkpoint_timeout = 5min,g" $pgconfdir
sed -i "s,checkpoint_completion_target = 0.9,#checkpoint_completion_target = 0.5,g" $pgconfdir

# RESTART POSTGRESQL
printf "${STATUS_COLOR}Restarting postgresql again${NC}\n";
su - postgres -c '/usr/pgsql-12/bin/pg_ctl restart -D '$pgdir
sleep 2

# FINISH TIME
END=$(date +%s)
DIFF=$(( $END - $START ))
printf "Data load took %7.1f seconds\n" $DIFF
