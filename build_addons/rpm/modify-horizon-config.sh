#!/bin/sh
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
#    helper script.

LOGLVL=1
APPLICATION_NAME="murano-dashboard"
APPLICATION_LOG_DIR="/var/log/murano"
APPLICATION_CACHE_DIR="/var/cache/$APPLICATION_NAME"
# Functions
# Loger function
log()
{
    MSG=$1
    if [ $LOGLVL -gt 0 ]; then
        echo "LOG:> $MSG"
    fi
}


# patching horizon configuration

modify_horizon_config()
{
    INFILE=$1
    REMOVE=$2
    PATTERN='from openstack_dashboard import policy'
    TMPFILE="/tmp/tmpfile"
    if [ -f $INFILE ]; then
        lines=$(sed -ne '/^#START_MURANO_DASHBOARD/,/^#END_MURANO_DASHBOARD/ =' $INFILE)
        if [ -n "$lines" ]; then
            if [ ! -z $REMOVE ]; then
                log "Removing $APPLICATION_NAME data from \"$INFILE\"..."
                sed -e '/^#START_MURANO_DASHBOARD/,/^#END_MURANO_DASHBOARD/ d' -i $INFILE
                if [ $? -ne 0 ];then
                    log "...can't modify \"$INFILE\", check permissions or something else, exiting!!!"
                    exit 1
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
        exit 1
    fi
}

# Command line args'
COMMAND="$1"
cfg_file="/usr/share/openstack-dashboard/openstack_dashboard/settings.py"
case $COMMAND in
    install )
        modify_horizon_config $cfg_file
        ;;

    uninstall )
        modify_horizon_config $cfg_file remove
        ;;

    *)
        exit 1
        ;;
esac
