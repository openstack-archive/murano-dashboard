#    Copyright (c) 2016 AT&T Corp
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

from django import forms as django_forms

from muranoclient.common import exceptions as exc
from muranodashboard.packages import consts
from muranodashboard.packages import forms
from openstack_dashboard.test import helpers


class TestImportBundleForm(helpers.APIMockTestCase):

    def test_clean_form(self):
        import_bundle_form = forms.ImportBundleForm()
        expected = {'import_type': 'by_name', 'name': 'test_form_name'}
        import_bundle_form.cleaned_data = expected

        cleaned_data = import_bundle_form.clean()
        self.assertEqual(expected, cleaned_data)

    def test_clean_form_except_validation_error(self):
        import_bundle_form = forms.ImportBundleForm()
        for attr in ['name', 'url']:
            import_bundle_form.cleaned_data = {
                'import_type': 'by_{0}'.format(attr), attr: None}
            expected_error_msg = 'Please supply a bundle {0}'.format(attr)

            with self.assertRaisesRegex(django_forms.ValidationError,
                                        expected_error_msg):
                import_bundle_form.clean()


class TestImportPackageForm(helpers.APIMockTestCase):

    def setUp(self):
        super(TestImportPackageForm, self).setUp()

        self.import_pkg_form = forms.ImportPackageForm()
        fields = self.import_pkg_form.fields
        self.assertEqual(
            'Optional',
            fields['repo_version'].widget.attrs['placeholder'])

    def test_clean_package(self):
        size_in_bytes = (consts.MAX_FILE_SIZE_MB - 1) << 20
        mock_package = mock.Mock(size=size_in_bytes)
        self.import_pkg_form.cleaned_data = {
            'package': mock_package
        }

        cleaned_data = self.import_pkg_form.clean_package()
        self.assertEqual(mock_package, cleaned_data)

    def test_clean_package_exception_validation_error(self):
        size_in_bytes = (consts.MAX_FILE_SIZE_MB + 1) << 20
        mock_package = mock.Mock(size=size_in_bytes)
        self.import_pkg_form.cleaned_data = {
            'package': mock_package
        }

        expected_error_msg = 'It is forbidden to upload files larger than {0} '\
                             'MB.'.format(consts.MAX_FILE_SIZE_MB)
        with self.assertRaisesRegex(django_forms.ValidationError,
                                    expected_error_msg):
            self.import_pkg_form.clean_package()

    def test_clean_form(self):
        expected = {
            'import_type': 'by_name',
            'repo_name': 'test_repo_name'
        }
        self.import_pkg_form.cleaned_data = expected

        cleaned_data = self.import_pkg_form.clean()
        self.assertEqual(expected, cleaned_data)

    def test_clean_form_except_validation_error(self):
        tuples = (
            ('upload', 'package', 'file'),
            ('by_name', 'repo_name', 'name'),
            ('by_url', 'url', 'url')
        )
        for _tuple in tuples:
            self.import_pkg_form.cleaned_data = {
                'import_type': '{0}'.format(_tuple[0]), _tuple[1]: None}
            expected_error_msg = 'Please supply a package {0}'.\
                                 format(_tuple[2])

            with self.assertRaisesRegex(django_forms.ValidationError,
                                        expected_error_msg):
                self.import_pkg_form.clean()


class TestUpdatePackageForm(helpers.APIMockTestCase):

    def setUp(self):
        super(TestUpdatePackageForm, self).setUp()

        mock_package = mock.MagicMock(
            tags=['bar', 'baz', 'qux'], is_public=False,
            enabled=True, description='quux')
        mock_package.configure_mock(name='foo')
        fake_response = {'status_code': 200}
        self.mock_request = mock.MagicMock(return_value=fake_response, META=[])
        kwargs = {'request': self.mock_request, 'package': mock_package}
        self.update_pkg_form = forms.UpdatePackageForm(**kwargs)

    def test_set_initial(self):
        # set_initial was already called by forms.UpdatePackageForm(**kwargs)
        self.assertEqual('foo', self.update_pkg_form.fields['name'].initial)
        self.assertEqual('bar, baz, qux',
                         self.update_pkg_form.fields['tags'].initial)
        self.assertEqual(False,
                         self.update_pkg_form.fields['is_public'].initial)
        self.assertEqual(True, self.update_pkg_form.fields['enabled'].initial)
        self.assertEqual('quux',
                         self.update_pkg_form.fields['description'].initial)


class TestModifyPackageForm(helpers.APIMockTestCase):

    def setUp(self):
        super(TestModifyPackageForm, self).setUp()

        mock_package = mock.MagicMock(
            type='Application', tags=['bar', 'baz', 'qux'], is_public=False,
            enabled=True, description='quux', categories=['c1', 'c2'])
        mock_package.configure_mock(name='foo')
        self.kwargs = {'initial': {'package': mock_package}}

        fake_response = {
            "status_code": 200,
            "text": '{"foo": "bar"}',
        }
        self.mock_request = mock.MagicMock(return_value=(fake_response))

        with mock.patch('muranodashboard.api.muranoclient') as mock_client:
            mock_categories = []
            for cname in ['c3', 'c4']:
                mock_category = mock.Mock()
                mock_category.configure_mock(name=cname)
                mock_categories.append(mock_category)
            mock_client().categories.list.return_value = mock_categories
            self.modify_pkg_form = forms.ModifyPackageForm(self.mock_request,
                                                           **self.kwargs)

    def test_init(self):
        self.assertEqual(
            [('c3', 'c3'), ('c4', 'c4')],
            self.modify_pkg_form.fields['categories'].choices)

        for key in ('c1', 'c2'):
            self.assertIn(key,
                          self.modify_pkg_form.fields['categories'].initial)
            self.assertEqual(
                True, self.modify_pkg_form.fields['categories'].initial[key])

    @mock.patch.object(forms, 'exceptions')
    @mock.patch.object(forms, 'reverse')
    @mock.patch('muranodashboard.api.muranoclient')
    def test_init_except_http_exception(self, mock_client, mock_reverse,
                                        mock_exceptions):
        mock_client().categories.list.side_effect = exc.HTTPException
        mock_reverse.return_value = 'test_redirect'

        self.modify_pkg_form = forms.ModifyPackageForm(self.mock_request,
                                                       **self.kwargs)
        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')
        mock_exceptions.handle.assert_called_once_with(
            self.mock_request, 'Unable to get list of categories',
            redirect='test_redirect')

    @mock.patch('muranodashboard.api.muranoclient')
    def test_handle(self, mock_client):
        mock_client().packages.update.return_value = {'status_code': 200}
        test_data = {'tags': 't1 ,t2  ,t3'}
        self.modify_pkg_form.initial['app_id'] = 'test_app_id'

        result = self.modify_pkg_form.handle(self.mock_request, test_data)

        self.assertEqual({'status_code': 200}, result)
        mock_client().packages.update.assert_called_once_with(
            'test_app_id', {'tags': ['t1', 't2', 't3']})

    @mock.patch.object(forms, 'exceptions')
    @mock.patch.object(forms, 'reverse')
    @mock.patch('muranodashboard.api.muranoclient')
    def test_handle_except_http_forbidden(self, mock_client, mock_reverse,
                                          mock_exceptions):
        mock_client().packages.update.side_effect = exc.HTTPForbidden
        mock_reverse.return_value = 'test_redirect'
        test_data = {'tags': 't1 ,t2  ,t3'}
        self.modify_pkg_form.initial['app_id'] = 'test_app_id'

        self.modify_pkg_form.handle(self.mock_request, test_data)

        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')
        mock_exceptions.handle.assert_called_once_with(
            self.mock_request, 'You are not allowed to perform this operation',
            redirect='test_redirect')

    @mock.patch.object(forms, 'exceptions')
    @mock.patch.object(forms, 'reverse')
    @mock.patch('muranodashboard.api.muranoclient')
    def test_handle_except_http_conflict(self, mock_client, mock_reverse,
                                         mock_exceptions):
        mock_client().packages.update.side_effect = exc.HTTPConflict
        mock_reverse.return_value = 'test_redirect'
        test_data = {'tags': 't1 ,t2  ,t3'}
        self.modify_pkg_form.initial['app_id'] = 'test_app_id'

        self.modify_pkg_form.handle(self.mock_request, test_data)

        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')
        mock_exceptions.handle.assert_called_once_with(
            self.mock_request,
            'Package or Class with the same name is already made public',
            redirect='test_redirect')

    @mock.patch.object(forms, 'exceptions')
    @mock.patch.object(forms, 'reverse')
    @mock.patch('muranodashboard.api.muranoclient')
    def test_handle_except_exception(self, mock_client, mock_reverse,
                                     mock_exceptions):
        e = Exception()
        setattr(e, 'details', '{"error": {"message": "test_error_message"}}')
        mock_client().packages.update.side_effect = e
        mock_reverse.return_value = 'test_redirect'
        test_data = {'tags': 't1 ,t2  ,t3'}
        self.modify_pkg_form.initial['app_id'] = 'test_app_id'

        self.modify_pkg_form.handle(self.mock_request, test_data)

        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')
        mock_exceptions.handle.assert_called_once_with(
            self.mock_request,
            'Failed to modify the package. {0}'.format('test_error_message'),
            redirect='test_redirect')


class TestSelectCategories(helpers.APIMockTestCase):

    def setUp(self):
        super(TestSelectCategories, self).setUp()

        fake_response = {
            "status_code": 200,
            "text": '{"foo": "bar"}',
        }
        self.mock_request = mock.MagicMock(return_value=(fake_response))
        self.kwargs = {'request': self.mock_request}

        with mock.patch('muranodashboard.api.muranoclient') as mock_client:
            mock_categories = []
            for cname in ['c1', 'c2']:
                mock_category = mock.Mock()
                mock_category.configure_mock(name=cname)
                mock_categories.append(mock_category)
            mock_client().categories.list.return_value = mock_categories
            self.select_categories_form = forms.SelectCategories(**self.kwargs)

    def test_init(self):
        self.assertEqual(
            [('c1', 'c1'), ('c2', 'c2')],
            self.select_categories_form.fields['categories'].choices)

    @mock.patch.object(forms, 'exceptions')
    @mock.patch.object(forms, 'reverse')
    @mock.patch('muranodashboard.api.muranoclient')
    def test_init_except_http_exception(self, mock_client, mock_reverse,
                                        mock_exceptions):
        mock_client().categories.list.side_effect = exc.HTTPException
        mock_reverse.return_value = 'test_redirect'

        forms.SelectCategories(**self.kwargs)

        mock_reverse.assert_called_once_with(
            'horizon:app-catalog:packages:index')
        mock_exceptions.handle.assert_called_once_with(
            self.mock_request, 'Unable to get list of categories',
            redirect='test_redirect')
