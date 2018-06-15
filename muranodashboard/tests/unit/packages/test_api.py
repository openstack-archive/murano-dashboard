# Copyright (c) 2016 AT&T Corp
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import mock
from six import PY3

from muranoclient.v1 import client
from muranodashboard.api import packages
from openstack_dashboard.test import helpers


def mock_next(obj, attr, value):
    if PY3:
        setattr(obj.__next__, attr, value)
    else:
        setattr(obj.next, attr, value)


class MagicIterMock(mock.MagicMock):
    if PY3:
        __next__ = mock.Mock(return_value=None)
    else:
        next = mock.Mock(return_value=None)


class TestPackagesAPI(helpers.APIMockTestCase):
    def setUp(self):
        super(TestPackagesAPI, self).setUp()

        self.packages = ['foo', 'bar', 'baz']
        self.mock_client = mock.Mock(spec=client)
        self.mock_client.packages.filter.return_value = self.packages

        packages.api = mock.Mock()
        packages.api.muranoclient.return_value = self.mock_client
        self.mock_request = mock.Mock()

        self.addCleanup(mock.patch.stopall)

    def test_package_list(self):
        package_list, more = packages.package_list(self.mock_request)

        self.assertEqual(self.packages, package_list)
        self.assertFalse(more)
        self.mock_client.packages.filter.assert_called_once_with(limit=100)

    def test_package_list_with_paginate(self):
        package_list, more = packages.package_list(self.mock_request,
                                                   paginate=True,
                                                   page_size=1)

        # Only one package should be returned.
        self.assertEqual(self.packages[:1], package_list)
        self.assertTrue(more)
        self.mock_client.packages.filter.assert_called_once_with(limit=2)
        self.mock_client.packages.filter.reset_mock()

        package_list, more = packages.package_list(self.mock_request,
                                                   paginate=True,
                                                   page_size=2)

        # Only two packages should be returned.
        self.assertEqual(self.packages[:2], package_list)
        self.assertTrue(more)
        self.mock_client.packages.filter.assert_called_once_with(limit=3)

    def test_package_list_with_filters(self):
        package_list, more = packages.package_list(self.mock_request,
                                                   marker='test_marker',
                                                   sort_dir='test_sort_dir')

        self.assertEqual(self.packages, package_list)
        self.assertFalse(more)
        self.mock_client.packages.filter.assert_called_once_with(
            limit=100, marker='test_marker', sort_dir='test_sort_dir')

    def test_apps_that_inherit(self):
        setattr(packages.settings, "MURANO_USE_GLARE", False)
        apps = packages.apps_that_inherit(self.mock_request, 'test_fqn')
        self.assertEqual([], apps)

        setattr(packages.settings, "MURANO_USE_GLARE", True)
        apps = packages.apps_that_inherit(self.mock_request, 'test_fqn')
        self.assertEqual(self.packages, apps)

        self.mock_client.packages.filter.assert_called_once_with(
            inherits='test_fqn')

    def test_app_by_fqn(self):
        self.mock_client = MagicIterMock(spec=client)
        mock_next(
            self.mock_client.packages.filter(),
            'return_value',
            self.packages[0]
        )
        packages.api.muranoclient.return_value = self.mock_client
        self.mock_client.reset_mock()

        setattr(packages.settings, "MURANO_USE_GLARE", True)
        app = packages.app_by_fqn(self.mock_request, 'test_fqn', version='1.0')

        self.assertIsNotNone(app)
        self.assertEqual(self.packages[0], app)
        self.mock_client.packages.filter.assert_called_once_with(
            fqn='test_fqn', catalog=True, version='1.0')

    def test_app_by_fqn_except_stop_iteration(self):
        self.mock_client = MagicIterMock(spec=client)
        mock_next(
            self.mock_client.packages.filter(),
            'side_effect',
            StopIteration
        )
        packages.api.muranoclient.return_value = self.mock_client
        self.mock_client.reset_mock()

        setattr(packages.settings, "MURANO_USE_GLARE", True)
        app = packages.app_by_fqn(self.mock_request, 'test_fqn', version='1.0')

        self.assertIsNone(app)
        self.mock_client.packages.filter.assert_called_once_with(
            fqn='test_fqn', catalog=True, version='1.0')

    def test_make_loader_cls(self):
        loader = packages.make_loader_cls()
        self.assertIsNotNone(loader)
        self.assertIn("Loader", str(loader))

    @mock.patch('muranodashboard.common.cache._load_from_file',
                return_value=None)
    @mock.patch('muranodashboard.common.cache._save_to_file')
    def test_get_app_ui(self, *args):
        mock_get_ui = packages.api.muranoclient().packages.get_ui
        mock_get_ui.return_value = 'foo_ui'

        ui = packages.get_app_ui(None, 'foo_app_id')
        mock_args = [arg for arg in mock_get_ui.call_args]

        self.assertEqual(ui, 'foo_ui')
        mock_get_ui.assert_called_once_with('foo_app_id', mock.ANY)
        self.assertEqual('Loader', mock_args[0][1].__name__)

    @mock.patch('muranodashboard.common.cache._load_from_file',
                return_value=None)
    @mock.patch('muranodashboard.common.cache._save_to_file')
    def test_get_app_logo(self, *args):
        mock_get_app_logo = packages.api.muranoclient().packages.get_logo
        mock_get_app_logo.return_value = 'foo_app_logo'

        app_logo = packages.get_app_logo(None, 'foo_app_id')

        self.assertEqual(app_logo, 'foo_app_logo')
        mock_get_app_logo.assert_called_once_with('foo_app_id')

    @mock.patch('muranodashboard.common.cache._load_from_file',
                return_value=None)
    @mock.patch('muranodashboard.common.cache._save_to_file')
    def test_get_app_supplier_logo(self, *args):
        mock_get_supplier_logo = packages.api.muranoclient().packages. \
            get_supplier_logo
        mock_get_supplier_logo.return_value = 'foo_app_supplier_logo'

        app_supplier_logo = packages.get_app_supplier_logo(None, 'foo_app_id')

        self.assertEqual(app_supplier_logo, 'foo_app_supplier_logo')
        mock_get_supplier_logo.assert_called_once_with('foo_app_id')

    @mock.patch('muranodashboard.common.cache._load_from_file',
                return_value=None)
    @mock.patch('muranodashboard.common.cache._save_to_file')
    def test_get_app_fqn(self, *args):
        mock_app = mock.Mock(fully_qualified_name='foo_app_fqn')
        mock_get_app = packages.api.muranoclient().packages.get
        mock_get_app.return_value = mock_app

        app_fqn = packages.get_app_fqn(None, 'foo_app_id')

        self.assertEqual(app_fqn, 'foo_app_fqn')
        mock_get_app.assert_called_once_with('foo_app_id')

    @mock.patch('muranodashboard.common.cache._load_from_file',
                return_value=None)
    @mock.patch('muranodashboard.common.cache._save_to_file')
    def test_get_service_name(self, *args):
        mock_app = mock.Mock()
        mock_app.configure_mock(name='foo_app_name')
        mock_get_app = packages.api.muranoclient().packages.get
        mock_get_app.return_value = mock_app

        app_service_name = packages.get_service_name(None, 'foo_app_id')

        self.assertEqual(app_service_name, 'foo_app_name')
        mock_get_app.assert_called_once_with('foo_app_id')

    @mock.patch('muranodashboard.common.cache._load_from_file',
                return_value=None)
    @mock.patch('muranodashboard.common.cache._save_to_file')
    def test_get_package_details(self, *args):
        mock_app = mock.Mock()
        mock_get_app = packages.api.muranoclient().packages.get
        mock_get_app.return_value = mock_app

        app_details = packages.get_package_details(None, 'foo_app_id')

        self.assertEqual(app_details, mock_app)
        mock_get_app.assert_called_once_with('foo_app_id')
