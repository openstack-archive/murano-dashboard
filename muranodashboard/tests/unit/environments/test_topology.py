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

import json
import mock

from muranodashboard.environments import consts
from muranodashboard.environments import topology

from openstack_dashboard.test import helpers


class TestTopology(helpers.APIMockTestCase):

    def setUp(self):
        super(TestTopology, self).setUp()
        self.mock_request = mock.Mock()

    @mock.patch.object(topology, 'reverse')
    @mock.patch.object(topology, 'pkg_cli')
    def test_get_app_image_with_package(self, mock_pkg_cli, mock_reverse):
        mock_package = mock.Mock(id='test_pkg_id')
        mock_pkg_cli.app_by_fqn.return_value = mock_package
        mock_reverse.return_value = '/foo/bar/baz'

        url = topology.get_app_image(self.mock_request, 'test_app_fqn')
        self.assertEqual('/foo/bar/baz', url)
        mock_reverse.assert_called_once_with(
            "horizon:app-catalog:catalog:images", args=('test_pkg_id',))

    @mock.patch.object(topology, 'pkg_cli')
    def test_get_app_image_without_package(self, mock_pkg_cli):
        mock_pkg_cli.app_by_fqn.return_value = None

        for status in (consts.STATUS_ID_DEPLOY_FAILURE,
                       consts.STATUS_ID_DELETE_FAILURE):
            url = topology.get_app_image(self.mock_request, 'test_app_fqn',
                                         status)
            self.assertEqual('/static/dashboard/img/stack-red.svg', url)

        url = topology.get_app_image(self.mock_request, 'test_app_fqn',
                                     consts.STATUS_ID_READY)
        self.assertEqual('/static/dashboard/img/stack-green.svg', url)

        for status in (consts.STATUS_ID_PENDING, consts.STATUS_ID_DEPLOYING,
                       consts.STATUS_ID_DELETING, consts.STATUS_ID_NEW):
            url = topology.get_app_image(self.mock_request, 'test_app_fqn',
                                         status)
            self.assertEqual('/static/dashboard/img/stack-gray.svg', url)

    def test_get_environment_status_message(self):
        for status, expected_msg in (
                (consts.STATUS_ID_DEPLOYING, 'Deployment is in progress'),
                (consts.STATUS_ID_DEPLOY_FAILURE, 'Deployment failed')):
            mock_entity = mock.Mock(status=status)
            in_progress, status_msg =\
                topology._get_environment_status_message(mock_entity)
            self.assertTrue(in_progress)
            self.assertEqual(expected_msg, status_msg)

    def test_get_environment_status_message_misc_status(self):
        mock_entity = mock.Mock(status='foo_status')
        in_progress, status_msg =\
            topology._get_environment_status_message(mock_entity)
        self.assertTrue(in_progress)
        self.assertEqual('', status_msg)

    def test_get_environment_status_message_in_progress(self):
        for status, expected_msg in (
                (consts.STATUS_ID_PENDING, 'Waiting for deployment'),
                (consts.STATUS_ID_READY, 'Deployed')):
            mock_entity = mock.Mock(status=status)
            in_progress, status_msg =\
                topology._get_environment_status_message(mock_entity)
            self.assertFalse(in_progress)
            self.assertEqual(expected_msg, status_msg)

            fake_entity = {'?': {'status': status}}
            in_progress, status_msg =\
                topology._get_environment_status_message(fake_entity)
            self.assertFalse(in_progress)
            self.assertEqual(expected_msg, status_msg)

    def test_truncate_type(self):
        self.assertEqual('foo', topology._truncate_type('foo', 4))
        self.assertEqual('...bar', topology._truncate_type('foo.bar', 4))
        self.assertEqual('foo.bar', topology._truncate_type('foo.bar', 7))

    @mock.patch.object(topology, 'loader')
    @mock.patch.object(topology, 'pkg_cli')
    def test_render_d3_data(self, mock_pkg_cli, mock_loader):
        mock_pkg_cli.app_by_fqn.return_value = None
        mock_loader.render_to_string.return_value = 'test_env_info'

        fake_services = [
            {
                '?': {
                    'id': 'test_service_id',
                    'status': consts.STATUS_ID_READY,
                    'type': 'io.murano.resources.foo',
                },
                'name': 'foo',
                'instance': {
                    '?': {
                        'id': 'test_instance_id',
                        'type': 'io.murano.resources.bar',
                    },
                    'assignFloatingIp': True,
                    'extra': [{'name': 'bar'}],
                    'name': 'bar',
                    'ipAddresses': ['127.0.0.1']
                }
            },
            {
                '?': {
                    'id': 'test_alt_service_id',
                    'status': consts.STATUS_ID_PENDING,
                    'type': 'test_service_type',
                },
                'name': 'baz',
                'instance': {
                    '?': {
                        'id': 'test_alt_instance_id',
                        'type': 'test_instance_type',
                    },
                    'assignFloatingIp': False,
                    'name': 'qux',
                    'required_by': 'test_service_id'
                },
            }
        ]

        mock_environment = mock.Mock(
            id='test_env_id',
            status=consts.STATUS_ID_READY,
            services=fake_services)
        mock_environment.configure_mock(name='test_env_name')

        expected_env = {
            'id': 'test_env_id',
            'in_progress': False,
            'info_box': 'test_env_info',
            'name': 'test_env_name',
            'status': 'Deployed'
        }

        expected_node_ids = (
            'External_Network', 'test_service_id', 'test_instance_id',
            'test_alt_service_id', 'test_alt_instance_id')

        result = topology.render_d3_data(self.request, mock_environment)
        result = json.loads(result)
        self.assertIsInstance(result, dict)
        self.assertIn('environment', result)
        self.assertIn('nodes', result)

        for key, val in expected_env.items():
            self.assertEqual(val, result['environment'][key])

        for node_id in expected_node_ids:
            self.assertIn(node_id,
                          [node['id'] for node in result['nodes']])

    def test_render_d3_data_without_environment(self):
        self.assertIsNone(topology.render_d3_data(self.request, None))
        # Test without environment.services
        mock_env = mock.Mock(services=None)
        self.assertIsNone(topology.render_d3_data(self.request, mock_env))
