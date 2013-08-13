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
#    Ubuntu script.

LOGLVL=1
SERVICE_CONTENT_DIRECTORY=`cd $(dirname "$0") && pwd`
DJBLETS_ZIP_URL=https://github.com/tsufiev/djblets/archive
PREREQ_PKGS="wget make git python-pip python-dev python-mysqldb libxml2-dev libxslt-dev unzip"
SERVICE_SRV_NAME="murano-dashboard"
GIT_CLONE_DIR=`echo $SERVICE_CONTENT_DIRECTORY | sed -e "s/$SERVICE_SRV_NAME//"`
HORIZON_CONFIGS="/opt/stack/horizon/openstack_dashboard/settings.py,/usr/share/openstack-dashboard/openstack_dashboard/settings.py"

# Functions
# Loger function
log()
{
	MSG=$1
	if [ $LOGLVL -gt 0 ]; then
		echo "LOG:> $MSG"
	fi
}

# Check or install package
in_sys_pkg()
{
	PKG=$1
	dpkg -s $PKG > /dev/null 2>&1
	if [ $? -eq 0 ]; then
	    log "Package \"$PKG\" already installed"
	else
		log "Installing \"$PKG\"..."
		apt-get install $PKG --yes > /dev/null 2>&1
		if [ $? -ne 0 ];then
			log "installation fails, exiting!!!"
			exit
		fi
	fi
}

# git clone
gitclone()
{
	FROM=$1
	CLONEROOT=$2
	log "Cloning from \"$FROM\" repo to \"$CLONEROOT\""
	cd $CLONEROOT && git clone $FROM > /dev/null 2>&1
	if [ $? -ne 0 ];then
	    log "cloning from \"$FROM\" fails, exiting!!!"
	    exit
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
			log "\"$1\" already has our data, you can change it manualy and restart apache2 service"
		fi
	else
		if [ -z $REMOVE ];then
			log "Adding our data into \"$1\"..."
			cat >> $1 << "EOF"
#START_MURANO_DASHBOARD
from muranoclient.common import exceptions as muranoclient
RECOVERABLE_EXC = (muranoclient.HTTPException,
                   muranoclient.CommunicationError,
                   muranoclient.Forbidden)
EXTENDED_RECOVERABLE_EXCEPTIONS = tuple(
    exceptions.RECOVERABLE + RECOVERABLE_EXC)
NOT_FOUND_EXC = (muranoclient.HTTPNotFound, muranoclient.EndpointNotFound)
EXTENDED_NOT_FOUND_EXCEPTIONS = tuple(exceptions.NOT_FOUND + NOT_FOUND_EXC)
UNAUTHORIZED_EXC = (muranoclient.HTTPUnauthorized, )
EXTENDED_UNAUTHORIZED_EXCEPTIONS = tuple(exceptions.UNAUTHORIZED + UNAUTHORIZED_EXC)
HORIZON_CONFIG['exceptions']['recoverable'] = EXTENDED_RECOVERABLE_EXCEPTIONS
HORIZON_CONFIG['exceptions']['not_found'] = EXTENDED_NOT_FOUND_EXCEPTIONS
HORIZON_CONFIG['exceptions']['unauthorized'] = EXTENDED_UNAUTHORIZED_EXCEPTIONS
HORIZON_CONFIG['customization_module'] = 'muranodashboard.panel.overrides'
INSTALLED_APPS += ('muranodashboard','djblets','djblets.datagrid','djblets.util','floppyforms',)
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

# searching horizon configuration
find_horizon_config()
{
	FOUND=0
	for cfg_file in $(echo $HORIZON_CONFIGS | sed 's/,/ /' )
	do
		if [ -e $cfg_file ];then
			log "Horizon config found at \"$cfg_file\""
			modify_horizon_config $cfg_file $1
			FOUND=1
		fi
	done
	if [ $FOUND -eq 0 ];then
		log "Horizon config not found or openstack-dashboard does not installed, to override this set proper \"HORIZON_CONFIGS\" variable, exiting!!!"
		exit 1
	fi
}

# install
inst()
{
CLONE_FROM_GIT=$1
# Checking packages
	for PKG in $PREREQ_PKGS
	do
		in_sys_pkg $PKG
	done 

# If clone from git set
	if [ ! -z $CLONE_FROM_GIT ]; then
# Preparing clone root directory
	if [ ! -d $GIT_CLONE_DIR ];then
		log "Creting $GIT_CLONE_DIR direcory..."
		mkdir -p $GIT_CLONE_DIR
		if [ $? -ne 0 ];then
			log "Can't create $GIT_CLONE_DIR, exiting!!!" 
			exit
		fi
	fi
# Cloning from GIT
		GIT_WEBPATH_PRFX="https://github.com/stackforge/"
		gitclone "$GIT_WEBPATH_PRFX$SERVICE_SRV_NAME.git" $GIT_CLONE_DIR
# End clone from git section 
	fi

# Setupping...
	log "Running setup.py"
	#MRN_CND_SPY=$GIT_CLONE_DIR/$SERVICE_SRV_NAME/setup.py
	MRN_CND_SPY=$SERVICE_CONTENT_DIRECTORY/setup.py
	if [ -e $MRN_CND_SPY ]; then
		chmod +x $MRN_CND_SPY
		log "$MRN_CND_SPY output:_____________________________________________________________"		
## Setup through pip
		# Creating tarball
		rm -rf $SERVICE_CONTENT_DIRECTORY/*.egg-info
		cd $SERVICE_CONTENT_DIRECTORY && python $MRN_CND_SPY egg_info
                if [ $? -ne 0 ];then
                        log "\"$MRN_CND_SPY\" egg info creation FAILS, exiting!!!"
                        exit 1
                fi
                rm -rf $SERVICE_CONTENT_DIRECTORY/dist
		cd $SERVICE_CONTENT_DIRECTORY && python $MRN_CND_SPY sdist
		if [ $? -ne 0 ];then
			log "\"$MRN_CND_SPY\" tarball creation FAILS, exiting!!!"
			exit 1
		fi
		# Running tarball install
		TRBL_FILE=$(basename `ls $SERVICE_CONTENT_DIRECTORY/dist/*.tar.gz`)
		pip install $SERVICE_CONTENT_DIRECTORY/dist/$TRBL_FILE
		if [ $? -ne 0 ];then
			log "pip install \"$TRBL_FILE\" FAILS, exiting!!!"
			exit 1
		fi
		# DJBLETS INSTALL START
                DJBLETS_SUFFIX=master.zip
                DJBLETS_OUTARCH_FILENAME=djblets-$DJBLETS_SUFFIX
		cd $SERVICE_CONTENT_DIRECTORY/dist && wget $DJBLETS_ZIP_URL/$DJBLETS_SUFFIX -O $DJBLETS_OUTARCH_FILENAME
                if [ $? -ne 0 ];then
                        log " Can't download \"$DJBLETS_OUTARCH_FILENAME\", exiting!!!"
                        exit 1
                fi
		cd $SERVICE_CONTENT_DIRECTORY/dist && unzip $DJBLETS_OUTARCH_FILENAME
                if [ $? -ne 0 ];then
                        log " Can't unzip \"$SERVICE_CONTENT_DIRECTORY/dist/$DJBLETS_OUTARCH_FILENAME\", exiting!!!"
                        exit 1
                fi
		cd $SERVICE_CONTENT_DIRECTORY/dist/djblets-master && python setup.py install
		if [ $? -ne 0 ]; then
			log "\"$SERVICE_CONTENT_DIRECTORY/dist/djblets-master/setup.py\" python setup FAILS, exiting!"
			exit 1
		fi
		# DJBLETS INSTALL END
	else
		log "$MRN_CND_SPY not found!"
	fi
}

# uninstall
uninst()
{
	# Uninstall trough  pip
	# looking up for python package installed
	PYPKG=`echo $SERVICE_SRV_NAME | tr -d '-'`
	pip freeze | grep $PYPKG
	if [ $? -eq 0 ]; then
		log "Removing package \"$PYPKG\" with pip"
		pip uninstall $PYPKG --yes
	else
		log "Python package \"$PYPKG\" not found"
	fi
}
# preinstall
preinst()
{
# check openstack-dashboard installed from system packages
	_PKG=openstack-dashboard
	dpkg -s $_PKG > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            log "Package \"$_PKG\" is not installed."
	fi
# python-muranoclient	
	_PREREQ=muranoclient
	pip freeze | grep $_PREREQ
	if [ $? -ne 0 ]; then
                log "\"$_PREREQ\" package not found, please install it first (\"https://github.com/stackforge/python-muranoclient\"), exiting!!!"
                exit 1
	else
		log "\"$_PREREQ\" found, doing next steps...."
        fi
}

# rebuild static
rebuildstatic()
{
    horizon_manage=$(dpkg-query -L openstack-dashboard | grep -E "*manage.py$")
    if [ $? -ne 0 ]; then
	log "openstack-dashboard manage.py not found, exiting!!!"
	exit 1
    fi
    log "Rebuilding STATIC...."
    python $horizon_manage collectstatic --noinput
    if [ $? -ne 0 ]; then
	log "\"$horizon_manage\" collectstatic failed, exiting!!!"
	exit 1
    fi
}
    
# postinstall
postinst()
{
        rebuildstatic
	sleep 2
	service apache2 restart
}
# Command line args'
COMMAND="$1"
case $COMMAND in
	testinstall )
		find_horizon_config
		;;

        testuninstall )
                find_horizon_config remove
                ;;

	install )
		preinst
		inst
		find_horizon_config
		postinst
		;;

	installfromgit )
		preinst
		inst "yes"
		find_horizon_config
		postinst
		;;

	uninstall )
		log "Uninstalling \"$SERVICE_SRV_NAME\" from system..."
		uninst
		find_horizon_config remove
		service apache2 restart
		;;

	* )
		echo "Usage: $(basename "$0") command \nCommands:\n\tinstall - Install $SERVICE_SRV_NAME software\n\tuninstall - Uninstall $SERVICE_SRV_NAME software"
		exit 1
		;;
esac

