#!/bin/bash

#KEEP TIME
START=$(date +%s)

pgdir='/cresis/snfs1/web/ops/pgsql/9.3/'
pgconfdir=$pgdir"postgresql.conf"

#MODIFY POSTGRESQL.CONF
sed -i "s,#checkpoint_segments = 3,checkpoint_segments = 100,g" $pgconfdir
sed -i "s,#checkpoint_timeout = 5min,checkpoint_timeout = 1h,g" $pgconfdir
sed -i "s,#checkpoint_completion_target = 0.5,checkpoint_completion_target = 0.9,g" $pgconfdir

#RESTART POSTGRESQL
su - postgres -c '/usr/pgsql-9.3/bin/pg_ctl restart -m fast -D '$pgdir
sleep 2

# PREPARE DB FOR DATA LOAD
psql -U postgres -d ops -c "SET maintenance_work_mem TO '1024MB';"

#Make a temporary directory and unpack initial data files to it. 
mkdir /tmp/pgdata/;

#Find all selected initial data files then unpack and load 
(
cd /vagrant/data/postgresql/
for pack in *.tar.gz
do 
	tar -zxf /vagrant/data/postgresql/$pack -C /tmp/pgdata/;
	#Use pg_bulkload to load initial data into the database. 
	cd /tmp/pgdata/
	for file in *; 
	do 
		/usr/pgsql-9.3/bin/pg_bulkload -d ops -U admin -i /tmp/pgdata/$file -O $file;
		rm -f $file;
	done
done
)
rmdir /tmp/pgdata/;

# CALL SQL TO RESUME NORMAL DATABASE 
su - postgres -c "psql -d ops -f /vagrant/conf/bulkload/pg_bulkload_cleanup.sql"

# RE-SET POSTGRESQL.CONF
sed -i "s,checkpoint_segments = 100,#checkpoint_segments = 3,g" $pgconfdir
sed -i "s,checkpoint_timeout = 1h,#checkpoint_timeout = 5min,g" $pgconfdir
sed -i "s,checkpoint_completion_target = 0.9,#checkpoint_completion_target = 0.5,g" $pgconfdir

# RESTART POSTGRESQL
su - postgres -c '/usr/pgsql-9.3/bin/pg_ctl restart -D '$pgdir
sleep 2

# FINISH TIME
END=$(date +%s)
DIFF=$(( $END - $START ))
printf "Data load took %7.1f seconds\n" $DIFF
