#!/bin/bash
DEST=${DEST:-/opt/stack/new}
DASHBOARD_DIR=$DEST/murano-dashboard

source $DASHBOARD_DIR/functional_tests/env_pkg_prepare.sh

XTRACE=$(set +o | grep xtrace)
set -o xtrace

prepare_packages
sync

$XTRACE
