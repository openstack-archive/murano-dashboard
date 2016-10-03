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

from muranodashboard.environments import consts
from muranodashboard.environments import tables


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

    def test_show_environment_services(self):
        self.show_environment_services = tables.ShowEnvironmentServices()
        self.assertTrue(self.show_environment_services.allowed("", ""))
