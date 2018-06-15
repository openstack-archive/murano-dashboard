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

from django import http
import mock

from muranodashboard.api.rest import environments

from openstack_dashboard.test import helpers

PARAM_MAPPING = {
    'None': None,
    'True': True,
    'False': False
}


@mock.patch.object(environments, 'api')
@mock.patch.object(environments, 'env_api')
class TestComponentsMetadataAPI(helpers.APIMockTestCase):

    def setUp(self):
        super(TestComponentsMetadataAPI, self).setUp()

        self.request = mock.Mock(body='{"foo": "bar"}', DATA={"foo"})
        self.request.GET = dict(PARAM_MAPPING)
        self.components_metadata = environments.ComponentsMetadata()

        self.addCleanup(mock.patch.stopall)

    def test_get(self, mock_env_api, mock_api):
        mock_sess = mock.Mock()
        mock_component = mock.Mock()
        test_response = http.HttpResponse(
            "Foobar metadata response.", content_type="text/plain")
        mock_component.to_dict.return_value = {
            '?': {
                'metadata': test_response
            }
        }
        mock_env_api.Session.get_or_create_or_delete.return_value = mock_sess
        mock_api.muranoclient().services.get.return_value = mock_component

        response = self.components_metadata.get(
            self.request, 'foo_env', 'foo_component')

        self.assertEqual(test_response, response)
        self.assertEqual(b"Foobar metadata response.", response.content)
        mock_env_api.Session.get_or_create_or_delete.assert_called_once_with(
            self.request, 'foo_env')
        mock_api.muranoclient().services.get.assert_called_once_with(
            'foo_env', '/foo_component', mock_sess)

    def test_get_empty_response(self, mock_env_api, mock_api):
        mock_env_api.Session.get_or_create_or_delete.return_value = mock.Mock()
        mock_api.muranoclient().services.get.return_value = None
        result = self.components_metadata.get(
            self.request, None, 'foo_component')
        self.assertEqual(200, result.status_code)
        self.assertEqual(b'{}', result.content)

    def test_post_updated(self, mock_env_api, mock_api):
        mock_sess = mock.Mock()
        mock_env_api.Session.get_or_create_or_delete.return_value = mock_sess

        self.request.body = '{"updated": true}'
        self.components_metadata.post(self.request, 'foo_env', 'foo_component')

        mock_env_api.Session.get_or_create_or_delete.assert_called_once_with(
            self.request, 'foo_env')
        mock_api.muranoclient.assert_called_once_with(self.request)
        mock_api.muranoclient().services.put.assert_called_once_with(
            'foo_env', '/foo_component/%3F/metadata', True, mock_sess)


@mock.patch.object(environments, 'api')
@mock.patch.object(environments, 'env_api')
class TestEnvironmentsMetadataApi(helpers.APIMockTestCase):

    def setUp(self):
        super(TestEnvironmentsMetadataApi, self).setUp()

        self.request = mock.Mock(body='{"foo": "bar"}', DATA={"foo"})
        self.request.GET = dict(PARAM_MAPPING)
        self.envs_metadata = environments.EnvironmentsMetadata()

        self.addCleanup(mock.patch.stopall)

    def test_get(self, mock_env_api, mock_api):
        mock_sess = mock.Mock()
        http_response = http.HttpResponse(
            "Foobar metadata response.", content_type="text/plain")
        test_response = {
            '?': {
                'metadata': http_response
            }
        }
        mock_env_api.Session.get_or_create_or_delete.return_value = mock_sess
        mock_api.muranoclient().environments.get_model.return_value =\
            test_response

        response = self.envs_metadata.get(self.request, 'foo_env')
        self.assertEqual(http_response, response)
        self.assertEqual(b"Foobar metadata response.", response.content)

        mock_env_api.Session.get_or_create_or_delete.assert_called_once_with(
            self.request, 'foo_env')
        mock_api.muranoclient().environments.get_model.assert_called_once_with(
            'foo_env', '/', mock_sess)

    def test_get_empty_response(self, mock_env_api, mock_api):
        mock_env_api.Session.get_or_create_or_delete.return_value = mock.Mock()
        mock_api.muranoclient().environments.get_model.return_value = None

        result = self.envs_metadata.get(self.request, 'foo_env')
        self.assertEqual(200, result.status_code)
        self.assertEqual(b'{}', result.content)

    def test_post(self, mock_env_api, mock_api):
        mock_sess = mock.Mock()
        mock_env_api.Session.get_or_create_or_delete.return_value = mock_sess

        self.request.body = '{"updated": true}'
        self.envs_metadata.post(self.request, 'foo_env')

        expected_patch = {
            "op": "replace",
            "path": "/?/metadata",
            "value": True
        }
        mock_api.muranoclient().environments.update_model.\
            assert_called_once_with('foo_env', [expected_patch], mock_sess)
