#!/bin/sh
#
# SCRIPT FOR CREATING THE WEEKLY POSTGRESQL LOG REPORT

now=$(date +"%Y-%m-%d")
pgbadger -f stderr -p '%t [%p]: [%l-1] user=%u,db=%d '  -O /cresis/snfs1/web/ops2/postgresql_reports/ -o postgresql_report_$now /cresis/snfs1/web/ops2/pgsql/9.3/pg_log/postgresql-*.log