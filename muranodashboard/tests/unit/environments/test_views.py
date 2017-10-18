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

import base64
from django.conf import settings
from django import http
from django.utils.translation import ugettext_lazy as _
import mock
import sys
import testtools

from horizon import conf

from muranoclient.common import exceptions as exc
from muranodashboard.environments import forms as env_forms
from muranodashboard.environments import tables as env_tables
from muranodashboard.environments import tabs as env_tabs
from muranodashboard.environments import views


@mock.patch.object(views, 'exceptions')
@mock.patch.object(views, 'api')
class TestIndexView(testtools.TestCase):

    def setUp(self):
        super(TestIndexView, self).setUp()
        self.index_view = views.IndexView()
        self.index_view.request = mock.Mock()

        self.assertEqual(env_tables.EnvironmentsTable,
                         self.index_view.table_class)
        self.assertEqual('environments/index.html',
                         self.index_view.template_name)
        self.assertEqual('Environments', self.index_view.page_title)

    def test_get_data(self, mock_api, mock_exc):
        mock_api.environments_list.return_value = ['foo_env', 'bar_env']
        environments = self.index_view.get_data()
        self.assertEqual(['foo_env', 'bar_env'], environments)

    def test_get_data_exception_communication_error(self, mock_api, mock_exc):
        mock_api.environments_list.side_effect = exc.CommunicationError
        self.index_view.get_data()
        mock_exc.handle.assert_called_once_with(
            self.index_view.request, 'Could not connect to Murano API '
                                     'Service, check connection details')

    def test_get_data_exception_http_internal_server_error(
            self, mock_api, mock_exc):
        mock_api.environments_list.side_effect = exc.HTTPInternalServerError
        self.index_view.get_data()
        mock_exc.handle.assert_called_once_with(
            self.index_view.request, 'Murano API Service is not responding. '
                                     'Try again later')

    def test_get_data_exception_http_unauthorized_error(
            self, mock_api, mock_exc):
        mock_api.environments_list.side_effect = exc.HTTPUnauthorized
        self.index_view.get_data()
        mock_exc.handle.assert_called_once_with(
            self.index_view.request, ignore=True, escalate=True)


class TestEnvironmentDetails(testtools.TestCase):

    def setUp(self):
        super(TestEnvironmentDetails, self).setUp()

        mock_request = mock.Mock()
        mock_request.user.service_catalog = None
        mock_token = mock.MagicMock()
        mock_token.tenant.__getitem__.return_value = 'foo_tenant_id'
        mock_request.session = {'token': mock_token}
        mock_tab_group = mock.Mock()

        self.env_details = views.EnvironmentDetails()
        self.env_details.request = mock_request
        self.env_details.tab_group_class = mock_tab_group
        self.env_details.kwargs = {'environment_id': 'foo_env_id'}

        self.assertEqual('services/index.html', self.env_details.template_name)
        self.assertEqual('{{ environment_name }}', self.env_details.page_title)

        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(views, 'reverse_lazy')
    @mock.patch.object(views, 'api')
    def test_get_context_data(self, mock_api, mock_reverse_lazy):
        setattr(settings, 'MURANO_USE_GLARE', False)

        mock_env = mock.Mock()
        mock_env.configure_mock(name='foo_env')
        mock_env.id = 'foo_env_id'
        mock_deployment = mock.Mock(id='foo_deployment')
        mock_reverse_lazy.return_value = 'foo_redirect_url'

        mock_api.environment_get.return_value = mock_env
        mock_api.deployments_list.return_value = [mock_deployment]
        mock_api.deployment_reports.return_value = []

        context = self.env_details.get_context_data()
        expected_context = {
            'tab_group': self.env_details.tab_group_class(),
            'tenant_id': 'foo_tenant_id',
            'environment_name': 'foo_env',
            'poll_interval': conf.HORIZON_CONFIG['ajax_poll_interval'],
            'actions': mock.ANY,
            'url': 'foo_redirect_url',
            'view': self.env_details
        }

        for key, val in expected_context.items():
            self.assertEqual(val, context[key])
        self.assertNotIn('__action_show', context['actions'])
        self.assertNotIn('__action_deploy', context['actions'])

    @mock.patch.object(views, 'reverse_lazy')
    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'api')
    def test_get_context_data_except_exception(
            self, mock_api, mock_exceptions, mock_reverse_lazy):
        mock_reverse_lazy.return_value = 'foo_redirect_url'
        mock_api.environment_get.side_effect = Exception
        expected_msg = "Sorry, this environment doesn't exist anymore"

        self.env_details.get_context_data()

        mock_exceptions.handle.assert_called_once_with(
            self.env_details.request, expected_msg,
            redirect='foo_redirect_url')

    @mock.patch.object(views, 'reverse_lazy')
    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'api')
    def test_get_tabs_except_http_exception(
            self, mock_api, mock_exceptions, mock_reverse_lazy):
        mock_reverse_lazy.return_value = 'foo_redirect_url'
        mock_api.deployments_list.side_effect = exc.HTTPException
        expected_msg = "Unable to retrieve list of deployments"

        result = self.env_details.get_tabs(None)

        self.assertEqual(self.env_details.tab_group_class(), result)
        mock_exceptions.handle.assert_called_once_with(
            self.env_details.request, expected_msg,
            redirect='foo_redirect_url')
        self.env_details.tab_group_class.assert_any_call(None, logs=[])


@mock.patch.object(views, 'api')
class TestDetailServiceView(testtools.TestCase):

    def setUp(self):
        super(TestDetailServiceView, self).setUp()
        self.detail_service_view = views.DetailServiceView()
        self.detail_service_view.kwargs = {
            'service_id': 'foo_service_id',
            'environment_id': 'foo_env_id'
        }
        self.mock_request = mock.Mock(GET={})
        self.mock_request.user.service_catalog = None
        self.mock_request.is_ajax.return_value = True
        self.mock_request.horizon = {
            'async_messages': [('tag', 'msg', 'extra')]
        }
        self.detail_service_view.request = self.mock_request

        self.assertEqual(env_tabs.ServicesTabs,
                         self.detail_service_view.tab_group_class)
        self.assertEqual('services/details.html',
                         self.detail_service_view.template_name)
        self.assertEqual('{{ service_name }}',
                         self.detail_service_view.page_title)

    @mock.patch('horizon.tables.views.MultiTableMixin.get_context_data')
    @mock.patch.object(views, 'reverse')
    def test_get_context_data(
            self, mock_reverse, mock_get_context_data, mock_api):
        mock_service = mock.MagicMock()
        mock_service.configure_mock(name='foo_service_name')
        mock_env = mock.Mock()
        mock_env.configure_mock(name='foo_env_name')
        mock_api.service_get.return_value = mock_service
        mock_api.environment_get.return_value = mock_env
        mock_reverse.return_value = 'foo_reverse_url'
        mock_get_context_data.return_value = {}

        context = self.detail_service_view.get_context_data()

        expected_context = {
            'service': mock_service,
            'service_name': 'foo_service_name',
            'environment_name': 'foo_env_name',
            'custom_breadcrumb': [
                ('foo_env_name', 'foo_reverse_url'),
                (_('Applications'), None)
            ]
        }

        for key, val in expected_context.items():
            self.assertEqual(val, context[key])

        self.assertEqual(mock_service, self.detail_service_view.service)
        self.assertEqual(mock_service, self.detail_service_view._service)
        mock_api.service_get.assert_any_call(
            self.mock_request, 'foo_env_id', 'foo_service_id')
        mock_api.environment_get.assert_any_call(
            self.mock_request, 'foo_env_id')

    @mock.patch.object(views, 'exceptions')
    def test_get_data_except_http_unauthorized(self, mock_exc, mock_api):
        mock_api.service_get.side_effect = exc.HTTPUnauthorized
        self.detail_service_view.get_data()
        mock_exc.handle.assert_called_once_with(self.mock_request)

    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'exceptions')
    def test_get_data_except_http_forbidden(self, mock_exc, mock_reverse,
                                            mock_api):
        mock_api.service_get.side_effect = exc.HTTPForbidden
        mock_reverse.return_value = 'foo_redirect_url'
        self.detail_service_view.get_data()
        mock_exc.handle.assert_called_once_with(
            self.mock_request, _('Unable to retrieve details for service'),
            redirect='foo_redirect_url')

    def test_get_tabs(self, mock_api):
        result = self.detail_service_view.get_tabs(self.mock_request)
        self.assertIsInstance(result, env_tabs.ServicesTabs)


class TestCreateEnvironmentView(testtools.TestCase):

    def setUp(self):
        super(TestCreateEnvironmentView, self).setUp()

        mock_request = mock.Mock(session={})
        mock_request.GET = {'next': 'next_foo_url'}
        mock_request.user.service_catalog = None

        self.create_env_view = views.CreateEnvironmentView()
        self.create_env_view.submit_url = 'foo_reverse_url'
        self.create_env_view.request = mock_request

        self.assertEqual(env_forms.CreateEnvironmentForm,
                         self.create_env_view.form_class)
        self.assertEqual('create_environment_form',
                         self.create_env_view.form_id)
        self.assertEqual(_('Create Environment'),
                         self.create_env_view.modal_header)
        self.assertEqual('environments/create.html',
                         self.create_env_view.template_name)
        self.assertEqual(_('Create Environment'),
                         self.create_env_view.page_title)
        self.assertEqual('environment',
                         self.create_env_view.context_object_name)
        self.assertEqual(_('Create'), self.create_env_view.submit_label)
        self.assertEqual('foo_reverse_url', self.create_env_view.submit_url)

    @mock.patch('muranodashboard.environments.forms.net')
    def test_get_form(self, mock_net):
        mock_net.get_available_networks.return_value = None
        form = self.create_env_view.get_form()

        self.assertIsInstance(form, env_forms.CreateEnvironmentForm)
        self.assertEqual('next_foo_url',
                         self.create_env_view.request.session['next_url'])

    @mock.patch.object(views, 'reverse_lazy')
    @mock.patch.object(views, 'reverse')
    def test_get_success_url(self, mock_reverse, mock_reverse_lazy):
        mock_reverse.return_value = 'foo_reverse_url'
        mock_reverse_lazy.return_value = 'foo_reverse_lazy_url'

        self.create_env_view.request.session['next_url'] = 'foo_next_url'
        self.assertEqual('foo_next_url',
                         self.create_env_view.get_success_url())

        del self.create_env_view.request.session['next_url']
        self.create_env_view.request.session['env_id'] = 'foo_env_id'
        self.assertEqual('foo_reverse_url',
                         self.create_env_view.get_success_url())
        self.assertNotIn('env_id', self.create_env_view.request.session)
        mock_reverse.assert_called_once_with(
            "horizon:app-catalog:environments:services", args=['foo_env_id'])

        self.assertEqual('foo_reverse_lazy_url',
                         self.create_env_view.get_success_url())
        mock_reverse_lazy.assert_called_once_with(
            'horizon:app-catalog:environments:index')


@mock.patch.object(views, 'reverse')
@mock.patch.object(views, 'api')
class TestDeploymentDetailsView(testtools.TestCase):

    def setUp(self):
        super(TestDeploymentDetailsView, self).setUp()

        self.mock_request = mock.Mock(session={}, GET={})
        self.mock_request.user.service_catalog = None

        self.deployment_details_view = views.DeploymentDetailsView()
        self.deployment_details_view.request = self.mock_request
        self.deployment_details_view.kwargs = {
            'deployment_id': 'foo_deployment_id',
            'environment_id': 'foo_env_id'
        }

        self.assertEqual(env_tabs.DeploymentDetailsTabs,
                         self.deployment_details_view.tab_group_class)
        self.assertEqual(env_tables.EnvConfigTable,
                         self.deployment_details_view.table_class)
        self.assertEqual('deployments/reports.html',
                         self.deployment_details_view.template_name)
        self.assertEqual('Deployment at {{ deployment_start_time }}',
                         self.deployment_details_view.page_title)

    def test_get_context_data(self, mock_api, mock_reverse):
        mock_env = mock.Mock()
        mock_env.configure_mock(name='foo_env_name')
        mock_api.muranoclient().deployments.list.return_value = []
        mock_api.environment_get.return_value = mock_env
        mock_api.get_deployment_start.return_value = 'foo_deployment_start'
        mock_reverse.return_value = 'foo_reverse_url'

        context = self.deployment_details_view.get_context_data()

        expected_context = {
            'environment_id': 'foo_env_id',
            'environment_name': 'foo_env_name',
            'deployment_start_time': 'foo_deployment_start',
            'custom_breadcrumb': [
                ('foo_env_name', 'foo_reverse_url'),
                (_('Deployments'), None)
            ]
        }

        for key, val in expected_context.items():
            self.assertEqual(val, context[key])

        mock_api.environment_get.assert_called_once_with(
            self.mock_request, 'foo_env_id')
        mock_api.get_deployment_start.assert_called_once_with(
            self.mock_request, 'foo_env_id', 'foo_deployment_id')

    def test_get_deployment(self, mock_api, mock_reverse):
        mock_api.get_deployment_descr.return_value = 'foo_deployment_descr'

        self.deployment_details_view.environment_id = 'foo_env_id'
        self.deployment_details_view.deployment_id = 'foo_deployment_id'

        self.assertEqual('foo_deployment_descr',
                         self.deployment_details_view.get_deployment())
        mock_api.get_deployment_descr.assert_called_once_with(
            self.mock_request, 'foo_env_id', 'foo_deployment_id')

    @mock.patch.object(views, 'exceptions')
    def test_get_deployment_negative(self, mock_exc, mock_api, mock_reverse):
        mock_reverse.return_value = 'foo_reverse_url'

        self.deployment_details_view.environment_id = 'foo_env_id'
        self.deployment_details_view.deployment_id = 'foo_deployment_id'

        for exception in [exc.HTTPInternalServerError, exc.HTTPNotFound]:
            mock_api.get_deployment_descr.side_effect = exception

            deployment = self.deployment_details_view.get_deployment()

            self.assertIsNone(deployment)
            mock_api.get_deployment_descr.assert_called_with(
                self.mock_request, 'foo_env_id', 'foo_deployment_id')
            mock_exc.handle.assert_called_with(
                self.mock_request,
                _("Deployment with id foo_deployment_id "
                  "doesn't exist anymore"), redirect='foo_reverse_url')

    def test_get_logs(self, mock_api, _):
        mock_api.deployment_reports.return_value = ['foo_log']

        self.deployment_details_view.environment_id = 'foo_env_id'
        self.deployment_details_view.deployment_id = 'foo_deployment_id'

        self.assertEqual(['foo_log'], self.deployment_details_view.get_logs())

    @mock.patch.object(views, 'exceptions')
    def test_get_logs_negative(self, mock_exc, mock_api, mock_reverse):
        mock_reverse.return_value = 'foo_reverse_url'

        self.deployment_details_view.environment_id = 'foo_env_id'
        self.deployment_details_view.deployment_id = 'foo_deployment_id'

        for exception in [exc.HTTPInternalServerError, exc.HTTPNotFound]:
            mock_api.deployment_reports.side_effect = exception

            logs = self.deployment_details_view.get_logs()

            self.assertEqual([], logs)
            mock_api.deployment_reports.assert_called_with(
                self.mock_request, 'foo_env_id', 'foo_deployment_id')
            mock_exc.handle.assert_called_with(
                self.mock_request,
                _("Deployment with id foo_deployment_id "
                  "doesn't exist anymore"), redirect='foo_reverse_url')

    def test_get_tabs(self, mock_api, _):
        mock_api.get_deployment_descr.return_value = 'foo_deployment_descr'
        mock_api.deployment_reports.return_value = ['foo_log']

        result = self.deployment_details_view.get_tabs(self.mock_request)
        self.assertIsInstance(result, env_tabs.DeploymentDetailsTabs)


class TestJSONView(testtools.TestCase):

    @mock.patch.object(views, 'api')
    def test_get(self, mock_api):
        mock_api.load_environment_data.return_value = "{'foo': 'bar'}"
        mock_request = mock.Mock()

        kwargs = {'environment_id': 'foo_env_id'}
        result = views.JSONView.get(mock_request, **kwargs)

        self.assertIsInstance(result, http.HttpResponse)
        self.assertEqual(b"{'foo': 'bar'}", result.content)
        mock_api.load_environment_data.assert_called_once_with(mock_request,
                                                               'foo_env_id')


class TestJSONResponse(testtools.TestCase):

    def test_init(self):
        kwargs = {'content_type': 'json'}
        json_response = views.JSONResponse(**kwargs)
        self.assertIsInstance(json_response, views.JSONResponse)
        self.assertEqual(b'{}', json_response.content)

        json_response = views.JSONResponse(content='foo', **kwargs)
        self.assertIsInstance(json_response, views.JSONResponse)
        self.assertEqual(b'"foo"', json_response.content)


class TestStartActionView(testtools.TestCase):

    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'api')
    def test_post(self, mock_api, mock_reverse):
        mock_api.action_allowed.return_value = True
        mock_reverse.return_value = 'foo_reverse_url'
        mock_request = mock.Mock()

        result = views.StartActionView.post(
            mock_request, 'foo_env_id', 'foo_action_id')
        self.assertIsInstance(result, views.JSONResponse)
        self.assertEqual(b'{"url": "foo_reverse_url"}', result.content)
        mock_api.run_action.assert_called_once_with(
            mock_request, 'foo_env_id', 'foo_action_id')

        mock_api.action_allowed.return_value = False
        result = views.StartActionView.post(
            mock_request, 'foo_env_id', 'foo_action_id')
        self.assertIsInstance(result, views.JSONResponse)
        self.assertEqual(b'{}', result.content)
        mock_api.action_allowed.assert_called_with(mock_request, 'foo_env_id')


class TestActionResultView(testtools.TestCase):

    def test_is_file_returned(self):
        test_result = {'result': {'?': {'type': 'io.murano.File'}}}
        self.assertTrue(views.ActionResultView.is_file_returned(test_result))

    def test_is_file_returned_negative(self):
        self.assertFalse(
            views.ActionResultView.is_file_returned({}))

    def test_compose_response(self):
        response = views.ActionResultView.compose_response('foo')
        self.assertIsInstance(response, http.HttpResponse)
        self.assertEqual(b'"foo"', response.content)
        self.assertTrue(response.has_header('Content-Disposition'))
        self.assertTrue(response.has_header('Content-Length'))
        self.assertEqual('attachment; filename=result.json',
                         response['Content-Disposition'])

    def test_compose_response_is_exc(self):
        response = views.ActionResultView.compose_response('foo', is_exc=True)
        self.assertIsInstance(response, http.HttpResponse)
        self.assertEqual(b'"foo"', response.content)
        self.assertTrue(response.has_header('Content-Disposition'))
        self.assertTrue(response.has_header('Content-Length'))
        self.assertEqual('attachment; filename=exception.json',
                         response['Content-Disposition'])

    def test_compose_response_is_file(self):
        base64_encoding = None
        if sys.version_info[0] == 2:
            base64_encoding = base64.b64encode(bytes('foo_base_64'))
        elif sys.version_info[0] == 3:
            base64_encoding = base64.b64encode(bytes('foo_base_64', 'UTF-8'))
        test_result = {
            'filename': 'filename.foo',
            'mimeType': 'foo_mime_type',
            'base64Content': base64_encoding
        }
        response = views.ActionResultView.compose_response(
            test_result, is_file=True)
        self.assertIsInstance(response, http.HttpResponse)
        self.assertEqual(b'foo_base_64', response.content)
        self.assertTrue(response.has_header('Content-Disposition'))
        self.assertTrue(response.has_header('Content-Length'))
        self.assertEqual('attachment; filename=filename.foo',
                         response['Content-Disposition'])

    @mock.patch.object(views, 'api_utils')
    def test_get(self, mock_api_utils):
        mock_api_utils.muranoclient().actions.get_result.return_value =\
            {'result': 'foo_result', 'foo': 'bar'}
        mock_request = mock.Mock()

        action_result_view = views.ActionResultView()
        result = action_result_view.get(
            mock_request, 'foo_env_id', 'foo_task_id', 'poll')
        self.assertIsInstance(result, views.JSONResponse)
        self.assertEqual(b'{"foo": "bar"}', result.content)

        mock_api_utils.muranoclient().actions.get_result.\
            assert_called_once_with('foo_env_id', 'foo_task_id')

    @mock.patch.object(views, 'api_utils')
    def test_get_with_compose_response(self, mock_api_utils):
        mock_api_utils.muranoclient().actions.get_result.return_value =\
            {'result': 'foo_result', 'isException': False}
        mock_request = mock.Mock()

        action_result_view = views.ActionResultView()
        result = action_result_view.get(
            mock_request, 'foo_env_id', 'foo_task_id', None)
        self.assertIsInstance(result, http.HttpResponse)
        self.assertEqual(b'"foo_result"', result.content)

        mock_api_utils.muranoclient().actions.get_result.\
            assert_called_once_with('foo_env_id', 'foo_task_id')

    @mock.patch.object(views, 'api_utils')
    def test_get_without_polling_result(self, mock_api_utils):
        mock_api_utils.muranoclient().actions.get_result.return_value = None
        mock_request = mock.Mock()

        action_result_view = views.ActionResultView()
        result = action_result_view.get(
            mock_request, 'foo_env_id', 'foo_task_id', None)
        self.assertIsInstance(result, views.JSONResponse)
        self.assertEqual(b'{}', result.content)

        mock_api_utils.muranoclient().actions.get_result.\
            assert_called_once_with('foo_env_id', 'foo_task_id')


class TestDeploymentHistoryView(testtools.TestCase):

    def setUp(self):
        super(TestDeploymentHistoryView, self).setUp()
        self.deployment_history_view = views.DeploymentHistoryView()

        self.mock_request = mock.Mock()
        self.deployment_history_view.request = self.mock_request
        self.deployment_history_view.environment_id = mock.sentinel.env_id

        self.assertEqual(env_tables.DeploymentHistoryTable,
                         self.deployment_history_view.table_class)
        self.assertEqual('environments/index.html',
                         self.deployment_history_view.template_name)
        self.assertEqual(_('Deployment History'),
                         self.deployment_history_view.page_title)

    @mock.patch.object(views, 'api', autospec=True)
    def test_get_data(self, mock_env_api):
        mock_env_api.deployment_history.return_value = \
            [mock.sentinel.deployment_history]

        result = self.deployment_history_view.get_data()
        self.assertEqual([mock.sentinel.deployment_history], result)

    @mock.patch.object(views, 'exceptions', autospec=True)
    @mock.patch.object(views, 'api', autospec=True)
    def test_get_data_except_http_unauthorized(self, mock_env_api,
                                               mock_exceptions):
        mock_env_api.deployment_history.side_effect = \
            exc.HTTPUnauthorized

        self.assertEqual([], self.deployment_history_view.get_data())
        mock_exceptions.handle.assert_called_once_with(self.mock_request)

    @mock.patch.object(views, 'exceptions', autospec=True)
    @mock.patch.object(views, 'reverse', autospec=True)
    @mock.patch.object(views, 'api', autospec=True)
    def test_get_data_except_http_forbidden(self, mock_env_api, mock_reverse,
                                            mock_exceptions):
        mock_env_api.deployment_history.side_effect = \
            exc.HTTPForbidden
        mock_reverse.return_value = mock.sentinel.redirect_url

        self.assertEqual([], self.deployment_history_view.get_data())
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:environments:services',
            args=[mock.sentinel.env_id])
        mock_exceptions.handle.assert_called_once_with(
            self.mock_request, _('Unable to retrieve deployment history.'),
            redirect=mock.sentinel.redirect_url)
