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

from django.conf import settings

from muranoclient.v1 import client
from muranodashboard import api

from openstack_dashboard.test import helpers


class TestApi(helpers.APIMockTestCase):

    def setUp(self):
        super(TestApi, self).setUp()

        factory = helpers.RequestFactoryWithMessages()
        self.request = factory.get('/path/for/testing')

        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(api, 'LOG')
    def test_handled_exceptions(self, mock_log):

        handled_exceptions = (
            (api.exc.CommunicationError,
                'Unable to communicate to murano-api server.'),
            (api.glance_exc.CommunicationError,
                'Unable to communicate to glare-api server.'),
            (api.exc.HTTPUnauthorized,
                'Check Keystone configuration of murano-api server.'),
            (api.exc.HTTPForbidden,
                'Operation is forbidden by murano-api server.'),
            (api.exc.HTTPNotFound,
                'Requested object is not found on murano server.'),
            (api.exc.HTTPConflict,
                'Requested operation conflicts with an existing object.'),
            (api.exc.BadRequest,
                'The request data is not acceptable by the server'),
            (api.exc.HTTPInternalServerError,
                'There was an error communicating with server'),
            (api.glance_exc.HTTPInternalServerError,
                'There was an error communicating with server'),
        )

        for (exception, expected_message) in handled_exceptions:
            try:
                with api.handled_exceptions(self.request):
                    raise exception()
            except exception:
                pass

            mock_log.exception.assert_called_once_with(expected_message)
            mock_log.exception.reset_mock()

    @mock.patch.object(api, 'LOG')
    def test_handled_exceptions_with_details(self, mock_log):
        exceptions_with_details = (
            (api.exc.HTTPInternalServerError,
                'There was an error communicating with server'),
            (api.glance_exc.HTTPInternalServerError,
                'There was an error communicating with server')
        )

        for (exception, expected_message) in exceptions_with_details:
            try:
                with api.handled_exceptions(self.request):
                    raise exception(details='test_details')
            except exception:
                pass

            mock_log.exception.assert_called_once_with(expected_message)
            mock_log.exception.reset_mock()

    @mock.patch.object(api, 'msg_api')
    @mock.patch.object(api, 'exceptions')
    def test_handled_exceptions_with_message_already_queued(self, mock_exc,
                                                            mock_msg_api):
        mock_message = mock.Mock(
            message='Unable to communicate to murano-api server.')
        mock_msg_api.get_messages.return_value = [mock_message]
        try:
            with api.handled_exceptions(self.request):
                raise api.exc.CommunicationError()
        except api.exc.CommunicationError:
            pass

        mock_exc.handle.assert_called_once_with(self.request, ignore=True)

    @mock.patch.object(api, 'exceptions')
    def test_handled_exceptions_with_ajax_request(self, mock_exc):
        async_messages = [('test_tag',
                           'Unable to communicate to murano-api server.',
                           'test_extra')]
        mock_request = mock.MagicMock()
        mock_request.is_ajax.return_value = True
        mock_request.horizon.__getitem__.return_value = async_messages
        try:
            with api.handled_exceptions(mock_request):
                raise api.exc.CommunicationError()
        except api.exc.CommunicationError:
            pass

        mock_exc.handle.assert_called_once_with(mock_request, ignore=True)
        self.assertTrue(mock_request.is_ajax.called)
        self.assertTrue(mock_request.horizon.__getitem__.called)

    def test_muranoclient(self):
        muranoclient = api.muranoclient(self.request)
        self.assertIsNotNone(muranoclient)
        self.assertEqual(client.Client, type(muranoclient))

    @mock.patch.object(api, 'LOG')
    @mock.patch('openstack_dashboard.api.base')
    def test_muranoclient_override_endpoints(self, mock_base, mock_log):
        mock_base.url_for = mock.MagicMock(
            side_effect=api.exceptions.ServiceCatalogException)

        setattr(settings, 'MURANO_USE_GLARE', True)
        setattr(settings, 'MURANO_API_URL', None)
        setattr(settings, 'GLARE_API_URL', None)

        muranoclient = api.muranoclient(self.request)
        self.assertIsNotNone(muranoclient)
        self.assertEqual(client.Client, type(muranoclient))

        self.assertEqual(2, mock_log.warning.call_count)
        mock_log.warning.assert_any_call(
            'Murano API location could not be found in Service '
            'Catalog, using default: http://localhost:8082')
        mock_log.warning.assert_any_call(
            'Glare API location could not be found in Service '
            'Catalog, using default: http://localhost:9494')
