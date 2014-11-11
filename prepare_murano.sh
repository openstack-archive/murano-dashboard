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
# *** This script is used only for developer purpuses ***
# It adds murano plugin file to horizon and copies current horizon settings file
# to murano direcotory. Thats allows to debug Murano Dashboard with
# Django developer server.

DEBUGLVL=2
SCRIPT_DIR=$(cd $(dirname "$0") && pwd)
PLUGIN_FILE="_50_murano.py"

if [ "$DEBUGLVL" -eq 4 ]; then
    set -o xtrace
fi

function check_succsess {
    if [ $? -ne 0 ]; then
        log "...can't finish copy operation"
        exit 1
    else
        echo "...SUCCESS"
    fi
}

function insert_plugin {
    local dest=$1
    local src="${SCRIPT_DIR}/muranodashboard/local/${PLUGIN_FILE}"
    echo "Copying plugin file from $src to $dest"
    cp ${src} ${dest}

    check_succsess
}

function copy_config {
    local src="${1}/settings.py"
    local dest="${SCRIPT_DIR}/muranodashboard"
    echo "Copying settings file from $src to $dest"
    cp ${src} ${dest}

    check_succsess
}

###########################
# Main script starts here #
###########################

usage="
Please, provide ONE of the following parameters:
--openstack-dashboard | -o  Openstack-dashboard package root directory location
--dest                | -d  Path to copy murano dashboard file
"

if [ "$*" == "" ] || [ "$*" == "-h" ] || [ "$*" == "--help" ]; then
    echo "$usage"
    exit 1
fi

while [[ "$#" -gt 1 ]]
do
    key="$1"
    shift

    case "$key" in
        -o|--openstack-dashboard)
            DASHBOARD_LOCATION="$1"
            shift
            ;;
        -d|--dest)
            DEST="$1"
            shift
            ;;
        *)
            echo "$usage"
            exit 1
            ;;
    esac
done

if [ -n "$DEST" ] && [ -n "$DASHBOARD_LOCATION" ]; then
    echo "$usage"
    exit 1
fi

if [ -n "$DEST" ]; then
    if [ ! -d "$DEST" ]; then
        echo "Specified distanation path $DEST doesn't exist"
        exit 1
    fi
    SETTINGS_DIR="${DEST%/local*}"
fi

if [ -n "$DASHBOARD_LOCATION" ]; then

    lastchr="${DASHBOARD_LOCATION: -1}"
    if [ "$lastchr" = "/" ]; then
        echo "Removimg trailing space from specified path"
        DASHBOARD_LOCATION="${DASHBOARD_LOCATION::-1}"
    fi
    DEST="${DASHBOARD_LOCATION}/local/enabled"
    SETTINGS_DIR="${DASHBOARD_LOCATION}"
fi

insert_plugin ${DEST}
copy_config ${SETTINGS_DIR}

exit 0