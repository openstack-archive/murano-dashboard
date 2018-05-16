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

import ast
from django import http as django_http
import mock
import testtools

from horizon import tables as hz_tables

from muranoclient.common import exceptions as exc
from muranodashboard.environments import consts
from muranodashboard.environments import tables
from muranodashboard.packages import consts as pkg_consts


class TestEnvironmentTables(testtools.TestCase):
    def test_check_row_actions_allowed(self):
        actions = mock.Mock()
        actions.table.data = None
        self.assertFalse(tables._check_row_actions_allowed(actions, ""))

        actions.table.data = ["test"]
        actions.allowed.return_value = False
        self.assertFalse(tables._check_row_actions_allowed(actions, ""))

        actions.allowed.return_value = True
        self.assertTrue(tables._check_row_actions_allowed(actions, ""))

    @mock.patch('muranodashboard.environments.api.deployments_list')
    def test_environment_has_deployed_services(self, deployments_list):
        deployments_list.return_value = False
        self.assertFalse(tables._environment_has_deployed_services('', ''))

        mock_deployment = mock.Mock()
        mock_deployment.description = {'services': 'service'}
        deployments_list.return_value = [mock_deployment]
        self.assertTrue(tables._environment_has_deployed_services('', ''))

        mock_deployment.description = {'services': None}
        self.assertFalse(tables._environment_has_deployed_services('', ''))

    @mock.patch('muranodashboard.environments.api.environment_get')
    def test_add_application_allowed(self, env_get):
        self.add_application = tables.AddApplication()
        self.add_application.table = mock.Mock()
        self.add_application.table.kwargs.get.return_value = "env_id"

        env_get.return_value = {'status': 'good', 'version': '1'}

        self.assertTrue(self.add_application.allowed("test", "test"))

    @mock.patch('muranodashboard.environments.tables.reverse')
    def test_add_application_get_link_url(self, reverse):
        self.add_application = tables.AddApplication()
        reverse.return_value = "reversed url"

        self.add_application.table = mock.Mock()
        self.add_application.table.kwargs = {'environment_id': 'id'}

        self.assertEqual('reversed url?next=reversed url',
                         self.add_application.get_link_url())

    def test_create_environment_allowed(self):
        self.create_environment = tables.CreateEnvironment()
        self.create_environment.table = mock.Mock()
        self.create_environment.table.data.return_value = True
        self.assertTrue(self.create_environment.allowed("test", "test"))

    @mock.patch('muranodashboard.environments.api.environment_create')
    def test_create_environment_action(self, create):
        self.create_environment = tables.CreateEnvironment()
        self.create_environment.action("", "")
        self.assertTrue(create.called)

    @mock.patch('muranodashboard.environments.tables.reverse')
    @mock.patch('muranodashboard.environments.tables.exceptions')
    def test_create_environment_action_fail(self, exceptions, reverse):
        self.create_environment = tables.CreateEnvironment()
        exceptions.handle.return_value = ""
        self.create_environment.action("", "")
        self.assertTrue(reverse.called)

    def test_delete_environment_allowed_with_environment(self):
        self.delete_environment = tables.DeleteEnvironment()
        test_environment = mock.Mock()
        test_environment.status = "test"
        self.assertTrue(self.delete_environment.allowed("", test_environment))

    def test_delete_environment_action_present(self):
        self.assertEqual('Delete Environment',
                         tables.DeleteEnvironment.action_present(1))
        self.assertEqual('Delete Environments',
                         tables.DeleteEnvironment.action_present(2))

    def test_delete_environment_action_past(self):
        self.assertEqual('Started Deleting Environment',
                         tables.DeleteEnvironment.action_past(1))
        self.assertEqual('Started Deleting Environments',
                         tables.DeleteEnvironment.action_past(2))

    @mock.patch('muranodashboard.environments.tables.'
                '_check_row_actions_allowed')
    def test_delete_environment_allowed_without_environment(self, row_actions):
        self.delete_environment = tables.DeleteEnvironment()
        row_actions.return_value = True
        self.assertTrue(self.delete_environment.allowed("", ""))

    @mock.patch('muranodashboard.environments.api.environment_delete')
    def test_delete_environment_action(self, delete):
        self.delete_environment = tables.DeleteEnvironment()
        self.delete_environment.action("", "")
        self.assertTrue(delete.called)

    @mock.patch('muranodashboard.environments.tables.reverse')
    @mock.patch('muranodashboard.environments.tables.exceptions')
    def test_delete_environment_action_fail(self, exceptions, reverse):
        self.delete_environment = tables.DeleteEnvironment()
        exceptions.handle.return_value = ""
        self.delete_environment.action("", "")
        self.assertTrue(reverse.called)

    def test_abandon_environment_is_allowed_with_environment(self):
        self.abandon_environment = tables.AbandonEnvironment()
        test_environment = mock.Mock()
        test_environment.status = "test"
        self.assertTrue(self.abandon_environment.allowed("",
                                                         test_environment))

        test_environment.status = "pending"
        self.assertFalse(self.abandon_environment.allowed("",
                                                          test_environment))

    @mock.patch('muranodashboard.environments.tables.'
                '_check_row_actions_allowed')
    def test_abandoin_environment_is_allowed_without_environment(self,
                                                                 actions):
        self.abandon_environment = tables.AbandonEnvironment()
        actions.return_value = True
        self.assertTrue(self.abandon_environment.allowed("", ""))

    @mock.patch('muranodashboard.environments.api.environment_delete')
    def test_abandon_environment_action(self, delete):
        self.abandon_environment = tables.AbandonEnvironment()
        self.abandon_environment.action("", "")
        self.assertTrue(delete.called)

    @mock.patch('muranodashboard.environments.tables.reverse')
    @mock.patch('muranodashboard.environments.tables.exceptions')
    def test_abandon_environment_action_fail(self, exceptions, reverse):
        self.abandon_environment = tables.AbandonEnvironment()
        exceptions.handle.return_value = ""
        self.abandon_environment.action("", "")
        self.assertTrue(reverse.called)

    def test_abandon_environment_action_present(self):
        self.assertEqual('Abandon Environment',
                         tables.AbandonEnvironment.action_present(1))
        self.assertEqual('Abandon Environments',
                         tables.AbandonEnvironment.action_present(2))

    def test_abandon_environment_action_past(self):
        self.assertEqual('Abandoned Environment',
                         tables.AbandonEnvironment.action_past(1))
        self.assertEqual('Abandoned Environments',
                         tables.AbandonEnvironment.action_past(2))

    @mock.patch('muranodashboard.environments.tables.'
                '_get_environment_status_and_version')
    def test_delete_service_is_allowed(self, status):
        self.delete_service = tables.DeleteService()
        status.return_value = 'test', 'test'
        self.assertTrue(self.delete_service.allowed("", ""))

    @mock.patch('muranodashboard.environments.tables.api.service_delete')
    def test_delete_service_action(self, delete):
        self.delete_service = tables.DeleteService()
        self.delete_service.table = mock.Mock()
        self.delete_service.table.kwargs.get.return_value = "test"
        self.delete_service.table.data = [{'?': {'id': 'service_id'}}]
        self.delete_service.action("", 'service_id')
        self.assertTrue(delete.called)

    @mock.patch('muranodashboard.environments.tables.reverse')
    @mock.patch('muranodashboard.environments.tables.exceptions')
    def test_delete_service_action_fail(self, exceptions, reverse):
        self.delete_service = tables.DeleteService()
        exceptions.handle.return_value = ""
        self.delete_service.action("", "")
        self.assertTrue(reverse.called)

    def test_delete_service_action_present(self):
        self.assertEqual('Delete Component',
                         tables.DeleteService.action_present(1))
        self.assertEqual('Delete Components',
                         tables.DeleteService.action_present(2))

    def test_delete_service_action_past(self):
        self.assertEqual('Started Deleting Component',
                         tables.DeleteService.action_past(1))
        self.assertEqual('Started Deleting Components',
                         tables.DeleteService.action_past(2))

    @mock.patch('muranodashboard.environments.tables.'
                '_environment_has_deployed_services')
    def test_deploy_environment_is_allowed_with_environment(self, deployed):
        self.deploy_environment = tables.DeployEnvironment()
        deployed.return_value = True
        test_environment = mock.Mock()
        test_environment.status = "pending"
        self.assertTrue(self.deploy_environment.allowed("", test_environment))

        deployed.return_value = False
        self.assertTrue(self.deploy_environment.allowed("", test_environment))

        test_environment.status = "test"
        self.assertFalse(self.deploy_environment.allowed("", test_environment))

    @mock.patch('muranodashboard.environments.tables.'
                '_check_row_actions_allowed')
    def test_deploy_environment_is_allowed_without_environment(self, actions):
        self.deploy_environment = tables.DeployEnvironment()
        actions.return_value = True
        self.assertTrue(self.deploy_environment.allowed("", ""))

    @mock.patch('muranodashboard.environments.tables.api.environment_deploy')
    def test_deploy_environment_action(self, deploy):
        self.deploy_environment = tables.DeployEnvironment()
        self.deploy_environment.action("", '')
        self.assertTrue(deploy.called)

    @mock.patch('muranodashboard.environments.tables.reverse')
    @mock.patch('muranodashboard.environments.tables.exceptions')
    def test_deploy_environment_action_fail(self, exceptions, reverse):
        self.deploy_environment = tables.DeployEnvironment()
        exceptions.handle.return_value = ""
        self.deploy_environment.action("", "")
        self.assertTrue(reverse.called)

    @mock.patch('muranodashboard.environments.tables.'
                '_get_environment_status_and_version')
    @mock.patch('muranodashboard.environments.tables.'
                '_environment_has_deployed_services')
    def test_deploy_this_environment_allowed_with_environment(self, deployed,
                                                              status):
        self.deploy_environment = tables.DeployThisEnvironment()
        deployed.return_value = True
        status.return_value = consts.STATUS_ID_READY, "version"

        self.deploy_environment.table = mock.Mock()
        self.deploy_environment.table.kwargs = {'environment_id': 'id'}

        self.assertFalse(self.deploy_environment.allowed(None, None))
        self.assertEqual('Update This Environment',
                         self.deploy_environment.verbose_name)

        deployed.return_value = False
        self.assertFalse(self.deploy_environment.allowed(None, None))
        self.assertEqual('Deploy This Environment',
                         self.deploy_environment.verbose_name)

        status.return_value = "", 0
        self.deploy_environment.table.data = None
        self.assertFalse(self.deploy_environment.allowed(None, None))

        status.return_value = "", 0
        self.deploy_environment.table.data = 'data'
        self.assertTrue(self.deploy_environment.allowed(None, None))

    @mock.patch('muranodashboard.environments.tables.reverse')
    @mock.patch('muranodashboard.environments.tables.messages')
    @mock.patch('muranodashboard.environments.tables.api.environment_deploy')
    def test_deploy_this_environment_single(self, mock_deploy,
                                            mock_messages, reverse):
        self.deploy_environment = tables.DeployThisEnvironment()

        data_table = mock.Mock()
        data_table.kwargs = {'environment_id': 'id'}

        mock_deploy.side_effect = None

        self.deploy_environment.single(data_table, None, None)
        self.assertTrue(mock_messages.success.called)

    @mock.patch('muranodashboard.environments.tables.reverse')
    @mock.patch('muranodashboard.environments.tables.messages')
    @mock.patch('muranodashboard.environments.tables.api.environment_deploy')
    def test_deploy_this_environment_single_exception(self, mock_deploy,
                                                      mock_messages, reverse):
        self.deploy_environment = tables.DeployThisEnvironment()

        data_table = mock.Mock()
        data_table.kwargs = {'environment_id': 'id'}

        mock_deploy.side_effect = Exception("test")

        self.assertRaises(BaseException, self.deploy_environment.single,
                          data_table, None, None)

    def test_deploy_environment_action_present_deploy(self):
        self.assertEqual('Deploy Environment',
                         tables.DeployEnvironment.action_present_deploy(1))
        self.assertEqual('Deploy Environments',
                         tables.DeployEnvironment.action_present_deploy(2))

    def test_deploy_environment_action_past_deploy(self):
        self.assertEqual('Started deploying Environment',
                         tables.DeployEnvironment.action_past_deploy(1))
        self.assertEqual('Started deploying Environments',
                         tables.DeployEnvironment.action_past_deploy(2))

    def test_deploy_environment_action_present_update(self):
        self.assertEqual('Update Environment',
                         tables.DeployEnvironment.action_present_update(1))
        self.assertEqual('Deploy Environments',
                         tables.DeployEnvironment.action_present_update(2))

    def test_deploy_environment_action_past_update(self):
        self.assertEqual('Updated Environment',
                         tables.DeployEnvironment.action_past_update(1))
        self.assertEqual('Deployed Environments',
                         tables.DeployEnvironment.action_past_update(2))

    def test_show_environment_services(self):
        self.show_environment_services = tables.ShowEnvironmentServices()
        self.assertTrue(self.show_environment_services.allowed("", ""))

    @mock.patch.object(tables, 'reverse')
    def test_get_service_details_link(self, mock_reverse):
        mock_service = mock.MagicMock(environment_id='foo_env_id')
        mock_service.__getitem__.return_value = {'id': 'foo_service_id'}
        mock_reverse.return_value = 'test_url'

        url = tables.get_service_details_link(mock_service)
        self.assertEqual('test_url', url)
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:environments:service_details',
            args=('foo_env_id', 'foo_service_id'))

    def test_get_service_type(self):
        test_datum = {
            '?': {
                consts.DASHBOARD_ATTRS_KEY: {
                    'name': 'foo_name'
                }
            }
        }
        self.assertEqual('foo_name', tables.get_service_type(test_datum))


class TestUpdateEnvironmentRow(testtools.TestCase):
    def setUp(self):
        super(TestUpdateEnvironmentRow, self).setUp()

        self.mock_data_table = mock.Mock()
        foo_column = mock.Mock(status='foo_status')
        foo_column.configure_mock(name='foo_column')
        bar_column = mock.Mock(status='bar_status')
        bar_column.configure_mock(name='bar_column')
        self.mock_data_table.columns = {
            'foo_column': foo_column,
            'bar_column': bar_column
        }
        self.mock_data_table._meta.status_columns = [
            'foo_column', 'bar_column'
        ]
        self.mock_data_table.attrs = {}
        self.mock_datum = mock.Mock(status='foo_status')

        self.addCleanup(mock.patch.stopall)

    def test_update_environment_row(self):
        data_table = tables.UpdateEnvironmentRow(
            self.mock_data_table, self.mock_datum)
        self.assertEqual('foo_status', data_table.attrs['status'])

    @mock.patch.object(tables, 'api')
    def test_get_data(self, mock_api):
        mock_api.environment_get.side_effect = None
        mock_api.environment_get.return_value = 'test_environment'

        data_table = tables.UpdateEnvironmentRow(self.mock_data_table)
        environment = data_table.get_data(None, 'foo_environment_id')

        self.assertEqual('test_environment', environment)
        mock_api.environment_get.assert_called_once_with(
            None, 'foo_environment_id')

    @mock.patch.object(tables, 'api')
    def test_get_data_except_http_not_found(self, mock_api):
        mock_api.environment_get.side_effect = exc.HTTPNotFound

        data_table = tables.UpdateEnvironmentRow(self.mock_data_table)

        with self.assertRaisesRegex(django_http.Http404, None):
            data_table.get_data(None, 'foo_environment_id')

    @mock.patch.object(tables, 'api')
    def test_get_data_except_exception(self, mock_api):
        mock_api.environment_get.side_effect = Exception('foo_error')

        data_table = tables.UpdateEnvironmentRow(self.mock_data_table)

        with self.assertRaisesRegex(Exception, 'foo_error'):
            data_table.get_data(None, 'foo_environment_id')


class TestUpdateServiceRow(testtools.TestCase):

    def setUp(self):
        super(TestUpdateServiceRow, self).setUp()
        self.addCleanup(mock.patch.stopall)

    def test_update_service_row(self):
        update_service_row = tables.UpdateServiceRow(None)
        self.assertTrue(update_service_row.ajax)

    @mock.patch.object(tables, 'api')
    def test_get_data(self, mock_api):
        mock_api.service_get.return_value = 'foo_env'
        update_service_row = tables.UpdateServiceRow(mock.Mock())
        update_service_row.table.kwargs = {'environment_id': 'foo_env_id'}

        update_service_row.get_data(None, 'foo_service_id')
        mock_api.service_get.assert_called_once_with(
            None, 'foo_env_id', 'foo_service_id')


class TestUpdateEnvMetadata(testtools.TestCase):

    def test_update_env_meta_data(self):
        kwargs = {'datum': 'foo_datum'}
        update_env_meta_data = tables.UpdateEnvMetadata(**kwargs)
        self.assertEqual("update_env_metadata", update_env_meta_data.name)
        self.assertEqual("Update Metadata", update_env_meta_data.verbose_name)
        self.assertFalse(update_env_meta_data.ajax)
        self.assertEqual("pencil", update_env_meta_data.icon)
        self.assertEqual({
            "ng-controller": "MetadataModalHelperController as modal"},
            update_env_meta_data.attrs)
        self.assertTrue(update_env_meta_data.preempt)
        self.assertEqual("foo_datum", update_env_meta_data.datum)

    def test_get_link_url(self):
        update_env_meta_data = tables.UpdateEnvMetadata()
        update_env_meta_data.session_id = 'foo_session_id'
        update_env_meta_data.attrs = {}

        result = update_env_meta_data.get_link_url(mock.Mock(id='foo_env_id'))
        self.assertEqual("javascript:void(0);", result)

        lindex = update_env_meta_data.attrs['ng-click'].find('{')
        rindex = update_env_meta_data.attrs['ng-click'].rfind('}') + 1
        attrs = ast.literal_eval(update_env_meta_data.attrs['ng-click']
                                                           [lindex:rindex])
        expected_attrs = {
            'environment': 'foo_env_id',
            'session': 'foo_session_id'
        }
        update_env_meta_data.attrs['ng-click'] =\
            update_env_meta_data.attrs['ng-click'][:lindex] +\
            update_env_meta_data.attrs['ng-click'][rindex + 2:]

        self.assertEqual("modal.openMetadataModal('muranoenv', true)",
                         update_env_meta_data.attrs['ng-click'])
        for key, val in expected_attrs.items():
            self.assertEqual(val, attrs[key])

    def test_allowed(self):
        update_env_meta_data = tables.UpdateEnvMetadata()
        allowed_statuses = (
            consts.STATUS_ID_READY, consts.STATUS_ID_PENDING,
            consts.STATUS_ID_DELETE_FAILURE, consts.STATUS_ID_DEPLOY_FAILURE,
            consts.STATUS_ID_NEW)
        disallowed_statuses = (
            consts.STATUS_ID_DEPLOYING, consts.STATUS_ID_DELETING)

        for status in allowed_statuses:
            env = mock.Mock(status=status)
            self.assertTrue(update_env_meta_data.allowed(None, env))

        for status in disallowed_statuses:
            env = mock.Mock(status=status)
            self.assertFalse(update_env_meta_data.allowed(None, env))

    @mock.patch.object(tables, 'api')
    def test_update(self, mock_api):
        mock_api.Session.get_if_available.return_value = 'foo_session_id'
        update_env_meta_data = tables.UpdateEnvMetadata()
        datum = mock.Mock()
        datum.id = 'foo_env_id'
        update_env_meta_data.session_id = None

        update_env_meta_data.update(None, datum)
        self.assertEqual('foo_session_id', update_env_meta_data.session_id)
        mock_api.Session.get_if_available.assert_called_once_with(
            None, 'foo_env_id')


class TestEnvironmentsTable(testtools.TestCase):

    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'policy')
    def test_environments_table(self, mock_policy, mock_reverse):
        mock_reverse.return_value = 'test_url'
        mock_env = mock.Mock(id='foo_env_id')
        envs_table = tables.EnvironmentsTable(None)
        self.assertEqual(tables.EnvironmentsTable.get_env_detail_link.__name__,
                         envs_table.columns['name'].get_link_url.__name__)

        mock_policy.check.return_value = False
        url = envs_table.columns['name'].get_link_url(mock_env)
        self.assertIsNone(url)
        self.assertFalse(mock_reverse.called)

        mock_policy.check.return_value = True
        url = envs_table.columns['name'].get_link_url(mock_env)
        self.assertEqual('test_url', url)
        mock_reverse.assert_called_once_with(
            "horizon:app-catalog:environments:services", args=('foo_env_id',))


class TestUpdateMetadata(testtools.TestCase):

    def setUp(self):
        super(TestUpdateMetadata, self).setUp()

        update_metadata = tables.UpdateMetadata()
        self.assertEqual("update_metadata", update_metadata.name)
        self.assertEqual("Update Metadata", update_metadata.verbose_name)
        self.assertFalse(update_metadata.ajax)
        self.assertEqual("pencil", update_metadata.icon)
        self.assertIsNone(update_metadata.session_id)

    def test_get_link_url(self):
        """Test get_link_url.

        Because the dictionary part of ``attrs[ng-click]`` may have different
        key orders, extract it, convert it to an actual dict, and check that
        each value in the dict matches the expected value.
        """
        update_metadata = tables.UpdateMetadata()
        update_metadata.table = mock.Mock()
        update_metadata.table.kwargs = {'environment_id': 'foo_env_id'}
        update_metadata.session_id = 'foo_session_id'
        test_service = {
            '?': {
                'id': 'foo_service_id'
            }
        }

        result = update_metadata.get_link_url(test_service)
        self.assertEqual("javascript:void(0);", result)

        lindex = update_metadata.attrs['ng-click'].find('{')
        rindex = update_metadata.attrs['ng-click'].rfind('}') + 1
        attrs = ast.literal_eval(update_metadata.attrs['ng-click']
                                                      [lindex:rindex])
        expected_attrs = {
            'environment': 'foo_env_id',
            'session': 'foo_session_id',
            'component': 'foo_service_id'
        }
        update_metadata.attrs['ng-click'] =\
            update_metadata.attrs['ng-click'][:lindex] +\
            update_metadata.attrs['ng-click'][rindex + 2:]

        self.assertEqual("modal.openMetadataModal('muranoapp', true)",
                         update_metadata.attrs['ng-click'])
        for key, val in expected_attrs.items():
            self.assertEqual(val, attrs[key])

    @mock.patch.object(tables, 'api')
    def test_allowed(self, mock_api):
        update_metadata = tables.UpdateMetadata()
        mock_api.environment_get.return_value = mock.Mock(
            status=consts.STATUS_ID_READY)
        mock_table = mock.Mock()
        mock_table.kwargs = {'environment_id': 'foo_env_id'}
        update_metadata.table = mock_table
        self.assertTrue(update_metadata.allowed(None))

        mock_api.environment_get.return_value = mock.Mock(
            status=consts.STATUS_ID_DEPLOYING)
        self.assertFalse(update_metadata.allowed(None))
        mock_api.environment_get.assert_called_with(None, 'foo_env_id')

    @mock.patch.object(tables, 'api')
    def test_update(self, mock_api):
        mock_api.Session.get_if_available.return_value = 'foo_session_id'
        update_metadata = tables.UpdateMetadata()
        update_metadata.table = mock.Mock()
        update_metadata.table.kwargs = {'environment_id': 'foo_env_id'}
        update_metadata.session_id = None

        update_metadata.update(None, None)
        self.assertEqual('foo_session_id', update_metadata.session_id)
        mock_api.Session.get_if_available.assert_called_once_with(
            None, 'foo_env_id')


class TestServicesTable(testtools.TestCase):

    def test_get_object_id(self):
        test_datum = {'?': {'id': 'foo'}}
        services_table = tables.ServicesTable(None)
        self.assertEqual('foo', services_table.get_object_id(test_datum))

    @mock.patch.object(tables, 'pkg_api')
    def test_get_apps_list(self, mock_pkg_api):
        foo_app = mock.Mock()
        foo_app.to_dict.return_value = {'foo': 'bar'}
        baz_app = mock.Mock()
        baz_app.to_dict.return_value = {'baz': 'qux'}
        mock_pkg_api.package_list.return_value = (
            [foo_app, baz_app], True
        )
        services_table = tables.ServicesTable(None)
        services_table.request = None
        services_table._more = False
        expected = [{'foo': 'bar'}, {'baz': 'qux'}]

        result = services_table.get_apps_list()
        for entry in expected:
            self.assertIn(entry, result)
        mock_pkg_api.package_list.assert_called_once_with(
            None, filters={'type': 'Application', 'catalog': True})

    @mock.patch.object(tables, 'api')
    def test_actions_allowed(self, mock_api):
        services_table = tables.ServicesTable(None)
        mock_api.environment_get.return_value = mock.Mock(
            status=consts.STATUS_ID_READY)
        services_table.kwargs = {'environment_id': 'foo_env_id'}
        self.assertTrue(services_table.actions_allowed())

        mock_api.environment_get.return_value = mock.Mock(
            status=consts.STATUS_ID_DEPLOYING)
        self.assertFalse(services_table.actions_allowed())
        mock_api.environment_get.assert_called_with(None, 'foo_env_id')

    @mock.patch.object(tables, 'catalog_views')
    def test_categories_list(self, mock_catalog_views):
        mock_catalog_views.get_categories_list.return_value = []
        services_table = tables.ServicesTable(None)
        services_table.request = None
        self.assertEqual([], services_table.get_categories_list())
        mock_catalog_views.get_categories_list.assert_called_once_with(None)

    @mock.patch('horizon.tables.actions.LinkAction.get_link_url')
    @mock.patch.object(tables, '_get_environment_status_and_version')
    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'api')
    def test_get_row_actions(
            self, mock_api, mock_reverse, mock_get_env_attrs, _):
        mock_api.extract_actions_list.return_value = [
            {'name': 'foo_bar', 'title': 'Foo Bar', 'id': 'foo_id'},
            {'name': 'baz_qux', 'title': 'Baz Qux', 'id': 'baz_id'}
        ]
        mock_reverse.return_value = 'test_url'

        mock_get_env_attrs.return_value = (consts.STATUS_ID_READY, None)
        mock_api.Session.get_if_available.return_value = 'session_id'
        services_table = tables.ServicesTable(None)
        services_table.kwargs = {'environment_id': 'foo_env_id'}

        mock_datum = mock.MagicMock()
        service = {'?': {'id': 'comp_id'}}
        mock_datum.__getitem__.side_effect = lambda key: service[key]
        actions = services_table.get_row_actions(mock_datum)
        custom_actions = []

        self.assertGreater(len(actions), 0)
        for action in actions:
            if action.__class__.__name__ == 'CustomAction':
                custom_actions.append(action)
        custom_actions = sorted(custom_actions,
                                key=lambda action: action.name)
        self.assertEqual(2, len(custom_actions))

        self.assertEqual('baz_qux', custom_actions[0].name)
        self.assertEqual('Baz Qux', custom_actions[0].verbose_name)
        self.assertEqual('foo_bar', custom_actions[1].name)
        self.assertEqual('Foo Bar', custom_actions[1].verbose_name)

    @mock.patch.object(tables, '_get_environment_status_and_version')
    @mock.patch.object(tables, 'reverse')
    @mock.patch.object(tables, 'api')
    def test_get_row_actions_with_no_action_allowed_status(
            self, mock_api, mock_reverse, mock_get_env_attrs):
        mock_api.extract_actions_list.return_value = [
            {'name': 'foo_bar', 'title': 'Foo Bar', 'id': 'foo_id'},
            {'name': 'baz_qux', 'title': 'Baz Qux', 'id': 'baz_id'}
        ]
        mock_reverse.return_value = 'test_url'

        mock_get_env_attrs.return_value = (consts.STATUS_ID_DEPLOYING, None)
        services_table = tables.ServicesTable(None)
        services_table.kwargs = {'environment_id': 'foo_env_id'}

        mock_datum = mock.MagicMock()
        actions = services_table.get_row_actions(mock_datum)
        self.assertEqual([], actions)

    def test_get_repo_url(self):
        services_table = tables.ServicesTable(None)
        self.assertEqual(pkg_consts.DISPLAY_MURANO_REPO_URL,
                         services_table.get_repo_url())

    @mock.patch.object(tables, 'reverse')
    def test_get_pkg_def_url(self, mock_reverse):
        mock_reverse.return_value = 'test_url'
        services_table = tables.ServicesTable(None)
        self.assertEqual('test_url',
                         services_table.get_pkg_def_url())
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')


class TestShowDeploymentDetails(testtools.TestCase):

    @mock.patch.object(tables, 'reverse')
    def test_get_link_url(self, mock_reverse):
        mock_reverse.return_value = 'test_url'
        mock_deployment = mock.Mock(
            id='foo_deployment_id', environment_id='foo_env_id')
        expected_kwargs = {'environment_id': 'foo_env_id',
                           'deployment_id': 'foo_deployment_id'}
        show_deployment_details = tables.ShowDeploymentDetails()

        url = show_deployment_details.get_link_url(mock_deployment)
        self.assertEqual('test_url', url)
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:environments:deployment_details',
            kwargs=expected_kwargs)

    def test_allowed(self):
        show_deployment_details = tables.ShowDeploymentDetails()
        self.assertTrue(show_deployment_details.allowed(None, None))


class TestEnvConfigTable(testtools.TestCase):

    def test_get_object_id(self):
        env_config_table = tables.EnvConfigTable(None)
        self.assertEqual('foo', env_config_table.get_object_id({
            '?': {'id': 'foo'}}))


class TestDeploymentHistoryTable(testtools.TestCase):

    def setUp(self):
        super(TestDeploymentHistoryTable, self).setUp()

        deployment_history_table = tables.DeploymentHistoryTable(
            mock.Mock())
        columns = deployment_history_table.columns

        self.assertIsInstance(columns['environment_name'],
                              hz_tables.WrappingColumn)
        self.assertIsInstance(columns['logs'], hz_tables.Column)
        self.assertIsInstance(columns['services'], hz_tables.Column)
        self.assertIsInstance(columns['status'], hz_tables.Column)

        self.assertEqual('Environment', str(columns['environment_name']))
        self.assertEqual('Logs (Created, Message)', str(columns['logs']))
        self.assertEqual('Services (Name, Type)', str(columns['services']))
        self.assertEqual('Status', str(columns['status']))
        self.assertTrue(columns['status'].status)
        self.assertEqual(consts.DEPLOYMENT_STATUS_DISPLAY_CHOICES,
                         columns['status'].display_choices)

    @mock.patch.object(tables, 'template')
    def test_get_deployment_history_services(self, mock_template):
        mock_template.loader.render_to_string.return_value = \
            mock.sentinel.rendered_template

        test_description = {'services': [
            {'name': 'foo_service', '?': {'type': 'foo/bar',
                                          'name': 'foo_service'}},
            {'name': 'bar_service', '?': {'type': 'baz/qux',
                                          'name': 'bar_service'}}
        ]}
        mock_deployment = mock.Mock(description=test_description)

        result = tables.get_deployment_history_services(mock_deployment)
        self.assertEqual(mock.sentinel.rendered_template, result)

        expected_services = {
            'services': {
                'bar_service': 'baz', 'foo_service': 'foo'
            }
        }
        mock_template.loader.render_to_string.assert_called_once_with(
            'deployments/_cell_services.html', expected_services)
