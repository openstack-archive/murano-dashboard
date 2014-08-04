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

SCRIPT_DIR=$(cd $(dirname "$0") && pwd)
INC_FILE="$SCRIPT_DIR/common.inc"
if [ -f "$INC_FILE" ]; then
    source "$INC_FILE"
else
    log "Can't load \"$INC_FILE\" or file not found, exiting!"
    exit 1
fi
LOGFILE="/tmp/murano_settings_update_run.log"

function modify_horizon_config()
{
    local config_file=$1

    if [ "$REMOVE" = true ]; then
        log "Removing Murano data from \"$config_file\" "
        sed -e '/^#START_MURANO_DASHBOARD/,/^#END_MURANO_DASHBOARD/ d' -i $config_file
        if [ $? -ne 0 ]; then
            log "...can't modify \"$config_file\", check permissions or something else, exiting!!!"
            exit 1
        else
            log "...SUCCESS"
        fi
    else
        if grep -q '#START_MURANO_DASHBOARD' "$config_file"; then
            log "\"$config_file\" already has Murano data, you can change it manually and restart apache2/httpd service"
            return
        fi

        local updated_data=$(mktemp)
        log "Creating \"$updated_data\" temprorary file to compose Murano Data"
        # Start to compose Murano data
        cat << EOF >> "$updated_data"
#START_MURANO_DASHBOARD
HORIZON_CONFIG['dashboards'] += ('murano',)
INSTALLED_APPS += ('muranodashboard', 'floppyforms',)
MIDDLEWARE_CLASSES += ('muranodashboard.middleware.ExceptionMiddleware',)
#NETWORK_TOPOLOGY = 'routed'
#MURANO_API_URL = 'http://localhost:8082'
#if murano-api is set up with ssl, uncomment next strings
#MURANO_API_INSECURE = True
MAX_FILE_SIZE_MB = 5
EOF
        if [ -n "$DASHBOARD_LOG_FILE" ]; then
            cat << EOF >> "$updated_data"
verbose_formatter = {'verbose': {'format': '[%(asctime)s] [%(levelname)s] [pid=%(process)d] %(message)s'}}
if 'formatters' in LOGGING: LOGGING['formatters'].update(verbose_formatter)
else: LOGGING['formatters'] = verbose_formatter
LOGGING['handlers']['murano-file'] = {'level': 'DEBUG', 'formatter': 'verbose', 'class': 'logging.FileHandler', 'filename': '$DASHBOARD_LOG_FILE'}
LOGGING['loggers']['muranodashboard'] = {'handlers': ['murano-file'], 'level': 'DEBUG'}
LOGGING['loggers']['muranoclient'] = {'handlers': ['murano-file'], 'level': 'ERROR'}
EOF
        fi

        if [ -n "$CACHE_DIR" ]; then
            cat << EOF >> "$updated_data"
METADATA_CACHE_DIR = "$CACHE_DIR"
EOF
        fi

        # End composing murano data
        cat << EOF >> "$updated_data"
#END_MURANO_DASHBOARD
EOF
        log "The following data will be added to the config: $(cat $updated_data)"
        log "Adding Murano data to \"$config_file\" "
        cat "$updated_data" >> "$config_file"
        if [ $? -ne 0 ];then
            log "Can't modify \"$config_file\", check permissions or something else, exiting!!!"
            exit 1
        else
            log "Deleting \"$updated_data\""
            rm "$updated_data"
            log "...SUCCESS"
        fi
    fi
    exit 0
}

###########################
# Main script starts here #
###########################

REMOVE=false
TAG="master"

for i in "$@"
do

    #Replace tilde, used in a path to the file, represented as a string
    i="${i/\~/$HOME}"

    case $i in
            -i=*|--input=*)
            INPUT="${i#*=}"
            shift
            ;;
            -o=*|--output=*)
            OUTPUT="${i#*=}"
            shift
            ;;
            -l=*|--log-file=*)
            DASHBOARD_LOG_FILE="${i#*=}"
            shift
            ;;
            -c=*|--cache-dir=*)
            CACHE_DIR="${i#*=}"
            shift
            ;;
            -t=*|--tag=*)
            TAG="${i#*=}"
            shift
            ;;
            -r|--remove)
            REMOVE=true
            shift
            ;;
            *)
                    # unknown option
            ;;
    esac
done

if [ -z "$INPUT" ] && [ -z "$OUTPUT" ]; then
    log "\nPlease, provide:\n
 --input={PATH}          to add Murano settings to the existing file\n
 --output={PATH}         for the result file \n
 --log-file={FILE_NAME}  to use separate file for murano-dashboard logging\n
 --cache-dir={PATH}      cache directory, default is '/tmp/muranodashboard-cache'\n
 --remove                remove murano data from the specified settings file
         "
    exit 1
fi

if [ -n "$OUTPUT" ] && [ -n "$INPUT" ]; then
    log "Copying input file for further modification"
    cp $INPUT $OUTPUT
fi

if [ -n "$INPUT" ] && [ ! -f "$INPUT" ]; then
    log "Updating file doen't exist"
    exit 1
fi

if [ -z "$OUTPUT" ] && [ -n "$INPUT" ]; then
    OUTPUT=$INPUT
fi

if [ -z "$INPUT" ]; then
    log "Downloading updated horizon config"
    settings="https://raw.githubusercontent.com/openstack/horizon/$TAG/openstack_dashboard/settings.py"
    wget -q -O $OUTPUT $settings
    if [ $? -ne 0 ];then
        log "Unable to download horizon settings file from $settings"
        exit 1
     fi
fi

modify_horizon_config $OUTPUT

exit 0
