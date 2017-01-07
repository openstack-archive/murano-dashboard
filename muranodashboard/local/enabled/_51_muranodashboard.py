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

ADD_INSTALLED_APPS = [
    'muranodashboard',
]

ADD_EXCEPTIONS = {
    'recoverable': exceptions.RECOVERABLE,
    'not_found': exceptions.NOT_FOUND,
    'unauthorized': exceptions.UNAUTHORIZED,
}

ADD_ANGULAR_MODULES = ['horizon.app.murano']

ADD_JS_FILES = [
    'muranodashboard/js/upload_form.js',
    'muranodashboard/js/import_bundle_form.js',
    'muranodashboard/js/more-less.js',
    'app/murano/murano.service.js',
    'app/murano/murano.module.js',
    'muranodashboard/js/add-select.js',
    'muranodashboard/js/draggable-components.js',
    'muranodashboard/js/environments-in-place.js',
    'muranodashboard/js/external-ad.js',
    'muranodashboard/js/horizon.muranotopology.js',
    'muranodashboard/js/murano.tables.js',
    'muranodashboard/js/load-modals.js',
    'muranodashboard/js/mixed-mode.js',
    'muranodashboard/js/passwordfield.js',
    'muranodashboard/js/submit-disabled.js',
    'muranodashboard/js/support_placeholder.js',
    'muranodashboard/js/validators.js'
]

FEATURE = True
