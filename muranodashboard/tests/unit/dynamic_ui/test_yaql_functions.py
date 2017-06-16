#    Copyright (c) 2016 Mirantis, Inc.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import re
import testtools

from castellan.common import exception as castellan_exception
from castellan.common.objects import opaque_data

from muranodashboard.dynamic_ui import helpers
from muranodashboard.dynamic_ui import yaql_functions


class TestYAQLFunctions(testtools.TestCase):

    def test_generate_hostname(self):
        self.assertEqual(
            yaql_functions._generate_hostname('foo-#', 1), 'foo-1')
        self.assertEqual(
            yaql_functions._generate_hostname('foo-#', 22), 'foo-22')

    def test_generate_hostname_random(self):
        random = yaql_functions._generate_hostname('', 3)
        self.assertTrue(bool(re.match(r'^\w{14}$', random)))

    def test_repeat(self):
        context = {}
        result = yaql_functions._repeat(context, 'foo_template', 2)
        self.assertEqual(['foo_template', 'foo_template'], [x for x in result])

    def test_name(self):
        context = mock.MagicMock()
        context.get_data.__getitem__.return_value = \
            {'application_name': 'foo_app'}
        self.assertEqual('foo_app', yaql_functions._name(context))

    def test_ref(self):
        parameters = {
            '#foo_template': {
                '?': {
                    'id': None
                }
            }
        }
        mock_service = mock.Mock(parameters=parameters)
        context = {'?service': mock_service}
        result = yaql_functions._ref(context, 'foo_template')
        self.assertIsInstance(result['?']['id'], helpers.ObjectID)

    def test_ref_with_id_only(self):
        object_id = helpers.ObjectID()
        parameters = {
            '#foo_template': {
                '?': {
                    'id': object_id
                }
            }
        }
        mock_service = mock.Mock(parameters=parameters)
        context = {'?service': mock_service}
        result = yaql_functions._ref(context, 'foo_template')
        self.assertIsInstance(result, helpers.ObjectID)
        self.assertEqual(object_id, result)

    def test_ref_with_evaluate_template(self):
        templates = {
            'foo_template': {
                '?': {
                    'id': helpers.ObjectID()
                }
            }
        }
        mock_service = mock.Mock(parameters={}, templates=templates)
        context = {'?service': mock_service}
        result = yaql_functions._ref(context, 'foo_template')
        self.assertIsInstance(result, helpers.ObjectID)

    def test_ref_return_none(self):
        mock_service = mock.Mock(parameters={'#foo_template': 'foo_data'})
        context = {'?service': mock_service}
        result = yaql_functions._ref(context, 'foo_template')
        self.assertIsNone(result)

    @mock.patch('muranodashboard.dynamic_ui.yaql_functions.settings')
    @mock.patch('muranodashboard.dynamic_ui.yaql_functions._oslo_context')
    @mock.patch('muranodashboard.dynamic_ui.yaql_functions.key_manager')
    @mock.patch('muranodashboard.dynamic_ui.yaql_functions.identity')
    def test_encrypt_data(self, mock_identity, mock_keymanager,
                          mock_oslo_context, _):
        mock_service = mock.Mock(parameters={'#foo_template': 'foo_data'})
        context = {'?service': mock_service}
        secret_value = 'secret_password'
        mock_auth_context = mock.MagicMock()
        mock_oslo_context.RequestContext.return_value = mock_auth_context
        yaql_functions._encrypt_data(context, secret_value)
        mock_keymanager.API().store.assert_called_once_with(
            mock_auth_context, opaque_data.OpaqueData(secret_value))

    def test_encrypt_data_not_configured(self):
        mock_service = mock.Mock(parameters={'#foo_template': 'foo_data'})
        context = {'?service': mock_service}
        self.assertRaises(castellan_exception.KeyManagerError,
                          yaql_functions._encrypt_data, context,
                          'secret_password')

    @mock.patch('muranodashboard.dynamic_ui.yaql_functions.identity')
    @mock.patch('muranodashboard.dynamic_ui.yaql_functions.settings')
    def test_encrypt_data_badly_configured(self, mock_settings, _):
        mock_service = mock.Mock(parameters={'#foo_template': 'foo_data'})
        context = {'?service': mock_service}
        mock_settings.KEY_MANAGER = {}
        self.assertRaises(castellan_exception.KeyManagerError,
                          yaql_functions._encrypt_data, context,
                          'secret_password')
