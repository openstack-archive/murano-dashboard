#!/bin/bash
#    Copyright (c) 2014 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.
#
RUN_DIR=$(cd $(dirname "$0") && pwd)
INC_FILE="$RUN_DIR/common.inc"
if [ -f "$INC_FILE" ]; then
    source "$INC_FILE"
else
    echo "Can't load \"$INC_FILE\" or file not found, exiting!"
    exit 1
fi
#
WEB_SERVICE_SYSNAME=${WEB_SERVICE_SYSNAME:-httpd}
WEB_SERVICE_USER=${WEB_SERVICE_USER:-apache}
WEB_SERVICE_GROUP=${WEB_SERVICE_GROUP:-apache}
APPLICATION_NAME="murano-dashboard"
APPLICATION_LOG_DIR="/var/log/$APPLICATION_NAME"
APPLICATION_CACHE_DIR="/var/cache/$APPLICATION_NAME"
APPLICATION_DB_DIR="/var/lib/openstack-dashboard"
LOGFILE="/tmp/${APPLICATION_NAME}_install.log"
HORIZON_CONFIGS="/opt/stack/horizon/openstack_dashboard/settings.py,/usr/share/openstack-dashboard/openstack_dashboard/settings.py"
common_pkgs="wget git make gcc python-pip python-setuptools unzip"
# Distro-specific package namings
debian_pkgs="python-dev python-mysqldb libxml2-dev libxslt1-dev libffi-dev mysql-client memcached apache2 libapache2-mod-wsgi openstack-dashboard"
redhat_pkgs="python-devel MySQL-python libxml2-devel libxslt-devel libffi-devel mysql memcached httpd python-memcached mod_wsgi openstack-dashboard python-netaddr"
#
get_os
eval req_pkgs="\$$(lowercase $DISTRO_BASED_ON)_pkgs"
REQ_PKGS="$common_pkgs $req_pkgs"

function install_prerequisites()
{
    retval=0
    _dist=$(lowercase $DISTRO_BASED_ON)
    log "Adding Extra repos, updating..."
    case $_dist in
        "debian")
            find_or_install "python-software-properties"
            if [ $? -eq 1 ]; then
                retval=1
                return $retval
            fi
            find /var/lib/apt/lists/ -name "*cloud.archive*" | grep -q "havana_main"
            if [ $? -ne 0 ]; then
                add-apt-repository -y cloud-archive:havana >> $LOGFILE 2>&1
                if [ $? -ne 0 ]; then
                    log "... can't enable \"cloud-archive:havana\", exiting !"
                    retval=1
                    return $retval
                fi
                apt-get update -y
                apt-get upgrade -y
                log "..success"
            fi
            ;;
        "redhat")
            $(yum repolist | grep -qoE "epel") || rpm -ivh "http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm" >> $LOGFILE 2>&1
            $(yum repolist | grep -qoE "openstack-havana") || rpm -ivh "http://rdo.fedorapeople.org/openstack-havana/rdo-release-havana.rpm" >> $LOGFILE 2>&1
            if [ $? -ne 0 ]; then
                log "... can't enable EPEL6 or RDO, exiting!"
                retval=1
                return $retval
            fi
            yum --quiet makecache
            log "..success"
            ;;
    esac
    for pack in $REQ_PKGS
    do
        find_or_install "$pack"
        if [ $? -eq 1 ]; then
            retval=1
            break
        else
            retval=0
        fi
    done
    return $retval
}
function make_tarball()
{
    retval=0
    log "Preparing tarball package..."
    setuppy="$RUN_DIR/setup.py"
    if [ -e "$setuppy" ]; then
        chmod +x $setuppy
        rm -rf $RUN_DIR/*.egg-info
        cd $RUN_DIR && python $setuppy egg_info > /dev/null 2>&1
        if [ $? -ne 0 ];then
            log "...\"$setuppy\" egg info creation fails, exiting!!!"
            retval=1
            exit 1
        fi
        rm -rf $RUN_DIR/dist/*
        log "...\"setup.py sdist\" output will be recorded in \"$LOGFILE\""
        cd $RUN_DIR && $setuppy sdist >> $LOGFILE 2>&1
        if [ $? -ne 0 ];then
            log "...\"$setuppy\" tarball creation fails, exiting!!!"
            retval=1
            exit 1
        fi
        #TRBL_FILE=$(basename $(ls $RUN_DIR/dist/*.tar.gz | head -n 1))
        TRBL_FILE=$(ls $RUN_DIR/dist/*.tar.gz | head -n 1)
        if [ ! -e "$TRBL_FILE" ]; then
            log "...tarball not found, exiting!"
            retval=1
        else
            log "...success, tarball created as \"$TRBL_FILE\""
            retval=0
        fi
    else
        log "...\"$setuppy\" not found, exiting!"
        retval=1
    fi
    return $retval
}
function run_pip_install()
{
    find_pip
    retval=0
    tarball_file=${1:-$TRBL_FILE}
    log "Running \"$PIPCMD install $PIPARGS $tarball_file\" output will be recorded in \"$LOGFILE\""
    $PIPCMD install $PIPARGS $tarball_file >> $LOGFILE 2>&1
    if [ $? -ne 0 ]; then
        log "...pip install fails, exiting!"
        retval=1
        exit 1
    fi
    return $retval
}
modify_horizon_config()
{
    INFILE=$1
    REMOVE=$2
    PATTERN='from openstack_dashboard import policy'
    TMPFILE="./tmpfile"
    retval=0
    if [ -f $INFILE ]; then
        lines=$(sed -ne '/^#START_MURANO_DASHBOARD/,/^#END_MURANO_DASHBOARD/ =' $INFILE)
        if [ -n "$lines" ]; then
            if [ ! -z $REMOVE ]; then
                log "Removing $APPLICATION_NAME data from \"$INFILE\"..."
                sed -e '/^#START_MURANO_DASHBOARD/,/^#END_MURANO_DASHBOARD/ d' -i $INFILE
                if [ $? -ne 0 ];then
                    log "...can't modify \"$INFILE\", check permissions or something else, exiting!!!"
                    retval=1
                    return $retval
                else
                    log "...success"
                fi
            else
                log "\"$INFILE\" already has $APPLICATION_NAME data, you can change it manually and restart apache2/httpd service"
            fi
        else
            if [ -z "$REMOVE" ]; then
                log "Adding $APPLICATION_NAME data to \"$INFILE\"..."
                rm -f $TMPFILE
                cat >> $TMPFILE << EOF
#START_MURANO_DASHBOARD
#TODO: should remove the next line once https://bugs.launchpad.net/ubuntu/+source/horizon/+bug/1243187 is fixed
LOGOUT_URL = '/horizon/auth/logout/'
METADATA_CACHE_DIR = '$APPLICATION_CACHE_DIR'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join('$APPLICATION_DB_DIR', 'openstack-dashboard.sqlite')
    }
}
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
HORIZON_CONFIG['dashboards'] += ('murano',)
INSTALLED_APPS += ('muranodashboard','floppyforms',)
MIDDLEWARE_CLASSES += ('muranodashboard.middleware.ExceptionMiddleware',)
verbose_formatter = {'verbose': {'format': '[%(asctime)s] [%(levelname)s] [pid=%(process)d] %(message)s'}}
if 'formatters' in LOGGING: LOGGING['formatters'].update(verbose_formatter)
else: LOGGING['formatters'] = verbose_formatter
LOGGING['handlers']['murano-file'] = {'level': 'DEBUG', 'formatter': 'verbose', 'class': 'logging.FileHandler', 'filename': '$APPLICATION_LOG_DIR/murano-dashboard.log'}
LOGGING['loggers']['muranodashboard'] = {'handlers': ['murano-file'], 'level': 'DEBUG'}
LOGGING['loggers']['muranoclient'] = {'handlers': ['murano-file'], 'level': 'ERROR'}
ADVANCED_NETWORKING_CONFIG = {'max_environments': 100, 'max_hosts': 250, 'env_ip_template': '10.0.0.0'}
NETWORK_TOPOLOGY = 'routed'
#MURANO_API_URL = "http://localhost:8082"
#MURANO_METADATA_URL = "http://localhost:8084/v1"
#if murano-api set up with ssl uncomment next strings
#MURANO_API_INSECURE = True
#END_MURANO_DASHBOARD
EOF
            sed -ne "/$PATTERN/r  $TMPFILE" -e 1x  -e '2,${x;p}' -e '${x;p}' -i $INFILE
            if [ $? -ne 0 ];then
                log "Can't modify \"$INFILE\", check permissions or something else, exiting!!!"
            else
                rm -f $TMPFILE
                log "...success"
            fi
        fi
    fi
    else
        echo "File \"$1\" not found, exiting!!!"
        retval=1
    fi
    return $retval
}
function find_horizon_config()
{
    retval=0
    for cfg_file in $(echo $HORIZON_CONFIGS | sed 's/,/ /')
    do
        if [ -e "$cfg_file" ]; then
            log "Horizon config found at \"$cfg_file\""
            modify_horizon_config $cfg_file $1
            retval=0
            break
        else
            retval=1
        fi
    done
    if [ $retval -eq 1 ]; then
        log "Horizon config not found or openstack-dashboard does not installed, to override this set proper \"HORIZON_CONFIGS\" variable, exiting!!!"
        #exit 1
    fi
    return $retval
}

function prepare_db()
{
    horizon_manage=$1
    retval=0
    log "Creating db for storing sessions..."
    #python $horizon_manage syncdb --noinput
    su -c "python $horizon_manage syncdb --noinput >> $LOGFILE 2>&1" -s /bin/bash $WEB_SERVICE_USER
    if [ $? -ne 0 ]; then
        log "...\"$horizon_manage\" syncdb failed, exiting!!!"
        retval=1
    else
        log "..success"
    fi
    return $retval
}
function rebuildstatic()
{
    retval=0
    _dist=$(lowercase $DISTRO_BASED_ON)
    log "Running collectstatic..."
    case $_dist in
        "debian")
            horizon_manage=$(dpkg-query -L openstack-dashboard | grep -E "*manage.py$")
            ;;
        "redhat")
            horizon_manage=$(rpm -ql openstack-dashboard | grep -E "*manage.py$")
            ;;
    esac
    if [ -z "$horizon_manage" ]; then
        log "...openstack-dashboard manage.py not found, exiting!!!"
        retval=1
        return $retval
    fi
    _old_murano_static="$(dirname $horizon_manage)/openstack_dashboard/static/muranodashboard"
    if [ -d "$_old_murano_static" ];then
        log "...$APPLICATION_NAME static for \"muranodashboard\" found under \"HORIZON\" STATIC, deleting \"$_old_murano_static\"..."
        rm -rf $_old_murano_static
        if [ $? -ne 0 ]; then
            log "...can't delete \"$_old_murano_static\, WARNING!!!"
        fi
    fi
    log "Rebuilding STATIC output will be recorded in \"$LOGFILE\""
    #python $horizon_manage collectstatic --noinput >> $LOGFILE 2>&1
    chmod a+rw $LOGFILE
    su -c "python $horizon_manage collectstatic --noinput >> $LOGFILE 2>&1" -s /bin/bash $WEB_SERVICE_USER
    if [ $? -ne 0 ]; then
        log "...\"$horizon_manage\" collectstatic failed, exiting!!!"
        retval=1
    else
        log "...success"
    fi
    prepare_db "$horizon_manage" || retval=$?
    return $retval
}
function run_pip_uninstall()
{
    find_pip
    retval=0
    pack_to_del=$(is_py_package_installed "$APPLICATION_NAME")
    if [ $? -eq 0 ]; then
        log "Running \"$PIPCMD uninstall $PIPARGS $APPLICATION_NAME\" output will be recorded in \"$LOGFILE\""
        $PIPCMD uninstall $pack_to_del --yes >> $LOGFILE 2>&1
        if [ $? -ne 0 ]; then
            log "...can't uninstall $APPLICATION_NAME with $PIPCMD"
            retval=1
        else
            log "...success"
        fi
    else
        log "Python package for \"$APPLICATION_NAME\" not found"
    fi
    return $retval
}
function install_application()
{
    install_prerequisites || exit 1
    make_tarball || exit $?
    run_pip_install || exit $?
    log "Configuring HORIZON..."
    find_horizon_config || exit $?
    _dist=$(lowercase $DISTRO_BASED_ON)
    log "Configuring system..."
    case $_dist in
        "debian")
            WEB_SERVICE_SYSNAME="apache2"
            WEB_SERVICE_USER="horizon"
            WEB_SERVICE_GROUP="horizon"
            dpkg --purge openstack-dashboard-ubuntu-theme
            ;;
        "redhat")
            WEB_SERVICE_SYSNAME="httpd"
            WEB_SERVICE_USER="apache"
            WEB_SERVICE_GROUP="apache"
            log "Disabling firewall and selinux..."
            service iptables stop
            chkconfig iptables off
            setenforce 0
            iniset '' 'SELINUX' 'permissive' '/etc/selinux/config'
            chkconfig $WEB_SERVICE_SYSNAME on
            ;;
    esac
    log "Creating required directories..."
    mk_dir "$APPLICATION_LOG_DIR" "$WEB_SERVICE_USER" "$WEB_SERVICE_GROUP" || exit $?
    mk_dir "$APPLICATION_CACHE_DIR" "$WEB_SERVICE_USER" "$WEB_SERVICE_GROUP" || exit $?
    horizon_etc_cfg=$(find /etc/openstack-dashboard -name "local_setting*" | head -n 1)
     if [ $? -ne 0 ]; then
        log "Can't find horizon config under \"/etc/openstack-dashboard...\""
        retval=1
    else
        iniset '' 'ALLOWED_HOSTS' "'*'" $horizon_etc_cfg
        iniset '' 'DEBUG' 'True' $horizon_etc_cfg
    fi
    return $retval
}
function uninstall_application()
{
    run_pip_uninstall || exit $?
    find_horizon_config remove || exit $?
}

function postinst()
{
    rebuildstatic || exit $?
    sleep 2
    chown -R $WEB_SERVICE_USER:$WEB_SERVICE_GROUP /var/lib/openstack-dashboard
    service $WEB_SERVICE_SYSNAME restart
}
function postuninst()
{
    _dist=$(lowercase $DISTRO_BASED_ON)
    case $_dist in
        "debian")
            WEB_SERVICE_SYSNAME="apache2"
            ;;
        "redhat")
            WEB_SERVICE_SYSNAME="httpd"
            ;;
    esac
    service $WEB_SERVICE_SYSNAME restart
}
# Command line args'
COMMAND="$1"
case $COMMAND in
    install)
        rm -rf $LOGFILE
        log "Installing \"$APPLICATION_NAME\" to system..."
        install_application || exit $?
        postinst || exit $?
        log "...success"
        ;;

    uninstall )
        log "Uninstalling \"$APPLICATION_NAME\" from system..."
        uninstall_application || exit $?
        postuninst
        log "Software uninstalled, application logs located at \"$APPLICATION_LOG_DIR\", cache files - at \"$APPLICATION_CACHE_DIR'\" ."
        ;;

    * )
        echo -e "Usage: $(basename "$0") [command] \nCommands:\n\tinstall - Install \"$APPLICATION_NAME\" software\n\tuninstall - Uninstall \"$APPLICATION_NAME\" software"
        exit 1
        ;;
esac