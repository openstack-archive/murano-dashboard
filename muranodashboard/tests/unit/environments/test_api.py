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

from muranoclient.common import exceptions as exc
from muranoclient.v1 import client
from muranodashboard.common import utils
from muranodashboard.environments import api as env_api
from muranodashboard.environments import consts
from openstack_dashboard.test import helpers


class TestEnvironmentsAPI(helpers.APIMockTestCase):
    def setUp(self):
        super(TestEnvironmentsAPI, self).setUp()

        self.mock_client = mock.Mock(spec=client)
        self.mock_request = mock.MagicMock()
        self.mock_request.session = {'django_timezone': 'UTC'}
        self.env_id = 'foo_env_id'
        self.session_id = 'foo_session_id'
        self.service_id = 'foo_service_id'
        self.deployment_id = 'foo_deployment_id'

        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_get_status_messages_for_service(self, mock_log, mock_api):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.deployments.list.return_value = [
            mock.Mock(id='foo_deployment_id'),
            mock.Mock(id='bar_deployment_id')
        ]

        mock_client.deployments.reports.side_effect = [
            [mock.Mock(text='foo_text', created='1970-01-01T12:23:00')],
            [mock.Mock(text='bar_text', created='1970-01-01T15:45:00')],
        ]

        expected_result = '\n1970-01-01 12:23:00 - foo_text\n' \
                          '1970-01-01 15:45:00 - bar_text\n'
        expected_reports_mock_calls = [
            mock.call('foo_env_id', 'bar_deployment_id', 'foo_service_id'),
            mock.call('foo_env_id', 'foo_deployment_id', 'foo_service_id')
        ]

        result = env_api.get_status_messages_for_service(
            self.mock_request, self.service_id, self.env_id)

        self.assertEqual(expected_result, result)
        mock_client.deployments.reports.assert_has_calls(
            expected_reports_mock_calls)
        mock_client.deployments.list.assert_called_once_with('foo_env_id')
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api', autospec=True)
    def test_environment_update(self, mock_api):
        env_name = "test_env"
        env_api.environment_update(self.mock_request, self.env_id, env_name)
        env_api.api.muranoclient.assert_called_once_with(self.mock_request)

    @mock.patch.object(env_api, 'api', autospec=True)
    def test_environment_list(self, mock_api):
        env_api.environments_list(self.mock_request)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        env_api.api.handled_exceptions.assert_called_with(self.mock_request)

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_environment_create(self, mock_log, mock_api):
        parameters = {
            'name': 'test_env',
            'defaultNetworks': 'test_net'
        }
        env_api.environment_create(self.mock_request, parameters)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_environment_delete(self, mock_log, mock_api):
        env_api.environment_delete(self.mock_request, self.env_id)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        (mock_log.debug.
            assert_called_once_with('Environment::{0} <Id :'
                                    ' {1}>'.format('Delete', self.env_id)))

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_environment_deploy(self, mock_log, mock_api):
        env_api.environment_deploy(self.mock_request, self.env_id)
        self.assertTrue(env_api.api.muranoclient.called)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_action_allowed(self, mock_log, mock_api):
        result = env_api.action_allowed(self.mock_request, self.env_id)
        self.assertTrue(result)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
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

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'Session', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_service_delete(self, mock_log, mock_session, mock_api):
        mock_response = mock.Mock(status_code=200)
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.services.delete.return_value = mock_response
        mock_session.get_or_create_or_delete.return_value = self.session_id

        result = env_api.service_delete(self.mock_request, self.env_id,
                                        self.service_id)

        self.assertEqual(mock_response, result)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        mock_session.get_or_create_or_delete.assert_called_with(
            self.mock_request, 'foo_env_id')
        mock_client.services.delete.assert_called_once_with(
            'foo_env_id', '/foo_service_id', 'foo_session_id')
        mock_log.debug.assert_called_with(
            'Service::Delete <SrvId: {0}>'.format('foo_service_id'))

    @mock.patch.object(env_api, 'services_list', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_service_get(self, mock_log, mock_services_list):
        mock_services_list.return_value = [{'?': {'id': 'foo_service_id'}}]
        result = env_api.service_get(self.mock_request, self.env_id,
                                     'foo_service_id')

        self.assertEqual({'?': {'id': 'foo_service_id'}}, result)
        mock_services_list.assert_called_once_with(
            self.mock_request, 'foo_env_id')
        mock_log.debug.assert_called_with(
            'Return service detail for a specified id')

    def test_extract_actions_list(self):
        service = {
            '?': {
                'test': 'test'
            }
        }
        result = env_api.extract_actions_list(service)
        self.assertEqual([], result)

    @mock.patch.object(env_api, 'api', autospec=True)
    def test_run_action(self, mock_api):
        env_api.run_action(self.mock_request, self.env_id, 'foo_action_id')
        env_api.api.muranoclient.assert_called_with(self.mock_request)

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_deployment_reports(self, mock_log, mock_api):
        env_api.deployment_reports(self.mock_request, self.env_id,
                                   self.deployment_id)
        env_api.api.muranoclient.assert_called_with(self.mock_request)
        self.assertTrue(mock_log.debug.called)

    @mock.patch.object(env_api, 'api', autospec=True)
    def test_get_deployment_start(self, mock_api):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.deployments.list.return_value = []
        result = env_api.get_deployment_start(self.mock_request, self.env_id,
                                              self.deployment_id)
        self.assertIsNone(result)

        mock_client.deployments.list.return_value = [
            mock.Mock(id='foo_deployment_id', started='1970-01-01T12:34:00')
        ]
        result = env_api.get_deployment_start(self.mock_request, self.env_id,
                                              self.deployment_id)
        self.assertEqual('1970-01-01 12:34:00', result)
        mock_client.deployments.list.assert_has_calls([
            mock.call('foo_env_id'), mock.call('foo_env_id')
        ])

    @mock.patch.object(env_api, 'api', autospec=True)
    def test_get_deployment_description(self, mock_api):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.deployments.list.return_value = []
        result = env_api.get_deployment_start(self.mock_request, self.env_id,
                                              self.deployment_id)
        self.assertIsNone(result)

        mock_client.deployments.list.return_value = [
            mock.Mock(id='foo_deployment_id', description='foo_descr')
        ]
        result = env_api.get_deployment_descr(self.mock_request, self.env_id,
                                              self.deployment_id)
        self.assertEqual('foo_descr', result)
        mock_client.deployments.list.assert_has_calls([
            mock.call('foo_env_id'), mock.call('foo_env_id')
        ])

    @mock.patch('muranodashboard.environments.api.topology.json.dumps',
                autospec=True)
    @mock.patch('muranodashboard.environments.api.topology._environment_info',
                autospec=True)
    @mock.patch.object(env_api, 'environment_get', autospec=True)
    def test_load_environment_data(self, mock_env_get,
                                   mock_env_info, mock_dump):
        mock_env_info.return_value = 'services/_environment_info.html'
        mock_dump.return_value = self.env_id
        result = env_api.load_environment_data(self.mock_request, self.env_id)
        self.assertTrue(mock_env_get.called)
        self.assertEqual(self.env_id, result)
        self.assertTrue(mock_dump.called)

    @mock.patch.object(env_api, 'deployments_list', autospec=True)
    def test_update_env_return_ready_status(self, mock_deployments_list):
        mock_deployments_list.return_value = []
        mock_env = mock.Mock(id='foo_env_id', services=[], version=1,
                             status=consts.STATUS_ID_PENDING)

        result = env_api._update_env(mock_env, self.mock_request)
        self.assertEqual(mock_env, result)
        self.assertEqual(consts.STATUS_ID_READY, result.status)
        self.assertFalse(result.has_new_services)

    @mock.patch.object(env_api, 'deployments_list', autospec=True)
    def test_update_env_return_new_status(self, mock_deployments_list):
        mock_deployments_list.return_value = []
        mock_env = mock.Mock(id='foo_env_id', services=[], version=0,
                             status=consts.STATUS_ID_READY)

        result = env_api._update_env(mock_env, self.mock_request)
        self.assertEqual(mock_env, result)
        self.assertEqual(consts.STATUS_ID_NEW, result.status)
        self.assertFalse(result.has_new_services)

    @mock.patch.object(env_api, 'Session', autospec=True)
    @mock.patch.object(env_api, 'packages_api', autospec=True)
    @mock.patch.object(env_api, 'api', autospec=True)
    def test_services_list(self, mock_api, mock_pkg_api, mock_session):
        mock_env = mock.Mock(version=0)
        mock_env.services = [
            {'?': {'id': 'foo_service_id', 'name': 'foo', 'type': 'foo_type'}},
            {'?': {'id': 'bar_service_id', 'name': 'bar',
                   'type': '/3@bar_type'}, 'updated': 'bar_time'},
        ]
        mock_foo_pkg = mock.Mock()
        mock_foo_pkg.configure_mock(name='foo_pkg')
        mock_bar_pkg = mock.Mock()
        mock_bar_pkg.configure_mock(name='bar_pkg')

        mock_session.get.return_value = 'foo_sess_id'
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.environments.get.return_value = mock_env
        mock_client.environments.last_status.return_value = {
            'foo_service': mock.Mock(text='foo'*100,
                                     updated='foo_time'),
            'bar_service': None
        }
        mock_pkg_api.app_by_fqn.side_effect = [mock_foo_pkg, mock_bar_pkg]

        expected_pkg_calls = [
            mock.call(self.mock_request, 'foo_type', version=None),
            mock.call(self.mock_request, 'bar_type', version='3')
        ]

        result = env_api.services_list(self.mock_request, 'foo_env_id')

        self.assertIsInstance(result, list)
        for obj in result:
            self.assertIsInstance(obj, utils.Bunch)

        mock_session.get.assert_called_once_with(
            self.mock_request, 'foo_env_id')
        mock_client.environments.get.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')
        mock_client.environments.last_status.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')
        mock_pkg_api.app_by_fqn.assert_has_calls(expected_pkg_calls)

    @mock.patch.object(env_api, 'LOG', autospec=True)
    @mock.patch.object(env_api, 'Session', autospec=True)
    @mock.patch.object(env_api, 'packages_api', autospec=True)
    @mock.patch.object(env_api, 'api', autospec=True)
    def test_services_list_except_http_not_found(self, mock_api, mock_pkg_api,
                                                 mock_session, mock_log):
        mock_env = mock.Mock(version=0)
        mock_env.services = [
            {'?': {'id': 'foo_service_id', 'name': 'foo', 'type': 'foo_type'}}
        ]
        mock_foo_pkg = mock.Mock()
        mock_foo_pkg.configure_mock(name='foo_pkg')

        mock_session.get.return_value = 'foo_sess_id'
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.environments.get.return_value = mock_env
        mock_client.environments.last_status.side_effect = exc.HTTPNotFound
        mock_pkg_api.app_by_fqn.side_effect = [mock_foo_pkg]

        expected_pkg_calls = [
            mock.call(self.mock_request, 'foo_type', version=None)
        ]

        result = env_api.services_list(self.mock_request, 'foo_env_id')

        self.assertIsInstance(result, list)
        for obj in result:
            self.assertIsInstance(obj, utils.Bunch)

        mock_session.get.assert_called_once_with(
            self.mock_request, 'foo_env_id')
        mock_client.environments.get.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')
        mock_client.environments.last_status.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')
        mock_log.exception.assert_called_once_with(
            'Could not retrieve latest status for the foo_env_id environment')
        mock_pkg_api.app_by_fqn.assert_has_calls(expected_pkg_calls)

    @mock.patch.object(env_api, 'services_list', autospec=True)
    def test_service_list_by_fqns(self, mock_services_list):
        self.assertEqual([], env_api.service_list_by_fqns(None, None, []))

        mock_services_list.return_value = [
            {'?': {'type': 'foo/bar'}}, {'?': {'type': 'baz/qux'}}
        ]
        result = env_api.service_list_by_fqns(
            self.mock_request, 'foo_env_id', ['foo'])
        self.assertEqual([{'?': {'type': 'foo/bar'}}], result)


class TestEnvironmentsSessionAPI(helpers.APIMockTestCase):
    def setUp(self):
        super(TestEnvironmentsSessionAPI, self).setUp()

        self.mock_client = mock.Mock(spec=client)
        self.mock_request = mock.MagicMock()
        self.env_id = 'foo_env_id'

        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(env_api, 'api', autospec=True)
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

    @mock.patch.object(env_api, 'create_session', autospec=True)
    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_gcd(self, mock_log, mock_api, mock_create_session):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_session_data = mock.Mock(state=consts.STATUS_ID_READY)
        mock_client.sessions.get.return_value = mock_session_data
        mock_create_session.return_value = 'bar_sess_id'

        self.mock_request.session = {'sessions': {'foo_env_id': 'foo_sess_id'}}
        result = env_api.Session.get_or_create_or_delete(self.mock_request,
                                                         'foo_env_id')

        self.assertEqual('bar_sess_id', result)
        mock_client.sessions.get.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')
        self.assertNotIn('foo_env_id', self.mock_request.session)
        mock_log.debug.assert_called_once_with(
            'The existing session has been already deployed. Creating a new '
            'session for the environment foo_env_id')
        mock_create_session.assert_called_once_with(
            self.mock_request, 'foo_env_id')

    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_gcd_with_active_session(self, mock_log, mock_api):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_session_data = mock.Mock(state='foo_bar_state')
        mock_client.sessions.get.return_value = mock_session_data

        self.mock_request.session = {'sessions': {'foo_env_id': 'foo_sess_id'}}
        result = env_api.Session.get_or_create_or_delete(self.mock_request,
                                                         'foo_env_id')

        self.assertEqual('foo_sess_id', result)
        mock_client.sessions.get.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')
        self.assertNotIn('foo_env_id', self.mock_request.session)
        mock_log.debug.assert_called_once_with(
            'Found active session for the environment foo_env_id')

    @mock.patch.object(env_api, 'create_session', autospec=True)
    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_gcd_with_new_session(self, mock_log, mock_api,
                                  mock_create_session):
        mock_create_session.return_value = 'bar_sess_id'

        result = env_api.Session.get_or_create_or_delete(self.mock_request,
                                                         'foo_env_id')

        self.assertEqual('bar_sess_id', result)
        mock_log.debug.assert_called_once_with('Creating a new session')
        mock_create_session.assert_called_once_with(
            self.mock_request, 'foo_env_id')

    @mock.patch.object(env_api, 'create_session', autospec=True)
    @mock.patch.object(env_api, 'api', autospec=True)
    @mock.patch.object(env_api, 'LOG', autospec=True)
    def test_gcd_except_http_forbidden(self, mock_log, mock_api,
                                       mock_create_session):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.sessions.get.side_effect = exc.HTTPForbidden
        mock_create_session.return_value = 'bar_sess_id'

        self.mock_request.session = {'sessions': {'foo_env_id': 'foo_sess_id'}}
        result = env_api.Session.get_or_create_or_delete(self.mock_request,
                                                         'foo_env_id')

        self.assertEqual('bar_sess_id', result)
        mock_client.sessions.get.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')
        self.assertNotIn('foo_env_id', self.mock_request.session)
        mock_log.debug.assert_called_once_with(
            'The environment is being deployed by other user. '
            'Creating a new session for the environment foo_env_id')
        mock_create_session.assert_called_once_with(
            self.mock_request, 'foo_env_id')

    @mock.patch.object(env_api, 'api', autospec=True)
    def test_get_if_available(self, mock_api):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.sessions.get.return_value = mock.Mock(
            state='foo_bar_state')

        self.mock_request.session = {'sessions': {'foo_env_id': 'foo_sess_id'}}
        result = env_api.Session.get_if_available(
            self.mock_request, 'foo_env_id')

        self.assertEqual('foo_sess_id', result)
        mock_client.sessions.get.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')

    @mock.patch.object(env_api, 'api', autospec=True)
    def test_get_if_available_with_none_returned(self, mock_api):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.sessions.get.return_value = \
            mock.Mock(state=consts.STATUS_ID_READY)

        self.mock_request.session = {'sessions': {'foo_env_id': 'foo_sess_id'}}
        result = env_api.Session.get_if_available(
            self.mock_request, 'foo_env_id')

        self.assertIsNone(result)
        mock_client.sessions.get.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')

    @mock.patch.object(env_api, 'api', autospec=True)
    def test_get_if_available_except_http_forbidden(self, mock_api):
        mock_client = mock_api.muranoclient(mock.Mock())
        mock_client.sessions.get.side_effect = exc.HTTPForbidden

        self.mock_request.session = {'sessions': {'foo_env_id': 'foo_sess_id'}}
        result = env_api.Session.get_if_available(
            self.mock_request, 'foo_env_id')

        self.assertIsNone(result)
        mock_client.sessions.get.assert_called_once_with(
            'foo_env_id', 'foo_sess_id')
