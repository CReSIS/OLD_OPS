#!/bin/sh
#
# Tool used to vacuum analyze the OPS database.

# Takes database name as argument.
dbName=$1

if [[ -z "$dbName" ]]; then
	echo "Please supply a database name!"
	echo "Example: sh vacuumAnalyzeOps.sh ops"
	exit;
fi

su postgres -c "psql -d "$dbName" -c 'VACUUM ANALYZE;'"
