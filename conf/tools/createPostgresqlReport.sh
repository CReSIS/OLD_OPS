#!/bin/sh
#
# Tool used to generate postgresql log reports.

# Takes output directory as an argument
outDir=$1
if [[ ! -d "$outDir" ]]; then
	echo "Please supply an existing directory for report output!"
	echo "Example: sh createPostgresqlReport.sh /existing/directory/"
	exit;
fi
 pgbadger -f stderr -p '%t [%p]: [%l-1] user=%u,db=%d '  -O $outDir -o postgresql_report_$(date +'%Y-%m-%d').html /db/pgsql/9.3/pg_log/postgresql-*.log;