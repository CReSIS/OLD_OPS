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

notify-send "Now building OpenPolarServer"
notify-send "Please watch for more prompts (there will only be one you need to act on). Thank you."

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
# SET SOME STATIC INPUTS
newDb=1;
serverName="192.168.111.222";
serverAdmin="root"; 
appName="ops";
dbName="ops";
installPgData=0;
webDataDir="/cresis/snfs1/web/ops/data";

# --------------------------------------------------------------------
# WRITE GEOSERVER_DATA_DIR TO ~/.bashrc

echo 'GEOSERVER_DATA_DIR="/cresis/snfs1/web/ops/geoserver"' >> ~/.bashrc
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
python-pip install --upgrade nose

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
yum install -y httpd-devel

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

mkdir -p $webDataDir
chmod 777 $webDataDir

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

# VACUUM ANALYZE-ONLY THE ENTIRE OPS DATABASE AT 2 AM DAILY
0 2 * * * root su postgres -c '/usr/pgsql-9.3/bin/vacuumdb -v -Z "$dbName"'

# VACUUM ANALYZE THE ENTIRE OPS DATABASE AT 2 AM ON THE 1ST OF EACH MONTH
0 2 1 * * root su postgres -c '/usr/pgsql-9.3/bin/vacuumdb -v -z "$dbName"'"

echo -n > /etc/crontab
echo "$cronStr" > /etc/crontab

service crond start
chkconfig crond on

# --------------------------------------------------------------------
# INSTALL JAVA JRE, JAI, JAI I/O

notify-send "Installing JAVA. Please manually accept the two license agreements in the terminal."

# COPY INSTALLATION FILES
cd ~
cp /vagrant/conf/software/jre-8-linux-x64.rpm ./
cp /vagrant/conf/software/jai-1_1_3-lib-linux-amd64-jre.bin ./
cp /vagrant/conf/software/jai_imageio-1_1-lib-linux-amd64-jre.bin ./

# INSTALL JAVA JRE
rpm -Uvh jre*
alternatives --install /usr/bin/java java /usr/java/latest/bin/java 200000
rm -f jre-8-linux-x64.rpm

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

notify-send "Thank you for your input. The installation will now automatically continue."

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE POSTGRESQL + POSTGIS

if [ $newDb -eq 1 ]; then

	pgDir='/cresis/snfs1/web/ops/pgsql/9.3/'

	# EXCLUDE POSTGRESQL FROM THE BASE CentOS RPM
	sed -i -e '/^\[base\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo 
	sed -i -e '/^\[updates\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo 

	# INSTALL POSTGRESQL
	yum install -y postgresql93* postgis2_93* 

	# INSTALL PYTHON PSYCOPG2 MODULE FOR POSTGRES
	export PATH=/usr/pgsql-9.3/bin:"$PATH"
	pip install psycopg2
	
	# MAKE THE SNFS1 MOCK DIRECTORY IF IT DOESNT EXIST
	if [ ! -d "/cresis/snfs1/web/ops/pgsql" ]
		then
			mkdir -p /cresis/snfs1/web/ops/pgsql/
			chown postgres:postgres /cresis/snfs1/web/ops/pgsql/
			chmod 700 /cresis/snfs1/web/ops/pgsql/
	fi
	
	# INITIALIZE THE DATABASE CLUSTER
	cmdStr='/usr/pgsql-9.3/bin/initdb -D '$pgDir
	su - postgres -c "$cmdStr"
	
	# WRITE PGDATA and PGLOG TO SERVICE CONFIG FILE 
	sed -i "s,PGDATA=/var/lib/pgsql/9.3/data,PGDATA=$pgDir,g" /etc/rc.d/init.d/postgresql-9.3
	sed -i "s,PGLOG=/var/lib/pgsql/9.3/pgstartup.log,PGLOG=$pgDir/pgstartup.log,g" /etc/rc.d/init.d/postgresql-9.3
	
	# CREATE STARTUP LOG
	touch /cresis/snfs1/web/ops/pgsql/9.3/pgstartup.log
	chown postgres:postgres /cresis/snfs1/web/ops/pgsql/9.3/pgstartup.log
	chmod 700 /cresis/snfs1/web/ops/pgsql/9.3/pgstartup.log
	
	# SET THE DEVELOPMENT USERNAME AND PASSWORD
	dbUser='admin'
	dbPswd='pubAdmin'

	# SET UP THE POSTGRESQL CONFIG FILES
	pgConfDir=$pgDir"postgresql.conf"
	sed -i "s,#port = 5432,port = 5432,g" $pgConfDir
	sed -i "s,#track_counts = on,track_counts = on,g" $pgConfDir
	sed -i "s,#autovacuum = on,autovacuum = on,g" $pgConfDir
	sed -i "s,local   all             all                                     peer,local   all             all                                     trust,g" $pgConfDir

	# START UP THE POSTGRESQL SERVER
	service postgresql-9.3 start

	# CREATE THE ADMIN ROLE
	cmdstring="CREATE ROLE "$dbUser" WITH SUPERUSER LOGIN PASSWORD '"$dbPswd"';"
	psql -U postgres -d postgres -c "$cmdstring"

	# CREATE THE POSTGIS TEMPLATE
	cmdstring="createdb postgis_template -O "$dbUser 
	su - postgres -c "$cmdstring"
	psql -U postgres -d postgis_template -c "CREATE EXTENSION postgis; CREATE EXTENSION postgis_topology;"

	# CREATE THE APP DATABASE
	cmdstring="createdb "$dbName" -O "$dbUser" -T postgis_template"
	su - postgres -c "$cmdstring"
	
fi

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
pip install Django==1.6.4

# CREATE DIRECTORY AND COPY PROJECT
mkdir -p /var/django/
cp -rf /vagrant/conf/django/* /var/django/

# MODIFY THE DATABASE NAME
sed -i "s,		'NAME': 'ops',		'NAME': '$dbName',g" /var/django/ops/ops/settings.py

if [ $newDb -eq 1 ]; then

	# SYNC THE DJANGO DEFINED DATABASE
	python /var/django/$appName/manage.py syncdb --noinput 

	# CREATE DATABASE VIEWS FOR CROSSOVER ERRORS
	viewstr='psql -U postgres -d ops -c "CREATE VIEW app_crossover_errors AS SELECT (SELECT name FROM app_seasons WHERE id = pt_pths1.season_id) AS season_1_name, (SELECT name FROM app_seasons WHERE id = pt_pths2.season_id) AS season_2_name, cx.angle,pt_pths1.geom AS point_path_1_geom, pt_pths2.geom AS point_path_2_geom, pt_pths1.gps_time AS gps_time_1, pt_pths2.gps_time AS gps_time_2, pt_pths1.heading AS heading_1,pt_pths2.heading AS heading_2,pt_pths1.roll AS roll_1,pt_pths2.roll AS roll_2, pt_pths1.pitch AS pitch_1,pt_pths2.pitch AS pitch_2,pt_pths1.location_id, cx.geom, COALESCE(lyr_pts1.layer_id,lyr_pts2.layer_id) AS layer_id, (SELECT name FROM app_frames WHERE id = pt_pths1.frame_id) AS frame_1_name, (SELECT name FROM app_frames WHERE id = pt_pths2.frame_id) AS frame_2_name,cx.point_path_1_id, cx.point_path_2_id,lyr_pts1.twtt AS twtt_1, lyr_pts2.twtt AS twtt_2, CASE WHEN COALESCE(lyr_pts1,lyr_pts2) IS NULL THEN NULL WHEN COALESCE(lyr_pts1.layer_id,lyr_pts2.layer_id) = 1 THEN ABS((ST_Z(pt_pths1.geom) - lyr_pts1.twtt*299792458.0003452/2)) ELSE ABS((ST_Z(pt_pths1.geom) - (SELECT twtt FROM app_layer_points WHERE layer_id=1 AND point_path_id = pt_pths1.id)*299792458.0003452/2 - (lyr_pts1.twtt - (SELECT twtt FROM app_layer_points WHERE layer_id = 1 AND point_path_id = pt_pths1.id))*299792458.0003452/2/sqrt(3.15))) END AS layer_elev_1, CASE WHEN COALESCE(lyr_pts1,lyr_pts2) IS NULL THEN NULL WHEN COALESCE(lyr_pts1.layer_id,lyr_pts2.layer_id) = 1 THEN ABS((ST_Z(pt_pths2.geom) - lyr_pts2.twtt*299792458.0003452/2)) ELSE ABS((ST_Z(pt_pths2.geom) - (SELECT twtt FROM app_layer_points WHERE layer_id=1 AND point_path_id = pt_pths2.id)*299792458.0003452/2 - (lyr_pts2.twtt - (SELECT twtt FROM app_layer_points WHERE layer_id = 1 AND point_path_id = pt_pths2.id))*299792458.0003452/2/sqrt(3.15))) END AS layer_elev_2 FROM app_crossovers AS cx LEFT JOIN app_layer_points AS lyr_pts1 ON lyr_pts1.point_path_id=cx.point_path_1_id LEFT JOIN app_layer_points AS lyr_pts2 ON lyr_pts2.point_path_id=cx.point_path_2_id LEFT JOIN app_point_paths AS pt_pths1 ON cx.point_path_1_id=pt_pths1.id LEFT JOIN app_point_paths AS pt_pths2 ON pt_pths2.id=cx.point_path_2_id WHERE lyr_pts1.layer_id = lyr_pts2.layer_id OR (lyr_pts1 IS NULL OR lyr_pts2 IS NULL);"'
	eval ${viewstr//app/rds}
	eval ${viewstr//app/snow}
	eval ${viewstr//app/accum}
	eval ${viewstr//app/kuband}

fi

# --------------------------------------------------------------------
# BULKLOAD DATA TO POSTGRESQL 

if [ $installPgData -eq 1 ]; then
	fCount=$(ls -A /vagrant/data/postgresql/ | wc -l);
	if [ $fCount -gt 1 ]; then
		
		# INSTALL pg_bulkload AND DEPENDENCIES
		cd ~ && cp -f /vagrant/conf/software/pg_bulkload-3.1.5-1.pg93.rhel6.x86_64.rpm ./
		cd ~ && cp -f /vagrant/conf/software/compat-libtermcap-2.0.8-49.el6.x86_64.rpm ./
		yum install -y openssl098e;
		rpm -Uvh ./compat-libtermcap-2.0.8-49.el6.x86_64.rpm;
		rpm -ivh ./pg_bulkload-3.1.5-1.pg93.rhel6.x86_64.rpm;
		rm -f compat-libtermcap-2.0.8-49.el6.x86_64.rpm && rm -f pg_bulkload-3.1.5-1.pg93.rhel6.x86_64.rpm
		
		# ADD pg_bulkload FUNCTION TO THE DATABASE
		su postgres -c "psql -f /usr/pgsql-9.3/share/contrib/pg_bulkload.sql "$appName"";
		
		# LOAD INITIAL DATA INTO THE DATABASE
		sh /vagrant/conf/bulkload/initdataload.sh
	fi
fi

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE APACHE TOMCAT AND GEOSERVER(WAR)

# INSALL APACHE TOMCAT
yum install -y tomcat6

# CONFIGURE TOMCAT6
echo 'JAVA_HOME="/usr/java/jre1.8.0/"' >> /etc/tomcat6/tomcat6.conf
echo 'JAVA_OPTS="-server -Xms512m -Xmx512m -XX:+UseParallelGC -XX:+UseParallelOldGC"' >> /etc/tomcat6/tomcat6.conf
echo 'CATALINA_OPTS="-DGEOSERVER_DATA_DIR=/cresis/snfs1/web/ops/geoserver"' >> /etc/tomcat6/tomcat6.conf

# MAKE THE EXTERNAL GEOSERVER DATA DIRECTORY (IF IT DOESNT EXIST)
if [ ! -d "/cresis/snfs1/web/ops/geoserver/" ]; then
	mkdir -p /cresis/snfs1/web/ops/geoserver/
fi

# EXTRACT THE OPS GEOSERVER DATA DIR TO THE DIRECTORY
cp -rf /vagrant/conf/geoserver/geoserver/* /cresis/snfs1/web/ops/geoserver/

# GET THE GEOSERVER REFERENCE DATA
if [ -f /vagrant/data/geoserver/geoserver.zip ]; then

	unzip /vagrant/data/geoserver/geoserver.zip -d /cresis/snfs1/web/ops/geoserver/data/

else

	# DOWNLOAD THE DATA PACK FROM CReSIS (MINIMAL LAYERS)
	cd /vagrant/data/geoserver/ && wget https://ops.cresis.ku.edu/data/geoserver/geoserver.zip
	
	# UNZIP THE DOWNLOADED DATA PACK
	unzip /vagrant/data/geoserver/geoserver.zip -d /cresis/snfs1/web/ops/geoserver/data/

fi

# TEMPORARY HACK UNTIL THE GEOSERVER.ZIP STRUCTURE CHANGES
mv /cresis/snfs1/web/ops/geoserver/data/geoserver/data/arctic /cresis/snfs1/web/ops/geoserver/data/
mv /cresis/snfs1/web/ops/geoserver/data/geoserver/data/antarctic /cresis/snfs1/web/ops/geoserver/data/
rm -rf /cresis/snfs1/web/ops/geoserver/data/geoserver/

# COPY THE GEOSERVER WAR TO TOMCAT
cp /vagrant/conf/geoserver/geoserver.war /var/lib/tomcat6/webapps

# SET OWNERSHIP/PERMISSIONS OF GEOSERVER DATA DIRECTORY
chmod -R u=rwX,g=rwX,o=rX /cresis/snfs1/web/ops/geoserver/
chown -R tomcat:tomcat /cresis/snfs1/web/ops/geoserver/

# START APACHE TOMCAT
service tomcat6 start

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE WEB APPLICATION

cp -rf /vagrant/conf/geoportal/* /var/www/html/ # COPY THE APPLICATION

# WRITE THE BASE URL TO app.js
# sed -i "s,	 baseUrl: ""http://192.168.111.222"",	 baseUrl: ""$serverName"",g" /var/www/html/app.js

# CREATE AND CONFIGURE ALL THE OUTPUT DIRECTORIES
mkdir -p /cresis/snfs1/web/ops/data/csv/
chmod 777 /cresis/snfs1/web/ops/data/csv/

mkdir -p /cresis/snfs1/web/ops/data/kml/
chmod 777 /cresis/snfs1/web/ops/data/kml/

mkdir -p /cresis/snfs1/web/ops/data/mat/
chmod 777 /cresis/snfs1/web/ops/data/mat/

mkdir -p /cresis/snfs1/web/ops/datapacktmp/
chmod 777 /cresis/snfs1/web/ops/datapacktmp/

mkdir -p  /cresis/snfs1/web/ops/data/datapacks/
chmod 777 /cresis/snfs1/web/ops/data/datapacks/

mkdir -p /cresis/snfs1/web/ops/data/reports/
chmod 777 /cresis/snfs1/web/ops/data/reports/

mkdir -p /var/profile_logs/txt/
chmod 777 /var/profile_logs/txt/

# --------------------------------------------------------------------
# MAKE SURE ALL SERVICES ARE STARTED AND ON

# APACHE HTTPD
service httpd start
chkconfig httpd on

if [ $newDb -eq 1 ]; then

	# POSTGRESQL
	service postgresql-9.3 start
	chkconfig postgresql-9.3 on

fi

# APACHE TOMCAT
service tomcat6 start
chkconfig tomcat6 on

# UPDATE SYSTEM (FORCES UPDATES FOR ALL NEW INSTALLS)
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

notify-send "OpenPolarServer build complete. See terminal for details."