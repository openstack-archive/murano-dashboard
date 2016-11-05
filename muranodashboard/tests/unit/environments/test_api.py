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
from muranodashboard.environments import api as env_api
from openstack_dashboard.test import helpers


class TestEnvironmentsAPI(helpers.APITestCase):
    def setUp(self):
        super(TestEnvironmentsAPI, self).setUp()

        self.mock_client = mock.Mock(spec=client)
        self.mock_request = mock.MagicMock()
        self.env_id = 12

        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_get_status_messages_for_service(self, mock_log, mock_api):
        service_id = 11
        result = env_api.get_status_messages_for_service(self.mock_request,
                                                         service_id,
                                                         self.env_id)
        self.assertEqual('\n', result)
        env_api.api.muranoclient.assert_called_once_with(self.mock_request)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api')
    def test_environment_update(self, mock_api):
        env_name = "test_env"
        env_api.environment_update(self.mock_request, self.env_id, env_name)
        env_api.api.muranoclient.assert_called_once_with(self.mock_request)

    @mock.patch.object(env_api, 'api')
    def test_environment_list(self, mock_api):
        env_api.environments_list(self.mock_request)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        env_api.api.handled_exceptions.assert_called_with(self.mock_request)

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_environment_create(self, mock_log, mock_api):
        parameters = {
            'name': 'test_env',
            'defaultNetworks': 'test_net'
        }
        env_api.environment_create(self.mock_request, parameters)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_environment_delete(self, mock_log, mock_api):
        env_api.environment_delete(self.mock_request, self.env_id)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        (mock_log.debug.
            assert_called_once_with('Environment::{0} <Id :'
                                    ' {1}>'.format('Delete', self.env_id)))

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_environment_deploy(self, mock_log, mock_api):
        env_api.environment_deploy(self.mock_request, self.env_id)
        self.assertTrue(env_api.api.muranoclient.called)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_action_allowed(self, mock_log, mock_api):
        result = env_api.action_allowed(self.mock_request, self.env_id)
        self.assertTrue(result)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_service_create(self, mock_log, mock_api):
        parameters = {
            '?': {
                'type': 'test.Service'
            }
        }
        env_api.service_create(self.mock_request, self.env_id, parameters)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        mock_log.debug.assert_called_with('Service::Create {0}'
                                          .format(parameters['?']['type']))

    @mock.patch.object(env_api, 'api')
    @mock.patch("muranodashboard.environments.api.Session."
                "get_or_create_or_delete")
    @mock.patch.object(env_api, 'LOG')
    def test_service_delete(self, mock_log, mock_gcd, mock_api):
        service_id = str(11)
        mock_gcd.return_value = self.env_id
        env_api.service_delete(self.mock_request, self.env_id, service_id)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        mock_log.debug.assert_called_with('Service::Delete <SrvId: '
                                          '{0}>'.format(service_id))
        mock_gcd.assert_called_with(self.mock_request, self.env_id)

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_service_get(self, mock_log, mock_api):
        service_id = 11
        result = env_api.service_get(self.mock_request,
                                     self.env_id, service_id)
        self.assertIsNone(result)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        mock_log.debug.assert_called_with('Return service'
                                          ' detail for a specified id')

    def test_extract_actions_list(self):
        service = {
            '?': {
                'test': 'test'
            }
        }
        result = env_api.extract_actions_list(service)
        self.assertEqual([], result)

    @mock.patch.object(env_api, 'api')
    def test_run_action(self, mock_api):
        action_id = 11
        env_api.run_action(self.mock_request, self.env_id, action_id)
        env_api.api.muranoclient.assert_called_with(self.mock_request)

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_deployment_reports(self, mock_log, mock_api):
        deployment_id = 11
        env_api.deployment_reports(self.mock_request, self.env_id,
                                   deployment_id)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_get_deployment_start(self, mock_log, mock_api):
        deployment_id = 11
        result = env_api.get_deployment_start(self.mock_request, self.env_id,
                                              deployment_id)
        self.assertIsNone(result)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        mock_log.debug.assert_called_with('Get deployment start time')

    @mock.patch.object(env_api, 'api')
    @mock.patch.object(env_api, 'LOG')
    def test_get_deployment_descr(self, mock_log, mock_api):
        deployment_id = 11
        result = env_api.get_deployment_descr(self.mock_request, self.env_id,
                                              deployment_id)
        self.assertIsNone(result)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        mock_log.debug.assert_called_with('Get deployment description')

    @mock.patch('muranodashboard.environments.api.topology.json.dumps')
    @mock.patch('muranodashboard.environments.api.topology._environment_info')
    @mock.patch('muranodashboard.environments.api.environment_get')
    def test_load_environment_data(self, mock_env_get,
                                   mock_env_info, mock_dump):
        mock_env_info.return_value = 'services/_environment_info.html'
        mock_dump.return_value = self.env_id
        result = env_api.load_environment_data(self.mock_request, self.env_id)
        self.assertTrue(mock_env_get.called)
        self.assertEqual(self.env_id, result)
        self.assertTrue(mock_dump.called)


class TestEnvironmentsSessionAPI(helpers.APITestCase):
    def setUp(self):
        super(TestEnvironmentsSessionAPI, self).setUp()

        self.mock_client = mock.Mock(spec=client)
        self.mock_request = mock.MagicMock()
        self.env_id = 12

        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(env_api, 'api')
    def test_get_or_create(self, mock_api):
        self.session = env_api.Session()
        result = self.session.get_or_create(self.mock_request, self.env_id)
        self.assertIsNotNone(result)
        env_api.api.muranoclient.assert_called_once_with(self.mock_request)

    def test_set(self):
        session_id = 11
        self.session = env_api.Session()
        result = self.session.set(self.mock_request, self.env_id, session_id)
        self.assertIsNone(result)
