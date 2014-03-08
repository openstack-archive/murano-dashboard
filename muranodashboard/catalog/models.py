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
import logging
import os
import random
import uuid

from django.utils import datastructures

from muranodashboard.image_cache import cache as image_utils


LOG = logging.getLogger(__name__)


class Application(object):
    def __init__(self, dct):
        self.id = unicode(uuid.uuid4())
        self.update(dct)

    def __repr__(self):
        return getattr(self, 'title', 'No Title')

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
    def __init__(self, n=20):
        dct = {'description': 'A simple description with not very long text. '
                              'Like MySQL database'}
        self.app_list = datastructures.SortedDict()
        for i in range(1, n):
            dct['title'] = 'Test App {0}'.format(i)
            dct['image'] = get_image_name()
            app = Application(dct)
            self.app_list[app.id] = app

    def all(self, n=20):
        return self.app_list.values()[1:n]

    def get_items(self, count):
        return self.app_list.values()[1:count]

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
            'author': 'Test Author, Inc.',
            'active': 'Yes',
            'fqdn': 'com.openstack.murano.TestApp'
        }

        LOG.debug('Current storage: {0}'.format(self.app_list))
        app = self.app_list.get(app_id)
        details = copy.deepcopy(app)
        details.update(dct)
        return details

perm_objects = AppCatalogObjects()


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
