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

from django.utils.translation import ugettext_lazy as _

from muranoclient.common import exceptions as exc
from muranodashboard.environments import forms as env_forms


class TestCreateEnvForm(testtools.TestCase):
    def setUp(self):
        super(TestCreateEnvForm, self).setUp()
        self.mock_request = mock.MagicMock()
        self.data = {
            'name': 'test',
            'net_config': 'Nova'
        }

    @mock.patch.object(env_forms, 'ast')
    @mock.patch.object(env_forms, 'api')
    @mock.patch('muranodashboard.common.net.get_available_networks')
    def test_handle(self, mock_net, mock_api, mock_ast):
        mock_net.return_value = None
        test_env_form = env_forms.CreateEnvironmentForm(self.mock_request)
        self.assertEqual([((None, None), _('Unavailable'))],
                         test_env_form.fields['net_config'].choices)
        self.assertEqual(env_forms.net.NN_HELP,
                         test_env_form.fields['net_config'].help_text)

        self.assertTrue(test_env_form.handle(self.mock_request, self.data))
        mock_api.environment_create.assert_called_once_with(self.mock_request,
                                                            self.data)
        mock_ast.literal_eval.assert_called_once_with('Nova')

    @mock.patch.object(env_forms, 'LOG')
    @mock.patch.object(env_forms, 'ast')
    @mock.patch.object(env_forms, 'api')
    @mock.patch('muranodashboard.common.net.get_available_networks')
    def test_handle_error(self, mock_net, mock_api, mock_ast, mock_log):
        mock_net.return_value = None
        test_env_form = env_forms.CreateEnvironmentForm(self.mock_request)
        self.assertEqual([((None, None), _('Unavailable'))],
                         test_env_form.fields['net_config'].choices)
        self.assertEqual(env_forms.net.NN_HELP,
                         test_env_form.fields['net_config'].help_text)

        mock_api.environment_create.side_effect = exc.HTTPConflict
        msg = _('Environment with specified name already exists')
        self.assertRaises(exc.HTTPConflict, test_env_form.handle,
                          self.mock_request, self.data)
        mock_ast.literal_eval.assert_called_once_with('Nova')
        mock_log.exception.assert_called_once_with(msg)
