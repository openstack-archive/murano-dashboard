# Copyright (c) 2016 AT&T Inc.
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
import testtools

from django import http

from muranodashboard.catalog import views


class TestCatalogViews(testtools.TestCase):
    def setUp(self):
        super(TestCatalogViews, self).setUp()
        self.mock_request = mock.MagicMock()
        self.env = mock.MagicMock(id='12', name='test_env', status='READY')

        self.addCleanup(mock.patch.stopall)

    def test_is_valid_environment(self):
        mock_env1 = mock.MagicMock(id='13')
        valid_envs = [mock_env1, self.env]
        self.assertTrue(views.is_valid_environment(self.env, valid_envs))

    @mock.patch.object(views, 'env_api')
    def test_get_environments_context(self, mock_env_api):
        mock_env_api.environments_list.return_value = [self.env]
        self.assertIsNotNone(views.get_environments_context(self.mock_request))
        mock_env_api.environments_list.assert_called_with(self.mock_request)

    @mock.patch.object(views, 'api')
    def test_get_categories_list(self, mock_api):
        self.assertEqual([], views.get_categories_list(self.mock_request))
        mock_api.handled_exceptions.assert_called_once_with(self.mock_request)
        mock_api.muranoclient.assert_called_once_with(self.mock_request)

    @mock.patch.object(views, 'env_api')
    def test_create_quick_environment(self, mock_env_api):
        views.create_quick_environment(self.mock_request)
        self.assertTrue(mock_env_api.environment_create.called)

    @mock.patch.object(views, 'pkg_api')
    def test_get_image(self, mock_pkg_api):
        app_id = 13
        result = views.get_image(self.mock_request, app_id)
        self.assertIsInstance(result, http.HttpResponse)
        (mock_pkg_api.get_app_logo.
         assert_called_once_with(self.mock_request, app_id))
        mock_pkg_api.reset_mock()

        mock_pkg_api.get_app_logo.return_value = None
        result = views.get_image(self.mock_request, app_id)
        self.assertIsInstance(result, http.HttpResponseRedirect)
        (mock_pkg_api.get_app_logo.
         assert_called_once_with(self.mock_request, app_id))

    @mock.patch.object(views, 'pkg_api')
    def test_get_supplier_image(self, mock_pkg_api):
        app_id = 13
        result = views.get_supplier_image(self.mock_request, app_id)
        self.assertIsInstance(result, http.HttpResponse)
        (mock_pkg_api.get_app_supplier_logo.
         assert_called_once_with(self.mock_request, app_id))
        mock_pkg_api.reset_mock()

        mock_pkg_api.get_app_supplier_logo.return_value = None
        result = views.get_supplier_image(self.mock_request, app_id)
        self.assertIsInstance(result, http.HttpResponseRedirect)
        (mock_pkg_api.get_app_supplier_logo.
         assert_called_once_with(self.mock_request, app_id))

    @mock.patch.object(views, 'pkg_api')
    @mock.patch('muranodashboard.dynamic_ui.services.version')
    @mock.patch('muranodashboard.dynamic_ui.services.pkg_api')
    def test_quick_deploy_error(self, services_pkg_api,
                                mock_version, views_pkg_api):
        mock_version.check_version.return_value = '0.2'
        app_id = 'app_id'
        self.assertRaises(ValueError, views.quick_deploy,
                          self.mock_request, app_id=app_id)
        (services_pkg_api.get_app_ui.
         assert_called_once_with(self.mock_request, app_id))
        views_pkg_api.get_app_fqn.assert_called_with(self.mock_request, app_id)
