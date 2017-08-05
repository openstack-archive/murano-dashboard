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
                                            filter=test_filter,
                                            murano_networks='include')

        expected_result = [
            (('foo-network-id', 'foo-subnet-id'), "Network of 'foo'"),
            (('foo-network-id', None), "Network of 'foo': random subnet"),
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
                                            filter=test_filter,
                                            murano_networks='include')

        expected_result = [
            (('foo-network-id', 'foo-subnet-id'), "Network of 'foo'"),
            (('foo-network-id', None), "Network of 'foo': random subnet"),
            (('bar-network-id', 'bar-subnet-id'),
                'bar-network: 255.0.0.0 bar-subnet'),
            (('bar-network-id', None), "bar-network: random subnet"),
        ]

        self.assertEqual(expected_result, result)
        mock_neutron.network_list_for_tenant.assert_called_once_with(
            self.mock_request, tenant_id='foo_tenant_id')
        self.mock_env_api.environments_list.assert_called_once_with(
            self.mock_request)

    @mock.patch.object(net, 'neutron', autospec=True)
    def test_get_available_networks(self, mock_neutron):
        foo_subnets = [
            type('%s-subnet' % k, (object, ),
                 {'id': '%s-subnet-id' % k, 'cidr': '255.0.0.0',
                  'name_or_id': '%s-name-or-id' % k})
            for k in ('fake1', 'fake2')]
        bar_subnets = [
            type('fake3-subnet', (object, ),
                 {'id': 'fake3-subnet-id', 'cidr': '255.255.0.0',
                  'name_or_id': 'fake3-name-or-id'})]
        foo_network = type('FooNetwork', (object, ), {
            'router__external': False,
            'id': 'foo-network-id',
            'subnets': foo_subnets,
            'name': 'foo-network-name',
            'name_or_id': 'foo-network-name-or-id',
        })
        bar_network = type('BarNetwork', (object, ), {
            'router__external': False,
            'id': 'bar-network-id',
            'subnets': bar_subnets,
            'name': 'bar-network-name',
            'name_or_id': 'bar-network-name-or-id',
        })
        mock_neutron.network_list_for_tenant.return_value = [
            foo_network, bar_network,
        ]

        result = net.get_available_networks(
            self.mock_request, filter=None, murano_networks='exclude')

        expected_result = [
            ((foo_network.id, foo_subnets[0].id),
             '%s: %s %s' % (
                 foo_network.name_or_id, foo_subnets[0].cidr,
                 foo_subnets[0].name_or_id)),
            ((foo_network.id, foo_subnets[1].id),
             '%s: %s %s' % (
                 foo_network.name_or_id, foo_subnets[1].cidr,
                 foo_subnets[1].name_or_id)),
            ((foo_network.id, None),
             '%s: random subnet' % foo_network.name_or_id),
            ((bar_network.id, bar_subnets[0].id),
             '%s: %s %s' % (
                 bar_network.name_or_id, bar_subnets[0].cidr,
                 bar_subnets[0].name_or_id)),
            ((bar_network.id, None),
             '%s: random subnet' % bar_network.name_or_id),
        ]

        self.assertIsInstance(result, list)
        self.assertEqual(len(expected_result), len(result))
        for choice in expected_result:
            self.assertIn(choice, result)
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
