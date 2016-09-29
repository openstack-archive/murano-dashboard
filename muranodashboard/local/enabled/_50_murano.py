#  Licensed under the Apache License, Version 2.0 (the "License"); you may
#  not use this file except in compliance with the License. You may obtain
#  a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#  License for the specific language governing permissions and limitations
#  under the License.

from muranodashboard import exceptions

# The name of the dashboard to be added to HORIZON['dashboards']. Required.
DASHBOARD = 'app-catalog'

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
    'muranodashboard/js/upload_form.js',
    'muranodashboard/js/import_bundle_form.js',
    'muranodashboard/js/murano.service.js',
    'muranodashboard/js/more-less.js',
]
