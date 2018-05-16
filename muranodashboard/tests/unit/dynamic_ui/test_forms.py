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

import collections
import mock
import testtools
from yaql.language import contexts as yaql_contexts

from django import forms as django_forms

from muranodashboard.dynamic_ui import fields
from muranodashboard.dynamic_ui import forms
from muranodashboard.dynamic_ui import yaql_expression


class TestAnyFieldDict(testtools.TestCase):

    def test_missing(self):
        any_field_dict = forms.AnyFieldDict()
        result = any_field_dict.__missing__(['foo', 'bar'])
        self.assertEqual('DynamicSelect', result.__name__)


class TestDynamicUiForm(testtools.TestCase):

    def test_collect_fields_process_widget(self):
        test_spec = {
            'type': 'text',
            'name': 'foo_spec',
            'widget_media': {
                'js': 'foo.js',
                'css': 'foo.css'
            },
            'widget_attrs': {'foo': 'bar'}
        }

        result = forms._collect_fields([test_spec], 'foo_form', None)

        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))
        self.assertEqual('foo_spec', result[0][0])
        self.assertIsInstance(result[0][1], fields.CharField)

        field = result[0][1]

        self.assertTrue(hasattr(field, 'widget'))
        self.assertTrue(hasattr(field.widget, 'Media'))
        self.assertEqual('foo.js', field.widget.Media.js)
        self.assertEqual('foo.css', field.widget.Media.css)
        self.assertIn('foo', field.widget.__dict__['attrs'])
        self.assertEqual('bar', field.widget.__dict__['attrs']['foo'])

    def test_collect_fields_parse_spec_with_yaql_expression(self):
        mock_yaql = mock.Mock(spec=yaql_expression.YaqlExpression)
        test_spec = {
            'type': 'choice',
            'name': 'foo_spec',
            'validators': [{'expr': mock_yaql}]
        }

        result = forms._collect_fields([test_spec], 'foo_form', None)

        self.assertIsInstance(result, list)
        self.assertEqual(1, len(result))
        self.assertEqual('foo_spec', result[0][0])
        self.assertIsInstance(result[0][1], fields.ChoiceField)

        field = result[0][1]

        self.assertTrue(hasattr(field, 'validators'))
        self.assertIn('expr', field.validators[0])
        self.assertIsInstance(field.validators[0]['expr'], fields.RawProperty)
        self.assertEqual(mock_yaql, field.validators[0]['expr'].spec)


class TestDynamicFormMetaclass(testtools.TestCase):

    def test_new(self):
        test_dict = {
            'name': 'foo_form',
            'field_specs': [{'type': 'text', 'name': 'foo_spec'}],
            'service': 'foo_service',
        }

        form = forms.DynamicFormMetaclass('foo_form', (), test_dict)
        self.assertEqual('foo_form', form.__name__)
        self.assertEqual('foo_service', form.service)
        self.assertIsInstance(form.declared_fields, collections.OrderedDict)
        self.assertIn('foo_spec', form.declared_fields)
        self.assertIsInstance(form.declared_fields['foo_spec'],
                              fields.CharField)


class TestUpdatableFieldsForm(testtools.TestCase):

    def setUp(self):
        super(TestUpdatableFieldsForm, self).setUp()

        self.form = forms.UpdatableFieldsForm(None)
        self.assertEqual('required', self.form.required_css_class)

    def test_update_fields(self):
        mock_password_field = mock.Mock(spec=fields.PasswordField)
        mock_password_field.confirm_input = True
        mock_password_field.has_clone = False
        mock_password_field.original = True
        mock_password_field.required = True
        mock_password_field.update = mock.Mock()
        mock_password_field.initial = 'foo_initial'
        mock_password_field.get_clone_name.return_value = 'bar_password_field'
        mock_clone_password_field = mock.Mock(
            spec=fields.PasswordField, required=True)
        mock_password_field.clone_field.return_value = \
            mock_clone_password_field

        self.form.fields = collections.OrderedDict({
            'foo_password_field': mock_password_field})
        self.form.update_fields()

        self.assertEqual(2, len(self.form.fields))
        self.assertIn('foo_password_field', self.form.fields)
        self.assertIn('bar_password_field', self.form.fields)
        self.assertEqual(mock_password_field,
                         self.form.fields['foo_password_field'])
        self.assertEqual(mock_clone_password_field,
                         self.form.fields['bar_password_field'])
        mock_password_field.get_clone_name.assert_called_once_with(
            'foo_password_field')
        self.assertTrue(mock_password_field.get_clone_name.called)
        self.assertTrue(mock_password_field.update.called)


class TestServiceConfigurationForm(testtools.TestCase):

    def setUp(self):
        super(TestServiceConfigurationForm, self).setUp()

        mock_service = mock.Mock()
        mock_service.update_cleaned_data.return_value = \
            {'foo': 'bar', 'baz': 'qux'}

        self.form = forms.ServiceConfigurationForm(
            initial={'app_id': 'foo_app'})
        self.form._errors = []
        self.form.validators = []
        self.form.cleaned_data = {'foo': 'bar', 'baz': 'qux'}
        self.form.service = mock_service

        self.assertEqual('foo_app_%s', self.form.auto_id)
        self.assertIsInstance(self.form.context, yaql_contexts.Context)

    @mock.patch.object(forms, 'LOG', autospec=True)
    def test_clean(self, mock_log):
        password_field = mock.Mock(spec=fields.PasswordField)
        password_field.enabled = True
        password_field.confirm_input = True

        foo_field = mock.Mock()
        foo_field.enabled = False
        foo_field.postclean.return_value = 'post_foo'

        self.form.fields = {'foo': foo_field, 'password': password_field}
        result = self.form.clean()
        expected_cleaned_data = {'foo': 'post_foo', 'baz': 'qux'}

        for key, val in expected_cleaned_data.items():
            self.assertEqual(val, result[key])

        # NOTE(felipemonteiro): mock.ANY is being used in the assertions
        # below, rather than `{'foo': 'bar', 'baz': 'qux'}` because
        # `cleaned_data[name] = value` in clean() appears to also change the
        # dict that was passed in to mock objects in previous lines of code.
        foo_field.postclean.assert_called_once_with(self.form, 'foo', mock.ANY)
        password_field.compare.assert_called_once_with('password', mock.ANY)
        mock_log.debug.assert_called_once_with(
            "Update 'foo' data in postclean method")
        self.form.service.update_cleaned_data.assert_called_with(
            mock.ANY, form=self.form)

    def test_clean_except_validation_error(self):
        mock_expr = mock.Mock()
        mock_expr.evaluate.return_value = False
        test_validator = {'expr': mock_expr, 'message': 'Foo Error'}

        self.form.validators = [test_validator]
        with self.assertRaisesRegex(django_forms.ValidationError,
                                    'Foo Error'):
            self.form.clean()

        self.form.service.update_cleaned_data.assert_called_once_with(
            {'foo': 'bar', 'baz': 'qux'}, form=self.form)
        mock_expr.evaluate.assert_called_once_with(
            data={'foo': 'bar', 'baz': 'qux'}, context=self.form.context)

    def test_clean_with_errors(self):
        self.form._errors = ['foo_error']
        self.assertEqual({'foo': 'bar', 'baz': 'qux'}, self.form.clean())
