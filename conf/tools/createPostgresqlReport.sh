#!/bin/sh
#
# Tool used to generate postgresql log reports.
 pgbadger -f stderr -p '%t [%p]: [%l-1] user=%u,db=%d '  -O /cresis/snfs1/web/ops2/postgresql_reports/ -o postgresql_report_$(date +'%Y-%m-%d').html /cresis/snfs1/web/ops2/pgsql/9.3/pg_log/postgresql-*.log;