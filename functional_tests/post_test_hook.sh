#!/bin/bash

XTRACE=$(set +o | grep xtrace)
set -o xtrace

DEST=${DEST:-/opt/stack/new}
DASHBOARD_DIR=$DEST/murano-dashboard

source $DASHBOARD_DIR/functional_tests/collect_results.sh
source $DASHBOARD_DIR/functional_tests/run_test.sh

echo "#Run murano-dashboard functional test"
set +e
start_xvfb_session
run_tests
EXIT_CODE=$?
set -e

echo "Collect the test results"
do_collect_results

echo "Kill Xvfb"
sudo pkill Xvfb

exit $EXIT_CODE

$XTRACE
