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

import collections
import mock
import testtools

from django.conf import settings
from django.forms import formsets
from django import http
from django.utils.translation import ugettext_lazy as _

from horizon.forms import views as horizon_views

from muranoclient.common import exceptions as exc

from muranodashboard.catalog import tabs as catalog_tabs
from muranodashboard.catalog import views

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class TestCatalogViews(testtools.TestCase):
    def setUp(self):
        super(TestCatalogViews, self).setUp()
        self.mock_request = mock.MagicMock(session={})
        self.env = mock.MagicMock(id='12', name='test_env', status='READY')

        self.addCleanup(mock.patch.stopall)

    def test_is_valid_environment(self):
        mock_env1 = mock.MagicMock(id='13')
        valid_envs = [mock_env1, self.env]
        self.assertTrue(views.is_valid_environment(self.env, valid_envs))

    @mock.patch.object(views, 'env_api')
    def test_get_environments_context(self, mock_env_api):
        mock_env_api.environments_list.return_value = [self.env]
        self.assertIsNotNone(views.get_environments_context(self.mock_request))
        mock_env_api.environments_list.assert_called_with(self.mock_request)

    @mock.patch.object(views, 'api')
    def test_get_categories_list(self, mock_api):
        self.assertEqual([], views.get_categories_list(self.mock_request))
        mock_api.handled_exceptions.assert_called_once_with(self.mock_request)
        mock_api.muranoclient.assert_called_once_with(self.mock_request)

    @mock.patch.object(views, 'env_api')
    def test_create_quick_environment(self, mock_env_api):
        views.create_quick_environment(self.mock_request)
        self.assertTrue(mock_env_api.environment_create.called)

    @mock.patch.object(views, 'pkg_api')
    def test_get_image(self, mock_pkg_api):
        app_id = 13
        result = views.get_image(self.mock_request, app_id)
        self.assertIsInstance(result, http.HttpResponse)
        (mock_pkg_api.get_app_logo.
         assert_called_once_with(self.mock_request, app_id))
        mock_pkg_api.reset_mock()

        mock_pkg_api.get_app_logo.return_value = None
        result = views.get_image(self.mock_request, app_id)
        self.assertIsInstance(result, http.HttpResponseRedirect)
        (mock_pkg_api.get_app_logo.
         assert_called_once_with(self.mock_request, app_id))

    @mock.patch.object(views, 'pkg_api')
    def test_get_supplier_image(self, mock_pkg_api):
        app_id = 13
        result = views.get_supplier_image(self.mock_request, app_id)
        self.assertIsInstance(result, http.HttpResponse)
        (mock_pkg_api.get_app_supplier_logo.
         assert_called_once_with(self.mock_request, app_id))
        mock_pkg_api.reset_mock()

        mock_pkg_api.get_app_supplier_logo.return_value = None
        result = views.get_supplier_image(self.mock_request, app_id)
        self.assertIsInstance(result, http.HttpResponseRedirect)
        (mock_pkg_api.get_app_supplier_logo.
         assert_called_once_with(self.mock_request, app_id))

    @mock.patch.object(views, 'pkg_api')
    @mock.patch('muranodashboard.dynamic_ui.services.version')
    @mock.patch('muranodashboard.dynamic_ui.services.pkg_api')
    def test_quick_deploy_error(self, services_pkg_api,
                                mock_version, views_pkg_api):
        mock_version.check_version.return_value = '0.2'
        app_id = 'app_id'
        self.assertRaises(ValueError, views.quick_deploy,
                          self.mock_request, app_id=app_id)
        (services_pkg_api.get_app_ui.
         assert_called_once_with(self.mock_request, app_id))
        views_pkg_api.get_app_fqn.assert_called_with(self.mock_request, app_id)

    @mock.patch.object(views, 'shortcuts')
    @mock.patch.object(views, 'get_available_environments')
    @mock.patch.object(views, 'http_utils')
    def test_switch(self, mock_http_utls, mock_get_available_environments,
                    mock_shortcuts):
        mock_http_utls.is_safe_url.return_value = True
        self.mock_request.GET = {'redirect': 'redirect_to_foo'}
        mock_env = mock.Mock(id='foo_env_id')
        mock_get_available_environments.return_value = [mock_env]
        mock_shortcuts.redirect.return_value = 'foo_redirect'

        result = views.switch(self.mock_request, 'foo_env_id',
                              redirect_field_name='redirect')
        self.assertEqual('foo_redirect', result)
        self.assertEqual(mock_env, self.mock_request.session['environment'])
        mock_shortcuts.redirect.assert_called_once_with('redirect_to_foo')
        mock_shortcuts.redirect.reset_mock()

        mock_http_utls.is_safe_url.return_value = False
        result = views.switch(self.mock_request, 'foo_env_id',
                              redirect_field_name='redirect')
        self.assertEqual('foo_redirect', result)
        self.assertEqual(mock_env, self.mock_request.session['environment'])
        mock_shortcuts.redirect.assert_called_once_with(
            settings.LOGIN_REDIRECT_URL)

    @mock.patch.object(views, 'env_api')
    def test_get_next_quick_environment_name(self, mock_env_api):
        # Test whether non-matching name is not returned.
        match_env = mock.Mock()
        match_env.configure_mock(name='quick-env-123')
        non_match_env = mock.Mock()
        non_match_env.configure_mock(name='quick-env-foo')
        mock_env_api.environments_list.return_value = [
            match_env, non_match_env
        ]
        result = views.get_next_quick_environment_name(self.mock_request)
        self.assertEqual('quick-env-124', result)

        # Test whether matching name with biggest number is returned.
        non_match_env.configure_mock(name='quick-env-124')
        mock_env_api.environments_list.return_value = [
            match_env, non_match_env
        ]
        result = views.get_next_quick_environment_name(self.mock_request)
        self.assertEqual('quick-env-125', result)

    @mock.patch.object(views, 'api')
    def test_cleaned_latest_apps(self, mock_api):
        foo_app = mock.Mock(id='foo_id')
        bar_app = mock.Mock(id='bar_id')
        mock_api.muranoclient().packages.filter.return_value = [
            foo_app, bar_app
        ]
        self.mock_request.session['latest_apps'] = ['foo', 'bar']

        expected_params = {
            'type': 'Application',
            'catalog': True,
            'id': 'in:foo,bar'
        }

        result = views.cleaned_latest_apps(self.mock_request)
        self.assertEqual([foo_app, bar_app], result)
        self.assertEqual(collections.deque(['foo_id', 'bar_id']),
                         self.mock_request.session['latest_apps'])
        mock_api.muranoclient().packages.filter.assert_called_once_with(
            **expected_params)


class TestLazyWizard(testtools.TestCase):

    @mock.patch.object(views.LazyWizard, 'http_method_names',
                       new_callable=mock.PropertyMock)
    def test_as_view_except_type_error(self, mock_http_method_names):
        mock_http_method_names.return_value = ['patch']

        # Test that first occurrence of type error is thrown.
        kwargs = {'patch': ''}
        expected_error_msg = "You tried to pass in the {0} method name as a "\
                             "keyword argument to LazyWizard(). "\
                             "Don't do that.".format("patch")
        e = self.assertRaises(TypeError, views.LazyWizard.as_view,
                              None, **kwargs)
        self.assertEqual(expected_error_msg, str(e))

        # Test that second occurrence of type error is thrown.
        kwargs = {'foobar': ''}
        expected_error_msg = "LazyWizard() received an invalid keyword "\
                             "'foobar'"
        e = self.assertRaises(TypeError, views.LazyWizard.as_view,
                              None, **kwargs)
        self.assertEqual(expected_error_msg, str(e))

    @mock.patch.object(views.LazyWizard, 'dispatch')
    def test_as_view(self, mock_dispatch):
        form = mock.Mock()
        form.__name__ = 'test_form'
        form.base_fields = {'foo': None, 'bar': None}
        formset = formsets.formset_factory(form)

        mock_request = mock.Mock()
        mock_request.session = {}
        mock_initforms = mock.Mock(return_value=[formset])
        kwargs = {'app_id': 'foo'}
        view = views.LazyWizard.as_view(mock_initforms)

        self.assertTrue(hasattr(view, '__call__'))
        view(mock_request, **kwargs)
        mock_initforms.assert_called_once_with(mock_request, kwargs)
        mock_dispatch.assert_called_once_with(mock_request, **kwargs)


class TestWizard(testtools.TestCase):

    def setUp(self):
        super(TestWizard, self).setUp()
        self.wizard = views.Wizard()
        self.wizard.storage = mock.MagicMock()
        self.wizard.storage.extra_data.__getitem__().name = 'foo_app'
        self.wizard.kwargs = {
            'do_redirect': 'redirect_to_foo',
            'environment_id': 'foo_env_id',
            'app_id': 'foo_app_id'
        }
        self.wizard.request = mock.Mock()
        self.wizard.request.META = {}
        self.wizard.request.session = {'quick_env_id': 'quick_foo_env_id'}
        self.assertEqual('services/wizard_create.html',
                         self.wizard.template_name)

        self.assertEqual(False, self.wizard.do_redirect)
        self.assertEqual('Add Application', self.wizard.page_title)

    def test_get_prefix(self):
        kwargs = {'foo': 'bar'}
        prefix = self.wizard.get_prefix(None, **kwargs)
        self.assertIsInstance(prefix, str)

    def test_get_form_prefix(self):
        self.wizard.steps = mock.Mock()
        self.wizard.steps.step0 = 'foo_step'
        self.wizard.steps.all.index.return_value = 'bar_step'
        self.assertEqual('foo_step', self.wizard.get_form_prefix())
        self.assertEqual('bar_step', self.wizard.get_form_prefix(step='bar'))

    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'env_api')
    @mock.patch.object(views, 'reverse')
    def test_done(self, mock_reverse, mock_env_api, mock_log, mock_messages):
        mock_service = mock.Mock()
        mock_service.service.extract_attributes.return_value = {'foo': 'bar'}
        mock_created_service = mock.Mock()
        setattr(mock_created_service, '?', {'id': 'foo_service_id'})
        mock_env_api.service_create.return_value = mock_created_service

        self.wizard.done([mock_service])

        mock_reverse.assert_any_call(
            "horizon:app-catalog:environments:index")
        mock_reverse.assert_any_call(
            "horizon:app-catalog:environments:services",
            args=('quick_foo_env_id',))
        mock_env_api.service_create.assert_called_once_with(
            self.wizard.request, 'quick_foo_env_id', mock.ANY)

        expected_message = "The 'foo_app' application successfully added to "\
            "environment."
        mock_log.info.assert_called_once_with(expected_message)
        mock_messages.success.assert_called_once_with(
            self.wizard.request, expected_message)

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'env_api')
    @mock.patch.object(views, 'reverse')
    def test_done_except_http_forbidden(self, mock_reverse, mock_env_api,
                                        mock_exceptions):
        mock_reverse.return_value = 'foo_url'
        mock_service = mock.Mock()
        mock_service.service.extract_attributes.return_value = {'foo': 'bar'}
        mock_env_api.service_create.side_effect = exc.HTTPForbidden

        self.wizard.done([mock_service])

        expected_error_msg = _("Sorry, you can't add application right now. "
                               "The environment is deploying.")
        mock_exceptions.handle.assert_called_once_with(
            self.wizard.request, expected_error_msg, redirect='foo_url')

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'env_api')
    @mock.patch.object(views, 'reverse')
    def test_done_except_exception(self, mock_reverse, mock_env_api, mock_log,
                                   mock_exceptions):
        mock_reverse.return_value = 'foo_url'
        mock_service = mock.Mock()
        mock_service.service.extract_attributes.return_value = {'foo': 'bar'}
        mock_env_api.service_create.side_effect = Exception

        self.wizard.done([mock_service])

        expected_error_msg = _('Adding application to an environment failed.')
        mock_log.exception(expected_error_msg)
        mock_env_api.environment_delete.assert_called_once_with(
            self.wizard.request, 'quick_foo_env_id')
        mock_exceptions.handle.assert_called_once_with(
            self.wizard.request, expected_error_msg, redirect='foo_url')

    def test_create_hacked_response(self):
        self.wizard.request.META = {
            horizon_views.ADD_TO_FIELD_HEADER: 'foo_field_id'
        }
        response = self.wizard.create_hacked_response(
            'foo_obj_id', 'foo_obj_name')
        self.assertIsInstance(response, http.HttpResponse)
        self.assertEqual(b'["foo_obj_id", "foo_obj_name"]', response.content)
        self.assertTrue(response.has_header('X-Horizon-Add-To-Field'))
        self.assertEqual('foo_field_id',
                         response['X-Horizon-Add-To-Field'])

    def test_create_hacked_response_empty_response(self):
        response = self.wizard.create_hacked_response(None, None)
        self.assertIsInstance(response, http.HttpResponse)
        self.assertEqual(b'', response.content)

    @mock.patch.object(views, 'utils')
    def test_get_form_initial(self, mock_utils):
        mock_utils.ensure_python_obj.return_value = 'foo_env_id'
        self.wizard.initial_dict = {'foo_step': 'foo'}

        # Test whether correct dict entry is returned.
        result = self.wizard.get_form_initial('foo_step')
        self.assertEqual('foo', result)
        mock_utils.ensure_python_obj.assert_called_once_with('foo_env_id')

        # Test whether init_dict returned because key not found.
        result = self.wizard.get_form_initial('bar_step')
        expected = {
            'request': self.wizard.request,
            'app_id': 'foo_app_id',
            'environment_id': 'foo_env_id'
        }
        for key, val in expected.items():
            self.assertEqual(val, result[key])

        # Test whether alternate env_id is used.
        mock_utils.ensure_python_obj.return_value = None
        result = self.wizard.get_form_initial('bar_step')
        expected = {
            'request': self.wizard.request,
            'app_id': 'foo_app_id',
            'environment_id': 'quick_foo_env_id'
        }
        for key, val in expected.items():
            self.assertEqual(val, result[key])

    @mock.patch.object(
        views, 'nova',
        mock.MagicMock(side_effect=views.nova_exceptions.ClientException))
    def test_get_flavors(self):
        result = self.wizard.get_flavors()

        self.assertEqual('[]', result)
        views.nova.flavor_list.assert_called_once_with(self.wizard.request)

    @mock.patch.object(views, 'nova')
    @mock.patch.object(views, 'quotas')
    @mock.patch.object(views, 'services')
    @mock.patch.object(views, 'api')
    def test_get_context_data(self, mock_api, mock_services, mock_quotas,
                              mock_nova):
        mock_api.muranoclient().environments.get().name = 'foo_env_name'
        mock_services.get_app_field_descriptions.return_value = [
            'foo_field_descr', 'foo_extended_descr'
        ]
        mock_nova.flavor_list.return_value = [
            type('FakeFlavor%s' % k, (object, ),
                 {'id': 'fake_id_%s' % k, 'name': 'fake_name_%s' % k,
                  '_info': {'foo': 'bar'}})
            for k in (1, 2)
        ]

        form = mock.Mock()
        app = mock.Mock(fully_qualified_name='foo_app_fqn')
        app.configure_mock(name='foo_app')

        self.wizard.request.GET = {}
        self.wizard.request.POST = {}
        self.wizard.storage.extra_data.get.return_value = app
        self.wizard.steps = mock.Mock(index='foo_step_index', step0=-1)
        self.wizard.prefix = 'foo_prefix'
        self.wizard.kwargs['do_redirect'] = 'foo_do_redirect'
        self.wizard.kwargs['drop_wm_form'] = 'foo_drop_wm_form'
        context = self.wizard.get_context_data(form)

        expected_context = {
            'type': 'foo_app_fqn',
            'service_name': 'foo_app',
            'app_id': 'foo_app_id',
            'environment_id': 'foo_env_id',
            'environment_name': 'foo_env_name',
            'do_redirect': 'foo_do_redirect',
            'drop_wm_form': 'foo_drop_wm_form',
            'prefix': 'foo_prefix',
            'wizard_id': mock.ANY,
            'field_descriptions': 'foo_field_descr',
            'extended_descriptions': 'foo_extended_descr'
        }
        for key, val in expected_context.items():
            self.assertIn(key, context)
            self.assertEqual(val, context[key])

        mock_api.muranoclient().environments.get.assert_called_with(
            'foo_env_id')
        mock_services.get_app_field_descriptions.assert_called_once_with(
            self.wizard.request, 'foo_app_id', 'foo_step_index')
        mock_nova.flavor_list.assert_called_once_with(self.wizard.request)

    @mock.patch.object(views, 'nova')
    @mock.patch.object(views, 'quotas')
    @mock.patch.object(views, 'env_api')
    @mock.patch.object(views, 'utils')
    @mock.patch.object(views, 'services')
    @mock.patch.object(views, 'api')
    def test_get_context_data_alternate_control_flow(
            self, mock_api, mock_services, mock_utils, mock_env_api,
            mock_quatas, mock_nova):
        form = mock.Mock()
        app = mock.Mock(fully_qualified_name='foo_app_fqn')
        app.configure_mock(name='foo_app')

        mock_api.muranoclient().environments.get().name = 'foo_env_name'
        mock_api.muranoclient().packages.get.return_value = app
        mock_services.get_app_field_descriptions.return_value = [
            'foo_field_descr', 'foo_extended_descr'
        ]
        mock_utils.ensure_python_obj.return_value = None
        mock_env_api.environments_list.return_value = []
        mock_nova.flavor_list.return_value = [
            type('FakeFlavor%s' % k, (object, ),
                 {'id': 'fake_id_%s' % k, 'name': 'fake_name_%s' % k,
                  '_info': {'foo': 'bar'}})
            for k in (1, 2)
        ]

        self.wizard.request.GET = {}
        self.wizard.request.POST = {'wizard_id': 'foo_wizard_id'}
        self.wizard.storage.extra_data = {}
        self.wizard.steps = mock.Mock(index='foo_step_index', step0=0)
        self.wizard.steps.all = []
        self.wizard.prefix = 'foo_prefix'
        context = self.wizard.get_context_data(form)

        expected_context = {
            'type': 'foo_app_fqn',
            'service_name': 'foo_app',
            'app_id': 'foo_app_id',
            'environment_id': None,
            'environment_name': 'quick-env-1',
            'do_redirect': mock.ANY,
            'drop_wm_form': mock.ANY,
            'prefix': 'foo_prefix',
            'wizard_id': 'foo_wizard_id',
            'field_descriptions': 'foo_field_descr',
            'extended_descriptions': 'foo_extended_descr'
        }
        for key, val in expected_context.items():
            self.assertIn(key, context)
            self.assertEqual(val, context[key])
        self.assertEqual(app, self.wizard.storage.extra_data['app'])

        mock_api.muranoclient().packages.get.assert_called_once_with(
            'foo_app_id')
        mock_api.muranoclient().environments.get.assert_called_once_with()
        mock_services.get_app_field_descriptions.assert_called_once_with(
            self.wizard.request, 'foo_app_id', 'foo_step_index')
        mock_nova.flavor_list.assert_called_once_with(self.wizard.request)


class TestIndexView(testtools.TestCase):

    def setUp(self):
        super(TestIndexView, self).setUp()
        self.index_view = views.IndexView()

        self.assertEqual(6, self.index_view.paginate_by)
        self.assertEqual(_("Browse"), self.index_view.page_title)
        self.assertIsNone(self.index_view._more)

        self.index_view.request = mock.Mock()
        self.index_view.request.GET = {
            'category': 'foo_category',
            'search': 'foo_search',
            'order_by': 'foo_col',
            'sort_dir': 'desc',
            'marker': 'foo_marker'
        }

    def test_get_object_id(self):
        mock_datum = mock.Mock(id='foo_datum_id')
        self.assertEqual('foo_datum_id',
                         views.IndexView.get_object_id(mock_datum))

    def test_get_marker(self):
        mock_datum = mock.Mock(id='foo_datum_id')
        self.index_view.object_list = [mock_datum]
        self.assertEqual('foo_datum_id', self.index_view.get_marker())

        self.index_view.object_list = []
        self.assertEqual('', self.index_view.get_marker())

    def test_get_query_params(self):
        expected = {
            'search': 'foo_search',
            'order_by': 'foo_col',
            'sort_dir': 'desc'
        }

        query_params = self.index_view.get_query_params(internal_query=False)
        for key, val in expected.items():
            self.assertEqual(val, query_params[key])

        expected['type'] = 'Application'
        query_params = self.index_view.get_query_params(internal_query=True)
        for key, val in expected.items():
            self.assertEqual(val, query_params[key])

    @mock.patch.object(views, 'pkg_api')
    def test_get_queryset(self, mock_pkg_api):
        mock_pkg_api.package_list.return_value = (
            ['bar_pkg', 'foo_pkg'], False)

        self.index_view.paginate_by = 123
        packages = self.index_view.get_queryset()

        self.assertEqual(['foo_pkg', 'bar_pkg'], packages)
        self.assertFalse(self.index_view._more)
        mock_pkg_api.package_list.assert_called_once_with(
            self.index_view.request, filters=mock.ANY, paginate=True,
            marker='foo_marker', page_size=123, sort_dir='desc',
            limit=123)

    def test_get_template_names(self):
        self.assertEqual(['catalog/index.html'],
                         self.index_view.get_template_names())

    def test_has_next_page(self):
        self.index_view.request.GET = {'sort_dir': 'asc'}
        self.index_view._more = False
        self.assertFalse(self.index_view.has_next_page())

    @mock.patch.object(views, 'pkg_api')
    def test_has_next_page_with_api_query(self, mock_pkg_api):
        mock_pkg_api.package_list.return_value = (['foo'], False)

        self.index_view.get_marker = lambda: 'foo_marker'
        result = self.index_view.has_next_page()

        self.assertTrue(result)
        mock_pkg_api.package_list.assert_called_once_with(
            self.index_view.request, filters=mock.ANY, paginate=True,
            marker='foo_marker', page_size=1)

    def test_has_prev_page(self):
        self.index_view._more = False
        self.index_view.request.GET = {'sort_dir': 'desc'}
        self.assertFalse(self.index_view.has_prev_page())

        self.index_view.request.GET = {'sort_dir': 'asc', 'marker': 'foo'}
        self.assertTrue(self.index_view.has_prev_page())

    def test_paginate_queryset(self):
        result = self.index_view.paginate_queryset({}, 3)
        self.assertEqual((None, None, {}, None), result)

    def test_get_current_category(self):
        self.assertEqual('foo_category',
                         self.index_view.get_current_category())

    @mock.patch.object(views, 'reverse')
    def test_current_page_url(self, mock_reverse):
        mock_reverse.return_value = 'foo_curr_url'
        self.index_view.get_marker = lambda: 'foo_marker'

        result = self.index_view.current_page_url()
        result_parts = urlparse(result).query.split('&')
        expected = "sort_dir=desc&marker=foo_marker&search="\
                   "foo_search&order_by=foo_col".split('&')
        self.assertEqual('foo_curr_url', urlparse(result).path)
        self.assertEqual(sorted(expected), sorted(result_parts))

    @mock.patch.object(views, 'reverse')
    def test_prev_page_url(self, mock_reverse):
        mock_reverse.return_value = 'foo_prev_url'
        self.index_view.get_marker = lambda i: 'foo_marker'

        result = self.index_view.prev_page_url()
        result_parts = urlparse(result).query.split('&')
        expected = "sort_dir=desc&marker=foo_marker&search="\
                   "foo_search&order_by=foo_col".split('&')
        self.assertEqual('foo_prev_url', urlparse(result).path)
        self.assertEqual(sorted(expected), sorted(result_parts))

    @mock.patch.object(views, 'reverse')
    def test_next_page_url(self, mock_reverse):
        mock_reverse.return_value = 'foo_next_url'
        self.index_view.get_marker = lambda: 'foo_marker'

        result = self.index_view.next_page_url()
        result_parts = urlparse(result).query.split('&')
        expected = "sort_dir=asc&marker=foo_marker&search="\
                   "foo_search&order_by=foo_col".split('&')
        self.assertEqual('foo_next_url', urlparse(result).path)
        self.assertEqual(sorted(expected), sorted(result_parts))

    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'get_environments_context')
    @mock.patch.object(views, 'cleaned_latest_apps')
    @mock.patch.object(views, 'get_categories_list')
    def test_get_context_data(self, mock_get_categories_list,
                              mock_cleaned_latest_apps,
                              mock_get_environments_context, mock_reverse):
        mock_get_categories_list.return_value = [
            'foo_category', 'bar_category'
        ]
        mock_cleaned_latest_apps.return_value = ['foo_app', 'bar_app']
        mock_get_environments_context.return_value = {}
        mock_reverse.return_value = 'foo_url'
        mock_token = mock.Mock(tenant={'id': 'foo_tenant_id'})

        setattr(settings, 'MURANO_USE_GLARE', True)

        self.index_view.request.session = {'token': mock_token}
        self.index_view.object_list = []
        context_data = self.index_view.get_context_data()

        expected = {
            'ALL_CATEGORY_NAME': 'All',
            'MURANO_USE_GLARE': True,
            'categories': ['foo_category', 'bar_category'],
            'current_category': 'foo_category',
            'display_repo_url': 'http://apps.openstack.org/#tab=murano-apps',
            'is_paginated': None,
            'latest_list': ['foo_app', 'bar_app'],
            'no_apps': False,
            'object_list': [],
            'page_obj': None,
            'paginator': None,
            'pkg_def_url': 'foo_url',
            'search': 'foo_search',
            'tenant_id': 'foo_tenant_id',
            'view': self.index_view
        }

        for key, val in expected.items():
            self.assertEqual(val, context_data[key])
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')


class TestAppDetailsView(testtools.TestCase):

    def setUp(self):
        super(TestAppDetailsView, self).setUp()
        self.app_details_view = views.AppDetailsView()
        self.app_details_view.request = mock.Mock(GET={})
        self.app_details_view.request.user.service_catalog = ['foo_service']

        self.assertEqual(catalog_tabs.ApplicationTabs,
                         self.app_details_view.tab_group_class)
        self.assertEqual('catalog/app_details.html',
                         self.app_details_view.template_name)
        self.assertEqual('{{ app.name }}', self.app_details_view.page_title)
        self.assertIsNone(self.app_details_view.app)

    @mock.patch.object(views, 'api')
    def test_get_data(self, mock_api):
        mock_api.muranoclient().packages.get.return_value = 'foo_app'
        kwargs = {'application_id': 'foo_app_id'}

        app = self.app_details_view.get_data(**kwargs)

        self.assertEqual('foo_app', app)
        self.assertEqual('foo_app', self.app_details_view.app)
        mock_api.muranoclient().packages.get.assert_called_with(
            'foo_app_id')

    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'get_environments_context')
    def test_get_context_data(self, mock_get_environments_context, mock_api):
        mock_api.muranoclient().packages.get.return_value = 'foo_app'
        mock_get_environments_context.return_value = {}

        context = self.app_details_view.get_context_data()
        expected = {'app': 'foo_app'}
        for key, val in expected.items():
            self.assertEqual(val, context[key])

    @mock.patch.object(views, 'api')
    def test_get_tabs(self, mock_api):
        mock_api.muranoclient().packages.get.return_value = 'foo_app'
        kwargs = {'application_id': 'foo_app_id'}

        tabs = self.app_details_view.get_tabs(self.app_details_view.request,
                                              **kwargs)
        self.assertIsInstance(tabs, catalog_tabs.ApplicationTabs)
        expected_kwargs = {
            'application': 'foo_app', 'application_id': 'foo_app_id'}
        for key, val in expected_kwargs.items():
            self.assertEqual(val, tabs.kwargs[key])
