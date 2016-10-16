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

from muranoclient.v1 import client
from muranodashboard.api import packages
from openstack_dashboard.test import helpers


class TestPackages(helpers.APITestCase):

    def setUp(self):
        super(TestPackages, self).setUp()

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
        self.mock_client.packages.filter.assert_called_once_with(
            limit=100)

    def test_package_list_with_paginate(self):
        package_list, more = packages.package_list(self.mock_request,
                                                   paginate=True,
                                                   page_size=1)

        # Only one package should be returned.
        self.assertEqual(self.packages[:1], package_list)
        self.assertTrue(more)
        self.mock_client.packages.filter.assert_called_once_with(
            limit=2)
        self.mock_client.packages.filter.reset_mock()

        package_list, more = packages.package_list(self.mock_request,
                                                   paginate=True,
                                                   page_size=2)

        # Only two packages should be returned.
        self.assertEqual(self.packages[:2], package_list)
        self.assertTrue(more)
        self.mock_client.packages.filter.assert_called_once_with(
            limit=3)

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
        self.mock_client = mock.Mock(spec=client)
        self.mock_client.packages.filter().next.return_value = self.packages[0]
        packages.api.muranoclient.return_value = self.mock_client
        self.mock_client.reset_mock()

        setattr(packages.settings, "MURANO_USE_GLARE", True)
        app = packages.app_by_fqn(self.mock_request, 'test_fqn', version='1.0')

        self.assertIsNotNone(app)
        self.assertEqual(self.packages[0], app)
        self.mock_client.packages.filter.assert_called_once_with(
            fqn='test_fqn', catalog=True, version='1.0')

    def test_app_by_fqn_except_stop_iteration(self):
        self.mock_client = mock.Mock(spec=client)
        self.mock_client.packages.filter().next.side_effect = StopIteration
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
