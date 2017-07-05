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

import collections
import mock
import testtools

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from muranoclient.common import exceptions as exc
from muranodashboard.environments import tables
from muranodashboard.environments import tabs


class TestOverviewTab(testtools.TestCase):

    def setUp(self):
        super(TestOverviewTab, self).setUp()
        self.overview_tab = tabs.OverviewTab(None)

        self.assertEqual(_('Component'), self.overview_tab.name)
        self.assertEqual('_service', self.overview_tab.slug)
        self.assertEqual('services/_overview.html',
                         self.overview_tab.template_name)

    @mock.patch.object(tabs, 'heat_api')
    @mock.patch.object(tabs, 'nova_api')
    @mock.patch.object(tabs, 'consts')
    def test_get_context_data(self, mock_consts, mock_nova_api, mock_heat_api):
        mock_consts.STATUS_DISPLAY_CHOICES = [('foo_status_id', 'foo_status')]
        foo_mock_instance = mock.Mock(id='foo_instance_id')
        foo_mock_instance.configure_mock(name='foo-instance-name')
        bar_mock_instance = mock.Mock(id='bar_instance_id')
        bar_mock_instance.configure_mock(name='bar-instance-name')
        baz_mock_instance = mock.Mock(id='baz_instance_id')
        baz_mock_instance.configure_mock(name='baz-instance-name')
        mock_nova_api.server_list.side_effect = [
            ([foo_mock_instance], False), ([bar_mock_instance], False),
            ([baz_mock_instance], False)
        ]
        mock_heat_api.stacks_list.side_effect = [
            (
                [mock.Mock(id='foo_stack_id', stack_name='foo_stack_name')],
                False, False
            ),
            (
                [mock.Mock(id='bar_stack_id', stack_name='bar_stack_name')],
                False, False
            ),
            (
                [mock.Mock(id='baz_stack_id', stack_name='baz_stack_name')],
                False, False
            )
        ]
        mock_request = mock.Mock()
        mock_request.session = {'django_timezone': 'UTC'}

        expected_service = {
            'service': collections.OrderedDict([
                ('Name', 'foo_service_data_name'),
                ('ID', 'foo_service_data_id'),
                ('Type', 'Unknown'),
                ('Status', 'foo_status'),
                ('Domain', 'foo_domain'),
                ('Application repository', 'foo_repository'),
                ('Load Balancer URI', 'foo_uri'),
                ('Floating IP', 'foo_floatingip'),
                ('Instance',
                    {'name': 'foo-instance-name', 'id': 'foo_instance_id'}),
                ('Stack',
                    {'id': 'foo_stack_id', 'name': 'foo_stack_name'}),
                ('Instances', [
                    {'name': 'bar-instance-name', 'id': 'bar_instance_id'},
                    {'name': 'baz-instance-name', 'id': 'baz_instance_id'}]),
                ('Stacks', [
                    {'id': 'bar_stack_id', 'name': 'bar_stack_name'},
                    {'id': 'baz_stack_id', 'name': 'baz_stack_name'}])
            ])
        }

        def service_data_side_effect(*args, **kwargs):
            if args[0] == 'instances':
                return [
                    {
                        'status': 'bar_status_id',
                        'id': 'bar_service_data_id',
                        'name': 'instance-name',
                        'openstackId': 'bar_instance_id'
                    },
                    {
                        'status': 'baz_status_id',
                        'id': 'baz_service_data_id',
                        'name': 'instance-name',
                        'openstackId': 'baz_instance_id'
                    }
                ]
            elif args[0] == 'instance':
                return {
                    'name': 'instance-name',
                    'openstackId': 'instance_id'
                }
            elif args[0] == '?':
                return {
                    'status': 'foo_status_id',
                    'id': 'foo_service_data_id',
                }

        service_data = mock.MagicMock()
        service_data.__getitem__.side_effect = service_data_side_effect
        service_data.configure_mock(name='foo_service_data_name')
        service_data.domain = 'foo_domain'
        service_data.repository = 'foo_repository'
        service_data.uri = 'foo_uri'
        service_data.floatingip = 'foo_floatingip'

        self.overview_tab.tab_group = mock.Mock()
        self.overview_tab.tab_group.kwargs = {
            'service': service_data
        }

        result = self.overview_tab.get_context_data(mock_request)

        self.assertIsInstance(result, dict)
        self.assertIn('service', result)
        self.assertEqual(expected_service, result)
        self.assertEqual(3, mock_nova_api.server_list.call_count)
        self.assertEqual(3, mock_heat_api.stacks_list.call_count)
        mock_nova_api.server_list.assert_any_call(mock_request)
        mock_heat_api.stacks_list.assert_any_call(mock_request, sort_dir='asc')

    @mock.patch.object(tabs, 'heat_api')
    @mock.patch.object(tabs, 'nova_api')
    def test_get_context_data_find_stack_has_more(self, mock_nova_api,
                                                  mock_heat_api):
        foo_mock_instance = mock.Mock(id='foo_instance_id')
        foo_mock_instance.configure_mock(name='foo-instance-name')
        mock_nova_api.server_list.side_effect = [
            ([foo_mock_instance], False)
        ]
        mock_heat_api.stacks_list.side_effect = [
            (
                [mock.Mock(id='bar_stack_id', stack_name='bar_stack_name')],
                True, False
            ),
            (
                [mock.Mock(id='foo_stack_id', stack_name='foo_stack_name')],
                False, False
            )
        ]
        mock_request = mock.Mock()

        expected_service = {
            'service': collections.OrderedDict([
                ('Name', 'foo_service_data_name'),
                ('ID', 'foo_service_data_id'),
                ('Type', 'Unknown'),
                ('Status', ''),
                ('Domain', 'Not in domain'),
                ('Application repository', 'foo_repository'),
                ('Load Balancer URI', 'foo_uri'),
                ('Floating IP', 'foo_floatingip'),
                ('Instance',
                    {'name': 'foo-instance-name', 'id': 'foo_instance_id'}),
                ('Stack',
                    {'id': 'foo_stack_id', 'name': 'foo_stack_name'}),
            ])
        }

        expected_mock_calls = [
            mock.call(mock_request, sort_dir='asc'),
            mock.call(mock_request, sort_dir='asc', marker='bar_stack_id')
        ]

        def service_data_side_effect(*args, **kwargs):
            if args[0] == 'instance':
                return {
                    'name': 'instance-name',
                    'openstackId': 'instance_id'
                }
            elif args[0] == '?':
                return {
                    'status': 'foo_status_id',
                    'id': 'foo_service_data_id',
                }

        service_data = mock.MagicMock()
        service_data.__getitem__.side_effect = service_data_side_effect
        service_data.configure_mock(name='foo_service_data_name')
        service_data.domain = None
        service_data.repository = 'foo_repository'
        service_data.uri = 'foo_uri'
        service_data.floatingip = 'foo_floatingip'

        self.overview_tab.tab_group = mock.Mock()
        self.overview_tab.tab_group.kwargs = {
            'service': service_data
        }

        result = self.overview_tab.get_context_data(mock_request)

        self.assertIsInstance(result, dict)
        self.assertIn('service', result)
        self.assertEqual(expected_service, result)
        # Test whether the expected number of calls were made. 1 call should
        # be made to nova_api but 2 should be made to heat_api, since that
        # call is recursive.
        self.assertEqual(1, mock_nova_api.server_list.call_count)
        self.assertEqual(2, mock_heat_api.stacks_list.call_count)
        mock_nova_api.server_list.assert_any_call(mock_request)
        self.assertEqual(expected_mock_calls,
                         mock_heat_api.stacks_list.mock_calls)


class TestServiceLogsTab(testtools.TestCase):

    def setUp(self):
        super(TestServiceLogsTab, self).setUp()
        self.service_logs_tab = tabs.ServiceLogsTab(None)

        self.assertEqual(_('Logs'), self.service_logs_tab.name)
        self.assertEqual('service_logs', self.service_logs_tab.slug)
        self.assertEqual('services/_logs.html',
                         self.service_logs_tab.template_name)
        self.assertFalse(self.service_logs_tab.preload)

    @mock.patch.object(tabs, 'api')
    def test_get_context_data(self, mock_api):
        mock_api.get_status_messages_for_service.return_value = ['foo_report']
        mock_request = mock.Mock()
        self.service_logs_tab.tab_group = mock.Mock()

        self.service_logs_tab.tab_group.kwargs = {
            'service_id': 'foo_service_id',
            'environment_id': 'foo_environment_id'
        }

        reports = self.service_logs_tab.get_context_data(mock_request)

        self.assertEqual({'reports': ['foo_report']}, reports)
        mock_api.get_status_messages_for_service.assert_called_once_with(
            mock_request, 'foo_service_id', 'foo_environment_id')


class TestEnvLogsTab(testtools.TestCase):

    def setUp(self):
        super(TestEnvLogsTab, self).setUp()
        self.env_logs_tab = tabs.EnvLogsTab(None)

        self.assertEqual(_('Logs'), self.env_logs_tab.name)
        self.assertEqual('env_logs', self.env_logs_tab.slug)
        self.assertEqual('deployments/_logs.html',
                         self.env_logs_tab.template_name)
        self.assertFalse(self.env_logs_tab.preload)

    def test_get_context_data(self):
        mock_report = mock.Mock(created='1970-01-01T12:34:00')
        self.env_logs_tab.tab_group = mock.Mock()
        self.env_logs_tab.tab_group.kwargs = {
            'logs': [mock_report]
        }
        mock_request = mock.MagicMock()
        mock_request.session = {'django_timezone': 'UTC'}

        reports = self.env_logs_tab.get_context_data(mock_request)

        mock_report.created = '1970-01-01 12:34:00'
        self.assertEqual({'reports': [mock_report]}, reports)


class TestLatestLogTab(testtools.TestCase):

    def test_allowed(self):
        mock_request = mock.MagicMock()
        mock_request.session = {'django_timezone': 'UTC'}
        mock_report = mock.Mock(created='1970-01-01T12:34:00')
        tab_group = mock.Mock()
        tab_group.kwargs = {'logs': [mock_report]}
        latest_logs_tab = tabs.LatestLogsTab(tab_group, request=mock_request)

        self.assertEqual(_('Latest Deployment Log'), latest_logs_tab.name)
        mock_report.created = '1970-01-01 12:34:00'
        self.assertEqual([mock_report], latest_logs_tab.allowed(mock_request))


class TestEnvConfigTab(testtools.TestCase):

    def setUp(self):
        super(TestEnvConfigTab, self).setUp()
        mock_tab_group = mock.Mock(kwargs={})
        self.env_config_tab = tabs.EnvConfigTab(mock_tab_group, None)

        self.assertEqual(_('Configuration'), self.env_config_tab.name)
        self.assertEqual('env_config', self.env_config_tab.slug)
        self.assertEqual((tables.EnvConfigTable,),
                         self.env_config_tab.table_classes)
        self.assertEqual('horizon/common/_detail_table.html',
                         self.env_config_tab.template_name)
        self.assertFalse(self.env_config_tab.preload)

    def test_get_environment_and_configuration_data(self):
        self.env_config_tab.tab_group = mock.Mock()
        self.env_config_tab.tab_group.kwargs = {
            'deployment': {
                'services': ['foo_service']
            }
        }

        result = self.env_config_tab.get_environment_configuration_data()
        self.assertEqual(['foo_service'], result)


class TestEnvironmentTopologyTab(testtools.TestCase):

    def setUp(self):
        super(TestEnvironmentTopologyTab, self).setUp()
        self.env_topology_tab = tabs.EnvironmentTopologyTab(None)

        self.assertEqual(_('Topology'), self.env_topology_tab.name)
        self.assertEqual('topology', self.env_topology_tab.slug)
        self.assertEqual('services/_detail_topology.html',
                         self.env_topology_tab.template_name)
        self.assertFalse(self.env_topology_tab.preload)

    @mock.patch.object(tabs, 'api')
    def test_allowed_true(self, mock_api):
        self.env_topology_tab.tab_group = mock.Mock()
        self.env_topology_tab.tab_group.kwargs = {
            'environment_id': 'foo_env_id'
        }

        mock_api.load_environment_data.return_value =\
            '{"environment": {"status": "foo_status"}}'  # d3 data
        self.assertTrue(self.env_topology_tab.allowed(None))
        mock_api.load_environment_data.assert_called_with(None, 'foo_env_id')

    @mock.patch.object(tabs, 'api')
    def test_allowed_false(self, mock_api):
        self.env_topology_tab.tab_group = mock.Mock()
        self.env_topology_tab.tab_group.kwargs = {
            'environment_id': 'foo_env_id'
        }

        mock_api.load_environment_data.return_value =\
            '{"environment": {"status": null}}'  # d3 data
        self.assertFalse(self.env_topology_tab.allowed(None))
        mock_api.load_environment_data.assert_called_with(None, 'foo_env_id')


@mock.patch.object(tabs, 'api')
class TestEnvironmentServicesTab(testtools.TestCase):

    def setUp(self):
        super(TestEnvironmentServicesTab, self).setUp()

        test_kwargs = {'environment_id': 'foo_env_id'}
        mock_tab_group = mock.Mock(kwargs=test_kwargs)
        self.mock_request = mock.Mock()
        self.env_services_tab = tabs.EnvironmentServicesTab(mock_tab_group,
                                                            self.mock_request)

        self.assertEqual(_('Components'), self.env_services_tab.name)
        self.assertEqual('services', self.env_services_tab.slug)
        self.assertEqual((tables.ServicesTable,),
                         self.env_services_tab.table_classes)
        self.assertEqual('services/_service_list.html',
                         self.env_services_tab.template_name)
        self.assertFalse(self.env_services_tab.preload)

    def test_get_services_data(self, mock_api):
        mock_api.services_list.return_value = ['foo_service']

        services_data = self.env_services_tab.get_services_data()

        self.assertEqual(['foo_service'], services_data)
        self.assertEqual('foo_env_id', self.env_services_tab.environment_id)

    @mock.patch.object(tabs, 'reverse')
    @mock.patch.object(tabs, 'exceptions')
    def test_get_services_data_except_http_forbidden(
            self, mock_exc, mock_reverse, mock_api):
        mock_api.services_list.side_effect = exc.HTTPForbidden
        mock_reverse.return_value = 'foo_reverse_url'

        services_data = self.env_services_tab.get_services_data()

        self.assertEqual([], services_data)
        expected_msg = _(
            'Unable to retrieve list of services. This environment '
            'is deploying or already deployed by other user.')
        mock_exc.handle.assert_called_once_with(
            self.mock_request, expected_msg, redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:environments:index')

    @mock.patch.object(tabs, 'reverse')
    @mock.patch.object(tabs, 'exceptions')
    def test_get_services_data_except_internal_server_and_not_found_errors(
            self, mock_exc, mock_reverse, mock_api):
        mock_reverse.return_value = 'foo_reverse_url'
        expected_msg = "Environment with id foo_env_id doesn't exist anymore"

        for exception_cls in (exc.HTTPInternalServerError, exc.HTTPNotFound):
            mock_api.services_list.side_effect = exception_cls

            services_data = self.env_services_tab.get_services_data()

            self.assertEqual([], services_data)
            mock_exc.handle.assert_called_with(
                self.mock_request, expected_msg, redirect='foo_reverse_url')
            mock_reverse.assert_called_with(
                'horizon:app-catalog:environments:index')

    @mock.patch.object(tabs, 'exceptions')
    def test_get_services_data_except_http_unauthorized(
            self, mock_exc, mock_api):
        mock_api.services_list.side_effect = exc.HTTPUnauthorized
        self.env_services_tab.get_services_data()
        mock_exc.handle.assert_called_once_with(self.mock_request)

    def test_get_context_data(self, _):
        setattr(settings, 'MURANO_USE_GLARE', True)

        expected_context = {
            'MURANO_USE_GLARE': True,
            'table': mock.ANY,
            'services_table': mock.ANY
        }

        context = self.env_services_tab.get_context_data(self.mock_request)

        for key, val in expected_context.items():
            self.assertEqual(val, context.get(key))


@mock.patch.object(tabs, 'api')
class TestDeploymentTab(testtools.TestCase):

    def setUp(self):
        super(TestDeploymentTab, self).setUp()

        test_kwargs = {'environment_id': 'foo_env_id'}
        mock_tab_group = mock.Mock(kwargs=test_kwargs)
        self.mock_request = mock.Mock()
        self.deployment_tab = tabs.DeploymentTab(mock_tab_group,
                                                 self.mock_request)

        self.assertEqual(_('Deployment History'), self.deployment_tab.name)
        self.assertEqual('deployments', self.deployment_tab.slug)
        self.assertEqual((tables.DeploymentsTable,),
                         self.deployment_tab.table_classes)
        self.assertEqual('horizon/common/_detail_table.html',
                         self.deployment_tab.template_name)
        self.assertFalse(self.deployment_tab.preload)

    @mock.patch.object(tabs, 'policy')
    def test_allowed(self, mock_policy, _):
        mock_policy.check.return_value = True
        self.assertTrue(self.deployment_tab.allowed(self.mock_request))
        mock_policy.check.assert_called_once_with(
            (("murano", "list_deployments"),), self.mock_request)

    def test_get_deployments_data(self, mock_api):
        mock_api.deployments_list.return_value = ['foo_deployment']
        deployments = self.deployment_tab.get_deployments_data()
        self.assertEqual(['foo_deployment'], deployments)
        mock_api.deployments_list.assert_called_once_with(
            self.mock_request, 'foo_env_id')

    @mock.patch.object(tabs, 'reverse')
    @mock.patch.object(tabs, 'exceptions')
    def test_get_deployments_data_except_http_forbidden(
            self, mock_exc, mock_reverse, mock_api):
        mock_api.deployments_list.side_effect = exc.HTTPForbidden
        mock_reverse.return_value = 'foo_reverse_url'

        self.deployment_tab.get_deployments_data()

        mock_exc.handle.assert_called_once_with(
            self.mock_request, _('Unable to retrieve list of deployments'),
            redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            "horizon:app-catalog:environments:index")

    @mock.patch.object(tabs, 'reverse')
    @mock.patch.object(tabs, 'exceptions')
    def test_get_deployments_data_except_http_server_error(
            self, mock_exc, mock_reverse, mock_api):
        mock_api.deployments_list.side_effect = exc.HTTPInternalServerError
        mock_reverse.return_value = 'foo_reverse_url'

        self.deployment_tab.get_deployments_data()

        mock_exc.handle.assert_called_once_with(
            self.mock_request,
            "Environment with id foo_env_id doesn't exist anymore",
            redirect='foo_reverse_url')
        mock_reverse.assert_called_once_with(
            "horizon:app-catalog:environments:index")


class TestEnvironmentDetailsTabs(testtools.TestCase):

    @mock.patch.object(tabs, 'api')
    def test_init(self, mock_api):
        mock_api.load_environment_data.return_value =\
            '{"environment": {"status": "foo_status"}}'

        mock_request = mock.Mock(GET={})
        mock_request.session = {'django_timezone': 'UTC'}
        mock_logs = mock.Mock(created='1970-01-01T12:34:00')
        mock_logs.created = '1970-01-01 12:34:00'
        env_details_tabs = tabs.EnvironmentDetailsTabs(
            mock_request, environment_id='foo_env_id', logs=[mock_logs])

        self.assertEqual('environment_details', env_details_tabs.slug)
        self.assertEqual(
            (tabs.EnvironmentServicesTab, tabs.EnvironmentTopologyTab,
             tabs.DeploymentTab, tabs.LatestLogsTab),
            env_details_tabs.tabs)
        self.assertTrue(env_details_tabs.sticky)


class TestServicesTabs(testtools.TestCase):

    def test_init(self):
        mock_request = mock.Mock(GET={})
        services_tabs = tabs.ServicesTabs(mock_request)

        self.assertEqual('services_details', services_tabs.slug)
        self.assertEqual(
            (tabs.OverviewTab, tabs.ServiceLogsTab),
            services_tabs.tabs)
        self.assertTrue(services_tabs.sticky)


class TestDeploymentDetailsTabs(testtools.TestCase):

    def test_init(self):
        mock_request = mock.Mock(GET={})
        deployment_details_tabs = tabs.DeploymentDetailsTabs(mock_request)

        self.assertEqual('deployment_details', deployment_details_tabs.slug)
        self.assertEqual((tabs.EnvConfigTab, tabs.EnvLogsTab,),
                         deployment_details_tabs.tabs)
        self.assertTrue(deployment_details_tabs.sticky)
