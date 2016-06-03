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

	cd ~ && cp /vagrant/conf/software/epel-release-6-8.noarch.rpm ./
	rpm -Uvh epel-release-6*.rpm 
	rm -f epel-release-6-8.noarch.rpm
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
cd ~ && cp -f /vagrant/conf/software/pgdg-centos93-9.3-1.noarch.rpm ./
rpm -Uvh pgdg-centos93-9.3-1.noarch.rpm
rm -f pgdg-centos93-9.3-1.noarch.rpm

# --------------------------------------------------------------------
# INSTALL PYTHON 2.7 WITH DEPENDENCIES IN A VIRTUALENV

# INSTALL DEPENDENCIES
yum install -y python-pip zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel
pip install --upgrade nose

# INSTALL PYTHON 2.7.6
cd ~ && cp -f /vagrant/conf/software/Python-2.7.6.tar.xz ./
tar xf Python-2.7.6.tar.xz
cd Python-2.7.6
./configure --prefix=/usr --enable-shared LDFLAGS="-Wl,-rpath /usr/lib"
make && make altinstall
cd ~ && rm -rf Python-2.7.6 && rm -f Python-2.7.6.tar.xz

# INSTALL AND ACTIVATE VIRTUALENV
pip install virtualenv
virtualenv -p /usr/bin/python2.7 /usr/bin/venv
source /usr/bin/venv/bin/activate

# --------------------------------------------------------------------
# INSTALL APACHE WEB SERVER AND MOD_WSGI

# INSTALL APACHE HTTPD
yum install -y httpd httpd-devel

# INSTALL MOD_WSGI (COMPILE WITH Python27)
cd ~ && cp -f /vagrant/conf/software/mod_wsgi-3.4.tar.gz ./
tar xvfz mod_wsgi-3.4.tar.gz
cd mod_wsgi-3.4/
./configure --with-python=/usr/bin/python2.7
LD_RUN_PATH=/usr/lib make && make install
cd ~ && rm -f mod_wsgi-3.4.tar.gz && rm -rf mod_wsgi-3.4

# --------------------------------------------------------------------
# WRITE CONFIG FILES FOR HTTPD

# INCLUDE THE SITE CONFIGURATION FOR HTTPD
echo "Include /var/www/sites/"$serverName"/conf/"$appName".conf" >> /etc/httpd/conf/httpd.conf

mkdir -m 777 -p $webDataDir

# WRITE THE DJANGO WSGI CONFIGURATION
wsgiStr="
LoadModule wsgi_module modules/mod_wsgi.so

WSGISocketPrefix run/wsgi
WSGIDaemonProcess $appName user=apache python-path=/var/django/$appName:/usr/bin/venv/lib/python2.7/site-packages
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

import urllib2
import cgi
import sys, os

allowedHosts = ['"$serverName"',
				'www.openlayers.org', 'openlayers.org', 
				'labs.metacarta.com', 'world.freemap.in', 
				'prototype.openmnnd.org', 'geo.openplans.org',
				'sigma.openplans.org', 'demo.opengeo.org',
				'www.openstreetmap.org', 'sample.azavea.com',
				'v2.suite.opengeo.org', 'v-swe.uni-muenster.de:8080', 
				'vmap0.tiles.osgeo.org', 'www.openrouteservice.org']

method = os.environ['REQUEST_METHOD']

if method == 'POST':
	qs = os.environ['QUERY_STRING']
	d = cgi.parse_qs(qs)
	if d.has_key('url'):
		url = d['url'][0]
	else:
		url = 'http://www.openlayers.org'
else:
	fs = cgi.FieldStorage()
	url = fs.getvalue('url', 'http://www.openlayers.org')

try:
	host = url.split('/')[2]
	if allowedHosts and not host in allowedHosts:
		print 'Status: 502 Bad Gateway'
		print 'Content-Type: text/plain'
		print
		print 'This proxy does not allow you to access that location (%s).' % (host,)
		print
		print os.environ
  
	elif url.startswith('http://') or url.startswith('https://'):
	
		if method == 'POST':
			length = int(os.environ['CONTENT_LENGTH'])
			headers = {'Content-Type': os.environ['CONTENT_TYPE']}
			body = sys.stdin.read(length)
			r = urllib2.Request(url, body, headers)
			y = urllib2.urlopen(r)
		else:
			y = urllib2.urlopen(url)
		
		# print content type header
		i = y.info()
		if i.has_key('Content-Type'):
			print 'Content-Type: %s' % (i['Content-Type'])
		else:
			print 'Content-Type: text/plain'
		print
		
		print y.read()
		
		y.close()
	else:
		print 'Content-Type: text/plain'
		print
		print 'Illegal request.'

except Exception, E:
	print 'Status: 500 Unexpected Error'
	print 'Content-Type: text/plain'
	print 
	print 'Some unexpected error occurred. Error text was:', E"

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
cp /vagrant/conf/software/jre-8-linux-x64.rpm ./
cp /vagrant/conf/software/jai-1_1_3-lib-linux-amd64-jre.bin ./
cp /vagrant/conf/software/jai_imageio-1_1-lib-linux-amd64-jre.bin ./

# INSTALL JAVA JRE
rpm -Uvh jre*
alternatives --install /usr/bin/java java /usr/java/latest/bin/java 200000
rm -f jre-8-linux-x64.rpm

# NOT INSTALLING JAI/JAIIO UNTIL WE FIGURE OUT HOW TO MAKE THEM USER FRIENDLY INSTALLS.

##notify-send "Installing JAVA. Please manually accept the two license agreements in the terminal."

# INSTALL JAI
cd /usr/java/jre1.8.0/
chmod u+x ~/jai-1_1_3-lib-linux-amd64-jre.bin
~/jai-1_1_3-lib-linux-amd64-jre.bin
rm -f ~/jai-1_1_3-lib-linux-amd64-jre.bin

# INSTALL JAI-IO
export _POSIX2_VERSION=199209 
chmod u+x ~/jai_imageio-1_1-lib-linux-amd64-jre.bin 
~/jai_imageio-1_1-lib-linux-amd64-jre.bin 
rm -f ~/jai_imageio-1_1-lib-linux-amd64-jre.bin && cd ~

##notify-send "Thank you for your input. The installation will now automatically continue."

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE POSTGRESQL + POSTGIS

pgDir=$opsDataPath'pgsql/9.3/'
pgPth=$opsDataPath'pgsql/'

# EXCLUDE POSTGRESQL FROM THE BASE CentOS RPM
sed -i -e '/^\[base\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo 
sed -i -e '/^\[updates\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo 

# INSTALL POSTGRESQL
yum install -y postgresql93* postgis2_93* 

# INSTALL PYTHON PSYCOPG2 MODULE FOR POSTGRES
export PATH=/usr/pgsql-9.3/bin:"$PATH"
pip install psycopg2

if [ $newDb -eq 1 ]; then
	
	# MAKE THE SNFS1 MOCK DIRECTORY IF IT DOESNT EXIST
	if [ ! -d $pgPth ]
		then
			mkdir -p $pgPth
			chown postgres:postgres $pgPth
			chmod 700 $pgPth
	fi
	
	# INITIALIZE THE DATABASE CLUSTER
	cmdStr='/usr/pgsql-9.3/bin/initdb -D '$pgDir
	su - postgres -c "$cmdStr"
	
	# WRITE PGDATA and PGLOG TO SERVICE CONFIG FILE 
	sed -i "s,PGDATA=/var/lib/pgsql/9.3/data,PGDATA=$pgDir,g" /etc/rc.d/init.d/postgresql-9.3
	sed -i "s,PGLOG=/var/lib/pgsql/9.3/pgstartup.log,PGLOG=$pgDir/pgstartup.log,g" /etc/rc.d/init.d/postgresql-9.3
	
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
	service postgresql-9.3 start

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
pip install Django==1.6.5

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
	python /var/django/$appName/manage.py syncdb --noinput
	
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
cd ~ && cp -f /vagrant/conf/software/pg_bulkload-3.1.5-1.pg93.rhel6.x86_64.rpm ./
cd ~ && cp -f /vagrant/conf/software/compat-libtermcap-2.0.8-49.el6.x86_64.rpm ./
yum install -y openssl098e;
rpm -Uvh ./compat-libtermcap-2.0.8-49.el6.x86_64.rpm;
rpm -ivh ./pg_bulkload-3.1.5-1.pg93.rhel6.x86_64.rpm;
rm -f compat-libtermcap-2.0.8-49.el6.x86_64.rpm && rm -f pg_bulkload-3.1.5-1.pg93.rhel6.x86_64.rpm

# ADD pg_bulkload FUNCTION TO THE DATABASE
su postgres -c "psql -f /usr/pgsql-9.3/share/contrib/pg_bulkload.sql "$appName"";

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
yum install -y tomcat6

# CONFIGURE TOMCAT6
echo 'JAVA_HOME="/usr/java/jre1.8.0/"' >> /etc/tomcat6/tomcat6.conf
echo 'JAVA_OPTS="-server -Xms512m -Xmx512m -XX:+UseParallelGC -XX:+UseParallelOldGC"' >> /etc/tomcat6/tomcat6.conf
echo 'CATALINA_OPTS="-DGEOSERVER_DATA_DIR='$opsDataPath'geoserver"' >> /etc/tomcat6/tomcat6.conf

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

# COPY THE GEOSERVER WAR TO TOMCAT
cp /vagrant/conf/geoserver/geoserver.war /var/lib/tomcat6/webapps

# SET OWNERSHIP/PERMISSIONS OF GEOSERVER DATA DIRECTORY
chmod -R u=rwX,g=rwX,o=rX $geoServerDataPath
chown -R tomcat:tomcat $geoServerDataPath

# START APACHE TOMCAT
service tomcat6 start

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
service httpd start
chkconfig httpd on

# POSTGRESQL
service postgresql-9.3 start
chkconfig postgresql-9.3 on

# APACHE TOMCAT
service tomcat6 start
chkconfig tomcat6 on

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
