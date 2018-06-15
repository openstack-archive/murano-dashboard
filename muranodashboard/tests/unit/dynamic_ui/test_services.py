#    Copyright (c) 2015 Mirantis, Inc.
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

import collections
from django import forms
import mock
import semantic_version
from yaql.language import factory

from muranodashboard.catalog import forms as catalog_forms
from muranodashboard.catalog import views as catalog_views
from muranodashboard.dynamic_ui import forms as service_forms
from muranodashboard.dynamic_ui import services

from openstack_dashboard.test import helpers


class TestService(helpers.APIMockTestCase):
    def setUp(self):
        super(TestService, self).setUp()

        self.application = {'?': {'type': 'test.App'}}
        factory = helpers.RequestFactoryWithMessages()
        self.request = factory.get('/path/for/testing')
        self.request.session = {}

    def test_service_field_hidden_false(self):
        """Test that service field is hidden

        When Service class instantiated with some field having `hidden`
        attribute set to `false` - the generated form field should have
        widget different from `HiddenInput`.

        Bug: #1368120
        """
        ui = [{
            'appConfiguration': {'fields': [{'hidden': False, 'type': 'string',
                                             'name': 'title'}]}
        }]

        service = services.Service(cleaned_data={},
                                   version=2,
                                   fqn='io.murano.Test',
                                   application=self.application,
                                   forms=ui)
        form = next(e for e in service.forms
                    if e.__name__ == 'appConfiguration')
        field = form.base_fields['title']

        self.assertNotIsInstance(field.widget, forms.HiddenInput)

    def test_service_field_hidden_true(self):
        """Test hidden widget

        `hidden: true` in UI definition results to HiddenInput in Django form.
        """
        ui = [{
            'appConfiguration': {'fields': [{'hidden': True, 'type': 'string',
                                             'name': 'title'}]}
        }]

        service = services.Service(cleaned_data={},
                                   version=2,
                                   fqn='io.murano.Test',
                                   application=self.application,
                                   forms=ui)
        form = next(e for e in service.forms
                    if e.__name__ == 'appConfiguration')
        field = form.base_fields['title']

        self.assertIsInstance(field.widget, forms.HiddenInput)

    def test_init_service_with_kwargs_and_version_coercion(self):
        kwargs = {'foo': 'bar', 'baz': 'qux', 'quux': 'corge'}
        service = services.Service(cleaned_data={},
                                   version=semantic_version.Version('2.3.0'),
                                   fqn='io.murano.Test',
                                   application=self.application,
                                   **kwargs)

        for key, val in kwargs.items():
            self.assertTrue(hasattr(service, key))
            self.assertEqual(val, getattr(service, key))

        self.assertEqual(1, len(service.forms))
        for key, val in kwargs.items():
            self.assertTrue(hasattr(service.forms[0].service, key))
            self.assertEqual(val, getattr(service.forms[0].service, key))

    def test_init_service_except_value_error(self):
        with self.assertRaisesRegex(ValueError,
                                    'Application section is required'):
            services.Service(cleaned_data={},
                             version=2,
                             fqn='io.murano.Test',
                             application=None)

    def test_extract_attributes(self):
        cleaned_data = {
            services.catalog_forms.WF_MANAGEMENT_NAME: {
                'application_name': 'foobar'
            }
        }
        templates = {'t1': 'foo', 't2': 'bar', 't3': 'baz'}
        service = services.Service(cleaned_data=cleaned_data,
                                   version=semantic_version.Version('2.3.0'),
                                   fqn='io.murano.Test',
                                   application=self.application,
                                   templates=templates)

        attributes = service.extract_attributes()
        expected = {'?': {'type': 'test.App', 'name': 'foobar'}}

        self.assertIsInstance(attributes, dict)
        self.assertEqual(expected['?']['type'], attributes['?']['type'])
        self.assertEqual(expected['?']['name'], attributes['?']['name'])
        self.assertEqual('foobar', service.application['?']['name'])

    def test_get_and_set_cleaned_data(self):
        cleaned_data = {
            catalog_forms.WF_MANAGEMENT_NAME: {
                'application_name': 'foobar'
            }
        }
        engine_factory = factory.YaqlFactory()
        engine = engine_factory.create()
        expr = engine('$')

        service = services.Service(cleaned_data={},
                                   version=semantic_version.Version('2.3.0'),
                                   fqn='io.murano.Test',
                                   application=self.application)
        service.set_data(cleaned_data)
        result = service.get_data(catalog_forms.WF_MANAGEMENT_NAME, expr)
        expected = {'workflowManagement': {'application_name': 'foobar'}}

        self.assertEqual(expected, result)

        # Test whether passing data to get_data works.
        service.set_data({})
        cleaned_data = cleaned_data[catalog_forms.WF_MANAGEMENT_NAME]
        result = service.get_data(
            catalog_forms.WF_MANAGEMENT_NAME, expr, data=cleaned_data)
        self.assertEqual(expected, result)

    def test_get_apps_data(self):
        result = services.get_apps_data(self.request)
        self.assertEqual({}, result)
        self.assertEqual(self.request.session['apps_data'], result)

    @mock.patch.object(services, 'pkg_api')
    def test_import_app(self, mock_pkg_api):
        mock_pkg_api.get_app_ui.return_value = {
            'foo': 'bar',
            'application': self.application
        }
        mock_pkg_api.get_app_fqn.return_value = 'foo_fqn'

        service = services.import_app(self.request, '123')
        self.assertEqual(services.Service, type(service))
        self.assertEqual('bar', service.foo)
        self.assertEqual(self.application, service.application)

    @mock.patch.object(services, 'pkg_api')
    def test_condition_getter_with_stay_at_the_catalog(self, mock_pkg_api):
        mock_pkg_api.get_app_ui.return_value = {
            'foo': 'bar',
            'application': self.application
        }

        service = services.Service(cleaned_data={},
                                   version=semantic_version.Version('2.2.1'),
                                   fqn='io.murano.Test',
                                   application=self.application)
        form = service_forms.ServiceConfigurationForm()
        form.service = service
        form.base_fields = {'stay_at_the_catalog': True}
        wizard = catalog_views.Wizard()
        wizard.kwargs = {'drop_wm_form': True}

        wizard.form_list = collections.OrderedDict({
            '123': form
        })

        kwargs = {'app_id': '123'}
        result = services.condition_getter(self.request, kwargs)
        self.assertIn('Step 1', result)
        self.assertIsNotNone(result['Step 1'])

        result = result['Step 1'](wizard)
        self.assertTrue(result)
        self.assertNotIn('stay_at_the_catalog', form.base_fields)

    @mock.patch.object(services, 'pkg_api')
    def test_condition_getter_with_application_name(self, mock_pkg_api):
        mock_pkg_api.get_app_ui.return_value = {
            'foo': 'bar',
            'application': self.application
        }

        service = services.Service(cleaned_data={},
                                   version=semantic_version.Version('2.1.9'),
                                   fqn='io.murano.Test',
                                   application=self.application)
        form = service_forms.ServiceConfigurationForm()
        form.service = service
        form.base_fields = {'application_name': 'foo_app_name'}
        wizard = catalog_views.Wizard()
        wizard.kwargs = {'drop_wm_form': False}

        wizard.form_list = collections.OrderedDict({
            '123': form
        })

        kwargs = {'app_id': '123'}
        result = services.condition_getter(self.request, kwargs)
        self.assertIn('Step 1', result)
        self.assertIsNotNone(result['Step 1'])

        result = result['Step 1'](wizard)
        self.assertTrue(result)
        self.assertNotIn('application_name', form.base_fields)

    @mock.patch.object(services, 'pkg_api')
    def test_condition_getter_with_form_hidden(self, mock_pkg_api):
        mock_pkg_api.get_app_ui.return_value = {
            'foo': 'bar',
            'application': self.application
        }

        service = services.Service(cleaned_data={},
                                   version=semantic_version.Version('2.1.9'),
                                   fqn='io.murano.Test',
                                   application=self.application)
        form = service_forms.ServiceConfigurationForm()
        form.service = service
        wizard = catalog_views.Wizard()
        wizard.kwargs = {'drop_wm_form': True}

        wizard.form_list = collections.OrderedDict({
            '123': form
        })

        kwargs = {'app_id': '123'}
        result = services.condition_getter(self.request, kwargs)
        self.assertIn('Step 1', result)
        self.assertIsNotNone(result['Step 1'])

        result = result['Step 1'](wizard)
        self.assertFalse(result)

    @mock.patch.object(services, 'pkg_api')
    def test_get_app_forms(self, mock_pkg_api):
        mock_pkg_api.get_app_ui.return_value = {'Application': {}}

        kwargs = {'app_id': '123'}
        result = services.get_app_forms(self.request, kwargs)
        self.assertIsNotNone(result)
        result = next(iter(result))
        self.assertEqual('Step 1', result[0])
        self.assertEqual(service_forms.DynamicFormMetaclass,
                         type(result[1]))

    def test_service_type_from_id(self):
        match_id = 'aaa123-345'
        non_match_ids = ['aaa', '-aaa', 'aaa123-aaa']

        result = services.service_type_from_id(match_id)
        self.assertEqual('aaa123', result)

        for non_match_id in non_match_ids:
            result = services.service_type_from_id(non_match_id)
            self.assertEqual(non_match_id, result)

    @mock.patch.object(services, 'import_app')
    def test_get_app_field_description(self, mock_import_app):
        form = service_forms.ServiceConfigurationForm()
        mock_field = mock.Mock(description_title='test_title',
                               description='test_description')
        mock_field.widget.is_hidden = False
        form.base_fields = {'foo': mock_field}
        mock_import_app.return_value = mock.Mock(forms=[form])

        result = services.get_app_field_descriptions(self.request, '123', 0)
        self.assertEqual(2, len(result))
        descriptions, no_field_descriptions = result

        self.assertEqual([('foo', 'test_title', 'test_description')],
                         descriptions)
        self.assertEqual([], no_field_descriptions)

    @mock.patch.object(services, 'import_app')
    def test_get_app_field_description_with_hidden_field(self,
                                                         mock_import_app):
        form = service_forms.ServiceConfigurationForm()
        mock_field = mock.Mock(description_title='test_title',
                               description='test_description')
        mock_field.widget.is_hidden = True
        form.base_fields = {'foo': mock_field}
        mock_import_app.return_value = mock.Mock(forms=[form])

        result = services.get_app_field_descriptions(self.request, '123', 0)
        self.assertEqual(2, len(result))
        descriptions, no_field_descriptions = result

        self.assertEqual(['test_description', 'test_title'],
                         sorted(no_field_descriptions))
        self.assertEqual([], descriptions)
