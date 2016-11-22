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
import testtools

from horizon import exceptions

from muranodashboard.common import net


class TestNet(testtools.TestCase):

    def setUp(self):
        super(TestNet, self).setUp()

        mock_request = mock.Mock()
        mock_request.user.tenant_id = 'foo_tenant_id'
        self.mock_request = mock_request

        mock_env_patcher = mock.patch.object(net, 'env_api', autospec=True)
        mock_env = mock.Mock()
        mock_env.configure_mock(name='foo')
        self.mock_env_api = mock_env_patcher.start()
        self.mock_env_api.environments_list.return_value = [mock_env]

        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(net, 'neutron', autospec=True)
    def test_get_available_networks_with_filter_one(self, mock_neutron):
        foo_mock_network = mock.Mock(router__external=False,
                                     id='foo-network-id',
                                     subnets=[mock.Mock(id='foo-subnet-id')])
        foo_mock_network.configure_mock(name='foo-network')
        bar_mock_network = mock.Mock()  # Will be excluded by test_filter.
        bar_mock_network.configure_mock(name='bar-network')
        mock_neutron.network_list_for_tenant.return_value = [
            foo_mock_network, bar_mock_network
        ]

        test_filter = '^foo\-[\w]+'
        result = net.get_available_networks(self.mock_request,
                                            include_subnets=True,
                                            filter=test_filter,
                                            murano_networks='include')

        expected_result = [
            (('foo-network-id', 'foo-subnet-id'), "Network of 'foo'")
        ]

        self.assertEqual(expected_result, result)
        mock_neutron.network_list_for_tenant.assert_called_once_with(
            self.mock_request, tenant_id='foo_tenant_id')
        self.mock_env_api.environments_list.assert_called_once_with(
            self.mock_request)

    @mock.patch.object(net, 'neutron', autospec=True)
    def test_get_available_networks_with_filter_none(self, mock_neutron):
        foo_mock_network = mock.Mock(router__external=False,
                                     id='foo-network-id',
                                     subnets=[mock.Mock(id='foo-subnet-id')])
        foo_mock_network.configure_mock(name='foo-network')
        bar_mock_subnet = mock.Mock(
            id='bar-subnet-id', name_or_id='bar-subnet', cidr='255.0.0.0')
        bar_mock_network = mock.Mock(router__external=False,
                                     id='bar-network-id',
                                     name_or_id='bar-network',
                                     subnets=[bar_mock_subnet])
        bar_mock_network.configure_mock(name='bar-network')
        mock_neutron.network_list_for_tenant.return_value = [
            foo_mock_network, bar_mock_network
        ]

        test_filter = '^[\w]+\-[\w]+'
        result = net.get_available_networks(self.mock_request,
                                            include_subnets=True,
                                            filter=test_filter,
                                            murano_networks='include')

        expected_result = [
            (('foo-network-id', 'foo-subnet-id'), "Network of 'foo'"),
            (('bar-network-id', 'bar-subnet-id'),
                'bar-network: 255.0.0.0 bar-subnet')
        ]

        self.assertEqual(expected_result, result)
        mock_neutron.network_list_for_tenant.assert_called_once_with(
            self.mock_request, tenant_id='foo_tenant_id')
        self.mock_env_api.environments_list.assert_called_once_with(
            self.mock_request)

    @mock.patch.object(net, 'neutron', autospec=True)
    def test_get_available_networks_with_exclude(self, mock_neutron):
        foo_mock_network = mock.Mock(router__external=False,
                                     id='foo-network-id',
                                     subnets=[mock.Mock(id='foo-subnet-id')])
        foo_mock_network.configure_mock(name='foo-network')
        bar_mock_subnet = mock.Mock(
            id='bar-subnet-id', name_or_id='bar-subnet', cidr='255.0.0.0')
        bar_mock_network = mock.Mock(router__external=False,
                                     id='bar-network-id',
                                     name_or_id='bar-network',
                                     subnets=[bar_mock_subnet])
        bar_mock_network.configure_mock(name='bar-network')
        mock_neutron.network_list_for_tenant.return_value = [
            foo_mock_network, bar_mock_network
        ]

        result = net.get_available_networks(self.mock_request,
                                            include_subnets=True,
                                            filter=None,
                                            murano_networks='exclude')

        expected_result = [
            (('bar-network-id', 'bar-subnet-id'),
                'bar-network: 255.0.0.0 bar-subnet')
        ]

        self.assertEqual(expected_result, result)
        mock_neutron.network_list_for_tenant.assert_called_once_with(
            self.mock_request, tenant_id='foo_tenant_id')
        self.mock_env_api.environments_list.assert_called_once_with(
            self.mock_request)

    @mock.patch.object(net, 'neutron', autospec=True)
    def test_get_available_networks_without_include_subnet(self, mock_neutron):
        mock_netwok = mock.Mock(router__external=False,
                                id='foo-network-id',
                                subnets=[mock.Mock(id='foo-subnet-id')])
        mock_netwok.configure_mock(name='foo-network')
        mock_neutron.network_list_for_tenant.return_value = [
            mock_netwok
        ]

        result = net.get_available_networks(self.mock_request,
                                            include_subnets=False,
                                            filter=None,
                                            murano_networks='include')

        # Subnet specified in mock_network should be None with include_subnets
        # set to False.
        expected_result = [
            (('foo-network-id', None), "Network of 'foo'")
        ]

        self.assertEqual(expected_result, result)
        mock_neutron.network_list_for_tenant.assert_called_once_with(
            self.mock_request, tenant_id='foo_tenant_id')
        self.mock_env_api.environments_list.assert_called_once_with(
            self.mock_request)

    @mock.patch.object(net, 'LOG', autospec=True)
    @mock.patch.object(net, 'neutron', autospec=True)
    def test_get_available_networks_except_service_catalog_exception(
            self, mock_neutron, mock_log):
        mock_neutron.network_list_for_tenant.side_effect = \
            exceptions.ServiceCatalogException('test_exception')
        result = net.get_available_networks(self.mock_request)

        self.assertEqual([], result)
        mock_log.warning.assert_called_once_with(
            'Neutron not found. Assuming Nova Network usage')
        mock_neutron.network_list_for_tenant.assert_called_once_with(
            self.mock_request, tenant_id='foo_tenant_id')
