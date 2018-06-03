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

from django.core.files import storage
from django import http
from django.utils.translation import ugettext_lazy as _

import mock

from horizon import exceptions as horizon_exceptions
from muranoclient.common import exceptions as exc

from muranodashboard.packages import consts as packages_consts
from muranodashboard.packages import forms
from muranodashboard.packages import tables
from muranodashboard.packages import views

from openstack_dashboard.test import helpers


class TestPackageView(helpers.APIMockTestCase):

    use_mox = True

    def setUp(self):
        super(TestPackageView, self).setUp()

        fake_response = {'status_code': 200}
        self.mock_request = mock.Mock(return_value=fake_response)

        self.addCleanup(mock.patch.stopall)

    @mock.patch('muranodashboard.packages.views.api.muranoclient')
    def test_download_package(self, mock_client):
        mock_client().packages.download.return_value = {}

        response =\
            views.download_packge(self.mock_request, 'test_app_name', None)
        expected_response = {
            'Content-Type': 'application/octet-stream',
            'Content-Disposition': 'filename=test_app_name.zip'
        }

        self.assertIsInstance(response, http.HttpResponse)
        for key, val in expected_response.items():
            self.assertIn(key.lower(), response._headers)
            self.assertEqual((key, val), response._headers[key.lower()])

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'LOG')
    @mock.patch('muranodashboard.packages.views.api.muranoclient')
    def test_download_package_except_http_exception(self, mock_client,
                                                    mock_log, mock_reverse,
                                                    mock_exc):
        mock_client().packages.download.side_effect = exc.HTTPException
        mock_reverse.return_value = 'test_redirect'

        views.download_packge(self.mock_request, 'test_app_name', None)

        mock_log.exception.assert_called_once_with(
            'Something went wrong during package downloading')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')
        mock_exc.handle.assert_called_once_with(
            self.mock_request, 'Unable to download package.',
            redirect='test_redirect')

    def test_is_app(self):
        mock_wizard = mock.Mock()
        mock_step_data = mock.MagicMock()
        mock_step_data.__getitem__().type = 'Application'
        mock_wizard.storage.get_step_data.return_value = mock_step_data
        self.assertTrue(views.is_app(mock_wizard))

        mock_step_data.__getitem__().type = 'Non-Application'
        mock_wizard.storage.get_step_data.return_value = mock_step_data
        self.assertFalse(views.is_app(mock_wizard))


class TestDetailView(helpers.APIMockTestCase):

    use_mox = True

    def setUp(self):
        super(TestDetailView, self).setUp()

        self.detail_view = views.DetailView()
        fake_response = {'status_code': 200}
        self.mock_request = mock.Mock(return_value=fake_response)
        self.detail_view.request = self.mock_request
        self.detail_view.kwargs = {'app_id': 'foo'}

        self.assertEqual('packages/detail.html',
                         self.detail_view.template_name)
        self.assertEqual('{{ app.name }}', self.detail_view.page_title)

        self.addCleanup(mock.patch.stopall)

    @mock.patch('muranodashboard.packages.views.api.muranoclient')
    def test_get_context_data(self, mock_client):
        mock_client().packages.get.return_value = 'test_app'

        context = self.detail_view.get_context_data()
        self.assertIn('app', context)
        self.assertIn('view', context)
        self.assertIsInstance(context['view'], views.DetailView)
        self.assertEqual('test_app', context['app'])

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'reverse')
    @mock.patch('muranodashboard.packages.views.api.muranoclient')
    def test_get_context_data_except_exception(self, mock_client, mock_reverse,
                                               mock_exc):
        mock_client().packages.get.side_effect = Exception
        mock_reverse.return_value = 'test_redirect'

        self.detail_view.get_context_data()

        mock_exc.handle.assert_called_once_with(
            self.mock_request, 'Unable to retrieve package details.',
            redirect='test_redirect')


class TestModifyPackageView(helpers.APIMockTestCase):

    use_mox = True

    def setUp(self):
        super(TestModifyPackageView, self).setUp()

        self.modify_pkg_view = views.ModifyPackageView()
        fake_response = {'status_code': 200}
        self.mock_request = mock.Mock(return_value=fake_response, META=[])
        self.modify_pkg_view.request = self.mock_request
        self.modify_pkg_view.kwargs = {'app_id': 'foo'}

        self.assertEqual(forms.ModifyPackageForm,
                         self.modify_pkg_view.form_class)
        self.assertEqual('packages/modify_package.html',
                         self.modify_pkg_view.template_name)
        self.assertEqual('Modify Package', self.modify_pkg_view.page_title)

        self.addCleanup(mock.patch.stopall)

    @mock.patch('muranodashboard.packages.views.api.muranoclient')
    def test_get_initial(self, mock_client):
        mock_package = mock.Mock()
        mock_client().packages.get.return_value = mock_package
        expected_result = {
            'package': mock_package,
            'app_id': 'foo'
        }

        result = self.modify_pkg_view.get_initial()

        for key, val in expected_result.items():
            self.assertEqual(val, result[key])

    def test_get_context_data(self):
        mock_form = mock.Mock(return_value=type(
            'FakeForm', (object, ), {'initial': {
                'package': type(
                    'FakeFormInner', (object, ), {'type': 'test_type'}
                )
            }}
        ))
        self.modify_pkg_view.get_form = mock_form
        expected_context = {
            'app_id': 'foo',
            'type': 'test_type',
            'form': mock_form
        }

        context = self.modify_pkg_view.get_context_data(form=mock_form)

        self.assertIn('view', context)
        self.assertIsInstance(context['view'], views.ModifyPackageView)

        for key, val in expected_context.items():
            self.assertIn(key, context)
            self.assertEqual(val, context[key])
        self.modify_pkg_view.get_form.assert_called_once_with()


class TestImportPackageWizard(helpers.APIMockTestCase):

    use_mox = True

    def setUp(self):
        super(TestImportPackageWizard, self).setUp()

        fake_response = {'status_code': 200}
        self.mock_request = mock.MagicMock(return_value=fake_response, META=[])

        self.import_pkg_wizard = views.ImportPackageWizard()
        self.import_pkg_wizard.request = self.mock_request

        all_cleaned_data = {
            'enabled': False,
            'is_public': True,
            'package': 'test_package',
            'import_type': 'test_import_type',
            'url': 'test_url',
            'repo_version': 'test_repo_version',
            'repo_name': 'test_repo_name',
            'tags': 'foo,bar,baz,qux'
        }
        self.import_pkg_wizard.get_all_cleaned_data = lambda: all_cleaned_data
        self.import_pkg_wizard.steps = mock.Mock(current='upload')

        self.assertIsInstance(self.import_pkg_wizard.file_storage,
                              storage.FileSystemStorage)
        self.assertEqual('packages/upload.html',
                         self.import_pkg_wizard.template_name)
        self.assertEqual({'add_category': views.is_app},
                         self.import_pkg_wizard.condition_dict)
        self.assertEqual('Import Package',
                         self.import_pkg_wizard.page_title)

        self.addCleanup(mock.patch.stopall)

    def test_get_form_initial(self):
        self.mock_request.GET = {
            'url': 'test_url',
            'repo_name': 'test_repo_name',
            'repo_version': 'test_repo_version',
            'import_type': 'test_import_type'
        }
        expected_dict = {
            'foo': 'bar',
            'url': 'test_url',
            'repo_name': 'test_repo_name',
            'repo_version': 'test_repo_version',
            'import_type': 'test_import_type'
        }

        self.import_pkg_wizard.initial_dict = {'upload': {'foo': 'bar'}}
        initial_dict = self.import_pkg_wizard.get_form_initial('upload')

        for key, val in expected_dict.items():
            self.assertIn(key, initial_dict)
            self.assertEqual(val, initial_dict[key])

    def test_get_context_data(self):
        mock_form = mock.Mock()

        self.import_pkg_wizard.storage = mock.Mock(
            extra_data={'extra': 'data'})
        self.import_pkg_wizard.prefix = 'test_prefix'

        expected_result = {
            'form': mock_form,
            'modal_backdrop': 'static',
            'extra': 'data',
            'murano_repo_url': 'http://apps.openstack.org',
            'wizard': {
                'steps': self.import_pkg_wizard.steps,
                'form': mock_form
            }
        }

        result = self.import_pkg_wizard.get_context_data(form=mock_form)

        self.assertIn('view', result)
        self.assertIsInstance(result['view'], views.ImportPackageWizard)

        for key, val in expected_result.items():
            if isinstance(val, dict):
                for key_, val_ in val.items():
                    self.assertEqual(val_, val[key_])
            else:
                self.assertEqual(val, result[key])

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'glance')
    @mock.patch.object(views, 'api')
    def test_done(self, mock_api, mock_glance, mock_reverse, mock_exc):
        mock_storage = mock.MagicMock()
        mock_storage.get_step_data().__getitem__.return_value =\
            mock.Mock(id='test_package_id')
        mock_storage.get_step_data().get.side_effect = [
            [mock.Mock(id='test_dep_pkg_id', fully_qualified_name='fqn')],
            [{'id': 'test_image_id'}]
        ]

        self.import_pkg_wizard.storage = mock_storage
        self.import_pkg_wizard.form_list = {}

        self.import_pkg_wizard.done({})

        expected_api_mock_calls = [
            mock.call('test_dep_pkg_id',
                      {'enabled': False, 'is_public': True}),
            mock.call('test_package_id',
                      {'enabled': False, 'is_public': True,
                       'tags': ['foo', 'bar', 'baz', 'qux']}),
        ]

        mock_api.muranoclient().packages.update.assert_has_calls(
            expected_api_mock_calls)
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')
        mock_glance.glanceclient().images.update.assert_called_once_with(
            mock.ANY, is_public=True)
        mock_storage.get_step_data.assert_any_call('upload')
        mock_storage.get_step_data().get.assert_any_call('dependencies', [])
        mock_storage.get_step_data().get.assert_any_call('images', [])
        mock_exc.handle.assert_not_called()

    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'glance')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'api')
    def test_done_except_murano_client_exception(self, mock_api, mock_messages,
                                                 mock_log, *args):
        mock_storage = mock.MagicMock()
        mock_storage.get_step_data().__getitem__.return_value =\
            mock.Mock(id='test_package_id')
        mock_storage.get_step_data().get.side_effect = [
            [mock.Mock(id='test_dep_pkg_id', fully_qualified_name='fqn')],
            [{'id': 'test_image_id'}]
        ]
        mock_api.muranoclient().packages.update.side_effect = [
            Exception("murano client error message."), None
        ]

        self.import_pkg_wizard.storage = mock_storage
        self.import_pkg_wizard.form_list = {}

        self.import_pkg_wizard.done({})

        expected_msg = "Couldn't update package {0} parameters. Error: {1}"\
                       .format('fqn', 'murano client error message.')
        mock_log.warning.assert_called_once_with(expected_msg)
        mock_messages.warning.assert_called_once_with(
            self.mock_request, expected_msg)

    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'glance')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'messages')
    def test_done_except_glance_init_exception(self, mock_messages, mock_log,
                                               mock_glance, *args):
        """Test null glance client with installed images throws exception."""
        mock_storage = mock.MagicMock()
        mock_storage.get_step_data().__getitem__.return_value =\
            mock.Mock(id='test_package_id')
        mock_storage.get_step_data().get.side_effect = [
            [mock.Mock(id='test_dep_pkg_id', fully_qualified_name='fqn')],
            [{'id': 'foo_image_id', 'name': 'foo_image_name'},
             {'id': 'bar_image_id', 'name': 'bar_image_name'}]
        ]
        mock_glance.glanceclient.return_value = None

        self.import_pkg_wizard.storage = mock_storage
        self.import_pkg_wizard.form_list = {}

        self.import_pkg_wizard.done({})

        expected_msg = "Couldn't initialise glance v1 client, therefore "\
                       "could not make the following images public: {0}"\
                       .format('foo_image_name bar_image_name')
        mock_log.warning.assert_called_once_with(expected_msg)
        mock_messages.warning.assert_called_once_with(
            self.mock_request, expected_msg)

    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'glance')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'messages')
    def test_done_except_glance_update_exception(self, mock_messages, mock_log,
                                                 mock_glance, *args):
        mock_storage = mock.MagicMock()
        mock_storage.get_step_data().__getitem__.return_value =\
            mock.Mock(id='test_package_id')
        mock_storage.get_step_data().get.side_effect = [
            [mock.Mock(id='test_dep_pkg_id', fully_qualified_name='fqn')],
            [{'id': 'test_image_id', 'name': 'test_image_name'}]
        ]
        glance_exception = Exception("glance client error message")
        mock_glance.glanceclient().images.update.side_effect =\
            glance_exception

        self.import_pkg_wizard.storage = mock_storage
        self.import_pkg_wizard.form_list = {}

        self.import_pkg_wizard.done({})

        expected_msg = "Error {0} occurred while setting image {1}, {2} "\
                       "public".format(glance_exception, "test_image_name",
                                       "test_image_id")
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_messages.error.assert_called_once_with(
            self.mock_request, expected_msg)

    @mock.patch.object(views, 'glance')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'api')
    def test_done_except_http_forbidden(self, mock_api, mock_exc, mock_log,
                                        mock_reverse, _):
        mock_storage = mock.MagicMock()
        mock_storage.get_step_data().__getitem__.return_value =\
            mock.Mock(id='test_package_id')
        mock_storage.get_step_data().get.side_effect = [
            [mock.Mock(id='test_dep_pkg_id', fully_qualified_name='fqn')],
            [{'id': 'test_image_id', 'name': 'test_image_name'}]
        ]
        mock_api.muranoclient().packages.update.side_effect = [
            None, exc.HTTPForbidden
        ]
        mock_reverse.return_value = 'test_redirect'

        self.import_pkg_wizard.storage = mock_storage
        self.import_pkg_wizard.form_list = {}

        self.import_pkg_wizard.done({})

        expected_msg = "You are not allowed to change this properties of the "\
                       "package"
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_exc.handle.assert_called_once_with(
            self.mock_request, expected_msg, redirect='test_redirect')

    @mock.patch.object(views, 'glance')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'api')
    def test_done_except_http_exception(self, mock_api, mock_exc, mock_log,
                                        mock_reverse, _):
        mock_storage = mock.MagicMock()
        mock_storage.get_step_data().__getitem__.return_value =\
            mock.Mock(id='test_package_id')
        mock_storage.get_step_data().get.side_effect = [
            [mock.Mock(id='test_dep_pkg_id', fully_qualified_name='fqn')],
            [{'id': 'test_image_id', 'name': 'test_image_name'}]
        ]
        mock_api.muranoclient().packages.update.side_effect = [
            None, exc.HTTPException
        ]
        mock_reverse.return_value = 'test_redirect'

        self.import_pkg_wizard.storage = mock_storage
        self.import_pkg_wizard.form_list = {}

        self.import_pkg_wizard.done({})

        expected_msg = 'Modifying package failed'
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_exc.handle.assert_called_once_with(
            self.mock_request, 'Unable to modify package',
            redirect='test_redirect')

    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'LOG')
    def test_handle_exception(self, mock_log, mock_exc, mock_reverse):
        mock_exception = mock.Mock()
        mock_exception.details = '{"error": {"message": "test_error_message"}}'
        mock_reverse.return_value = 'test_redirect'

        self.import_pkg_wizard.request = self.mock_request
        self.import_pkg_wizard._handle_exception(mock_exception)

        expected_msg = 'Uploading package failed. {0}'\
                       .format('test_error_message')
        mock_log.exception.assert_called_once_with(expected_msg)
        mock_exc.handle.assert_called_once_with(
            self.mock_request, expected_msg, redirect='test_redirect')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')

    @mock.patch.object(views, 'json')
    def test_handle_exception_except_value_error(self, mock_json):
        mock_json.loads.side_effect = ValueError('test_error_message')
        original_e = ValueError('original_error_message')
        setattr(original_e, 'details', 'error_details')
        with self.assertRaisesRegex(ValueError, 'original_error_message'):
            self.import_pkg_wizard._handle_exception(original_e)

    @mock.patch.object(views, 'glance')
    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranoclient_utils')
    def test_process_step(self, mock_murano_utils, mock_api, mock_messages, _):
        mock_package = mock.Mock()
        mock_package.manifest = {'FullName': 'foo'}
        mock_original_package = mock.Mock()
        mock_original_package.file.return_value = 'foo_file'
        mock_package.requirements.return_value =\
            {'foo': mock_original_package, 'bar': mock.Mock()}
        mock_murano_utils.ensure_images.return_value = [
            {'id': 1, 'name': 'foo'}, {'id': 2, 'name': 'bar'}
        ]
        mock_murano_utils.Package.from_file.return_value = mock_package

        mock_dependency_package = mock.Mock()
        mock_result_package = mock.Mock(id='result_package_id')
        mock_api.muranoclient().packages.create.side_effect = [
            mock_dependency_package,
            mock_result_package
        ]

        mock_form = mock.Mock()
        mock_form.cleaned_data = {
            'import_type': 'upload',
            'package': mock.Mock(file='test_package_file')
        }
        mock_form.data = {
            'dependencies': ['dep1', 'dep2'],
            'images': ['img1', 'img2']
        }

        step_data = self.import_pkg_wizard.process_step(mock_form)

        for expected_key in ('images', 'dependencies', 'package'):
            self.assertIn(expected_key, step_data)
        self.assertIn({'id': 1, 'name': 'foo'}, step_data['images'])
        self.assertIn({'id': 2, 'name': 'bar'}, step_data['images'])
        self.assertEqual([mock_dependency_package], step_data['dependencies'])
        self.assertEqual(mock_result_package, step_data['package'])
        self.assertEqual(2, mock_murano_utils.ensure_images.call_count)

        mock_murano_utils.Package.from_file.assert_called_once_with(
            'test_package_file')
        mock_api.muranoclient().packages.create.assert_any_call(
            mock.ANY, {'foo': 'foo_file'})
        mock_package.requirements.assert_called_once_with(
            base_url=packages_consts.MURANO_REPO_URL)
        mock_messages.success.assert_any_call(
            self.mock_request, 'Package bar uploaded')
        mock_messages.success.assert_any_call(
            self.mock_request, 'Package foo uploaded')

    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'muranoclient_utils')
    def test_process_step_except_from_file_exception(
            self, mock_murano_utils, mock_log, mock_reverse):
        mock_reverse.return_value = 'test_redirect'
        mock_form = mock.Mock()
        mock_form.cleaned_data = {
            'import_type': 'upload',
            'package': mock.Mock(file='test_package_file')
        }

        errors = (('(404) test_404_error', "Package creation failed."
                                           "Reason: Can't find Package name "
                                           "from repository."),
                  ('random error message', "Package creation failed.Reason: "
                                           "random error message"))
        for error_message, expected_error_message in errors:
            exception = Exception(error_message)
            exception.message = error_message
            mock_murano_utils.Package.from_file.side_effect = exception

            with self.assertRaisesRegex(horizon_exceptions.Http302,
                                        None):
                self.import_pkg_wizard.process_step(mock_form)

            mock_log.exception.assert_called_once_with(expected_error_message)
            mock_reverse.assert_called_once_with(
                'horizon:app-catalog:packages:index')
            mock_log.exception.reset_mock()
            mock_reverse.reset_mock()

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranoclient_utils')
    @mock.patch.object(views, 'glance')
    def test_process_step_except_package_create_exception(
            self, mock_glance, mock_murano_utils, mock_api, mock_log,
            mock_reverse, mock_messages, mock_exc):
        mock_murano_utils.Package.from_file.side_effect = None
        mock_reverse.return_value = 'test_redirect'
        mock_package = mock.Mock()
        mock_package.manifest = {'FullName': 'foo'}
        mock_murano_utils.Package.from_file.return_value = mock_package

        mock_form = mock.Mock()
        mock_form.cleaned_data = {
            'import_type': 'upload',
            'package': mock.Mock(file='test_package_file')
        }
        mock_form.data = {
            'dependencies': [],
            'images': []
        }

        # Test that first occurrence of exception is handled.
        mock_package.requirements.return_value =\
            {'foo': mock.Mock(), 'bar': mock.Mock()}
        expected_error_message = _(
            "Error test_error_message occurred while installing package bar")
        mock_api.muranoclient().packages.create.side_effect = [
            Exception('test_error_message'), mock.Mock(id='test_package_id')
        ]
        self.import_pkg_wizard.process_step(mock_form)
        mock_messages.error.assert_any_call(
            self.mock_request, expected_error_message)
        mock_messages.success.assert_any_call(
            self.mock_request, _('Package foo uploaded'))
        mock_log.exception.assert_called_once_with(expected_error_message)
        mock_log.exception.reset_mock()
        mock_messages.reset_mock()

        # Test that second occurrence of exception is handled.
        mock_package.requirements.return_value =\
            {'foo': mock.Mock(), 'bar': mock.Mock()}
        expected_error_message = 'Uploading package failed. {0}'.format('')
        mock_api.muranoclient().packages.create.side_effect = [
            mock.Mock(id='test_package_id'), Exception
        ]
        self.import_pkg_wizard.process_step(mock_form)
        mock_log.exception.assert_called_once_with(expected_error_message)
        mock_exc.handle.assert_called_once_with(
            self.mock_request, expected_error_message,
            redirect='test_redirect')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranoclient_utils')
    @mock.patch.object(views, 'glance')
    def test_process_step_except_http_conflict(
            self, mock_glance, mock_murano_utils, mock_api, mock_log,
            mock_reverse, mock_messages, mock_exc):
        mock_murano_utils.Package.from_file.side_effect = None
        mock_reverse.return_value = 'test_redirect'

        mock_form = mock.Mock()
        mock_form.cleaned_data = {
            'import_type': 'upload',
            'package': mock.Mock(file='test_package_file')
        }
        mock_form.data = {
            'dependencies': [],
            'images': []
        }

        # Test that first occurrence of HTTPConflict is caught.
        mock_package = mock.Mock()
        mock_package.manifest = {'FullName': 'foo'}
        mock_package.requirements.return_value =\
            {'foo': mock.Mock(), 'bar': mock.Mock()}
        mock_murano_utils.Package.from_file.return_value = mock_package
        expected_error_message = "Package bar already registered."
        mock_api.muranoclient().packages.create.side_effect = [
            exc.HTTPConflict, None
        ]
        self.import_pkg_wizard.process_step(mock_form)
        mock_log.exception.assert_any_call(expected_error_message)
        mock_messages.warning.assert_called_once_with(
            self.mock_request, expected_error_message)
        mock_log.exception.reset_mock()
        mock_messages.warning.reset_mock()

        # Test that second occurrence of HTTPConflict is caught.
        mock_package.requirements.return_value =\
            {'foo': mock.Mock(), 'bar': mock.Mock()}
        mock_murano_utils.Package.from_file.return_value = mock_package
        expected_error_message = _(
            "Package with specified name already exists")
        mock_api.muranoclient().packages.create.side_effect = [
            None, exc.HTTPConflict
        ]
        self.import_pkg_wizard.process_step(mock_form)
        mock_log.exception.assert_any_call(expected_error_message)
        mock_exc.handle.assert_any_call(
            self.mock_request, expected_error_message,
            redirect='test_redirect')

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranoclient_utils')
    @mock.patch.object(views, 'glance')
    def test_process_step_except_http_internal_server_error(
            self, mock_glance, mock_murano_utils, mock_api, mock_log,
            mock_reverse, mock_exc):
        mock_murano_utils.Package.from_file.side_effect = None
        mock_reverse.return_value = 'test_redirect'
        mock_package = mock.Mock()
        mock_package.manifest = {'FullName': 'foo'}
        mock_package.requirements.return_value =\
            {'foo': mock.Mock(), 'bar': mock.Mock()}
        mock_murano_utils.Package.from_file.return_value = mock_package

        mock_form = mock.Mock()
        mock_form.cleaned_data = {
            'import_type': 'upload',
            'package': mock.Mock(file='test_package_file')
        }
        mock_form.data = {
            'dependencies': [],
            'images': []
        }

        expected_error_message = "Uploading package failed. {0}"\
                                 .format('test_500_error_message')
        exception = exc.HTTPInternalServerError(
            details='{"error": {"message": "test_500_error_message"}}')
        mock_api.muranoclient().packages.create.side_effect = [
            mock.Mock(id='test_package_id'), exception
        ]
        self.import_pkg_wizard.process_step(mock_form)
        mock_log.exception.assert_called_once_with(expected_error_message)
        mock_exc.handle.assert_called_once_with(
            self.mock_request, expected_error_message,
            redirect='test_redirect')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'muranodashboard_utils')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranoclient_utils')
    @mock.patch.object(views, 'glance')
    def test_process_step_except_http_exception(
            self, mock_glance, mock_murano_utils, mock_api, mock_log,
            mock_dashboard_utils, mock_reverse, mock_exc):
        mock_murano_utils.Package.from_file.side_effect = None
        mock_reverse.return_value = 'test_redirect'
        mock_package = mock.Mock()
        mock_package.manifest = {'FullName': 'foo'}
        mock_package.requirements.return_value =\
            {'foo': mock.Mock(), 'bar': mock.Mock()}
        mock_murano_utils.Package.from_file.return_value = mock_package
        mock_dashboard_utils.parse_api_error.return_value = 'test_reason'

        mock_form = mock.Mock()
        mock_form.cleaned_data = {
            'import_type': 'upload',
            'package': mock.Mock(file='test_package_file')
        }
        mock_form.data = {
            'dependencies': [],
            'images': []
        }

        exception = exc.HTTPException(
            details='{"error": {"message": "test_error_message"}}')
        mock_api.muranoclient().packages.create.side_effect = [
            mock.Mock(id='test_package_id'), exception
        ]
        self.import_pkg_wizard.process_step(mock_form)
        mock_log.exception.assert_any_call('test_reason')
        mock_exc.handle.assert_called_once_with(
            self.mock_request, 'test_reason', redirect='test_redirect')
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')

    def test_get_form_kwargs(self):
        kwargs = self.import_pkg_wizard.get_form_kwargs('add_category')
        self.assertEqual({'request': self.mock_request}, kwargs)

        mock_storage = mock.Mock()
        mock_storage.get_step_data().get.return_value = 'test_package'
        self.import_pkg_wizard.storage = mock_storage
        kwargs = self.import_pkg_wizard.get_form_kwargs('modify')
        self.assertEqual({'request': self.mock_request,
                          'package': 'test_package'}, kwargs)


class TestImportBundleWizard(helpers.APIMockTestCase):

    use_mox = True

    def setUp(self):
        super(TestImportBundleWizard, self).setUp()

        fake_response = {'status_code': 200}
        self.mock_request = mock.MagicMock(
            name='mock_request', return_value=fake_response, META=[])
        self.import_bundle_wizard = views.ImportBundleWizard()
        self.import_bundle_wizard.request = self.mock_request
        self.import_bundle_wizard.storage = mock.Mock(
            name='mock_storage', extra_data={'foo': 'bar'})
        self.import_bundle_wizard.steps = mock.Mock(name='mock_steps')
        self.import_bundle_wizard.steps.current = 'upload'
        self.import_bundle_wizard.prefix = 'test_prefix'
        self.import_bundle_wizard.initial_dict = {'upload': {'foo': 'bar'}}
        self.import_bundle_wizard.get_form_step_data =\
            lambda f: 'test_step_form_data'

        self.assertEqual('packages/import_bundle.html',
                         self.import_bundle_wizard.template_name)
        self.assertEqual('Import Bundle',
                         self.import_bundle_wizard.page_title)

        self.addCleanup(mock.patch.stopall)

    def test_get_context_data(self):
        mock_form = mock.Mock(initial={'package': mock.Mock(type='test_type')})
        context = self.import_bundle_wizard.get_context_data(form=mock_form)

        expected_instances = {
            'view': views.ImportBundleWizard,
            'wizard': dict
        }
        expected_context = {
            'foo': 'bar',
            'form': mock.ANY,
            'hide': True,
            'modal_backdrop': 'static',
            'murano_repo_url': 'http://apps.openstack.org',
            'view': mock.ANY,
            'wizard': mock.ANY
        }

        for key, val in expected_context.items():
            self.assertIn(key, context)
            self.assertEqual(val, context[key])

        for key, val in expected_instances.items():
            self.assertIsInstance(context[key], val)

    def test_get_form_initial(self):
        self.import_bundle_wizard.request.GET = {
            'url': 'test_url', 'name': 'test_name',
            'import_type': 'test_import_type'
        }
        initial_dict = self.import_bundle_wizard.get_form_initial('upload')
        expected_dict = {
            'foo': 'bar',
            'url': 'test_url',
            'name': 'test_name',
            'import_type': 'test_import_type'
        }

        for key, val in expected_dict.items():
            self.assertIn(key, initial_dict)
            self.assertEqual(val, initial_dict[key])

    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranoclient_utils')
    @mock.patch.object(views, 'glance')
    def test_process_step(self, mock_glance, mock_murano_utils, mock_api):
        mock_bundle = mock.Mock()
        mock_bundle.package_specs.return_value = [
            {'Name': 'foo_spec', 'Version': '1.0.0', 'Url': 'www.foo.com'},
            {'Name': 'bar_spec', 'Version': '2.0.0', 'Url': 'www.bar.com'}
        ]
        mock_package = mock.Mock()
        mock_foo_dependency = mock.Mock(name='foo_package')
        mock_bar_dependency = mock.Mock(name='bar_package')
        mock_package.requirements.return_value = {
            'foo_package': mock_foo_dependency,
            'bar_package': mock_bar_dependency
        }
        mock_murano_utils.to_url.return_value = 'test_url'
        mock_form = mock.Mock()

        for import_type in ('by_url', 'by_name'):
            mock_form.cleaned_data = {
                'import_type': import_type,
                'url': 'test_url',
                'name': 'test_form_name'
            }

            mock_murano_utils.Bundle.from_file.return_value = mock_bundle
            mock_murano_utils.Package.from_location.return_value = mock_package

            step_data = self.import_bundle_wizard.process_step(mock_form)
            self.assertEqual('test_step_form_data', step_data)

            mock_murano_utils.Bundle.from_file.assert_called_once_with(
                'test_url')
            mock_murano_utils.Package.from_location.assert_any_call(
                'foo_spec', version='1.0.0', url='www.foo.com',
                base_url=packages_consts.MURANO_REPO_URL, path=None
            )
            mock_murano_utils.Package.from_location.assert_any_call(
                'bar_spec', version='2.0.0', url='www.bar.com',
                base_url=packages_consts.MURANO_REPO_URL, path=None
            )
            mock_api.muranoclient().packages.create.assert_any_call(
                {}, {'foo_package': mock_foo_dependency.file()})
            mock_api.muranoclient().packages.create.assert_any_call(
                {}, {'bar_package': mock_bar_dependency.file()})

            mock_murano_utils.reset_mock()
            mock_api.reset_mock()

    @mock.patch.object(views, 'reverse')
    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'muranoclient_utils')
    def test_process_step_except_from_file_exception(
            self, mock_murano_utils, mock_log, mock_messages, mock_reverse):
        mock_reverse.return_value = 'test_redirect'
        mock_form = mock.Mock(
            cleaned_data={'import_type': 'by_url', 'url': 'foo_url'})
        e_404 = Exception('(404)')
        e_404.message = '(404)'
        e = Exception('foo')
        e.message = 'foo'
        errors = ((e_404, "Bundle creation failed.Reason: Can't find Bundle "
                          "name from repository."),
                  (e, "Bundle creation failed.Reason: foo"))

        for exception, expected_error_message in errors:
            mock_murano_utils.Bundle.from_file.side_effect = exception

            with self.assertRaisesRegex(horizon_exceptions.Http302, None):
                self.import_bundle_wizard.process_step(mock_form)

            mock_log.exception.assert_called_once_with(expected_error_message)
            mock_messages.error.assert_called_once_with(
                self.mock_request, expected_error_message)
            mock_reverse.assert_called_once_with(
                'horizon:app-catalog:packages:index')

            for mock_ in (mock_log, mock_messages, mock_reverse):
                mock_.reset_mock()

    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'muranoclient_utils')
    def test_process_step_except_from_location_exception(
            self, mock_murano_utils, mock_log, mock_messages):
        mock_form = mock.Mock(
            cleaned_data={'import_type': 'by_url', 'url': 'foo_url'})
        mock_bundle = mock.Mock()
        mock_bundle.package_specs.return_value = [
            {'Name': 'foo_spec', 'Version': '1.0.0', 'Url': 'www.foo.com'},
            {'Name': 'bar_spec', 'Version': '2.0.0', 'Url': 'www.bar.com'}
        ]

        mock_murano_utils.Bundle.from_file.return_value = mock_bundle
        mock_murano_utils.Package.from_location.side_effect = Exception('foo')

        self.import_bundle_wizard.process_step(mock_form)

        for spec in ('foo_spec', 'bar_spec'):
            expected_error_message = 'Error foo occurred while parsing '\
                                     'package {0}'.format(spec)
            mock_log.exception.assert_any_call(expected_error_message)
            mock_messages.error.assert_any_call(
                self.mock_request, expected_error_message)

    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranoclient_utils')
    @mock.patch.object(views, 'glance')
    def test_process_step_except_http_conflict(
            self, mock_glance, mock_murano_utils, mock_api, mock_log,
            mock_messages):
        mock_form = mock.Mock(
            cleaned_data={'import_type': 'by_url', 'url': 'foo_url'})
        mock_bundle = mock.Mock()
        mock_bundle.package_specs.return_value = [
            {'Name': 'foo_spec', 'Version': '1.0.0', 'Url': 'www.foo.com'},
            {'Name': 'bar_spec', 'Version': '2.0.0', 'Url': 'www.bar.com'}
        ]
        mock_foo_dependency = mock.Mock(name='foo_package')
        mock_bar_dependency = mock.Mock(name='bar_package')
        mock_package = mock.Mock()
        mock_package.requirements.return_value = {
            'foo_package': mock_foo_dependency,
            'bar_package': mock_bar_dependency
        }

        mock_murano_utils.Bundle.from_file.return_value = mock_bundle
        mock_murano_utils.Package.from_location.return_value = mock_package
        mock_api.muranoclient().packages.create.side_effect = exc.HTTPConflict

        self.import_bundle_wizard.process_step(mock_form)

        for dep in ('foo_package', 'bar_package'):
            expected_error_message = 'Package {0} already registered.'\
                                     .format(dep)
            mock_log.exception.assert_any_call(expected_error_message)
            mock_messages.warning.assert_any_call(
                self.mock_request, expected_error_message)

    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranodashboard_utils')
    @mock.patch.object(views, 'muranoclient_utils')
    @mock.patch.object(views, 'glance')
    def test_process_step_except_http_exception(
            self, mock_glance, mock_murano_utils, mock_dashboard_utils,
            mock_api, mock_log, mock_messages):
        mock_form = mock.Mock(
            cleaned_data={'import_type': 'by_url', 'url': 'foo_url'})
        mock_bundle = mock.Mock()
        mock_bundle.package_specs.return_value = [
            {'Name': 'foo_spec', 'Version': '1.0.0', 'Url': 'www.foo.com'},
            {'Name': 'bar_spec', 'Version': '2.0.0', 'Url': 'www.bar.com'}
        ]
        mock_foo_dependency = mock.Mock(name='foo_package')
        mock_bar_dependency = mock.Mock(name='bar_package')
        mock_package = mock.Mock()
        mock_package.requirements.return_value = {
            'foo_package': mock_foo_dependency,
            'bar_package': mock_bar_dependency
        }

        mock_murano_utils.Bundle.from_file.return_value = mock_bundle
        mock_murano_utils.Package.from_location.return_value = mock_package
        mock_api.muranoclient().packages.create.side_effect =\
            exc.HTTPException('foo')
        mock_dashboard_utils.parse_api_error.return_value = 'foo'

        self.import_bundle_wizard.process_step(mock_form)

        for dep in ('foo_package', 'bar_package'):
            expected_error_message = 'Package {0} upload failed. foo'\
                                     .format(dep)
            mock_log.exception.assert_any_call(expected_error_message)
            mock_messages.warning.assert_any_call(
                self.mock_request, expected_error_message)

    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'api')
    @mock.patch.object(views, 'muranoclient_utils')
    @mock.patch.object(views, 'glance')
    def test_process_step_except_package_create_exception(
            self, mock_glance, mock_murano_utils, mock_api, mock_log,
            mock_messages):
        mock_form = mock.Mock(
            cleaned_data={'import_type': 'by_url', 'url': 'foo_url'})
        mock_bundle = mock.Mock()
        mock_bundle.package_specs.return_value = [
            {'Name': 'foo_spec', 'Version': '1.0.0', 'Url': 'www.foo.com'},
            {'Name': 'bar_spec', 'Version': '2.0.0', 'Url': 'www.bar.com'}
        ]
        mock_foo_dependency = mock.Mock(name='foo_package')
        mock_bar_dependency = mock.Mock(name='bar_package')
        mock_package = mock.Mock()
        mock_package.requirements.return_value = {
            'foo_package': mock_foo_dependency,
            'bar_package': mock_bar_dependency
        }

        mock_murano_utils.Bundle.from_file.return_value = mock_bundle
        mock_murano_utils.Package.from_location.return_value = mock_package
        mock_api.muranoclient().packages.create.side_effect =\
            Exception('foo')

        self.import_bundle_wizard.process_step(mock_form)

        for dep in ('foo_package', 'bar_package'):
            expected_error_message = 'Importing package {0} failed. '\
                                     'Reason: foo'.format(dep)
            mock_log.exception.assert_any_call(expected_error_message)
            mock_messages.warning.assert_any_call(
                self.mock_request, expected_error_message)

    @mock.patch.object(views, 'messages')
    @mock.patch.object(views, 'LOG')
    @mock.patch.object(views, 'reverse')
    def test_done(self, mock_reverse, mock_log, mock_messages):
        mock_reverse.redirect = 'test_redirect'

        result = self.import_bundle_wizard.done([])
        self.assertIsInstance(result, http.response.HttpResponseRedirect)

        expected_message = 'Bundle successfully imported.'
        mock_log.info.assert_any_call(expected_message)
        mock_messages.success.assert_called_once_with(
            self.mock_request, expected_message)
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')


class TestPackageDefinitionsView(helpers.APIMockTestCase):

    def setUp(self):
        super(TestPackageDefinitionsView, self).setUp()

        self.pkg_definitions_view = views.PackageDefinitionsView()
        mock_token = mock.MagicMock()
        mock_token.__getitem__.return_value = 'foo_token_id'
        self.mock_request = mock.MagicMock(
            name='mock_request', GET={'sort_dir': 'asc'},
            session={'token': mock_token})

        self.pkg_definitions_view.request = self.mock_request
        self.original_get_filters = self.pkg_definitions_view.get_filters
        self.pkg_definitions_view.get_filters = lambda opts: opts

        self.assertEqual(self.pkg_definitions_view.table_class,
                         tables.PackageDefinitionsTable)
        self.assertEqual(self.pkg_definitions_view.template_name,
                         'packages/index.html')
        self.assertEqual(self.pkg_definitions_view.page_title, 'Packages')
        self.assertFalse(self.pkg_definitions_view.has_more_data(None))
        self.assertFalse(self.pkg_definitions_view.has_prev_data(None))

        mock_horizon_utils = mock.patch.object(views, 'utils').start()
        mock_horizon_utils.get_page_size.return_value = 123
        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(views, 'pkg_api')
    def test_get_data_with_same_tenants(self, mock_pkg_api):
        mock_package = mock.Mock(
            id='foo_package', owner_id='test_tenant', tenant_name=None)
        mock_pkg_api.package_list.return_value =\
            ([mock_package], True)
        mock_tenant = mock.MagicMock()
        mock_tenant.__getitem__.side_effect = [
            'test_tenant', 'foo_tenant_name'
        ]

        self.pkg_definitions_view.request.user.is_superuser = False
        self.pkg_definitions_view.request.session['token'] =\
            mock.Mock(tenant=mock_tenant)

        packages = self.pkg_definitions_view.get_data()

        self.assertEqual([mock_package], packages)
        self.assertEqual('foo_tenant_name', mock_package.tenant_name)
        self.assertTrue(self.pkg_definitions_view.has_prev_data)
        mock_pkg_api.package_list.assert_any_call(
            self.mock_request, marker=None,
            filters={'include_disabled': True, 'sort_dir': 'desc'},
            paginate=True, page_size=123)
        mock_pkg_api.package_list.assert_any_call(
            self.mock_request, marker='foo_package',
            filters={'include_disabled': True, 'sort_dir': 'desc'},
            paginate=True, page_size=0)

    @mock.patch.object(views, 'pkg_api')
    def test_get_data_with_different_tenants(self, mock_pkg_api):
        mock_package = mock.Mock(id='foo_package', tenant_name='test_tenant')
        mock_pkg_api.package_list.return_value =\
            ([mock_package], True)

        self.pkg_definitions_view.request.user.is_superuser = False
        self.pkg_definitions_view.request.session['token'] =\
            mock.MagicMock(__getitem__='alt_test_tenant')

        packages = self.pkg_definitions_view.get_data()

        self.assertEqual([mock_package], packages)
        self.assertEqual('UNKNOWN', mock_package.tenant_name)
        self.assertTrue(self.pkg_definitions_view.has_prev_data)
        mock_pkg_api.package_list.assert_any_call(
            self.mock_request, marker=None,
            filters={'include_disabled': True, 'sort_dir': 'desc'},
            paginate=True, page_size=123)
        mock_pkg_api.package_list.assert_any_call(
            self.mock_request, marker='foo_package',
            filters={'include_disabled': True, 'sort_dir': 'desc'},
            paginate=True, page_size=0)

    @mock.patch.object(views, 'keystone')
    @mock.patch.object(views, 'pkg_api')
    def test_get_data_as_superuser(self, mock_pkg_api, mock_keystone):
        mock_keystone.tenant_list.side_effect = None
        super_user_tenant = mock.Mock(id='super_tenant_id')
        super_user_tenant.configure_mock(name='super_tenant_name')
        mock_keystone.tenant_list.return_value = ([super_user_tenant], False)
        mock_package = mock.Mock(
            id='foo_package', owner_id='super_tenant_id', tenant_name=None)
        mock_pkg_api.package_list.return_value =\
            ([mock_package], True)
        mock_tenant = mock.MagicMock()
        mock_tenant.__getitem__.side_effect = [
            'test_tenant', 'foo_tenant_name'
        ]

        self.pkg_definitions_view.request.user.is_superuser = True
        self.pkg_definitions_view.request.session['token'] =\
            mock.Mock(tenant=mock_tenant)

        packages = self.pkg_definitions_view.get_data()

        self.assertEqual([mock_package], packages)
        self.assertEqual('super_tenant_name', mock_package.tenant_name)
        self.assertTrue(self.pkg_definitions_view.has_more_data)

    @mock.patch.object(views, 'exceptions')
    @mock.patch.object(views, 'keystone')
    @mock.patch.object(views, 'pkg_api')
    def test_get_data_except_keystone_exception(self, mock_pkg_api,
                                                mock_keystone, mock_exc):
        mock_keystone.tenant_list.side_effect = Exception
        super_user_tenant = mock.Mock(id='super_tenant_id')
        super_user_tenant.configure_mock(name='super_tenant_name')
        mock_keystone.tenant_list.return_value = ([super_user_tenant], False)
        mock_package = mock.Mock(
            id='foo_package', owner_id='super_tenant_id', tenant_name=None)
        mock_pkg_api.package_list.return_value =\
            ([mock_package], True)
        mock_tenant = mock.MagicMock()
        mock_tenant.__getitem__.side_effect = [
            'test_tenant', 'foo_tenant_name'
        ]

        self.pkg_definitions_view.request.user.is_superuser = True
        self.pkg_definitions_view.request.session['token'] =\
            mock.Mock(tenant=mock_tenant)

        packages = self.pkg_definitions_view.get_data()

        self.assertEqual([mock_package], packages)
        self.assertIsNone(mock_package.tenant_name)
        self.assertTrue(self.pkg_definitions_view.has_more_data)
        mock_exc.handle.assert_called_once_with(
            self.mock_request, "Unable to retrieve project list.")

    @mock.patch.object(views, 'pkg_api')
    def test_get_data_desc_order(self, mock_pkg_api):
        mock_package = mock.Mock(
            id='foo_package', owner_id='test_tenant', tenant_name=None)
        mock_pkg_api.package_list.return_value =\
            ([mock_package], True)
        mock_tenant = mock.MagicMock()
        mock_tenant.__getitem__.side_effect = [
            'test_tenant', 'foo_tenant_name'
        ]

        self.pkg_definitions_view.request.GET = {'sort_dir': 'desc'}
        self.pkg_definitions_view.request.user.is_superuser = False
        self.pkg_definitions_view.request.session['token'] =\
            mock.Mock(tenant=mock_tenant)

        packages = self.pkg_definitions_view.get_data()

        self.assertEqual([mock_package], packages)
        self.assertEqual('foo_tenant_name', mock_package.tenant_name)
        self.assertTrue(self.pkg_definitions_view.has_more_data)

        mock_pkg_api.package_list.assert_any_call(
            self.mock_request, marker=None,
            filters={'include_disabled': True, 'sort_dir': 'asc'},
            paginate=True, page_size=123)
        mock_pkg_api.package_list.assert_any_call(
            self.mock_request, marker='foo_package',
            filters={'include_disabled': True, 'sort_dir': 'asc'},
            paginate=True, page_size=0)

    def test_get_context_data(self):
        mock_form = mock.Mock(initial={'package': mock.Mock(type='test_type')})
        self.pkg_definitions_view.table = 'foo_table'
        context = self.pkg_definitions_view.get_context_data(form=mock_form)

        expected_context = {
            'table': 'foo_table',
            'tenant_id': mock.ANY,
            'packages_table': 'foo_table',
            'form': mock.ANY,
            'view': mock.ANY
        }

        for key, val in expected_context.items():
            self.assertEqual(val, context[key])

        self.assertIsInstance(context['view'], views.PackageDefinitionsView)

    def test_get_filters(self):
        mock_filter_action = mock.Mock()
        mock_filter_action.is_api_filter.return_value = True
        self.pkg_definitions_view.table = mock.Mock()
        self.pkg_definitions_view.table._meta_._filter_action =\
            mock_filter_action
        self.pkg_definitions_view.table.get_filter_field.return_value =\
            'test_filter_field'
        self.pkg_definitions_view.table.get_filter_string.return_value =\
            'test_filter_string'

        self.pkg_definitions_view.get_filters = self.original_get_filters
        test_filters = {'foo': 'bar'}
        filters = self.pkg_definitions_view.get_filters(test_filters)

        expected_filters = {
            'test_filter_field': 'test_filter_string',
            'foo': 'bar'
        }

        for key, val in expected_filters.items():
            self.assertEqual(val, filters[key])
