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
printf "# The system will now be configured (30-40 minutes).\n"
printf "#   *If data is included it could be much longer (hour+).\n"
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
			printf "You must place the desired datapacks in \n/vagrant/data/postgresql/ before continuing.\n"
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
			wget https://data.cresis.ku.edu/data/ops/SampleData.zip -P /vagrant/data/postgresql/   
			unzip /vagrant/data/postgresql/SampleData.zip -d /vagrant/data/postgresql/
			rm /vagrant/data/postgresql/SampleData.zip
			break;;
		[Nn]* ) break;;
		* ) echo "Please answer yes or no.";;
	esac
done

# --------------------------------------------------------------------
# SET SOME STATIC INPUTS
preProv=1;
newDb=1;
serverName="192.168.111.222";
serverAdmin="root"; 
appName="ops";
dbName="ops";

opsDataPath="/db/";
webDataDir=$opsDataPath"data";

# --------------------------------------------------------------------
# GET SOME INPUTS FROM THE USER

read -s -p "Database User (default=admin): " dbUser && printf "\n";
read -s -p "Database Password (default=pubAdmin): " dbPswd && printf "\n";
if [[ -z "${dbUser// }" ]]; then
  dbUser="admin"
fi
if [[ -z "${dbPswd// }" ]]; then
  dbPswd="pubAdmin"
fi
echo -e $dbPswd > /etc/db_pswd.txt;

# --------------------------------------------------------------------
# PRE-PROVISION THE OPS (NEED FOR CRESIS VM TEMPLATE)

if [ $preProv -eq 1 ]; then

	cd ~ && cp /vagrant/conf/software/epel-release-latest-7.noarch.rpm ./
	rpm -Uvh epel-release-latest-7*.rpm 
	rm -f epel-release-latest-7.noarch.rpm
	yum update -y
	yum groupinstall -y "Development Tools"
	yum install -y gzip gcc unzip rsync wget git
	iptables -F 
	iptables -A INPUT -p tcp --dport 22 -j ACCEPT #SSH ON TCP 22
	iptables -A INPUT -p tcp --dport 80 -j ACCEPT #HTTP ON TCP 80
	iptables -A INPUT -p tcp --dport 443 -j ACCEPT #HTTPS ON TCP 443
	iptables -P INPUT DROP 
	iptables -P FORWARD DROP 
	iptables -P OUTPUT ACCEPT 
	iptables -A INPUT -i lo -j ACCEPT 
	iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT 
	/sbin/service iptables save 
	/sbin/service iptables restart 

fi

# --------------------------------------------------------------------
# WRITE GEOSERVER_DATA_DIR TO ~/.bashrc

geoServerStr="GEOSERVER_DATA_DIR="$opsDataPath"geoserver"
echo $geoServerStr >> ~/.bashrc
. ~/.bashrc

# --------------------------------------------------------------------
# UPDATE THE SYSTEM AND INSTALL PGDG REPO

# UPDATE SYSTEM
yum update -y

# INSTALL THE PGDG REPO
cd ~ && cp -f /vagrant/conf/software/pgdg-redhat-repo-latest.noarch.rpm ./
rpm -Uvh pgdg-redhat-repo-latest.noarch.rpm
rm -f pgdg-redhat-repo-latest.noarch.rpm

# --------------------------------------------------------------------

# INSTALL PYTHON3 and DEPENDENCIES
yum install -y centos-release-scl
yum-config-manager --enable centos-sclo-rh-testing
yum-config-manager --enable rhel-server-rhscl-7-rpms
yum-config-manager --enable rhel-server-rhscl-beta-7-rpms
yum install -y rh-python36
source scl_source enable rh-python36
echo -e "#!/bin/bash\nsource scl_source enable rh-python36" >> /etc/profile.d/python36.sh

python -m pip install --upgrade pip --no-cache-dir
python -m pip install pip --no-cache-dir # Try twice as it seems to fail sometimes
python -m venv /usr/bin/venv
source /usr/bin/venv/bin/activate

# --------------------------------------------------------------------
# INSTALL APACHE WEB SERVER AND MOD_WSGI

# Set SELinux policy to disabled
# TODO[reece]: This is presumably not ideal -- Determine best practice solution
setenforce 0

selinuxStr="# cat /etc/selinux/config

# This file controls the state of SELinux on the system.
# SELINUX= can take one of these three values:
#     enforcing - SELinux security policy is enforced.
#     permissive - SELinux prints warnings instead of enforcing.
#     disabled - No SELinux policy is loaded.
SELINUX=disabled
# SELINUXTYPE= can take one of three two values:
#     targeted - Targeted processes are protected,
#     minimum - Modification of targeted policy. Only selected processes are protected.
#     mls - Multi Level Security protection.
SELINUXTYPE=targeted
"

echo -e "$selinuxStr" > /etc/selinux/config

# INSTALL APACHE HTTPD
yum install -y httpd httpd-devel

# INSTALL MOD_WSGI (COMPILE WITH Python36)
pip install --upgrade mod_wsgi --no-cache-dir

# --------------------------------------------------------------------
# WRITE CONFIG FILES FOR HTTPD

# INCLUDE THE SITE CONFIGURATION FOR HTTPD
echo "Include /var/www/sites/"$serverName"/conf/"$appName".conf" >> /etc/httpd/conf/httpd.conf

mkdir -m 777 -p $webDataDir

# WRITE THE DJANGO WSGI CONFIGURATION
wsgiStr="
"$(mod_wsgi-express module-config)"

WSGISocketPrefix run/wsgi
WSGIDaemonProcess $appName user=apache python-path=/var/django/$appName:/usr/bin/venv/lib/python3.6/site-packages
WSGIProcessGroup $appName
WSGIScriptAlias /$appName /var/django/$appName/$appName/wsgi.py process-group=$appName application-group=%{GLOBAL}
<Directory /var/django/$appName/$appName>
	<Files wsgi.py>
		Order deny,allow
		Allow from all
	</Files>
</Directory>";

echo -e "$wsgiStr" > /etc/httpd/conf.d/djangoWsgi.conf

# WRITE THE GEOSERVER PROXY CONFIGURATION
geoservStr="
ProxyRequests Off
ProxyPreserveHost On

<Proxy *>
	Order deny,allow
	Allow from all
</Proxy>

ProxyPass /geoserver http://localhost:8080/geoserver
ProxyPassReverse /geoserver http://localhost:8080/geoserver"

echo -e "$geoservStr" > /etc/httpd/conf.d/geoserverProxy.conf

# WRITE THE HTTPD SITE CONFIGURATION
mkdir -p /var/www/sites/$serverName/conf
mkdir -p /var/www/sites/$serverName/logs
mkdir -p /var/www/sites/$serverName/cgi-bin

siteConf="
<VirtualHost *:80>
	
	ServerAdmin "$serverAdmin"
	DocumentRoot /var/www/html
	ServerName "$serverName"

	ErrorLog /var/www/sites/"$serverName"/logs/error_log
	CustomLog /var/www/sites/"$serverName"/logs/access_log combined

    LoadModule speling_module modules/mod_speling.so
	CheckSpelling on
	
	ScriptAlias /cgi-bin/ /var/www/"$serverName"/cgi-bin/
	<Location /cgi-bin>
		Options +ExecCGI
	</Location>

	Alias /data "$webDataDir"
	<Directory "$webDataDir">
		Options Indexes FollowSymLinks
		AllowOverride None
		Order allow,deny
		Allow from all
		ForceType application/octet-stream
		Header set Content-Disposition attachment
	</Directory>
	
	Alias /profile-logs /var/profile_logs/txt
	<Directory ""/var/profile_logs/txt"">
		Options Indexes FollowSymLinks
		AllowOverride None
		Order allow,deny
		Allow from all
	</Directory>

</VirtualHost>"

echo -e "$siteConf" > /var/www/sites/$serverName/conf/$appName.conf
touch /var/www/sites/$serverName/logs/error_log
touch /var/www/sites/$serverName/logs/access_log

# WRITE THE CGI PROXY
cgiStr="
#!/usr/bin/env python
import urllib.request, urllib.error, urllib.parse
import cgi
import sys, os

allowedHosts = [
    '"$serverName",
    'www.openlayers.org',
    'openlayers.org',
    'labs.metacarta.com',
    'world.freemap.in',
    'prototype.openmnnd.org',
    'geo.openplans.org',
    'sigma.openplans.org',
    'demo.opengeo.org',
    'www.openstreetmap.org',
    'sample.azavea.com',
    'v2.suite.opengeo.org',
    'v-swe.uni-muenster.de:8080',
    'vmap0.tiles.osgeo.org',
    'www.openrouteservice.org',
]

method = os.environ['REQUEST_METHOD']

if method == 'POST':
    qs = os.environ['QUERY_STRING']
    d = cgi.parse_qs(qs)
    if 'url' in d:
        url = d['url'][0]
    else:
        url = 'http://www.openlayers.org'
else:
    fs = cgi.FieldStorage()
    url = fs.getvalue('url', 'http://www.openlayers.org')

try:
    host = url.split('/')[2]
    if allowedHosts and not host in allowedHosts:
        print('Status: 502 Bad Gateway')
        print('Content-Type: text/plain')
        print()
        print('This proxy does not allow you to access that location (%s).' % (host,))
        print()
        print(os.environ)

    elif url.startswith('http://') or url.startswith('https://'):

        if method == 'POST':
            length = int(os.environ['CONTENT_LENGTH'])
            headers = {'Content-Type': os.environ['CONTENT_TYPE']}
            body = sys.stdin.read(length)
            r = urllib.request.Request(url, body, headers)
            y = urllib.request.urlopen(r)
        else:
            y = urllib.request.urlopen(url)

        # print content type header
        i = y.info()
        if 'Content-Type' in i:
            print('Content-Type: %s' % (i['Content-Type']))
        else:
            print('Content-Type: text/plain')
        print()

        print(y.read())

        y.close()
    else:
        print('Content-Type: text/plain')
        print()
        print('Illegal request.')

except Exception as E:
    print('Status: 500 Unexpected Error')
    print('Content-Type: text/plain')
    print()
    print('Some unexpected error occurred. Error text was:', E)"

echo -e "$cgiStr" > /var/www/sites/$serverName/cgi-bin/proxy.cgi
chmod +x /var/www/sites/$serverName/cgi-bin/proxy.cgi
		
# --------------------------------------------------------------------
# WRITE CRONTAB CONFIGURATION

cronStr="
SHELL=/bin/bash
PATH=/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=''
HOME=/

# REMOVE CSV FILES OLDER THAN 7 DAYS AT 2 AM DAILY
0 2 * * * root rm -f $(find "$webDataDir"/csv/*.csv -mtime +7);
0 2 * * * root rm -f $(find "$webDataDir"/kml/*.kml -mtime +7); 
0 2 * * * root rm -f $(find "$webDataDir"/mat/*.mat -mtime +7);
0 2 * * * root rm -f $(find "$webDataDir"/reports/*.csv -mtime +7);
0 2 * * * root rm -f $(find "$webDataDir"/datapacks/*.tar.gz -mtime +7);

# VACUUM ANALYZE-ONLY THE ENTIRE OPS DATABASE AT 2 AM DAILY
0 2 * * * root sh /vagrant/conf/tools/vacuumAnalyze.sh ops

# WEEKLY POSTGRESQL REPORT CREATION AT 2 AM SUNDAY
0 2 * * 7 root sh /vagrant/conf/tools/createPostgresqlReport.sh "$opsDataPath"postgresql_reports/

# REMOVE POSTGRESQL REPORTS OLDER THAN 2 MONTHS EVERY SUNDAY AT 2 AM
0 2 * * 7 root rm -f $(find "$opsDataPath"postgresql_reports/*.html -mtime +60);

# CLEAR THE CONTENTS OF THE DJANGO LOGS EVERY MONTH (FIRST OF MONTH, 2 AM)
0 2 1 * * root > "$opsDataPath"django_logs/createPath.log;

"

echo -n > /etc/crontab
echo "$cronStr" > /etc/crontab

service crond start
chkconfig crond on

# --------------------------------------------------------------------
# INSTALL JAVA JRE, JAI, JAI I/O

# COPY INSTALLATION FILES
cd ~
cp /vagrant/conf/software/jai-1_1_1_01-lib-linux-i586-jre.bin ./
cp /vagrant/conf/software/jai_imageio-1_0_01-lib-linux-i586-jre.bin ./

# INSTALL JAVA JRE
yum install -y java-11-openjdk-devel

# NOT INSTALLING JAI/JAIIO UNTIL WE FIGURE OUT HOW TO MAKE THEM USER FRIENDLY INSTALLS.

##notify-send "Installing JAVA. Please manually accept the two license agreements in the terminal."

# INSTALL JAI
cd /usr/java/jre11.0.9/
chmod u+x ~/jai-1_1_1_01-lib-linux-i586-jre.bin
~/jai-1_1_1_01-lib-linux-i586-jre.bin
rm -f ~/jai-1_1_1_01-lib-linux-i586-jre.bin

# INSTALL JAI-IO
export _POSIX2_VERSION=199209 
chmod u+x ~/jai_imageio-1_0_01-lib-linux-i586-jre.bin 
~/jai_imageio-1_0_01-lib-linux-i586-jre.bin 
rm -f ~/jai_imageio-1_0_01-lib-linux-i586-jre.bin && cd ~

##notify-send "Thank you for your input. The installation will now automatically continue."

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE POSTGRESQL + POSTGIS

pgDir=$opsDataPath'pgsql/12/'
pgPth=$opsDataPath'pgsql/'

# EXCLUDE POSTGRESQL FROM THE BASE CentOS RPM
sed -i -e '/^\[base\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo 
sed -i -e '/^\[updates\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo 

# INSTALL POSTGRESQL and POSTGIS
yum install -y postgresql12 postgresql12-server postgis30_12.x86_64

# INSTALL PYTHON PSYCOPG2 MODULE FOR POSTGRES
export PATH=/usr/pgsql-12/bin:"$PATH"
pip install psycopg2-binary

if [ $newDb -eq 1 ]; then
	
	# MAKE THE SNFS1 MOCK DIRECTORY IF IT DOESNT EXIST
	if [ ! -d $pgPth ]
		then
			mkdir -p $pgPth
			chown postgres:postgres $pgPth
			chmod 700 $pgPth
	fi
	
	# INITIALIZE THE DATABASE CLUSTER

    initScript="
    #!/bin/sh
#
# postgresql    This is the init script for starting up the PostgreSQL
#               server.
#
# chkconfig: - 64 36
# description: PostgreSQL database server.
# processname: postmaster
# pidfile=\"/var/run/${NAME}.pid\"

# This script is slightly unusual in that the name of the daemon (postmaster)
# is not the same as the name of the subsystem (postgresql)

# Version 9.0 Devrim Gunduz <devrim@gunduz.org>
# Get rid of duplicate PGDATA assignment.
# Ensure pgstartup.log gets the right ownership/permissions during initdb

# Version 9.1 Devrim Gunduz <devrim@gunduz.org>
# Update for 9.1
# Add an option to initdb to specify locale (default is $LANG):
# service postgresql initdb tr_TR.UTF-8

# Version 9.2 Devrim Gunduz <devrim@gunduz.org>
# Update for 9.2

# Version 9.2.1 Devrim Gunduz <devrim@gunduz.org>
# Fix version number in initdb warning message, per Jose Pedro Oliveira.
# Add new functionality: Upgrade from previous version.
# Usage: service postgresql-9.2 upgrade

# Version 9.2.3 Devrim Gunduz <devrim@gunduz.org>
# Fix longstanding bug: Enable pidfile and lockfile variables to be defined
# in sysconfig file.
# Use $pidfile in status().

# Version 9.2.4 Devrim Gunduz <devrim@gunduz.org>
# Fix pid file name in init script, so that it is more suitable for
# multiple postmasters. Per suggestion from Andrew Dunstan. Fixes #92.

# Version 9.3.0 Devrim Gunduz <devrim@gunduz.org>
# Add support for pg_ctl promote. Per suggestion from Magnus Hagander. Fixes #93.
# Remove hardcoded script names in init script. Fixes #102.

# Version 9.3.1 Devrim Gunduz <devrim@gunduz.org>
# Fix PGPREVMAJORVERSION parameter, per report from Igor Poteryaev.
# Remove extra whitespace in upgrade() code, per report from Igor Poteryaev.

# Version 9.3.2 Devrim Gunduz <devrim@gunduz.org>
# Add process name to the status() call. Patch from Darrin Smart

# PGVERSION is the full package version, e.g., 9.3.0
# Note: the specfile inserts the correct value during package build
PGVERSION=9.3.13
# PGMAJORVERSION is major version, e.g., 9.3 (this should match PG_VERSION)
PGMAJORVERSION=`echo \"$PGVERSION\" | sed 's/^\([0-9]*\.[0-9]*\).*$/\1/'`
PGPREVMAJORVERSION=9.2

# Source function library.
INITD=/etc/rc.d/init.d
. $INITD/functions

# Get function listing for cross-distribution logic.
TYPESET=`typeset -f|grep \"declare\"`

# Get network config.
. /etc/sysconfig/network

# Find the name of the script
NAME=`basename $0`
if [ ${NAME:0:1} = \"S\" -o ${NAME:0:1} = \"K\" ]
then
	NAME=${NAME:3}
fi

# For SELinux we need to use 'runuser' not 'su'
if [ -x /sbin/runuser ]
then
    SU=runuser
else
    SU=su
fi

# Define variable for locale parameter:
LOCALEPARAMETER=$2

# Set defaults for configuration variables
PGENGINE=/usr/pgsql-9.3/bin
PGPORT=5432
PGDATA=/db/pgsql/9.3/
PGLOG=/db/pgsql/9.3//pgstartup.log
# Log file for pg_upgrade
PGUPLOG=/var/lib/pgsql/$PGMAJORVERSION/pgupgrade.log

lockfile=\"/var/lock/subsys/${NAME}\"
pidfile=\"/var/run/${NAME}.pid\"

# Override defaults from /etc/sysconfig/pgsql if file is present
[ -f /etc/sysconfig/pgsql/${NAME} ] && . /etc/sysconfig/pgsql/${NAME}

export PGDATA
export PGPORT

[ -f \"$PGENGINE/postmaster\" ] || exit 1

script_result=0

start(){
	[ -x \"$PGENGINE/postmaster\" ] || exit 5

	PSQL_START=$\"Starting ${NAME} service: \"

	# Make sure startup-time log file is valid
	if [ ! -e \"$PGLOG\" -a ! -h \"$PGLOG\" ]
	then
		touch \"$PGLOG\" || exit 1
		chown postgres:postgres \"$PGLOG\"
		chmod go-rwx \"$PGLOG\"
		[ -x /sbin/restorecon ] && /sbin/restorecon \"$PGLOG\"
	fi

	# Check for the PGDATA structure
	if [ -f \"$PGDATA/PG_VERSION\" ] && [ -d \"$PGDATA/base\" ]
	then
		# Check version of existing PGDATA

		if [ x`cat \"$PGDATA/PG_VERSION\"` != x\"$PGMAJORVERSION\" ]
		then
			SYSDOCDIR=\"(Your System's documentation directory)\"
			if [ -d \"/usr/doc/postgresql-$PGVERSION\" ]
			then
				SYSDOCDIR=/usr/doc
			fi
			if [ -d \"/usr/share/doc/postgresql-$PGVERSION\" ]
			then
				SYSDOCDIR=/usr/share/doc
			fi
			if [ -d \"/usr/doc/packages/postgresql-$PGVERSION\" ]
			then
				SYSDOCDIR=/usr/doc/packages
			fi
			if [ -d \"/usr/share/doc/packages/postgresql-$PGVERSION\" ]
			then
				SYSDOCDIR=/usr/share/doc/packages
			fi
			echo
			echo $\"An old version of the database format was found.\"
			echo $\"You need to upgrade the data format before using PostgreSQL.\"
			echo $\"See $SYSDOCDIR/postgresql-$PGVERSION/README.rpm-dist for more information.\"
			exit 1
		fi
	else
		# No existing PGDATA! Warn the user to initdb it.

		echo
		echo \"$PGDATA is missing. Use \\"service $NAME initdb\\" to initialize the cluster first.\"
		echo_failure
		echo
		exit 1
 	fi

	echo -n \"$PSQL_START\"
	$SU -l postgres -c \"$PGENGINE/postmaster -p '$PGPORT' -D '$PGDATA' ${PGOPTS} &\" >> \"$PGLOG\" 2>&1 < /dev/null
	sleep 2
	pid=`head -n 1 \"$PGDATA/postmaster.pid\" 2>/dev/null`
	if [ \"x$pid\" != x ]
	then
		success \"$PSQL_START\"
		touch \"$lockfile\"
		echo $pid > \"$pidfile\"
		echo
	else
		failure \"$PSQL_START\"
		echo
		script_result=1
	fi
}

stop(){
	echo -n $\"Stopping ${NAME} service: \"
	if [ -e \"$lockfile\" ]
	then
		$SU -l postgres -c \"$PGENGINE/pg_ctl stop -D '$PGDATA' -s -m fast\" > /dev/null 2>&1 < /dev/null
		ret=$? 
		if [ $ret -eq 0 ]
		then
			echo_success
			rm -f \"$pidfile\"
			rm -f \"$lockfile\"
		else
			echo_failure
			script_result=1
		fi
		else
			# not running; per LSB standards this is \"ok\"	
			echo_success
		fi
		echo
}

restart(){
    stop
    start
}

initdb(){
			# If the locale name is specified just after the initdb parameter, use it:
			if [ -z $LOCALEPARAMETER ]
			then
				LOCALE=`echo $LANG`
			else
				LOCALE=`echo $LOCALEPARAMETER`
			fi
				LOCALESTRING=\"--locale=$LOCALE\"

		if [ -f \"$PGDATA/PG_VERSION\" ]
		then
			echo \"Data directory is not empty!\"
			echo_failure
		else
			echo -n $\"Initializing database: \"
			if [ ! -e \"$PGDATA\" -a ! -h \"$PGDATA\" ]
			then
				mkdir -p \"$PGDATA\" || exit 1
				chown postgres:postgres \"$PGDATA\"
				chmod go-rwx \"$PGDATA\"
			fi
			# Clean up SELinux tagging for PGDATA
			[ -x /sbin/restorecon ] && /sbin/restorecon \"$PGDATA\"

			# Make sure the startup-time log file is OK, too
			if [ ! -e \"$PGLOG\" -a ! -h \"$PGLOG\" ]
			then
				touch \"$PGLOG\" || exit 1
				chown postgres:postgres \"$PGLOG\"
				chmod go-rwx \"$PGLOG\"
				[ -x /sbin/restorecon ] && /sbin/restorecon \"$PGLOG\"
			fi

			# Initialize the database
			$SU -l postgres -c \"$PGENGINE/initdb --pgdata='$PGDATA' --auth='ident' $LOCALESTRING\" >> \"$PGLOG\" 2>&1 < /dev/null

			# Create directory for postmaster log
			mkdir \"$PGDATA/pg_log\"
			chown postgres:postgres \"$PGDATA/pg_log\"
			chmod go-rwx \"$PGDATA/pg_log\"

			[ -f \"$PGDATA/PG_VERSION\" ] && echo_success
			[ ! -f \"$PGDATA/PG_VERSION\" ] && echo_failure
			echo
		fi
}

upgrade(){

# The second parameter is the new database version, i.e. $PGMAJORVERSION in this case.
# Use  \"postgresql-$PGMAJORVERSION\" service, if not specified.
INIT_SCRIPT=\"$2\"
if [ x\"$INIT_SCRIPT\" = x ]
then
    INIT_SCRIPT=postgresql-$PGMAJORVERSION
fi

# The third parameter is the old database version, i.e. $PGPREVMAJORVERSION in this case.
# Use  \"postgresql-$PGPREVMAJORVERSION\" service, if not specified.
OLD_INIT_SCRIPT=\"$3\"
if [ x\"$OLD_INIT_SCRIPT\" = x ]
then
    OLD_INIT_SCRIPT=postgresql-$PGPREVMAJORVERSION
fi

# Find the init script of the new version:
if [ ! -f \"/etc/init.d/${INIT_SCRIPT}\" ]
then
 	echo \"Could not find init script /etc/init.d/${INIT_SCRIPT}\"
fi

# Find the init script of the old version
if [ ! -f \"/etc/init.d/${OLD_INIT_SCRIPT}\" ]
then
	echo \"Could not find init script /etc/init.d/${OLD_INIT_SCRIPT}\"
	echo \"Please install postgresql91-server RPM first.\"
	exit
fi

# Get port number and data directory of the old instance from the init script
OLDPGDATA=` sed -n 's/^PGDATA=//p' /etc/init.d/postgresql-$PGPREVMAJORVERSION`
OLDPGPORT=`sed -n 's/^PGPORT=//p' /etc/init.d/postgresql-$PGPREVMAJORVERSION`

# Get port number and data directory of the new instance from the init script
NEWPGDATA=` sed -n 's/^PGDATA=//p' /etc/init.d/postgresql-$PGMAJORVERSION`
NEWPGPORT=`sed -n 's/^PGPORT=//p' /etc/init.d/postgresql-$PGMAJORVERSION`

if [ ! -x \"$PGENGINE/pg_upgrade\" ]
    then
	echo
	echo $\"Please install the postgresql92-contrib RPM for pg_upgrade command.\"
	echo
        exit 5
fi

# Perform initdb on the new server
/sbin/service $NAME initdb
RETVAL=$?
if [ $RETVAL -ne 0 ]
  then
	echo \"initdb failed!\"
	exit 1
fi

# Check the clusters first, without changing any data:
su -l postgres -c \"$PGENGINE/pg_upgrade -b /usr/pgsql-$PGPREVMAJORVERSION/bin/ -B $PGENGINE/ -d $OLDPGDATA -D $NEWPGDATA -p $OLDPGPORT -P $NEWPGPORT -c\"
RETVAL=$?
if [ $RETVAL -eq 0 ]
  then
	echo \"Clusters checked successfully, proceeding with upgrade from $PGPREVMAJORVERSION to $PGMAJORVERSION\"
	echo \"Stopping old cluster\"
	/sbin/service $OLD_INIT_SCRIPT stop

	# Set up log file for pg_upgrade
	rm -f \"$PGUPLOG\"
	touch \"$PGUPLOG\" || exit 1
	chown postgres:postgres \"$PGUPLOG\"
	chmod go-rwx \"$PGUPLOG\"
	[ -x /sbin/restorecon ] && /sbin/restorecon \"$PGUPLOG\"

	echo \"Performing upgrade\"
	su -l postgres -c \"$PGENGINE/pg_upgrade \
		-b /usr/pgsql-$PGPREVMAJORVERSION/bin/ -B $PGENGINE/ \
		-d $OLDPGDATA -D $NEWPGDATA \
		-p $OLDPGPORT -P $NEWPGPORT\" >> \"$PGUPLOG\" 2>&1 < /dev/null
  else
	echo \"Cluster check failed. Please see the output above.\"
	exit 1
fi
	echo

exit 0
}


condrestart(){
	[ -e \"$lockfile\" ] && restart || :
}

reload(){
    $SU -l postgres -c \"$PGENGINE/pg_ctl reload -D '$PGDATA' -s\" > /dev/null 2>&1 < /dev/null
}

promote(){
    $SU -l postgres -c \"$PGENGINE/pg_ctl promote -D '$PGDATA' -s\" > /dev/null 2>&1 < /dev/null
}

# See how we were called.
case \"$1\" in
  start)
	start
	;;
  stop)
	stop
	;;
  status)
	status -p $pidfile $NAME
	script_result=$?
	;;
  restart)
	restart
	;;
  initdb)
	initdb
	;;
  promote)
	promote
	;;
  upgrade)
	upgrade
	;;
  condrestart|try-restart)
	condrestart
	;;
  reload)
	reload
	;;
  force-reload)
	restart
	;;
  *)
	echo $\"Usage: $0 {start|stop|status|restart|upgrade|condrestart|try-restart|reload|force-reload|initdb|promote}\"
	exit 2
esac

exit $script_result
    "
    echo $initScript >> /etc/rc.d/init.d/postgresql-12

	cmdStr='/usr/pgsql-12/bin/postgresql-12-setup initdb -D '$pgDir
	su - postgres -c "$cmdStr"
	
	# WRITE PGDATA and PGLOG TO SERVICE CONFIG FILE 
	sed -i "s,PGDATA=/var/lib/pgsql/12/data,PGDATA=$pgDir,g" /etc/rc.d/init.d/postgresql-12
	sed -i "s,PGLOG=/var/lib/pgsql/12/pgstartup.log,PGLOG=$pgDir/pgstartup.log,g" /etc/rc.d/init.d/postgresql-12
	
	# CREATE STARTUP LOG
	touch $pgDir"pgstartup.log"
	chown postgres:postgres $pgDir"pgstartup.log"
	chmod 700 $pgDir"pgstartup.log"

	# SET UP THE POSTGRESQL CONFIG FILES
	pgConfDir=$pgDir"postgresql.conf"
	sed -i "s,#port = 5432,port = 5432,g" $pgConfDir
	sed -i "s,#track_counts = on,track_counts = on,g" $pgConfDir
	sed -i "s,#autovacuum = on,autovacuum = on,g" $pgConfDir
	sed -i "s,local   all             all                                     peer,local   all             all                                     trust,g" $pgConfDir
	# THE FOLLOWING SET UP POSTGRESQL LOGGING:
	sed -i "s,#log_min_duration_statement = -1, log_min_duration_statement = 1500,g" $pgConfDir
	sed -i "s@log_line_prefix = '< %m >'@log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d '@g" $pgConfDir
	sed -i "s,#log_checkpoints = off,log_checkpoints = on,g" $pgConfDir
	sed -i "s,#log_connections = off,log_connections = on,g" $pgConfDir
	sed -i "s,#log_disconnections = off,log_disconnections = on,g" $pgConfDir
	sed -i "s,#log_lock_waits = off,log_lock_waits = on,g" $pgConfDir
	sed -i "s,#log_temp_files = -1,log_temp_files = 0,g" $pgConfDir
	sed -i "s,lc_messages = 'en_US.UTF-8',lc_messages = 'C',g" $pgConfDir
	
	# START UP THE POSTGRESQL SERVER

	service postgresql-12 start

	# CREATE THE ADMIN ROLE
	cmdstring="CREATE ROLE "$dbUser" WITH SUPERUSER LOGIN PASSWORD '"$dbPswd"';"
	psql -U postgres -d postgres -c "$cmdstring"

	# CREATE THE POSTGIS TEMPLATE
	cmdstring="createdb postgis_template -O "$dbUser 
	su - postgres -c "$cmdstring"
	psql -U postgres -d postgis_template -c "CREATE EXTENSION postgis; CREATE EXTENSION postgis_topology;"

fi

# CREATE THE APP DATABASE
cmdstring="createdb "$dbName" -O "$dbUser" -T postgis_template"
su - postgres -c "$cmdstring"

# --------------------------------------------------------------------
# INSTALL PYTHON PACKAGES

# INSTALL PACKAGES WITH PIP
pip install Cython 
pip install geojson ujson django-extensions simplekml pylint
pip install --pre line_profiler

# INSTALL NUMPY/SCIPY 
yum -y install atlas-devel blas-devel
pip install numpy
pip install scipy

# INSTALL GEOS
yum -y install geos-devel

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE DJANGO

# INSTALL DJANGO
pip install Django==3.1.2

# CREATE DIRECTORY AND COPY PROJECT
mkdir -p /var/django/
cp -rf /vagrant/conf/django/* /var/django/

# GENERATE A NEW SECRET_KEY
NEW_SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9*^+()@' | fold -w 40 | head -n 1);
echo $NEW_SECRET_KEY >> /etc/secret_key.txt

# SET THE OPS_DATA_PATH
sed -i "s|OPS_DATA_PATH = ''|OPS_DATA_PATH = '$opsDataPath'|g" /var/django/ops/ops/settings.py;

# MODIFY THE DATABASE NAME
sed -i "s|		'NAME': 'ops'|		'NAME': '$dbName'|g" /var/django/ops/ops/settings.py
sed -i "s|		'USER': 'admin'|		'USER': '$dbUser'|g" /var/django/ops/ops/settings.py

#ADD DJANGO ADMINS.
while true; do
	if [[ -z "$adminStr" ]]; then
		read -p "Do you wish to add an admin to Django (receives error messages)? [y/n]" yn
	else
		read -p "Would you like to add another admin to Django (also receives error messages)? [y/n]" yn
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

#OPTIONALLY SET DJANGO TO BE IN DEBUG MODE. 			
while true; do		

	read -p "Would you like to have Django operate in debug mode (DEVELOPMENT ENVIRONMENT ONLY!)? [y/n]" yn
	case $yn in 
		[Yy]* ) 
			read -p "ARE YOU SURE YOU WANT DJANGO TO BE IN DEBUG MODE? THIS IS FOR DEVELOPMENT ENVIRONMENTS ONLY. [y/n]" yn
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
if [ $newDb -eq 1 ]; then

	# SYNC THE DJANGO DEFINED DATABASE
	python /var/django/$appName/manage.py makemigrations
	python /var/django/$appName/manage.py migrate
	
	# CREATE INDEXES ON POINT PATH GEOMETRIES
	indexStr='psql -U postgres -d '$dbName' -c "CREATE INDEX app_antarctic_geom_idx ON app_point_paths USING gist (ST_Transform(geom,3031)) WHERE location_id = 2; CREATE INDEX app_arctic_geom_idx ON app_point_paths USING gist (ST_Transform(geom,3413)) WHERE location_id = 1;"'
	eval ${indexStr//app/rds}
	eval ${indexStr//app/snow}
	eval ${indexStr//app/accum}
	eval ${indexStr//app/kuband}

fi

# --------------------------------------------------------------------
# BULKLOAD DATA TO POSTGRESQL 
		
# INSTALL pg_bulkload AND DEPENDENCIES
yum install -y openssl098e;
yum install -y pg_bulkload12;

# ADD pg_bulkload FUNCTION TO THE DATABASE
su postgres -c "psql -f /usr/pgsql-12/share/contrib/pg_bulkload.sql "$appName"";

if [ $installPgData -eq 1 ]; then
	fCount=$(ls -A /vagrant/data/postgresql/ | wc -l);
	if [ $fCount -gt 1 ]; then
		# LOAD INITIAL DATA INTO THE DATABASE
		sh /vagrant/conf/bulkload/initdataload.sh
	fi
fi

# --------------------------------------------------------------------
# INSTALL PGBADGER FOR LOG REPORT GENERATION

yum install -y pgbadger

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE APACHE TOMCAT AND GEOSERVER(WAR)

# INSALL APACHE TOMCAT
yum install -y tomcat

# CONFIGURE tomcat
echo 'JAVA_HOME="/usr/java/jre11.0.9/"' >> /etc/tomcat/tomcat.conf
echo 'JAVA_OPTS="-server -Xms512m -Xmx512m -XX:+UseParallelGC -XX:+UseParallelOldGC"' >> /etc/tomcat/tomcat.conf
echo 'CATALINA_OPTS="-DGEOSERVER_DATA_DIR='$opsDataPath'geoserver"' >> /etc/tomcat/tomcat.conf

# MAKE THE EXTERNAL GEOSERVER DATA DIRECTORY (IF IT DOESNT EXIST)
geoServerDataPath=$opsDataPath"geoserver/"
if [ ! -d $geoServerDataPath ]; then
	mkdir -p $geoServerDataPath
fi

# EXTRACT THE OPS GEOSERVER DATA DIR TO THE DIRECTORY
cp -rf /vagrant/conf/geoserver/geoserver/* $geoServerDataPath

# GET THE GEOSERVER REFERENCE DATA
if [ -f /vagrant/data/geoserver/geoserver.zip ]; then

	unzip /vagrant/data/geoserver/geoserver.zip -d $geoServerDataPath"data/"

else

	# DOWNLOAD THE DATA PACK FROM CReSIS (MINIMAL LAYERS)
	cd /vagrant/data/geoserver/ && wget https://data.cresis.ku.edu/data/ops/geoserver.zip
	
	# UNZIP THE DOWNLOADED DATA PACK
	unzip /vagrant/data/geoserver/geoserver.zip -d $geoServerDataPath"data/"

fi

# TEMPORARY HACK UNTIL THE GEOSERVER.ZIP STRUCTURE CHANGES
mv $geoServerDataPath"data/geoserver/data/arctic" $geoServerDataPath"data/"
mv $geoServerDataPath"data/geoserver/data/antarctic" $geoServerDataPath"data/"
rm -rf $geoServerDataPath"data/geoserver/"

# Download and move THE GEOSERVER WAR TO TOMCAT
cd ~
wget https://sourceforge.net/projects/geoserver/files/GeoServer/2.18.0/geoserver-2.18.0-war.zip/download -O geoserver-2.18.0-war.zip
if echo ae0ba0207e7bdf067893412a458f0115 geoserver-2.18.0-war.zip | md5sum --check; then
    unzip geoserver-2.18.0-war.zip -d geoserver-2.18.0-war
    mv geoserver-2.18.0-war/geoserver.war /var/lib/tomcat/webapps/geoserver.war
    rm -rf geoserver-2.18.0-war
else
    echo "GEOSERVER HASH COULD NOT BE VERIFIED, SKIPPING DOWNLOAD"
fi
rm -f geoserver-2.18.0-war.zip


# SET OWNERSHIP/PERMISSIONS OF GEOSERVER DATA DIRECTORY
chmod -R u=rwX,g=rwX,o=rX $geoServerDataPath
chown -R tomcat:tomcat $geoServerDataPath

# START APACHE TOMCAT
service tomcat start

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE WEB APPLICATION

cp -rf /vagrant/conf/geoportal/* /var/www/html/ # COPY THE APPLICATION

# WRITE THE BASE URL TO app.js
# sed -i "s,	 baseUrl: ""http://192.168.111.222"",	 baseUrl: ""$serverName"",g" /var/www/html/app.js

# CREATE AND CONFIGURE ALL THE OUTPUT DIRECTORIES
mkdir -m 777 -p $opsDataPath"data/csv/"
mkdir -m 777 -p $opsDataPath"data/kml/"
mkdir -m 777 -p $opsDataPath"data/mat/"
mkdir -m 777 -p $opsDataPath"datapacktmp/"
mkdir -m 777 -p  $opsDataPath"data/datapacks/"
mkdir -m 777 -p $opsDataPath"data/reports/"
mkdir -m 777 -p $opsDataPath"postgresql_reports/"
mkdir -m 777 -p $opsDataPath"django_logs/"
mkdir -m 777 -p /var/profile_logs/txt/

# --------------------------------------------------------------------
# MAKE SURE ALL SERVICES ARE STARTED AND ON

# APACHE HTTPD
setsebool -P httpd_unified 1  # Allow httpd to write to error_log
service httpd start
chkconfig httpd on

# POSTGRESQL
service postgresql-12 start
chkconfig postgresql-12 on

# APACHE TOMCAT
service tomcat start
chkconfig tomcat on

# --------------------------------------------------------------------
# DO A FINAL SYSTEM UPDATE
yum update -y

# --------------------------------------------------------------------
# PRINT OUT THE COMPLETION NOTICE

stopTime=$(date -u);

printf "\n"	
printf "SYSTEM INSTALLATION AND CONFIGURATION COMPLETE. INSTRUCTIONS BELOW.\n"
printf "\n"
printf "#########################################################################\n"
printf "#########################################################################\n"
printf "#\n"
printf "# Welcome to the OpenPolarServer (OPS)\n"
printf "#\n"
printf "# The Center for Remote Sensing of Ice Sheets (CReSIS)\n"
printf "# University of Kansas, Lawrence, Ks\n"
printf "#\n"
printf "# Developed by:\n" 
printf "#  - Kyle W Purdon\n"
printf "#  - Trey Stafford\n"
printf "#  - John Paden\n"
printf "#  - Sam Buchanan\n"
printf "#  - Haiji Wang\n"	
printf "# Updated by:\n"
printf "#  - Reece Mathews\n"
printf "#\n"
printf "# The system is now ready for use!\n"
printf "#\n"
printf "# INSTRUCTIONS:\n"
printf "#  - Open a web browser (inside or outside of the VM)\n"
printf "#  		- Google Chrome recommended.\n"
printf "#  - Enter %s as the url.\n" $serverName
printf "#  - Welcome the the OPS web interface!.\n"
printf "#\n"	
printf "#########################################################################\n"
printf "#########################################################################\n"
printf "\n"
echo "Started at:" $startTime
echo "Finished at:" $stopTime

#notify-send "OpenPolarServer build complete. See terminal for details."

# TODO: Either reboot now or correctly set SELinux policies instead of disabling