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

import socket

SECRET_KEY = 'HELLA_SECRET!'

DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3',
                         'NAME': 'test'}}

from horizon.test.settings import *  # noqa

socket.setdefaulttimeout(1)

DEBUG = False
TEMPLATE_DEBUG = DEBUG

TESTSERVER = 'http://testserver'


MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = ['--nocapture',
             '--nologcapture',
             '--cover-package=muranodashboard']

EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'

OPENSTACK_ADDRESS = "localhost"
OPENSTACK_ADMIN_TOKEN = "openstack"
OPENSTACK_KEYSTONE_URL = "http://%s:5000/v2.0" % OPENSTACK_ADDRESS
OPENSTACK_KEYSTONE_ADMIN_URL = "http://%s:35357/v2.0" % OPENSTACK_ADDRESS
OPENSTACK_KEYSTONE_DEFAULT_ROLE = "Member"

# Silence logging output during tests.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'level': 'DEBUG',
            'class': 'logging.NullHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['null'],
            'propagate': False,
        },
        'horizon': {
            'handlers': ['null'],
            'propagate': False,
        },
        'novaclient': {
            'handlers': ['null'],
            'propagate': False,
        },
        'keystoneclient': {
            'handlers': ['null'],
            'propagate': False,
        },
        'neutronclient': {
            'handlers': ['null'],
            'propagate': False,
        },
        'nose.plugins.manager': {
            'handlers': ['null'],
            'propagate': False,
        }
    }
}
