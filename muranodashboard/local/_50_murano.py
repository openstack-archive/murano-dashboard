from muranodashboard import exceptions

# The name of the dashboard to be added to HORIZON['dashboards']. Required.
DASHBOARD = 'murano'

# If set to True, this dashboard will not be added to the settings.
DISABLED = False

ADD_INSTALLED_APPS = [
    'muranodashboard',
]

ADD_EXCEPTIONS = {
    'recoverable': exceptions.RECOVERABLE,
    'not_found': exceptions.NOT_FOUND,
    'unauthorized': exceptions.UNAUTHORIZED,
}

ADD_JS_FILES = [
    'muranodashboard/js/murano.service.js',
    'muranodashboard/js/upload_form.js',
    'muranodashboard/js/import_bundle_form.js',
    'muranodashboard/js/more-less.js',
]
