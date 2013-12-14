#!/bin/sh
#    Copyright (c) 2013 Mirantis, Inc.
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
#    CentOS script.

LOGLVL=1
LOG_DIR="/var/log/murano"
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
modify_horizon_config() {
        REMOVE=$2
        if [ -f $1 ]; then
        lines=$(sed -ne '/^#START_MURANO_DASHBOARD/,/^#END_MURANO_DASHBOARD/ =' $1)
        if [ -n "$lines" ]; then
                if [ ! -z $REMOVE ]; then
                        log "Removing our data from \"$1\"..."
                        sed -e '/^#START_MURANO_DASHBOARD/,/^#END_MURANO_DASHBOARD/ d' -i $1
                        if [ $? -ne 0 ];then
                                log "Can't modify \"$1\", check permissions or something else, exiting!!!"
                                exit
                        fi
                else
                        log "\"$1\" already has our data, you can change it manually and restart apache2 service"
                fi
        else
                if [ -z $REMOVE ];then
                        log "Adding our data into \"$1\"..."
                        cat >> $1 << EOF
#START_MURANO_DASHBOARD
HORIZON_CONFIG['dashboards'] += ('murano',)
INSTALLED_APPS += ('muranodashboard','floppyforms',)
MIDDLEWARE_CLASSES += ('muranodashboard.middleware.ExceptionMiddleware',)
verbose_formatter = {'verbose': {'format': '[%(asctime)s] [%(levelname)s] [pid=%(process)d] %(message)s'}}
if 'formatters' in LOGGING: LOGGING['formatters'].update(verbose_formatter)
else: LOGGING['formatters'] = verbose_formatter
LOGGING['handlers']['murano-file'] = {'level': 'DEBUG', 'formatter': 'verbose', 'class': 'logging.FileHandler', 'filename': '$LOG_DIR/murano-dashboard.log'}
LOGGING['loggers']['muranodashboard'] = {'handlers': ['murano-file'], 'level': 'DEBUG'}
LOGGING['loggers']['muranoclient'] = {'handlers': ['murano-file'], 'level': 'ERROR'}
#MURANO_API_URL = "http://localhost:8082"
#MURANO_METADATA_URL = "http://localhost:8084"
#if murano-api set up with ssl uncomment next strings
#MURANO_API_INSECURE = True
#END_MURANO_DASHBOARD
EOF
                        if [ $? -ne 0 ];then
                                log "Can't modify \"$1\", check permissions or something else, exiting!!!"
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

	* )
  	  exit 1
	;;
esac
