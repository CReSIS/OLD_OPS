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

STATUS_COLOR='\033[1;34m';
NC='\033[0m' # No Color

configPath="/opt/ops/conf/provisions.config"

# Update $1 in the config with value $2
update_config() {
    sed -i "/^$1=/D" $configPath # Remove any old value
    assignment_str="$1=$2";
    echo $assignment_str >> $configPath # Add new value to config
    eval $assignment_str; # Update value locally
}

before_reboot() {
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

    update_config "startTime" "\"$(date -u)\""
    update_config "installPgData" 0

    printf "${STATUS_COLOR}Yum installing tools${NC}\n";
    yum install -y gzip gcc unzip rsync wget git

    # --------------------------------------------------------------------
    #PROMPT TO OPTIONALLY LOAD IN DATA (DATA BULKLOAD)
    while true; do
        read -p "Would you like to bulk load the OpenPolarServer with data? [y/n]" yn
        case $yn in
            [Yy]* )
                update_config "installPgData" 1;
                printf "		*****NOTE*****\n"
                printf "You must place the desired datapacks in \n/opt/ops/data/postgresql/ before continuing.\n"
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
                update_config "installPgData" 1;
                # DOWNLOAD A PREMADE DATA PACK FROM CReSIS (MINIMAL LAYERS)
                printf "${STATUS_COLOR}Downloading and unzipping premade datapack${NC}\n";
                wget https://data.cresis.ku.edu/data/ops/SampleData.zip -P /opt/ops/data/postgresql/
                unzip /opt/ops/data/postgresql/SampleData.zip -d /opt/ops/data/postgresql/
                rm /opt/ops/data/postgresql/SampleData.zip
                break;;
            [Nn]* ) break;;
            * ) echo "Please answer yes or no.";;
        esac
    done

    # --------------------------------------------------------------------
    # SET SOME STATIC INPUTS
    # Config used because values must persist after reboot
    update_config "preProv" 1;
    update_config "newDb" 1;
    update_config "serverName" "\"192.168.111.222\""
    update_config "serverAdmin" "\"root\"";
    update_config "appName" "\"ops\"";
    update_config "dbName" "\"ops\"";

    update_config "opsDataPath" "\"/db/\"";
    update_config "webDataDir" "\"${opsDataPath}data\"";

    # --------------------------------------------------------------------
    # GET SOME INPUTS FROM THE USER

    read -s -p "Database User (default=admin): " dbUser && printf "\n";
    read -s -p "Database Password (default=pubAdmin): " dbPswd && printf "\n";
    update_config "dbUser" $dbUser
    update_config "dbPswd" $dbPswd
    if [[ -z "${dbUser// }" ]]; then
    update_config "dbUser" "\"admin\""
    fi
    if [[ -z "${dbPswd// }" ]]; then
    update_config "dbPswd" "\"pubAdmin\""
    fi
    printf "${STATUS_COLOR}Storing db password${NC}\n";
    echo -e $dbPswd > /etc/db_pswd.txt;

    read -s -p "Gitlab External URL (default=http://"$serverName"/git): " GITLAB_URL && printf "\n";
    update_config "GITLAB_URL" $GITLAB_URL
    if [[ -z "${GITLAB_URL// }" ]]; then
    update_config "GITLAB_URL" "\"http://"$serverName"/git\""
    fi

    read -s -p "Timezone (default=America/Chicago): " timeZone && printf "\n";
    update_config "timeZone" $timeZone
    if [[ -z "${timeZone// }" ]]; then
    update_config "timeZone" "\"America/Chicago\""
    fi

    printf "${STATUS_COLOR}Setting Timezone${NC}\n";
    timedatectl set-timezone $timeZone


    # --------------------------------------------------------------------
    # PRE-PROVISION THE OPS (NEED FOR CRESIS VM TEMPLATE)

    if [ "$preProv" -eq 1 ]; then

        printf "${STATUS_COLOR}Yum isntalling epel-release${NC}\n";
        yum install -y epel-release
        printf "${STATUS_COLOR}Cleaning yum metadata${NC}\n";
        yum clean all  # seems to prevent timeouts during yum update
        printf "${STATUS_COLOR}Performing yum update${NC}\n";
        yum update -y
        printf "${STATUS_COLOR}Yum installing dev tools${NC}\n";
        yum groupinstall -y "Development Tools"
        yum install -y gzip gcc unzip rsync wget git

        printf "${STATUS_COLOR}Stopping firewalld${NC}\n";
        systemctl mask firewalld
        systemctl stop firewalld
        printf "${STATUS_COLOR}Installing IPTables${NC}\n";
        yum install -y iptables-services
        systemctl enable iptables
        printf "${STATUS_COLOR}Setting and restarting iptables${NC}\n";
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

    geoServerStr="GEOSERVER_DATA_DIR=${opsDataPath}geoserver"
    printf "${STATUS_COLOR}Adding GEOSERVER_DATA_DIR TO ~/.bashrc${NC}\n";
    echo $geoServerStr >> ~/.bashrc
    . ~/.bashrc

    # Update git to v2
    printf "${STATUS_COLOR}Removing old version of git${NC}\n";
    yum remove -y git*
    printf "${STATUS_COLOR}Adding repo which includes git v2 for centos 7${NC}\n";
    yum -y install https://packages.endpointdev.com/rhel/7/os/x86_64/endpoint-repo.x86_64.rpm
    printf "${STATUS_COLOR}Install git v2${NC}\n";
    yum install -y git

    # UPDATE SYSTEM
    printf "${STATUS_COLOR}Updating yum (outside conditional)${NC}\n";
    yum update -y

    # Set SELinux policy to disabled
    # TODO[reece]: This is presumably not ideal -- Determine best practice solution
    printf "${STATUS_COLOR}Disabling SELinux${NC}\n";
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
SELINUXTYPE=targeted"

    printf "${STATUS_COLOR}Updating SELinux config${NC}\n";
    echo -e "$selinuxStr" > /etc/selinux/config

    update_config "afterReboot" 1

    echo "Press enter to reboot. Rerun script after reboot to continue.";
    read;
    printf "${STATUS_COLOR}Rebooting${NC}\n";
    reboot
}


after_reboot() {
    printf "${STATUS_COLOR}Performing after-reboot steps${NC}\n";

    # INSTALL THE PGDG REPO
    printf "${STATUS_COLOR}Installing pgdg repo${NC}\n";
    cd ~
    wget https://download.postgresql.org/pub/repos/yum/reporpms/EL-7-x86_64/pgdg-redhat-repo-latest.noarch.rpm
    rpm -Uvh pgdg-redhat-repo-latest.noarch.rpm
    rm -f pgdg-redhat-repo-latest.noarch.rpm

    # --------------------------------------------------------------------

    # INSTALL PYTHON3 and DEPENDENCIES
    printf "${STATUS_COLOR}Yum installing python3.8 dependencies${NC}\n";
    yum -y groupinstall "Development Tools"
    yum -y install openssl-devel bzip2-devel libffi-devel

    printf "${STATUS_COLOR}Downloading python 3.8.7 tar${NC}\n";
    cd ~
    wget https://data.cresis.ku.edu/data/temp/ct/ops/Python-3.8.7.tgz
    printf "${STATUS_COLOR}Extracting python 3.8.7 tar${NC}\n";
    tar xvf Python-3.8.7.tgz
    rm -f Python-3.8.7.tgz
    cd Python-3.8.7
    printf "${STATUS_COLOR}Configuring python 3.8.7${NC}\n";
    ./configure --enable-shared --prefix=/opt/python LDFLAGS=-Wl,-rpath=/opt/python/lib --enable-optimizations
    printf "${STATUS_COLOR}Making python 3.8.7${NC}\n";
    make altinstall

    printf "${STATUS_COLOR}Copying python3.8 to python${NC}\n";
    cp /opt/python/bin/python3.8 /opt/python/bin/python
    cp /opt/python/bin/pip3.8 /opt/python/bin/pip
    printf "${STATUS_COLOR}Adding /opt/python/bin to PATH${NC}\n";
    cat > /etc/profile.d/python38.sh << EOM
#!/bin/bash
if [[ -z "${VIRTUAL_ENV_LAUNCHED_PREV}" ]]; then
    export VIRTUAL_ENV_LAUNCHED_PREV=1
    if [[ ":$PATH:" != *":/opt/python/bin/:"* ]]; then
        export PATH=/opt/python/bin/:$PATH
        source /usr/bin/venv/bin/activate
    fi
    if [[ ":$PATH:" != *":/usr/bin/venv/bin:"* ]]; then
        source /usr/bin/venv/bin/activate
    fi
fi
EOM
    export PATH=/opt/python/bin/:$PATH

    printf "${STATUS_COLOR}Updating pip${NC}\n";
    python -m pip install --upgrade pip --no-cache-dir
    python -m pip install pip --no-cache-dir # Try twice as it seems to fail sometimes
    printf "${STATUS_COLOR}Creating and activating python virtual env${NC}\n";
    python -m venv /usr/bin/venv
    # Source python venv after adding python install path to path so that it takes priority
    source /usr/bin/venv/bin/activate
    echo -e "source /usr/bin/venv/bin/activate" >> /etc/profile.d/python38.sh
    printf "${STATUS_COLOR}Updating venv pip${NC}\n";
    python -m pip install --upgrade pip --no-cache-dir

    # --------------------------------------------------------------------
    # INSTALL APACHE WEB SERVER AND MOD_WSGI

    # INSTALL APACHE HTTPD
    printf "${STATUS_COLOR}Yum installing httpd${NC}\n";
    yum install -y httpd httpd-devel

    # INSTALL MOD_WSGI (COMPILE WITH Python38)
    printf "${STATUS_COLOR}Pip installing mod_wsgi${NC}\n";
    pip install --upgrade mod_wsgi==4.8 --no-cache-dir

    # --------------------------------------------------------------------
    # WRITE CONFIG FILES FOR HTTPD

    # INCLUDE THE SITE CONFIGURATION FOR HTTPD
    printf "${STATUS_COLOR}Updating httpd site config globally${NC}\n";
    echo "Include /var/www/sites/"$serverName"/conf/"$appName".conf" >> /etc/httpd/conf/httpd.conf
    echo "SetEnv TZ ${timeZone}" >> /etc/httpd/conf/httpd.conf

    printf "${STATUS_COLOR}Creating webdata dir${NC}\n";
    mkdir -m 777 -p $webDataDir

    # WRITE THE DJANGO WSGI CONFIGURATION
wsgiStr="
"$(mod_wsgi-express module-config)"

WSGISocketPrefix run/wsgi
WSGIDaemonProcess $appName user=apache python-home=/usr/bin/venv python-path=/var/django/$appName:/usr/bin/venv/lib/python3.8/site-packages
WSGIProcessGroup $appName
WSGIScriptAlias /$appName /var/django/$appName/$appName/wsgi.py process-group=$appName application-group=%{GLOBAL}
<Directory /var/django/$appName/$appName>
    <Files wsgi.py>
        Require all granted
    </Files>
</Directory>";

    printf "${STATUS_COLOR}Creating django wsgi config${NC}\n";
    echo -e "$wsgiStr" > /etc/httpd/conf.d/djangoWsgi.conf

    # WRITE THE GEOSERVER PROXY CONFIGURATION
geoservStr="
ProxyRequests Off
ProxyPreserveHost On

<Proxy *>
    Require all granted
</Proxy>

ProxyPass /geoserver http://localhost:8080/geoserver
ProxyPassReverse /geoserver http://localhost:8080/geoserver"

    printf "${STATUS_COLOR}Creating geoserver proxy config${NC}\n";
    echo -e "$geoservStr" > /etc/httpd/conf.d/geoserverProxy.conf

    # WRITE THE HTTPD SITE CONFIGURATION
    printf "${STATUS_COLOR}Creating httpd sites dirs${NC}\n";
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
        Require all granted
        ForceType application/octet-stream
        Header set Content-Disposition attachment
    </Directory>

    Alias /profile-logs /var/profile_logs/txt
    <Directory ""/var/profile_logs/txt"">
        Options Indexes FollowSymLinks
        AllowOverride None
        Require all granted
    </Directory>

    Header add Strict-Transport-Security: \"max-age=15768000;includeSubdomains\"
    <Location /git>
        Require all granted

        #Allow forwarding to gitlab-workhorse
        ProxyPassReverse http://127.0.0.1:8188
        ProxyPassReverse http://"$serverName"/git

        RewriteEngine on

        RewriteCond %{DOCUMENT_ROOT}/%{REQUEST_FILENAME} !-f [OR]
        RewriteCond %{REQUEST_URI} ^/uploads/.*
        RewriteRule .* http://127.0.0.1:8188%{REQUEST_URI} [P,QSA,NE]

        ErrorDocument 404 /404.html
        ErrorDocument 422 /422.html
        ErrorDocument 500 /500.html
        ErrorDocument 502 /502.html
        ErrorDocument 503 /503.html
        RequestHeader set "X-Forwarded-Proto" expr="%{REQUEST_SCHEME}e"
    </Location>

</VirtualHost>"

    printf "${STATUS_COLOR}Creating httpd site config for site${NC}\n";
    echo -e "$siteConf" > /var/www/sites/$serverName/conf/$appName.conf
    printf "${STATUS_COLOR}Creating httpd error and access logs${NC}\n";
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

    printf "${STATUS_COLOR}Creating and chmodding site proxy cgi${NC}\n";
    echo -e "$cgiStr" > /var/www/sites/$serverName/cgi-bin/proxy.cgi
    chmod +x /var/www/sites/$serverName/cgi-bin/proxy.cgi

    # --------------------------------------------------------------------
    # WRITE CRONTAB CONFIGURATION

    printf "${STATUS_COLOR}Creating crontab${NC}\n";
    echo -n > /etc/crontab

cat << EOM > /etc/crontab
SHELL=/bin/bash
PATH=/sbin:/bin:/usr/sbin:/usr/bin
MAILTO=''
HOME=/

# REMOVE CSV FILES OLDER THAN 7 DAYS AT 2 AM DAILY
0 2 * * * root rm -f \$(find $webDataDir/csv/*.csv -mtime +7);
0 2 * * * root rm -f \$(find $webDataDir/kml/*.kml -mtime +7);
0 2 * * * root rm -f \$(find $webDataDir/mat/*.mat -mtime +7);
0 2 * * * root rm -f \$(find $webDataDir/reports/*.csv -mtime +7);
0 2 * * * root rm -f \$(find $webDataDir/datapacks/*.tar.gz -mtime +7);

# VACUUM ANALYZE-ONLY THE ENTIRE OPS DATABASE AT 2 AM DAILY
0 2 * * * root sh /opt/ops/conf/tools/vacuumAnalyze.sh ops

# WEEKLY POSTGRESQL REPORT CREATION AT 2 AM SUNDAY
0 2 * * 7 root sh /opt/ops/conf/tools/createPostgresqlReport.sh "$opsDataPath"postgresql_reports/

# REMOVE POSTGRESQL REPORTS OLDER THAN 2 MONTHS EVERY SUNDAY AT 2 AM
0 2 * * 7 root rm -f \$(find $opsDataPath/postgresql_reports/*.html -mtime +60);

# CLEAR THE CONTENTS OF THE DJANGO LOGS EVERY MONTH (FIRST OF MONTH, 2 AM)
0 2 1 * * root > $opsDataPath/django_logs/createPath.log;
EOM

    printf "${STATUS_COLOR}Restarting crond${NC}\n";
    service crond start
    chkconfig crond on

    # --------------------------------------------------------------------
    # INSTALL AND CONFIGURE POSTGRESQL + POSTGIS

    pgDir=$opsDataPath'pgsql/12/'
    pgPth=$opsDataPath'pgsql/'

    # EXCLUDE POSTGRESQL FROM THE BASE CentOS RPM
    printf "${STATUS_COLOR}Excluding postgresql from base centos rpm${NC}\n";
    sed -i -e '/^\[base\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo
    sed -i -e '/^\[updates\]$/a\exclude=postgresql*' /etc/yum.repos.d/CentOS-Base.repo

    # INSTALL POSTGRESQL and POSTGIS
    printf "${STATUS_COLOR}Yum installing postgres and dependencies${NC}\n";
    yum install -y yum-utils
    yum install -y postgresql12 postgresql12-server postgis30_12.x86_64
    yum-config-manager --enable pgdg12

    # INSTALL PYTHON PSYCOPG2 MODULE FOR POSTGRES
    printf "${STATUS_COLOR}Pip installing psycopg2${NC}\n";
    export PATH=/usr/pgsql-12/bin:"$PATH"
    pip install psycopg2-binary==2.9

    if [ "$newDb" -eq 1 ]; then

        # MAKE THE SNFS1 MOCK DIRECTORY IF IT DOESNT EXIST
        if [ ! -d "$pgPth" ]
            then
                printf "${STATUS_COLOR}Creating SNFS1 mock dir${NC}\n";
                mkdir -p $pgPth
                chown postgres:postgres $pgPth
                chmod 700 $pgPth
        fi

        # INITIALIZE THE DATABASE CLUSTER
postgresServiceStr="
[Service]
Environment=\"PGDATA=$pgDir\"
Environment=\"PGLOG=${pgDir}pgstartup.log\"
"
        printf "${STATUS_COLOR}Updating postgresql-12 service systemd override${NC}\n";
        mkdir -p "/etc/systemd/system/postgresql-12.service.d/"
        echo -e "$postgresServiceStr" > "/etc/systemd/system/postgresql-12.service.d/override.conf"
        printf "${STATUS_COLOR}Initializing db cluster${NC}\n";
        /usr/pgsql-12/bin/postgresql-12-setup initdb
        printf "${STATUS_COLOR}Replacing postgresql.conf${NC}\n";
        mv $pgDir"postgresql.conf" $pgDir"postgresql.conf-default"
        cp /opt/ops/conf/configs/postgresql.conf $pgDir"postgresql.conf"
        printf "${STATUS_COLOR}Enabling postgres service${NC}\n";
        systemctl enable --now postgresql-12

        # CREATE STARTUP LOG
        printf "${STATUS_COLOR}Creating pg startup log${NC}\n";
        touch $pgDir"pgstartup.log"
        chown postgres:postgres $pgDir"pgstartup.log"
        chmod 700 $pgDir"pgstartup.log"

        # SET UP THE POSTGRESQL CONFIG FILES
        printf "${STATUS_COLOR}Updating postgresql config files${NC}\n";
        pgConfDir=$pgDir"postgresql.conf"
        pghbaConfDir=$pgDir"pg_hba.conf"
        sed -i "s,#port = 5432,port = 5432,g" $pgConfDir
        sed -i "s,#track_counts = on,track_counts = on,g" $pgConfDir
        sed -i "s,#autovacuum = on,autovacuum = on,g" $pgConfDir
        sed -i "s,local   all             all                                     peer,local   all             all                                     trust,g" $pghbaConfDir
        sed -i "s,host    all             all             127.0.0.1/32            ident,host    all             all             127.0.0.1/32            trust,g" $pghbaConfDir
        # THE FOLLOWING SET UP POSTGRESQL LOGGING:
        printf "${STATUS_COLOR}Updating postgresql logging${NC}\n";
        sed -i "s,#log_min_duration_statement = -1, log_min_duration_statement = 1500,g" $pgConfDir
        sed -i "s@log_line_prefix = '< %m >'@log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d '@g" $pgConfDir
        sed -i "s,#log_checkpoints = off,log_checkpoints = on,g" $pgConfDir
        sed -i "s,#log_connections = off,log_connections = on,g" $pgConfDir
        sed -i "s,#log_disconnections = off,log_disconnections = on,g" $pgConfDir
        sed -i "s,#log_lock_waits = off,log_lock_waits = on,g" $pgConfDir
        sed -i "s,#log_temp_files = -1,log_temp_files = 0,g" $pgConfDir
        sed -i "s,lc_messages = 'en_US.UTF-8',lc_messages = 'C',g" $pgConfDir

        # START UP THE POSTGRESQL SERVER

        printf "${STATUS_COLOR}Restarting postgresql service${NC}\n";
        systemctl restart postgresql-12

        # CREATE THE ADMIN ROLE
        printf "${STATUS_COLOR}PSQL creating admin role${NC}\n";
        cmdstring="CREATE ROLE "$dbUser" WITH SUPERUSER LOGIN PASSWORD '"$dbPswd"';"
        psql -U postgres -d postgres -c "$cmdstring"

        # CREATE THE POSTGIS TEMPLATE
        printf "${STATUS_COLOR}PSQL creating postgis template${NC}\n";
        cmdstring="createdb postgis_template -O "$dbUser
        su - postgres -c "$cmdstring"
        psql -U postgres -d postgis_template -c "CREATE EXTENSION postgis; CREATE EXTENSION postgis_topology;"

    fi

    # CREATE THE APP DATABASE
    printf "${STATUS_COLOR}Creating app db${NC}\n";
    cmdstring="createdb "$dbName" -O "$dbUser" -T postgis_template"
    su - postgres -c "$cmdstring"

    # --------------------------------------------------------------------
    # INSTALL PYTHON PACKAGES

    # INSTALL PACKAGES WITH PIP
    printf "${STATUS_COLOR}Pip installing website dependencies${NC}\n";
    pip install Cython==0.29
    pip install geojson==2.5 ujson==4.0 django-extensions==3.1 simplekml==1.3 pylint
    pip install --pre line_profiler==3.3

    # INSTALL NUMPY/SCIPY
    printf "${STATUS_COLOR}Yum installing atlas and blas${NC}\n";
    yum -y install atlas-devel blas-devel
    printf "${STATUS_COLOR}Pip installing numpy and scipy${NC}\n";
    pip install numpy==1.21
    pip install scipy==1.7

    # INSTALL GEOS
    printf "${STATUS_COLOR}Yum installing geos${NC}\n";
    yum -y install geos-devel

    # --------------------------------------------------------------------
    # INSTALL AND CONFIGURE DJANGO

    # INSTALL DJANGO
    printf "${STATUS_COLOR}Pip installing django and debugpy${NC}\n";
    pip install Django==3.2
    # Used to open port for remote debugger attachment to Django instance in wsgi.py
    pip install debugpy

    # CREATE DIRECTORY AND COPY PROJECT
    printf "${STATUS_COLOR}Creating django dir${NC}\n";
    mkdir -p /var/django/
    printf "${STATUS_COLOR}Copying site from opt/ops to django${NC}\n";
    cp -rf /opt/ops/conf/django/* /var/django/

    printf "${STATUS_COLOR}Setting Django settings env var${NC}\n";
    echo -e "#!/bin/bash\nexport DJANGO_SETTINGS_MODULE=ops.settings" >> /etc/profile.d/django.sh
    export DJANGO_SETTINGS_MODULE=ops.settings

    # GENERATE A NEW SECRET_KEY
    printf "${STATUS_COLOR}Generating secret key${NC}\n";
    NEW_SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9*^+()@' | fold -w 40 | head -n 1);
    echo $NEW_SECRET_KEY >> /etc/secret_key.txt

    # SET THE OPS_DATA_PATH
    printf "${STATUS_COLOR}Setting OPS_DATA_PATH in settings.py${NC}\n";
    sed -i "s|OPS_DATA_PATH = ''|OPS_DATA_PATH = '$opsDataPath'|g" /var/django/ops/ops/settings.py;

    # MODIFY THE DATABASE NAME
    printf "${STATUS_COLOR}Setting db name and user in settings.py${NC}\n";
    sed -i "s|		'NAME': 'ops'|		'NAME': '$dbName'|g" /var/django/ops/ops/settings.py
    sed -i "s|		'USER': 'admin'|		'USER': '$dbUser'|g" /var/django/ops/ops/settings.py

    # ADD DJANGO ADMINS.
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
    printf "${STATUS_COLOR}Setting django admins in settings.py${NC}\n";
    sed -i "s,ADMINS = (),ADMINS = ($adminStr),g" /var/django/ops/ops/settings.py

    #OPTIONALLY SET DJANGO TO BE IN DEBUG MODE.
    while true; do

        read -p "Would you like to have Django operate in debug mode (DEVELOPMENT ENVIRONMENT ONLY!)? [y/n]" yn
        case $yn in
            [Yy]* )
                read -p "ARE YOU SURE YOU WANT DJANGO TO BE IN DEBUG MODE? THIS IS FOR DEVELOPMENT ENVIRONMENTS ONLY. [y/n]" yn
                case $yn in
                    [Yy]* )
                        printf "${STATUS_COLOR}Setting debug mode in settings.py${NC}\n";
                        sed -i "s,DEBUG = False,DEBUG = True,g" /var/django/ops/ops/settings.py;
                        break;;
                    * ) echo "Please answer yes or no.";;
                esac;;
            [Nn]* ) break;;
            * ) echo "Please answer yes or no.";;
        esac
    done
    if [ "$newDb" -eq 1 ]; then

        # SYNC THE DJANGO DEFINED DATABASE
        printf "${STATUS_COLOR}Making django migrations${NC}\n";
        python /var/django/$appName/manage.py makemigrations
        apps="auth contenttypes messages staticfiles gis django_extensions rds accum snow kuband opsuser"
        for app in $apps
        do
            printf "${STATUS_COLOR}Making django migration for app ${app}${NC}\n";
            python /var/django/$appName/manage.py makemigrations $app
        done

        ## No longer necessary as initial migrations are now included in the repo
        # printf "${STATUS_COLOR}Reordering Migrations${NC}\n";
        # python /opt/ops/conf/tools/reorder_migrations.py

        printf "${STATUS_COLOR}Migrating${NC}\n";
        python /var/django/$appName/manage.py migrate

        printf "${STATUS_COLOR}Loading initial data${NC}\n";
        cd /var/django/$appName/
        for app in */
        do
            if [ -d "${app}fixtures" ]
            then
                for data_file in $app/fixtures/*
                do
                    printf "${STATUS_COLOR}Loading data ${data_file}${NC}\n";
                    python manage.py loaddata "${data_file}";
                done
            fi
        done

        printf "${STATUS_COLOR}Creating default user${NC}\n";
        python manage.py shell -c "exec(open('/opt/ops/conf/tools/createDefaultUser.py').read())"

        # CREATE INDEXES ON POINT PATH GEOMETRIES
        printf "${STATUS_COLOR}Creating indices on point path geometries${NC}\n";
        indexStr='psql -U postgres -d '$dbName' -c "CREATE INDEX app_antarctic_geom_idx ON app_point_paths USING gist (ST_Transform(geom,3031)) WHERE location_id = 2; CREATE INDEX app_arctic_geom_idx ON app_point_paths USING gist (ST_Transform(geom,3413)) WHERE location_id = 1;"'
        eval ${indexStr//app/rds}
        eval ${indexStr//app/snow}
        eval ${indexStr//app/accum}
        eval ${indexStr//app/kuband}

    fi

    # --------------------------------------------------------------------
    # BULKLOAD DATA TO POSTGRESQL

    # INSTALL pg_bulkload AND DEPENDENCIES
    printf "${STATUS_COLOR}Yum installing openssl and pg_bulkload${NC}\n";
    yum install -y openssl098e;
    yum install -y pg_bulkload12;

    # ADD pg_bulkload FUNCTION TO THE DATABASE
    printf "${STATUS_COLOR}PSQL adding pg_bulkload function to db${NC}\n";
    su - postgres -c "psql -f /usr/pgsql-12/share/extension/pg_bulkload.sql "$appName"";

    if [ "$installPgData" -eq 1 ]; then
        fCount=$(ls -A /opt/ops/data/postgresql/ | wc -l);
        if [ "$fCount" -gt 1 ]; then
            # LOAD INITIAL DATA INTO THE DATABASE
            printf "${STATUS_COLOR}Running initdataload.sh${NC}\n";
            sh /opt/ops/conf/bulkload/initdataload.sh
        fi
    fi

    # --------------------------------------------------------------------
    # INSTALL PGBADGER FOR LOG REPORT GENERATION

    printf "${STATUS_COLOR}Yum installing pgbadger${NC}\n";
    yum install -y pgbadger

    # --------------------------------------------------------------------
    # Install gitlab
    printf "${STATUS_COLOR}Installing gitlab dependencies${NC}\n";
    sudo yum install -y curl policycoreutils-python openssh-server perl
    printf "${STATUS_COLOR}Installing gitlab repo${NC}\n";
    curl -sS https://packages.gitlab.com/install/repositories/gitlab/gitlab-ee/script.rpm.sh | sudo bash
    printf "${STATUS_COLOR}Installing gitlab${NC}\n";
    sudo EXTERNAL_URL="${GITLAB_URL}" GITLAB_ROOT_EMAIL="root@local" GITLAB_ROOT_PASSWORD="pubMaster" yum install -y gitlab-ee

    printf "${STATUS_COLOR}Updating config${NC}\n";
    gitlabConfDir=/etc/gitlab/gitlab.rb
    sed -i "s,# web_server\['external_users'\] = \[\],web_server['external_users'] = ['apache'],g" $gitlabConfDir
    sed -i "s,# nginx\['enable'\] = true,nginx['enable'] = false,g" $gitlabConfDir
    sed -i "s,# gitlab_workhorse\['listen_network'\] = \"unix\",gitlab_workhorse['listen_network'] = \"tcp\",g" $gitlabConfDir
    sed -i "s,# gitlab_workhorse\['listen_addr'\] = \"/var/opt/gitlab/gitlab-workhorse/sockets/socket\",gitlab_workhorse['listen_addr'] = \"127.0.0.1:8188\",g" $gitlabConfDir
    sed -i "s,# puma\['port'\] = 8080,puma['port'] = 8189,g" $gitlabConfDir
    sed -i "s,# gitlab_rails\['time_zone'\] = 'UTC',gitlab_rails['time_zone'] = '${timeZone}',g" $gitlabConfDir
    sudo gitlab-ctl reconfigure

    printf "${STATUS_COLOR}Restarting apache${NC}\n";
    sudo service httpd restart
    printf "${STATUS_COLOR}Reconfiguring gitlab${NC}\n";
    sudo gitlab-ctl restart

    # printf "${STATUS_COLOR}Removing host key check requirement for gitlab.com${NC}\n";
    # printf "Host gitlab.com\n\tStrictHostKeyChecking no\n" >> ~/.ssh/config

    printf "${STATUS_COLOR}Cloning repos from CReSIS Gitlab${NC}\n";
    mkdir ~/repos
    cd ~/repos
    git clone https://gitlab.com/openpolarradar/opr.git
    git clone https://gitlab.com/openpolarradar/opr.wiki.git
    git clone https://gitlab.com/openpolarradar/opr_params.git

    # --------------------------------------------------------------------
    # INSTALL AND CONFIGURE APACHE TOMCAT AND GEOSERVER(WAR)

    # INSALL APACHE TOMCAT

    printf "${STATUS_COLOR}Installing Java JDK${NC}\n";
    yum install -y java-11-openjdk-devel

    printf "${STATUS_COLOR}Creating Tomcat user${NC}\n";
    useradd -m -U -d /opt/tomcat -s /bin/false tomcat
    printf "${STATUS_COLOR}Downloading tomcat 8.5${NC}\n";
    cd /tmp
    wget https://data.cresis.ku.edu/data/temp/ct/ops/apache-tomcat-8.5.66.zip

    printf "${STATUS_COLOR}Installing tomcat8.5${NC}\n";
    unzip apache-tomcat-*.zip
    mkdir -p /opt/tomcat
    mv apache-tomcat-8.5.66 /opt/tomcat/

    printf "${STATUS_COLOR}Linking tomcat and setting permissions${NC}\n";
    ln -s /opt/tomcat/apache-tomcat-8.5.66 /opt/tomcat/latest
    chown -R tomcat:tomcat /opt/tomcat
    sh -c 'chmod +x /opt/tomcat/latest/bin/*.sh'

    # CONFIGURE tomcat
    printf "${STATUS_COLOR}Configuring Tomcat${NC}\n";
    tomcatService="
[Unit]
Description=Tomcat 8.5 servlet container
After=network.target

[Service]
Type=forking

User=tomcat
Group=tomcat

Environment=JAVA_HOME="$(find /usr/lib/jvm -name 'java-11-openjdk-*')"
Environment=JAVA_OPTS=-Djava.security.egd=file:///dev/urandom -Xms512M -Xmx1024M -server -XX:+UseParallelGC -XX:+UseParallelOldGC

Environment=CATALINA_BASE=/opt/tomcat/latest
Environment=CATALINA_HOME=/opt/tomcat/latest
Environment=CATALINA_PID=/opt/tomcat/latest/temp/tomcat.pid
Environment=CATALINA_OPTS=-DGEOSERVER_DATA_DIR=${opsDataPath}geoserver

ExecStart=/opt/tomcat/latest/bin/startup.sh
ExecStop=/opt/tomcat/latest/bin/shutdown.sh

[Install]
WantedBy=multi-user.target"

    echo -e "$tomcatService" > /etc/systemd/system/tomcat.service

    # MAKE THE EXTERNAL GEOSERVER DATA DIRECTORY (IF IT DOESNT EXIST)
    geoServerDataPath=$opsDataPath"geoserver/"
    if [ ! -d "$geoServerDataPath" ]; then
        printf "${STATUS_COLOR}Creating external geoserver data dir${NC}\n";
        mkdir -p $geoServerDataPath
    fi

    # EXTRACT THE OPS GEOSERVER DATA DIR TO THE DIRECTORY
    printf "${STATUS_COLOR}Copying geoserver data dir from opt/ops to geoServerDataPath${NC}\n";
    cp -rf /opt/ops/conf/geoserver/geoserver/* $geoServerDataPath

    # GET THE GEOSERVER REFERENCE DATA
    if [ -f /opt/ops/data/geoserver/geoserver.zip ]; then

        printf "${STATUS_COLOR}Unzipping geoserver.zip${NC}\n";
        unzip /opt/ops/data/geoserver/geoserver.zip -d $geoServerDataPath"data/"

    else

        # DOWNLOAD THE DATA PACK FROM CReSIS (MINIMAL LAYERS)
        printf "${STATUS_COLOR}Downloading minimal data pack from cresis${NC}\n";
        cd /opt/ops/data/geoserver/ && wget https://data.cresis.ku.edu/data/ops/geoserver.zip

        # UNZIP THE DOWNLOADED DATA PACK
        printf "${STATUS_COLOR}Unzipping geoserver.zip${NC}\n";
        unzip /opt/ops/data/geoserver/geoserver.zip -d $geoServerDataPath"data/"

    fi

    # TEMPORARY HACK UNTIL THE GEOSERVER.ZIP STRUCTURE CHANGES
    printf "${STATUS_COLOR}Moving geoserver data subdirs into geoserver data dir${NC}\n";
    mv $geoServerDataPath"data/geoserver/data/arctic" $geoServerDataPath"data/"
    mv $geoServerDataPath"data/geoserver/data/antarctic" $geoServerDataPath"data/"
    rm -rf $geoServerDataPath"data/geoserver/"

    # Download and move THE GEOSERVER WAR TO TOMCAT
    printf "${STATUS_COLOR}Dowloading geoserver war${NC}\n";
    cd ~
    wget https://data.cresis.ku.edu/data/temp/ct/ops/geoserver-2.19.1-war.zip -O geoserver-2.19.1-war.zip
    printf "${STATUS_COLOR}Unzipping geoserver war${NC}\n";
    unzip geoserver-2.19.1-war.zip -d geoserver-2.19.1-war
    printf "${STATUS_COLOR}Moving geoserver war${NC}\n";
    mv geoserver-2.19.1-war/geoserver.war /opt/tomcat/latest/webapps/geoserver.war
    chown tomcat:tomcat /opt/tomcat/latest/webapps/geoserver.war
    rm -rf geoserver-2.19.1-war
    rm -f geoserver-2.19.1-war.zip


    # SET OWNERSHIP/PERMISSIONS OF GEOSERVER DATA DIRECTORY
    printf "${STATUS_COLOR}Setting permissions on geoserver data dir${NC}\n";
    chmod -R u=rwX,g=rwX,o=rX $geoServerDataPath
    chown -R tomcat:tomcat $geoServerDataPath

    # START APACHE TOMCAT
    printf "${STATUS_COLOR}Starting tomcat service${NC}\n";
    systemctl daemon-reload
    systemctl start tomcat
    systemctl enable tomcat

    # --------------------------------------------------------------------
    # INSTALL AND CONFIGURE WEB APPLICATION

    printf "${STATUS_COLOR}Copying geoportal from opt/ops to www${NC}\n";
    cp -rf /opt/ops/conf/geoportal/* /var/www/html/ # COPY THE APPLICATION

    # WRITE THE BASE URL TO app.js
    # sed -i "s,	 baseUrl: ""http://192.168.111.222"",	 baseUrl: ""$serverName"",g" /var/www/html/app.js

    # CREATE AND CONFIGURE ALL THE OUTPUT DIRECTORIES
    printf "${STATUS_COLOR}Creating all output dirs${NC}\n";
    mkdir -m 777 -p $opsDataPath"data/csv/"
    mkdir -m 777 -p $opsDataPath"data/kml/"
    mkdir -m 777 -p $opsDataPath"data/mat/"
    mkdir -m 777 -p $opsDataPath"datapacktmp/"
    mkdir -m 777 -p  $opsDataPath"data/datapacks/"
    mkdir -m 777 -p $opsDataPath"data/reports/"
    mkdir -m 777 -p $opsDataPath"postgresql_reports/"
    mkdir -m 777 -p $opsDataPath"django_logs/debug/"
    mkdir -m 777 -p /var/profile_logs/txt/

    # --------------------------------------------------------------------
    # Create ops account
    printf "${STATUS_COLOR}Create ops user${NC}\n";
    adduser ops
    printf "${STATUS_COLOR}Granting sudo access to OPS user${NC}\n";
    usermod -aG wheel ops
    printf "${STATUS_COLOR}Changing root and ops passwords${NC}\n";
    echo -e "pubMaster\npubMaster" | passwd root
    echo -e "pubOps\npubOps" | passwd ops

    # --------------------------------------------------------------------
    # MAKE SURE ALL SERVICES ARE STARTED AND ON

    # APACHE HTTPD
    printf "${STATUS_COLOR}Allowing httpd to write to error_log${NC}\n";
    setsebool -P httpd_unified 1  # Allow httpd to write to error_log
    printf "${STATUS_COLOR}Starting httpd service${NC}\n";
    service httpd start
    printf "${STATUS_COLOR}chkconfig httpd on${NC}\n";
    chkconfig httpd on

    # POSTGRESQL
    printf "${STATUS_COLOR}Killing current postgres processes${NC}\n";
    pkill postgres;
    printf "${STATUS_COLOR}Restarting postgresql service${NC}\n";
    systemctl restart postgresql-12
    printf "${STATUS_COLOR}chkconfig postgresql-12 on${NC}\n";
    chkconfig postgresql-12 on

    # APACHE TOMCAT
    printf "${STATUS_COLOR}Starting tomcat service${NC}\n";
    service tomcat start
    printf "${STATUS_COLOR}chkconfig tomcat on${NC}\n";
    chkconfig tomcat on

    # --------------------------------------------------------------------
    # Push repos to gitlab now that it has had time to start up
    printf "${STATUS_COLOR}Pushing opr to local gitlab${NC}\n";
    cd ~/repos/opr
    git push -u http://root:pubMaster@localhost/git/root/opr.git master
    printf "${STATUS_COLOR}Pushing opr wiki to local gitlab${NC}\n";
    cd ~/repos/opr.wiki
    git push http://root:pubMaster@localhost/git/root/opr.wiki.git HEAD:master
    printf "${STATUS_COLOR}Pushing opr params to local gitlab${NC}\n";
    cd ~/repos/opr_params
    git push -u http://root:pubMaster@localhost/git/root/opr_params.git master

    cd ~


    # --------------------------------------------------------------------
    # DO A FINAL SYSTEM UPDATE
    printf "${STATUS_COLOR}Final yum update${NC}\n";
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
}

# Load config if exists and check reboot status or perform before_reboot
if [ ! -f "$configPath" ]; then
    touch $configPath
    update_config "afterReboot" 0
fi

. $configPath
if [[ "$afterReboot" -eq 1 ]]; then
    after_reboot
else
    before_reboot
fi
