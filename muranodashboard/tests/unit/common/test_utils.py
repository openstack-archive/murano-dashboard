#    Copyright (c) 2016 Mirantis, Inc.
#
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

try:
    import cPickle as pickle
except ImportError:
    import pickle

import mock
import testtools
import yaql

from muranodashboard.common import utils
from muranodashboard.dynamic_ui import yaql_expression


class TestUtils(testtools.TestCase):

    def test_parse_api_error(self):
        test_html = '<html><body><h1>Foo Header</h1>Foo Error </body></html>'
        self.assertEqual('Foo Error', utils.parse_api_error(test_html))

    def test_parse_api_error_without_body(self):
        test_html = '<html></html>'
        self.assertIsNone(utils.parse_api_error(test_html))


class TestCustomPickler(testtools.TestCase):

    def setUp(self):
        super(TestCustomPickler, self).setUp()
        self.custom_pickler = utils.CustomPickler(mock.Mock())
        self.assertTrue(hasattr(self.custom_pickler.dump, '__call__'))
        self.assertTrue(hasattr(self.custom_pickler.clear_memo, '__call__'))

    def test_persistent_id(self):
        yaql_obj = mock.Mock(spec=yaql.factory.YaqlEngine)
        self.assertEqual('filtered:YaqlEngine',
                         self.custom_pickler.persistent_id(yaql_obj))

    def test_persistent_id_with_wrong_obj_type(self):
        self.assertIsNone(self.custom_pickler.persistent_id(None))


class TestCustomUnpickler(testtools.TestCase):

    def setUp(self):
        super(TestCustomUnpickler, self).setUp()
        self.custom_unpickler = utils.CustomUnpickler(mock.Mock())
        self.assertTrue(hasattr(self.custom_unpickler.load, '__call__'))
        if 'noload' in dir(pickle.Unpickler):
            self.assertTrue(hasattr(self.custom_unpickler.noload, '__call__'))

    def test_persistent_load(self):
        result = self.custom_unpickler.persistent_load('filtered:YaqlEngine')
        self.assertEqual(yaql_expression.YAQL, result)

    def test_persistent_load_with_wrong_obj_type(self):
        e = self.assertRaises(pickle.UnpicklingError,
                              self.custom_unpickler.persistent_load, None)
        self.assertEqual('Invalid persistent id', str(e))
