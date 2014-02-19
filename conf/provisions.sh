#!/bin/sh
#
# VAGRANT SHELL PROVISIONING
#
# SYSTEM: OpenPolarServer (public)
#
# CONTACT: cresis_data@cresis.ku.edu
#
# AUTHOR: Kyle W. Purdon, Trey Stafford
#
# SYSTEM DESCRIPTION AND NOTES
# 	- This file installs and configures the complete OPS SDI.
#
# PRIMARY SOFTWARE INSTALLED AND CONFIGURED
#	- APACHE HTTPD, APACHE TOMCAT, POSTGRESQL, POSTGIS, GEOSERVER(WAR), DJANGO FRAMEWORK, PYTHON27(VIRTUALENV)
#

# =================================================================================
# USER SETUP PARAMETERS

# BASIC SYSTEM INFORMATION
serverAdmin="root"; # REPLACE WITH AN EMAIL IF YOU WISH

serverName="192.168.111.222"; # PROBABLY SHOULD NOT CHANGE THIS. (HAVE NOT TRACKED DOWN ALL DEPENDENCIES YET)

# OPTIONAL INSTALLATIONS
installPgData=0; # LOAD DATA FROM ./data/postgresql/* USING BULKLOAD
useCron=0; # SET UP CRON TO DO AUTOMATIC DELETION AND DATBASE MAINTNACE (REQUIRES SSMTP SETUP BELOW)
installSsmtp=0; # INSTALL SSMTP FOR NOTIFICATION EMAILS (GMAIL ONLY FOR NOW)
ssmtpUser=""; # YOUR GMAIL USERNAME (youremail DONT INCLUDE (@gmail.com))
ssmtpPasswd=""; # YOUR GMAIL PASSWORD (don't share this with others, stored in plain text)

# =================================================================================
# ---------------------------------------------------------------------------------
# ****************** DO NOT MODIFY ANYTHING BELOW THIS LINE ***********************
# ---------------------------------------------------------------------------------
# =================================================================================

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
appName="ops";

# --------------------------------------------------------------------
# UPDATE THE SYSTEM AND INSTALL REPOS AND UTILITY PACKAGES

# UPDATE SYSTEM
yum update -y

# INSTALL UTILITY PACKAGES
yum install -y gzip gcc unzip rsync wget 

# INSTALL THE EPEL REPO
wget  http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm 
rpm -Uvh epel-release-6*.rpm 

# INSTALL THE PGDG REPO
wget http://yum.postgresql.org/9.3/redhat/rhel-6-x86_64/pgdg-centos93-9.3-1.noarch.rpm
rpm -Uvh pgdg-centos93-9.3-1.noarch.rpm

# --------------------------------------------------------------------
# CONFIGURE IPTABLES

# FLUSH CURRENT RULES
iptables -F 

# SET NEW PORT RULES
iptables -A INPUT -p tcp --dport 22 -j ACCEPT #SSH ON TCP 22
iptables -A INPUT -p tcp --dport 80 -j ACCEPT #HTTP ON TCP 80
iptables -A INPUT -p tcp --dport 443 -j ACCEPT #HTTPS ON TCP 443

# SET I/O POLICIES
iptables -P INPUT DROP 
iptables -P FORWARD DROP 
iptables -P OUTPUT ACCEPT 

# OPEN LOCALHOST
iptables -A INPUT -i lo -j ACCEPT 

# ACCEPT ESTABLISHED/RELATED (ALREADY OPEN CONNECTIONS)
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT 

# SAVE NEW RULES AND RESTART SERVICE
/sbin/service iptables save 
/sbin/service iptables restart 

# --------------------------------------------------------------------
# INSTALL PYTHON 2.7 AND VIRTUALENV WITH DEPENDENCIES

# INSTALL DEPENDENCIES
yum groupinstall -y "Development tools"
yum install -y wget python-pip zlib-devel bzip2-devel openssl-devel ncurses-devel sqlite-devel readline-devel tk-devel
python-pip install --upgrade nose

# DOWNLOAD AND INSTALL PYTHON 2.7.6
wget http://www.python.org/ftp/python/2.7.6/Python-2.7.6.tar.xz
tar xf Python-2.7.6.tar.xz
cd Python-2.7.6
./configure --prefix=/usr --enable-shared LDFLAGS="-Wl,-rpath /usr/lib"
make && make altinstall

# INSTALL AND ACTIVATE VIRTUALENV
pip install virtualenv
virtualenv -p /usr/bin/python2.7 /usr/bin/venv
source /usr/bin/venv/bin/activate

# --------------------------------------------------------------------
# INSTALL APACHE WEB SERVER AND MOD_WSGI

# INSTALL APACHE HTTPD
yum install -y httpd httpd-devel

# DOWNLOAD AND INSTALL MOD_WSGI (COMPILE WITH Python27)
cd ~ && wget https://modwsgi.googlecode.com/files/mod_wsgi-3.4.tar.gz
tar xvfz mod_wsgi-3.4.tar.gz
cd mod_wsgi-3.4/
./configure --with-python=/usr/bin/python2.7
LD_RUN_PATH=/usr/lib make && make install
rm -f ~/mod_wsgi-3.4.tar.gz
rm -f ~/mod_wsgi-3.4

# INCLUDE THE SITE CONFIGURATION FOR HTTPD
echo "Include /var/www/sites/"$serverName"/conf/"$appName".conf" >> /etc/httpd/conf/httpd.conf

# --------------------------------------------------------------------
# WRITE CONFIG FILES FOR HTTPD

webDataDir="/cresis/snfs1/web/ops/data";
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

if [ $useCron -eq 1 ]; then

	cronStr="
	SHELL=/bin/bash
	PATH=/sbin:/bin:/usr/sbin:/usr/bin
	MAILTO=''
	HOME=/
	# REMOVE CSV FILES OLDER THAN 7 DAYS AT 2 AM DAILY
	0 2 * * * root fns=\$(find "$webDataDir"/csv/*.csv -mtime +7); if [ -n '\$fns' ]; then rm -f \$fns; printf '%s' \$fns | mail -s 'OPS CSV CLEANUP' "$ssmtpUser"@gmail.com; fi;
	# REMOVE KML FILES OLDER THAN 7 DAYS AT 2 AM DAILY
	0 2 * * * root fns=\$(find "$webDataDir"/kml/*.kml -mtime +7); if [ -n '\$fns' ]; then rm -f \$fns; printf '%s' \$fns | mail -s 'OPS KML CLEANUP'"$ssmtpUser"@gmail.com; fi;
	# REMOVE MAT FILES OLDER THAN 7 DAYS AT 2 AM DAILY
	0 2 * * * root fns=\$(find "$webDataDir"/mat/*.mat -mtime +7); if [ -n '\$fns' ]; then rm -f \$fns; printf '%s' \$fns | mail -s 'OPS MAT CLEANUP' "$ssmtpUser"@gmail.com; fi;
	# VACUUM ANALYZE-ONLY THE ENTIRE OPS DATABASE AT 2 AM DAILY
	0 2 * * * root su postgres -c '/usr/pgsql-9.3/bin/vacuumdb -v -Z "$appName"'
	# VACUUM ANALYZE THE ENTIRE OPS DATABASE AT 2 AM ON THE 1ST OF EACH MONTH
	0 2 1 * * root su postgres -c '/usr/pgsql-9.3/bin/vacuumdb -v -z "$appName"'"

	echo -n > /etc/crontab
	echo "$cronStr" > /etc/crontab
	
fi

# --------------------------------------------------------------------
# WRITE SSMTP CONFIGURATION

if [ $installSsmtp -eq 1 ]; then
	
	yum install -y ssmtp
	
	ssmtpStr="
	root="$ssmtpUser"@gmail.com
	mailhub=smtp.gmail.com:587
	rewriteDomain=gmail.com
	hostname=localhost
	UseTLS=Yes
	UseSTARTTLS=Yes
	AuthUser="$ssmtpUser"
	AuthPass="$ssmtpPasswd"
	FromLineOverride=yes"
	
	echo -n > /etc/ssmtp/ssmtp.conf
	echo -e "$ssmtpStr" > /etc/ssmtp/ssmtp.conf
	chown root:mail /etc/ssmtp/ssmtp.conf
	
	gpasswd -a vagrant mail
	gpasswd -a root mail
	
	echo -n > /etc/ssmtp/revaliases
	echo "root:"$ssmtpUser"@gmail.com:smtp.gmail.com:587" > /etc/ssmtp/revaliases
	echo "vagrant:"$ssmtpUser"@gmail.com:smtp.gmail.com:587" > /etc/ssmtp/revaliases
	
fi

# --------------------------------------------------------------------
# INSTALL JAVA JRE, JAI, JAI I/O

cd ~ && wget --no-check-certificate --no-cookies --header "Cookie: gpw_e24=http%3A%2F%2Fwww.oracle.com" "http://download.oracle.com/otn-pub/java/jdk/7/jre-7-linux-x64.rpm"
rpm -Uvh jre*
alternatives --install /usr/bin/java java /usr/java/latest/bin/java 200000
rm -f ~/jre-7-linux-x64.rpm

cd ~ && wget http://download.java.net/media/jai/builds/release/1_1_3/jai-1_1_3-lib-linux-amd64-jre.bin
cd ~ && wget http://download.java.net/media/jai-imageio/builds/release/1.1/jai_imageio-1_1-lib-linux-amd64-jre.bin

cd /usr/java/jre1.7.0/
chmod u+x ~/jai-1_1_3-lib-linux-amd64-jre.bin 
echo "yes" | ~/jai-1_1_3-lib-linux-amd64-jre.bin 
rm -f ~/jai-1_1_3-lib-linux-amd64-jre.bin 

export _POSIX2_VERSION=199209 
chmod u+x ~/jai_imageio-1_1-lib-linux-amd64-jre.bin 
echo "yes" | ~/jai_imageio-1_1-lib-linux-amd64-jre.bin 
rm -f ~/jai_imageio-1_1-lib-linux-amd64-jre.bin

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE POSTGRESQL + POSTGIS

# EXCLUDE POSTGRESQL FROM THE BASE CentOS RPM
sed -i -e '/^\[base\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo 
sed -i -e '/^\[updates\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo 

# INSTALL POSTGRESQL
yum install -y postgresql93* postgis2_93* 

# INSTALL PYTHON PSYCOPG2 MODULE FOR POSTGRES
export PATH=/usr/pgsql-9.3/bin:"$PATH"
pip install psycopg2

# MAKE THE SNFS1 MOCK DIRECTORY IF IT DOESNT EXIST
if [ ! -d "/cresis/snfs1/web/ops/pgsql/9.3/" ]
	then
		mkdir -p /cresis/snfs1/web/ops/pgsql/9.3/
		chown postgres:postgres /cresis/snfs1/web/ops/pgsql/9.3/
		chmod 700 /cresis/snfs1/web/ops/pgsql/9.3/
fi

# SET THE DEVELOPMENT USERNAME AND PASSWORD
dbUser='admin'
dbPswd='pubAdmin'

# INITIALIZE THE DATABASE CLUSTER
pgDir='/cresis/snfs1/web/ops/pgsql/9.3/'
cmdStr='/usr/pgsql-9.3/bin/initdb -D '$pgDir
su - postgres -c "$cmdStr"
pgConfDir=$pgDir"postgresql.conf"

# SET UP THE POSTGRESQL CONFIG FILES
sed -i "s,#port = 5432,port = 5432,g" $pgConfDir
sed -i "s,#track_counts = on,track_counts = on,g" $pgConfDir
sed -i "s,#autovacuum = on,autovacuum = on,g" $pgConfDir
sed -i "s,local   all             all                                     peer,local   all             all                                     trust,g" $pgConfDir

# START UP THE POSTGRESQL SERVER
su - postgres -c '/usr/pgsql-9.3/bin/pg_ctl start -D '$pgDir
sleep 5

# CREATE THE ADMIN ROLE
cmdstring="CREATE ROLE "$dbUser" WITH SUPERUSER LOGIN PASSWORD '"$dbPswd"';"
psql -U postgres -d postgres -c "$cmdstring"

# CREATE THE POSTGIS TEMPLATE
cmdstring="createdb postgis_template -O "$dbUser 
su - postgres -c "$cmdstring"
psql -U postgres -d postgis_template -c "CREATE EXTENSION postgis; CREATE EXTENSION postgis_topology;"

# CREATE THE APP DATABASE
cmdstring="createdb "$appName" -O "$dbUser" -T postgis_template"
su - postgres -c "$cmdstring"

# --------------------------------------------------------------------
# INSTALL PYTHON PACKAGES / SCIPY / GEOS

# INSTALL PACKAGES WITH PIP
pip install Cython 
pip install geojson 
pip install ujson 
pip install django-extensions 
pip install simplekml
pip install --pre line_profiler

# INSTALL SCIPY 
yum -y install atlas-devel blas-devel
pip install numpy
pip install scipy 

# INSTALL GEOS
yum -y install geos-devel

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE DJANGO

# INSTALL DJANGO
pip install Django==1.6.2

# CREATE DIRECTORY AND COPY PROJECT
mkdir -p /var/django/
cp -rf /vagrant/conf/django/* /var/django/

# SYNC THE DJANGO DEFINED DATABASE
python /var/django/$appName/manage.py syncdb --noinput 

# --------------------------------------------------------------------
# BULKLOAD DATA TO POSTGRESQL

if [ $installPgData -eq 1 ]; then
	
	if [ "$(ls -A /vagrant/data/postgresql)" ]; then
		
		# INSTALL pg_bulkload AND DEPENDENCIES
		cd ~ && wget "http://pgfoundry.org/frs/download.php/3568/pg_bulkload-3.1.5-1.pg93.rhel6.x86_64.rpm"
		yum install -y openssl098e;
		rpm -Uvh ftp://rpmfind.net/linux/centos/6/os/x86_64/Packages/compat-libtermcap-2.0.8-49.el6.x86_64.rpm;
		rpm -ivh ~/pg_bulkload-3.1.5-1.pg93.rhel6.x86_64.rpm;
		
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

# INSTALL GEOSERVER WAR
cd ~ && wget https://ops.cresis.ku.edu/data/geoserver/geoserver.pub.war
mv ./geoserver.pub.war /var/lib/tomcat6/webapps/geoserver.war

# MAKE THE DIRECTORY FOR DATA
mkdir -p /cresis/web/

# GET/UNZIP THE DATA
if [ -f /vagrant/data/geoserver/geoserver.zip ]; then

	# UNZIP THE EXISTING DATA PACK
	unzip /vagrant/data/geoserver/geoserver.zip -d /cresis/web

else 

	# DOWNLOAD THE DATA PACK FROM CReSIS (MINIMAL LAYERS)
	cd /vagrant/data/geoserver/ && wget https://ops.cresis.ku.edu/data/geoserver/geoserver.zip
	
	# UNZIP THE DOWNLOADED DATA PACK
	unzip /vagrant/data/geoserver/geoserver.zip -d /cresis/web

fi

# START APACHE TOMCAT (UNPACKS GEOSERVER WEB ARCHIVE)
service tomcat6 start

# --------------------------------------------------------------------
# INSTALL AND CONFIGURE WEB APPLICATION

cp -rf /vagrant/conf/geoportal/* /var/www/html/ # COPY THE APPLICATION

# WRITE THE BASE URL TO globals.js
sed -i "s,	 baseUrl: ""http://192.168.111.222"",	 baseUrl: ""$serverName"",g" /var/www/html/app/Global.js

# CREATE AND CONFIGURE ALL THE OUTPUT DIRECTORIES
mkdir -p /cresis/snfs1/web/ops/data/csv/
chmod 777 /cresis/snfs1/web/ops/data/csv/

mkdir -p /cresis/snfs1/web/ops/data/kml/
chmod 777 /cresis/snfs1/web/ops/data/kml/

mkdir -p /cresis/snfs1/web/ops/data/mat/
chmod 777 /cresis/snfs1/web/ops/data/mat/

mkdir -p /var/profile_logs/txt/
chmod 777 /var/profile_logs/txt/

# --------------------------------------------------------------------
# MAKE SURE ALL SERVICES ARE STARTED AND ON

# APACHE HTTPD
service httpd start
chkconfig httpd on

# POSTGRESQL
su - postgres -c '/usr/pgsql-9.3/bin/pg_ctl start -D '$pgDir
sleep 5

# APACHE TOMCAT
service tomcat6 start
chkconfig tomcat6 on

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
printf "#  - Open a web browser (Google Chrome recommended)\n"
printf "#  - Enter %s as the url.\n" $serverName
printf "#  - Welcome the the OPS web interface!.\n"
printf "#\n"	
printf "#########################################################################\n"
printf "#########################################################################\n"
printf "\n"
echo "Started at:" $startTime
echo "Finished at:" $stopTime