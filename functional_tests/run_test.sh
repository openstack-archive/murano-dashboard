DEST=${DEST:-/opt/stack/new}
DASHBOARD_DIR=$DEST/murano-dashboard

function start_xvfb_session() {

    export VFB_DISPLAY_SIZE='1280x1024'
    export VFB_COLOR_DEPTH=16
    export VFB_DISPLAY_NUM=22

    export DISPLAY=:${VFB_DISPLAY_NUM}

    fonts_path="/usr/share/fonts/X11/misc/"

    # Start XVFB session
    sudo Xvfb -fp "${fonts_path}" "${DISPLAY}" -screen 0 "${VFB_DISPLAY_SIZE}x${VFB_COLOR_DEPTH}" &
}

function run_nosetests() {
    local tests=$*

    export NOSETESTS_CMD="$(which nosetests)"

    $NOSETESTS_CMD -s -v \
        --with-xunit \
        --xunit-file="$WORKSPACE/logs/test_report.xml" \
        $tests

}

function run_tests() {
    sudo rm -f /tmp/parser_table.py
    sudo pip install "selenium<3.0.0,>=2.50.1"
    sudo pip install "nose"
    sudo pip install "lxml"
    sudo pip install "jinja2"

    cd $DASHBOARD_DIR/muranodashboard/tests/functional

    run_nosetests sanity_check

}
