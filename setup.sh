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
common_pkgs="wget git make gcc python-pip python-setuptools unzip ntpdate"
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
            find /var/lib/apt/lists/ -name "*cloud.archive*" | grep -q "icehouse_main"
            if [ $? -ne 0 ]; then
                # Ubuntu 14.04 already has icehouse repos.
                if [ $REV != "14.04" ]; then
                    add-apt-repository -y cloud-archive:icehouse >> $LOGFILE 2>&1
                    if [ $? -ne 0 ]; then
                        log "... can't enable \"cloud-archive:havana\", exiting !"
                        retval=1
                        return $retval
                    fi
                    apt-get update -y
                    apt-get upgrade -y -o Dpkg::Options::="--force-confnew"
                    log "..success"
                fi
            fi
            ;;
        "redhat")
            $(yum repolist | grep -qoE "epel") || rpm -ivh "http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm" >> $LOGFILE 2>&1
            $(yum repolist | grep -qoE "openstack-icehouse") || rpm -ivh "http://rdo.fedorapeople.org/openstack-icehouse/rdo-release-icehouse.rpm" >> $LOGFILE 2>&1
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

function find_horizon_config()
{
    retval=0
    for cfg_file in $(echo $HORIZON_CONFIGS | sed 's/,/ /')
    do
        if [ -e "$cfg_file" ]; then
            log "Horizon config found at \"$cfg_file\""
            if [ -z "$1" ]; then
                ./update_setting.sh --input=$cfg_file --cache-dir=$APPLICATION_CACHE_DIR --log-file="$APPLICATION_LOG_DIR/murano-dashboard.log"
                if [ $? -ne 0 ]; then
                    log "Updating config failed!"
                    return 1
                fi
            else
                ./update_setting.sh --input=$cfg_file -r
                if [ $? -ne 0 ]; then
                    log "Updating config failed!"
                    return 1
                fi
            fi
            return 0
        else
            log "Horizon settings file is not found '$cfg_file'"
            retval=1
        fi
    done
    if [ $retval -eq 1 ]; then
        log "Horizon config not found or openstack-dashboard does not installed, to override this set proper \"HORIZON_CONFIGS\" variable, exiting!!!"
        #exit 1
    fi
    return $retval
}

function save_symlinks_from_static_dir()
{
    # Save all symbolic links from openstack_dashboard/static dir
    #------------------------------------------------------------
    local currdir=$RUN_DIR
    cd $1/static

    rm -f .symlinks
    for f in $(find . -type l); do
        log $(printf "Saving symlink '%s' ...\n" $f)
        printf "%s\t%s\n" $f $(readlink $f) >> .symlinks
        rm -f $f
    done

    cd $currdir
    #------------------------------------------------------------
}

function restore_symlinks_from_static_dir()
{
    # Restore sympbolic links
    #------------------------
    local currdir=$RUN_DIR
    cd $1/static

    if [ ! -f .symlinks ]; then
        cd $currdir
        return
    fi

    while read name path; do
        log $(printf "Restoring symlink '%s' ...\n" $f)
            if [ -d "$name" ]; then
                rm -rf "$name"
            fi
            ln -s "$path" "$name"
    done < .symlinks

    rm -f .symlinks

    cd $currdir
    #------------------------
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
    save_symlinks_from_static_dir "$(dirname $horizon_manage)"
    _static_dirs="muranodashboard floppyforms"
    for _static_dir in $_static_dirs
    do
        _old_murano_static="$(dirname $horizon_manage)/static/$_static_dir"
        if [ -d "$_old_murano_static" ];then
            log "...$APPLICATION_NAME static for \"$_static_dir\" found under \"HORIZON\" STATIC, deleting \"$_old_murano_static\"..."
            rm -rf ${_old_murano_static}/*
            if [ $? -ne 0 ]; then
                log "...can't delete \"$_old_murano_static\, WARNING!!!"
            fi
        else
            mk_dir "$_old_murano_static" "$WEB_SERVICE_USER" "$WEB_SERVICE_GROUP" || exit $?
        fi
    done
    log "Rebuilding STATIC output will be recorded in \"$LOGFILE\""
    chmod a+rw $LOGFILE
    su -c "python $horizon_manage collectstatic --noinput >> $LOGFILE 2>&1" -s /bin/bash $WEB_SERVICE_USER
    if [ $? -ne 0 ]; then
        log "...\"$horizon_manage\" collectstatic failed, exiting!!!"
        retval=1
    else
        log "...success"
    fi
    restore_symlinks_from_static_dir "$(dirname $horizon_manage)"
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
    #small cleanup
    rm -rf /tmp/pip-build-*
    install_prerequisites || exit 1
    if [ -n "$1" ]; then
        #syncing clock
        log "Syncing clock..."
        ntpdate -u pool.ntp.org
        log "Continuing installation..."
    fi
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
SUB_COMMAND="$2"
case $COMMAND in
    install)
        rm -rf $LOGFILE
        log "Installing \"$APPLICATION_NAME\" to system..."
        if [ "$SUB_COMMAND" == "timesync" ]; then
            install_application $SUB_COMMAND || exit $?
        else
            install_application || exit $?
        fi
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
