DEST=${DEST:-/opt/stack/new}
DASHBOARD_DIR=$DEST/murano-dashboard

function create_artifacts_dir() {
    dst="${WORKSPACE}/logs/artifacts"
    mkdir -p "${dst}"
}

function collect_screenshots() {
    # Copy screenshots for failed tests
    if [[ -d "$DASHBOARD_DIR/muranodashboard/tests/functional/screenshots/" ]]; then
        mkdir -p "${WORKSPACE}/logs/artifacts/screenshots"
        cp -Rv $DASHBOARD_DIR/muranodashboard/tests/functional/screenshots/* "${WORKSPACE}/logs/artifacts/screenshots/"
    fi
}

function generate_html_report() {
    local xml_report="${WORKSPACE}/logs/test_report.xml"
    local html_report="${WORKSPACE}/logs/test_report.html"

    if [[ -f "${WORKSPACE}/logs/test_report.xml" ]]; then
        $(which python3) "$DASHBOARD_DIR/functional_tests/generate_html_report.py" "${xml_report}" "${html_report}"
        cp "${html_report}" "${WORKSPACE}/index.html"
    fi
}

function do_collect_results() {
    create_artifacts_dir
    collect_screenshots
    generate_html_report
}
