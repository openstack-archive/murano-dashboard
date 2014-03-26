#    Copyright (c) 2014 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the 'License'); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import copy
import json
import logging
import os
import random
import urllib2
import yaml
from django.utils import datastructures

from muranodashboard.image_cache import cache as image_utils


LOG = logging.getLogger(__name__)


class Application(object):
    def __init__(self, dct):
        self.id = dct.pop('id')
        self.update(dct)

    def __repr__(self):
        return getattr(self, 'name', 'No Name')

    def update(self, dct):
        for k, v in dct.items():
            setattr(self, k, v)


def get_image_name():
    folder = '/tmp/test_images/'
    if not os.path.exists(folder):
        return ''
    images = os.listdir(folder)
    rnd = random.randrange(0, len(images))
    return images[rnd]


def get_image(name):
    folder = '/tmp/test_images/'
    if not os.path.exists(folder):
        return None
    data = image_utils.load_from_file(folder + name)
    return data


class AppCatalogObjects(object):
    def __init__(self, url):
        self.app_list = datastructures.SortedDict()
        self.url = url
        string = self.query(url)
        data = json.loads(string)
        for dct in data['packages']:
            dct['image'] = get_image_name()
            app = Application(dct)
            self.app_list[app.id] = app

    @staticmethod
    def query(url):
        request = urllib2.Request(url)
        return urllib2.urlopen(request).read()

    def all(self, n=20):
        return self.app_list.values()[:n]

    def get(self, **kwargs):
        return self.app_list[kwargs.pop('app_id')]

    def filter(self, **kwargs):
        def filter_func(_app):
            for key, value in kwargs.iteritems():
                if not hasattr(_app, key) or getattr(_app, key) != value:
                    return False
            return True

        return [app for app in self.app_list.itervalues() if filter_func(app)]

    def get_ui(self, **kwargs):
        app_id = kwargs.pop('app_id')
        url = '{0}/{1}/ui'.format(self.url, app_id)
        yaml_desc = None
        try:
            yaml_desc = yaml.load(self.query(url))
        except (OSError, yaml.ScannerError) as e:
            LOG.warn("Failed to import service definition from {0},"
                     " reason: {1!s}".format(url, e))
        return yaml_desc

    def get_items(self, count):
        return self.app_list.values()[:count]

    def get_application(self, app_id):
        return self.app_list.get(app_id)

    def get_info(self, app_id):
        dct = {
            'overview': 'Nullam quis risus eget urna mollis orare vel eu leo.'
                        'Cum sociis natoque penatibus et magnis dis parturien'
                        'montes, nascetur ridiculus mus.' * 7,
            'requirements': {
                'Database': 'MySQL DB',
                'Servlet Container': 'Tomcat'},
            'license': '#    Licensed under the Apache License, Version 2.0 '
                       '(the "License"); '
                       'you may not use this file except in compliance'
                       ' with the License. '
                       'You may obtain a copy of the License at '
                       'http://www.apache.org/licenses/LICENSE-2.0 '
                       'Unless required by applicable law or agreed to in '
                       'writing, software distributed under '
                       'the License is distributed on an "AS IS" BASIS, '
                       'WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, '
                       'either express or implied. See the License for '
                       'the specific language governing permissions and '
                       'limitations under the License.',
            'version': '1.0.1.2',
            'active': 'Yes',
        }

        LOG.debug('Current storage: {0}'.format(self.app_list))
        app = self.app_list.get(app_id)
        details = copy.deepcopy(app)
        details.update(dct)
        return details

perm_objects = AppCatalogObjects(
    'http://muranorepositoryapi.apiary-mock.com/v2/catalog/packages')


class AppCatalogModel(object):
    objects = perm_objects
    last_objects = perm_objects.get_items(4)


class Categories(object):
    _categories = ['DataBases', 'WebServers', 'Java Servlet Containers',
                   'Microsoft Services', 'SAP', 'Message Queues',
                   'Load Balancers', 'DB Tier', 'BigData', 'KeyValue Storage']

    def all(self, count=10):
        return self._categories[:count]


class ApplicationImageModel(object):
    def get_image(self, application):
        return get_image(application.image)
