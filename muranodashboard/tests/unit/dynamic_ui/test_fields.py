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

from django.core import exceptions
from django.core import validators as django_validator
from django import forms
from django.utils.translation import ugettext_lazy as _

import mock
import testtools

from muranodashboard.dynamic_ui import fields


class TestFields(testtools.TestCase):

    def setUp(self):
        super(TestFields, self).setUp()
        self.request = mock.Mock()
        self.request.user.service_region = None
        self.request.is_ajax = mock.Mock(side_effect=False)
        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(fields, 'LOG')
    def test_fields_with_initial_request(self, mock_log):
        test_initial = {
            'request': 'foo_request',
            'foo': 'bar'
        }
        self._test_fields_decorator_with_initial_request(test_initial)
        mock_log.debug.assert_called_once_with(
            "Using 'request' value from initial dictionary")

    @fields.with_request
    def _test_fields_decorator_with_initial_request(self, request, **kwargs):
        self.assertEqual('foo_request', request)
        self.assertEqual({'foo': 'bar'}, kwargs)

    @mock.patch.object(fields, 'LOG')
    def test_fields_with_request(self, mock_log):
        test_request = {
            'foo': 'bar'
        }
        self._test_fields_decorator_with_request({}, request=test_request)
        mock_log.debug.assert_called_once_with("Using direct 'request' value")

    @fields.with_request
    def _test_fields_decorator_with_request(self, request, **kwargs):
        self.assertEqual({'foo': 'bar'}, request)
        self.assertEqual({}, kwargs)

    @mock.patch.object(fields, 'LOG')
    def test_fields_except_validation_error(self, mock_log):
        with self.assertRaisesRegex(forms.ValidationError,
                                    "Can't get a request information"):
            self._test_fields_decorator_with_validation_error({}, request=None)
        mock_log.error.assert_called_once_with(
            "No 'request' value passed neither via initial dictionary, nor "
            "directly")

    @fields.with_request
    def _test_fields_decorator_with_validation_error(self, request, **kwargs):
        pass

    def test_make_yaql_validator(self):
        mock_validator_property = mock.MagicMock()
        mock_validator_property.__getitem__().spec.evaluate.return_value = True
        mock_validator_property.get.return_value = 'foo_message'

        validator_func = fields.make_yaql_validator(mock_validator_property)
        self.assertTrue(hasattr(validator_func, '__call__'))
        validator_func('bar')
        mock_validator_property.__getitem__().spec.evaluate.\
            assert_called_once_with(context=mock.ANY)

    def test_make_yaql_validator_except_validation_error(self):
        mock_validator_property = mock.MagicMock()
        mock_validator_property.__getitem__().spec.evaluate.return_value =\
            False
        mock_validator_property.get.return_value = 'foo_message'

        validator_func = fields.make_yaql_validator(mock_validator_property)
        self.assertTrue(hasattr(validator_func, '__call__'))
        e = self.assertRaises(forms.ValidationError, validator_func, 'bar')
        self.assertEqual('foo_message', e.message)

    def test_get_regex_validator(self):
        validator = django_validator.RegexValidator()
        test_expr = {
            'validators': [
                validator
            ]
        }
        result = fields.get_regex_validator(test_expr)
        self.assertEqual(validator, result)

    def test_get_regex_validator_except_error(self):
        for error in (TypeError, KeyError, IndexError):
            mock_expr = mock.MagicMock()
            mock_expr.__getitem__.side_effect = error
            result = fields.get_regex_validator(mock_expr)
            self.assertIsNone(result)

    def test_wrap_regex_validator(self):
        def _validator(value):
            pass

        func = fields.wrap_regex_validator(_validator, None)
        func(None)
        self.assertTrue(hasattr(func, '__call__'))

    def test_wrap_regex_validator_except_validation_error(self):
        def _validator(value):
            raise forms.ValidationError(None)

        with self.assertRaisesRegex(forms.ValidationError, 'foo'):
            func = fields.wrap_regex_validator(_validator, 'foo')
            func(None)

    @mock.patch.object(fields, 'glance')
    def test_get_murano_images(self, mock_glance):
        foo_image = mock.Mock(murano_property=None)
        foo_image.murano_image_info = '{"foo": "foo_val"}'
        bar_image = mock.Mock(murano_property=None)
        bar_image.murano_image_info = '{"bar": "bar_val"}'
        mock_glance.image_list_detailed.return_value = [
            [foo_image, bar_image], None
        ]

        murano_images = fields.get_murano_images(self.request)
        mock_glance.image_list_detailed.assert_called_once_with(self.request)
        self.assertEqual({"foo": "foo_val"}, foo_image.murano_property)
        self.assertEqual({"bar": "bar_val"}, bar_image.murano_property)

        expected_images = []
        foo_image.murano_property = {"foo": "foo_val"}
        bar_image.murano_property = {"bar": "bar_val"}
        expected_images.extend([foo_image, bar_image])

        self.assertEqual(expected_images, murano_images)

    @mock.patch.object(fields, 'exceptions')
    @mock.patch.object(fields, 'LOG')
    @mock.patch.object(fields, 'glance')
    def test_murano_images_except_exception(self, mock_glance, mock_log,
                                            mock_exceptions):
        mock_glance.image_list_detailed.side_effect = Exception

        murano_images = fields.get_murano_images(self.request)

        self.assertEqual([], murano_images)
        self.assertTrue(mock_log.error.called)
        mock_exceptions.handle.assert_called_once_with(
            self.request, _("Unable to retrieve public images."))

    @mock.patch.object(fields, 'messages')
    @mock.patch.object(fields, 'LOG')
    @mock.patch.object(fields, 'glance')
    def test_murano_images_except_value_error(self, mock_glance, mock_log,
                                              mock_messages):
        foo_image = mock.Mock(murano_property=None)
        foo_image.murano_image_info = "{'foo': 'foo_val'}"
        mock_glance.image_list_detailed.return_value = [
            [foo_image], None
        ]

        murano_images = fields.get_murano_images(self.request)

        self.assertEqual([], murano_images)
        mock_log.warning.assert_called_once_with(
            "JSON in image metadata is not valid. Check it in glance.")
        mock_messages.error.assert_called_once_with(
            self.request, _("Invalid murano image metadata"))

    def test_choice_get_title(self):
        choice = fields.Choice('test_title', True)
        self.assertEqual('test_title', fields._get_title(choice))
        self.assertIsNone(fields._get_title(None))

    def test_choice_disable_non_ready(self):
        choice = fields.Choice('test_title', True)
        self.assertEqual({}, fields._disable_non_ready(choice))
        choice = fields.Choice('test_title', False)
        self.assertEqual({'disabled': 'disabled'},
                         fields._disable_non_ready(choice))

    @mock.patch.object(fields, 'env_api')
    @mock.patch.object(fields, 'pkg_api')
    def test_make_select_cls_update(self, mock_pkg_api, mock_env_api):
        mock_pkg_api.app_by_fqn.return_value =\
            mock.Mock(fully_qualified_name='foo_class_fqn')
        mock_pkg_api.apps_that_inherit.return_value = [
            mock.Mock(fully_qualified_name='foo_class_fqn'),
            mock.Mock(fully_qualified_name='bar_class_fqn')
        ]
        expected_choices = [
            ('', 'Foo'), ('foo_app_id', 'foo_app_name'),
            ('bar_app_id', 'bar_app_name')
        ]

        foo_app = mock.MagicMock()
        foo_app.__getitem__.return_value = {'id': 'foo_app_id'}
        foo_app.configure_mock(name='foo_app_name')
        bar_app = mock.MagicMock()
        bar_app.__getitem__.return_value = {'id': 'bar_app_id'}
        bar_app.configure_mock(name='bar_app_name')
        mock_env_api.service_list_by_fqns.return_value = [foo_app, bar_app]

        dynamic_select_cls = fields.make_select_cls('foo_class_fqn')
        self.assertIsNotNone(dynamic_select_cls)
        self.assertEqual('DynamicSelect', dynamic_select_cls.__name__)

        dynamic_select = dynamic_select_cls(empty_value_message='Foo')
        dynamic_select.update({}, self.request, environment_id='foo_env_id')

        self.assertTrue(
            hasattr(dynamic_select.widget.add_item_link, '__call__'))
        self.assertEqual(expected_choices, dynamic_select.choices)
        self.assertIsNone(dynamic_select.initial)

        mock_pkg_api.app_by_fqn.assert_called_once_with(
            self.request, 'foo_class_fqn')
        mock_env_api.service_list_by_fqns.assert_called_once_with(
            self.request, 'foo_env_id',
            ['foo_class_fqn', 'bar_class_fqn']
        )

    @mock.patch.object(fields, 'env_api')
    @mock.patch.object(fields, 'pkg_api')
    def test_make_select_cls_update_2_choices(self, mock_pkg_api,
                                              mock_env_api):
        mock_pkg_api.app_by_fqn.return_value =\
            mock.Mock(fully_qualified_name='foo_class_fqn')
        mock_pkg_api.apps_that_inherit.return_value = []
        expected_choices = [
            ('', 'Foo'), ('foo_app_id', 'foo_app_name')
        ]

        foo_app = mock.MagicMock()
        foo_app.__getitem__.return_value = {'id': 'foo_app_id'}
        foo_app.configure_mock(name='foo_app_name')
        mock_env_api.service_list_by_fqns.return_value = [foo_app]

        dynamic_select_cls = fields.make_select_cls('foo_class_fqn')
        dynamic_select = dynamic_select_cls(empty_value_message='Foo')
        dynamic_select.update({}, self.request, environment_id='foo_env_id')

        self.assertEqual(expected_choices, dynamic_select.choices)
        self.assertEqual('foo_app_id', dynamic_select.initial)

        mock_pkg_api.app_by_fqn.assert_called_once_with(
            self.request, 'foo_class_fqn')
        mock_env_api.service_list_by_fqns.assert_called_once_with(
            self.request, 'foo_env_id', ['foo_class_fqn']
        )

    @mock.patch.object(fields, 'env_api')
    @mock.patch.object(fields, 'pkg_api')
    def test_make_select_cls_update_no_matching_classes(self, mock_pkg_api,
                                                        mock_env_api):
        mock_pkg_api.app_by_fqn.return_value = None
        mock_pkg_api.apps_that_inherit.return_value = []
        mock_env_api.service_list_by_fqns.return_value = []
        expected_choices = [('', 'Foo')]

        dynamic_select_cls = fields.make_select_cls('foo_class_fqn')
        dynamic_select = dynamic_select_cls(empty_value_message='Foo')
        dynamic_select.update({}, self.request, environment_id='foo_env_id')

        self.assertEqual(expected_choices, dynamic_select.choices)
        self.assertIsNone(dynamic_select.initial)

        mock_pkg_api.app_by_fqn.assert_called_once_with(
            self.request, 'foo_class_fqn')
        mock_env_api.service_list_by_fqns.assert_called_once_with(
            self.request, 'foo_env_id', [])

    @mock.patch.object(fields, 'reverse')
    @mock.patch.object(fields, 'env_api')
    @mock.patch.object(fields, 'pkg_api')
    def test_make_select_cls_update_make_link(self, mock_pkg_api, mock_env_api,
                                              mock_reverse):
        mock_pkg_api.app_by_fqn.return_value = None
        mock_pkg_api.apps_that_inherit.return_value = []
        mock_env_api.service_list_by_fqns.return_value = []
        mock_reverse.return_value = 'foo_url'

        dynamic_select_cls = fields.make_select_cls('foo_class_fqn')
        dynamic_select = dynamic_select_cls(empty_value_message='Foo')
        dynamic_select.update({}, self.request, environment_id='foo_env_id')

        result = dynamic_select.widget.add_item_link()
        self.assertEqual('', result)

        mock_pkg = mock.Mock(fully_qualified_name='foo_class_fqn')
        mock_pkg.configure_mock(name='foo_class_name')
        mock_pkg_api.app_by_fqn.return_value = mock_pkg
        dynamic_select.update({}, self.request, environment_id='foo_env_id')

        result = dynamic_select.widget.add_item_link()
        expected = '[["foo_class_name", "foo_url"]]'
        self.assertEqual(expected, result)

    @mock.patch.object(fields, 'env_api')
    @mock.patch.object(fields, 'pkg_api')
    def test_update_clean(self, mock_pkg_api, mock_env_api):
        mock_pkg_api.app_by_fqn.return_value = None
        mock_pkg_api.apps_that_inherit.return_value = []
        mock_env_api.service_list_by_fqns.return_value = []

        dynamic_select_cls = fields.make_select_cls('foo_class_fqn')
        dynamic_select = dynamic_select_cls(empty_value_message='Foo')
        dynamic_select.form = mock.Mock()
        dynamic_select.required = False
        dynamic_select.choices = [('value', '')]

        self.assertEqual('value', dynamic_select.clean('value'))


class TestRawProperty(testtools.TestCase):

    def test_finalize(self):
        class Control(object):
            def __init__(self):
                self.value = None

            @property
            def prop(self):
                return self.value

            @prop.setter
            def prop(self, value):
                self.value = value

            @prop.deleter
            def prop(self):
                delattr(self, 'value')

        mock_service = mock.Mock()
        mock_service.get_data.side_effect = ['foo_value']

        raw_property = fields.RawProperty('prop', 'foo_spec')
        props = raw_property.finalize(
            'foo_form_name', mock_service, Control)

        ctl = Control()

        result = props.fget(ctl)
        self.assertEqual('foo_value', result)

        props.fset(ctl, 'bar_value')
        self.assertEqual('bar_value', ctl.prop)

        props.fdel(ctl)
        self.assertNotIn('prop', ctl.__dict__)


class TestCustomPropertiesField(testtools.TestCase):

    def setUp(self):
        super(TestCustomPropertiesField, self).setUp()

        test_validator_1 = mock.MagicMock(__call__=lambda: None)
        test_validator_2 = {
            'expr': {
                'validators': [django_validator.RegexValidator()]
            }
        }
        test_validator_3 = {
            'expr': fields.RawProperty(None, None)
        }
        kwargs = {
            'validators': [
                test_validator_1, test_validator_2, test_validator_3
            ]
        }
        for arg in fields.FIELD_ARGS_TO_ESCAPE:
            kwargs[arg] = 'foo_' + arg

        custom_props_field = fields.CustomPropertiesField(**kwargs)

        for arg in fields.FIELD_ARGS_TO_ESCAPE:
            self.assertTrue(hasattr(custom_props_field, arg))
            self.assertEqual('foo_{0}'.format(arg),
                             getattr(custom_props_field, arg))
        self.assertEqual(3, len(custom_props_field.validators))

    def test_clean(self):
        mock_form = mock.Mock()
        mock_form.cleaned_data = 'test_cleaned_data'
        custom_props_field = fields.CustomPropertiesField()
        custom_props_field.form = mock_form

        custom_props_field.enabled = True
        self.assertEqual('foo', custom_props_field.clean('foo'))

        custom_props_field.enabled = False
        self.assertEqual('foo', custom_props_field.clean('foo'))

    def test_finalize_properties(self):
        finalize_properties = fields.CustomPropertiesField.finalize_properties
        kwargs = {
            'foo_raw_property': fields.RawProperty('foo_key', 'foo_spec')
        }
        mock_service = mock.Mock()

        result = finalize_properties(kwargs, 'foo_form_name', mock_service)
        self.assertIsNotNone(result)
        result = finalize_properties({}, 'foo_form_name', mock_service)
        self.assertIsNotNone(result)


class TestPasswordField(testtools.TestCase):

    def setUp(self):
        super(TestPasswordField, self).setUp()
        self.password_field = fields.PasswordField(None)
        self.password_field.original = True
        self.password_field.required = True
        self.addCleanup(mock.patch.stopall)

    def test_get_clone_name(self):
        self.assertEqual('foo-clone',
                         fields.PasswordField.get_clone_name('foo'))

    def test_compare(self):
        test_form_data = {'name': 'foo', 'name-clone': 'foo'}
        result = self.password_field.compare('name', test_form_data)
        self.assertIsNone(result)

    def test_compare_except_validation_error(self):
        test_form_data = {'name': 'foo', 'name-clone': 'bar'}
        self.assertRaises(forms.ValidationError, self.password_field.compare,
                          'name', test_form_data)

    def test_deepcopy(self):
        self.password_field.error_messages = None
        test_memo = {}
        result = self.password_field.__deepcopy__(test_memo)
        self.assertIsInstance(result, fields.PasswordField)
        self.assertGreater(len(test_memo.keys()), 0)

        self.password_field.error_messages = ['foo_error', 'bar_error']
        test_memo = {}
        result = self.password_field.__deepcopy__(test_memo)
        self.assertIsInstance(result, fields.PasswordField)
        self.assertGreater(len(test_memo.keys()), 0)
        self.assertEqual(['foo_error', 'bar_error'], result.error_messages)

    def test_clone_field(self):
        self.assertFalse(self.password_field.has_clone)

        result = self.password_field.clone_field()
        self.assertIsInstance(result, fields.PasswordField)
        self.assertFalse(result.original)
        self.assertEqual('Confirm password', result.label)
        self.assertEqual('Please confirm your password',
                         result.error_messages['required'])
        self.assertEqual('Retype your password', result.help_text)


class TestFlavorChoiceField(testtools.TestCase):

    def setUp(self):
        super(TestFlavorChoiceField, self).setUp()

        self.requirements = {
            'min_vcpus': 1,
            'min_disk': 100,
            'min_memory_mb': 500,
            'max_vcpus': 5,
            'max_disk': 5000,
            'max_memory_mb': 16000
        }
        kwargs = {
            'requirements': self.requirements
        }
        self.flavor_choice_field = fields.FlavorChoiceField(**kwargs)
        self.flavor_choice_field.choices = []
        self.flavor_choice_field.initial = None
        self.assertEqual(kwargs['requirements'],
                         self.flavor_choice_field.requirements)

        self.request = {'request': mock.Mock()}
        self.tiny_flavor = mock.Mock()
        self.tiny_flavor.configure_mock(id='id1', name='m1.tiny')
        self.small_flavor = mock.Mock()
        self.small_flavor.configure_mock(id='id2', name='m1.small')
        self.medium_flavor = mock.Mock()
        self.medium_flavor.configure_mock(id='id3', name='m1.medium')

        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(fields, 'nova')
    def test_update(self, mock_nova):
        """"Test if flavor with any invalid requirement is excluded."""
        mock_nova.novaclient().flavors.list.return_value = [
            self.tiny_flavor, self.small_flavor, self.medium_flavor
        ]
        expected_choices = [
            ('id3', 'm1.medium'), ('id2', 'm1.small')
        ]
        valid_requirements = [
            ('vcpus', 2), ('disk', 101), ('ram', 501)
        ]
        invalid_requirements = [
            ('vcpus', 0), ('vcpus', 6), ('disk', 99), ('disk', 5001),
            ('ram', 499), ('ram', 16001)
        ]

        for req in valid_requirements:
            for flavor in (self.small_flavor, self.medium_flavor):
                setattr(flavor, req[0], req[1])

        for invalid_req in invalid_requirements:
            for valid_req in valid_requirements:
                if invalid_req[0] != valid_req[0]:
                    setattr(self.tiny_flavor, valid_req[0], valid_req[1])
            setattr(self.tiny_flavor, invalid_req[0], invalid_req[1])
            self.flavor_choice_field.update(self.request)
            self.assertEqual(expected_choices,
                             self.flavor_choice_field.choices)
            self.assertEqual('id3', self.flavor_choice_field.initial)

    @mock.patch.object(fields, 'nova')
    def test_update_without_requirements(self, mock_nova):
        mock_nova.novaclient().flavors.list.return_value = [
            self.tiny_flavor, self.small_flavor, self.medium_flavor
        ]
        del self.flavor_choice_field.requirements

        expected_choices = [
            ('id3', 'm1.medium'),
            ('id2', 'm1.small'),
            ('id1', 'm1.tiny')
        ]

        self.flavor_choice_field.update(self.request)
        self.assertEqual(expected_choices, self.flavor_choice_field.choices)
        self.assertEqual('id3', self.flavor_choice_field.initial)


class TestKeyPairChoiceField(testtools.TestCase):

    def setUp(self):
        super(TestKeyPairChoiceField, self).setUp()
        self.request = {'request': mock.Mock()}
        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(fields, 'nova')
    def test_update(self, mock_nova):
        foo_keypair = mock.Mock()
        bar_keypair = mock.Mock()
        foo_keypair.configure_mock(name='foo')
        bar_keypair.configure_mock(name='bar')
        mock_nova.novaclient().keypairs.list.return_value = [
            foo_keypair, bar_keypair
        ]
        key_pair_choice_field = fields.KeyPairChoiceField()
        key_pair_choice_field.choices = []
        key_pair_choice_field.update(self.request)

        expected_choices = [
            ('', _('No keypair')), ('foo', 'foo'), ('bar', 'bar')
        ]
        self.assertEqual(sorted(expected_choices),
                         sorted(key_pair_choice_field.choices))


class TestSecurityGroupChoiceField(testtools.TestCase):

    def setUp(self):
        super(TestSecurityGroupChoiceField, self).setUp()
        self.request = {'request': mock.Mock()}
        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(fields, 'neutron')
    def test_update(self, mock_neutron):
        mock_neutron.security_group_list.return_value = [
            mock.Mock(name_or_id='foo'),
            mock.Mock(name_or_id='bar')
        ]
        security_group_choice_field = fields.SecurityGroupChoiceField()
        security_group_choice_field.choices = []
        security_group_choice_field.update(self.request)

        expected_choices = [
            ('', _('Application default security group')),
            ('foo', 'foo'), ('bar', 'bar')
        ]
        self.assertEqual(sorted(expected_choices),
                         sorted(security_group_choice_field.choices))


class TestImageChoiceField(testtools.TestCase):

    def setUp(self):
        super(TestImageChoiceField, self).setUp()
        self.request = {'request': mock.Mock()}
        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(fields, 'get_murano_images')
    def test_update(self, mock_get_murano_images):
        mock_get_murano_images.return_value = [
            # Test successful control flow.
            mock.Mock(id='foo_image_id', murano_property={
                      'title': 'foo_image_title', 'type': 'png'},
                      status='active'),
            # Test whether second continue statement works.
            mock.Mock(id='bar_image_id', murano_property={
                      'title': 'foo_image_title', 'type': 'jpg'},
                      status='active')
        ]
        image_choice_field = fields.ImageChoiceField()
        image_choice_field.image_type = 'png'
        image_choice_field.choices = []
        image_choice_field.update(self.request)

        self.assertEqual(("", _("Select Image")),
                         image_choice_field.choices[0])
        self.assertEqual("foo_image_id", image_choice_field.choices[1][0])
        self.assertIsInstance(image_choice_field.choices[1][1], fields.Choice)

        # Test whether first continue statement works.
        mock_get_murano_images.return_value = [
            mock.Mock(murano_property={
                      'title': 'bar_image_title', 'type': None},
                      status=None)
        ]
        image_choice_field.image_type = ''
        image_choice_field.choices = []
        image_choice_field.update(self.request)
        expected_choices = [("", _("No images available"))]
        self.assertEqual(expected_choices, image_choice_field.choices)


class TestNetworkChoiceField(testtools.TestCase):

    def setUp(self):
        super(TestNetworkChoiceField, self).setUp()
        self.network_choice_field = fields.NetworkChoiceField(
            filter=None,
            murano_networks='exclude',
            allow_auto=True)
        self.request = {'request': mock.Mock()}
        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(fields, 'net')
    def test_update(self, mock_net):
        mock_net.get_available_networks.return_value = [
            (('foo', 'foo'), _('Foo'))
        ]
        expected_choices = [
            ((None, None), _('Auto')), (('foo', 'foo'), _('Foo'))
        ]

        self.network_choice_field.update(self.request)
        self.assertEqual(expected_choices, self.network_choice_field.choices)
        mock_net.get_available_networks.assert_called_once_with(
            self.request['request'], None, 'exclude')

    def test_to_python(self):
        self.assertEqual({'foo': 'bar'},
                         self.network_choice_field.to_python('{"foo": "bar"}'))
        self.assertEqual((None, None),
                         self.network_choice_field.to_python(None))


class TestVolumeChoiceField(testtools.TestCase):

    def setUp(self):
        super(TestVolumeChoiceField, self).setUp()
        self.request = {'request': mock.Mock()}
        self.addCleanup(mock.patch.stopall)

    @mock.patch.object(fields, 'cinder')
    def test_update(self, mock_cinder):
        foo_vol = mock.Mock()
        bar_snap = mock.Mock()
        baz_snap = mock.Mock()
        foo_vol.configure_mock(name='foo_vol', id='foo_id', status='available')
        bar_snap.configure_mock(name='bar_snap', id='bar_id',
                                status='available')
        baz_snap.configure_mock(name='baz_snap', id='baz_id', status='error')
        mock_cinder.volume_list.return_value = [foo_vol]
        mock_cinder.volume_snapshot_list.return_value = [bar_snap]
        volume_choice_field = fields.VolumeChoiceField()
        volume_choice_field.choices = []
        volume_choice_field.update(self.request)

        expected_choices = [
            ('', _('Select volume')), ('foo_id', 'foo_vol'),
            ('bar_id', 'bar_snap')
        ]

        self.assertEqual(sorted(expected_choices),
                         sorted(volume_choice_field.choices))

    @mock.patch.object(fields, 'cinder')
    def test_update_withoutsnapshot(self, mock_cinder):
        foo_vol = mock.Mock()
        bar_vol = mock.Mock()
        baz_snap = mock.Mock()
        foo_vol.configure_mock(name='foo_vol', id='foo_id', status='available')
        bar_vol.configure_mock(name='bar_vol', id='bar_id', status='error')
        baz_snap.configure_mock(name='baz_snap', id='baz_id',
                                status='available')
        mock_cinder.volume_list.return_value = [foo_vol]
        mock_cinder.volume_snapshot_list.return_value = [baz_snap]
        volume_choice_field = fields.VolumeChoiceField(include_snapshots=False)
        volume_choice_field.choices = []
        volume_choice_field.update(self.request)

        expected_choices = [
            ('', _('Select volume')), ('foo_id', 'foo_vol')
        ]

        self.assertEqual(sorted(expected_choices),
                         sorted(volume_choice_field.choices))

    @mock.patch.object(fields, 'cinder')
    def test_update_withoutvolume(self, mock_cinder):
        foo_vol = mock.Mock()
        baz_snap = mock.Mock()
        foo_vol.configure_mock(name='foo_vol', id='foo_id', status='available')
        baz_snap.configure_mock(name='baz_snap', id='baz_id',
                                status='available')
        mock_cinder.volume_list.return_value = [foo_vol]
        mock_cinder.volume_snapshot_list.return_value = [baz_snap]
        volume_choice_field = fields.VolumeChoiceField(include_volumes=False)
        volume_choice_field.choices = []
        volume_choice_field.update(self.request)

        expected_choices = [
            ('', _('Select volume')), ('baz_id', 'baz_snap')
        ]

        self.assertEqual(sorted(expected_choices),
                         sorted(volume_choice_field.choices))

    @mock.patch.object(fields, 'exceptions')
    @mock.patch.object(fields, 'cinder')
    def test_update_except_snapshot_list_exception(self, mock_cinder,
                                                   mock_exceptions):
        foo_vol = mock.Mock()
        bar_vol = mock.Mock()
        foo_vol.configure_mock(name='foo_vol', id='foo_id', status='available')
        bar_vol.configure_mock(name='bar_vol', id='bar_id', status='error')
        mock_cinder.volume_list.return_value = [foo_vol]
        mock_cinder.volume_snapshot_list.side_effect = Exception
        volume_choice_field = fields.VolumeChoiceField(include_volumes=True,
                                                       include_snapshots=True)
        volume_choice_field.choices = []
        volume_choice_field.update(self.request)

        expected_choices = [
            ('', _('Select volume')), ('foo_id', 'foo_vol')
        ]

        self.assertEqual(sorted(expected_choices),
                         sorted(volume_choice_field.choices))
        mock_exceptions.handle.assert_called_once_with(
            self.request['request'], _('Unable to retrieve snapshot list.'))

    @mock.patch.object(fields, 'exceptions')
    @mock.patch.object(fields, 'cinder')
    def test_update_except_volume_list_exception(self, mock_cinder,
                                                 mock_exceptions):
        bar_snap = mock.Mock()
        bar_snap.configure_mock(name='bar_snap', id='bar_id',
                                status='available')
        mock_cinder.volume_list.side_effect = Exception
        mock_cinder.volume_snapshot_list.return_value = [bar_snap]
        volume_choice_field = fields.VolumeChoiceField(include_volumes=True,
                                                       include_snapshots=True)
        volume_choice_field.choices = []
        volume_choice_field.update(self.request)

        expected_choices = [
            ('', _('Select volume')), ('bar_id', 'bar_snap')
        ]

        self.assertEqual(expected_choices, volume_choice_field.choices)
        mock_exceptions.handle.assert_called_once_with(
            self.request['request'], _('Unable to retrieve volume list.'))

    @mock.patch.object(fields, 'exceptions')
    @mock.patch.object(fields, 'cinder')
    def test_update_except_exception(self, mock_cinder, mock_exceptions):
        mock_cinder.volume_list.side_effect = Exception
        mock_cinder.volume_snapshot_list.side_effect = Exception
        volume_choice_field = fields.VolumeChoiceField(include_volumes=True,
                                                       include_snapshots=True)
        volume_choice_field.choices = []
        volume_choice_field.update(self.request)

        expected_choices = [
            ('', _('No volumes available'))
        ]
        expected_calls = [
            mock.call(self.request['request'],
                      _('Unable to retrieve volume list.')),
            mock.call(self.request['request'],
                      _('Unable to retrieve snapshot list.'))
        ]
        self.assertEqual(expected_choices, volume_choice_field.choices)
        mock_exceptions.handle.assert_has_calls(expected_calls)


class TestAZoneChoiceField(testtools.TestCase):

    @mock.patch.object(fields, 'nova')
    def test_update(self, mock_nova):
        mock_nova.novaclient().availability_zones.list.return_value = [
            mock.Mock(zoneName='foo_zone', zoneState='foo_state'),
            mock.Mock(zoneName='bar_zone', zoneState='bar_state')
        ]
        request = {'request': mock.Mock()}
        a_zone_choice_field = fields.AZoneChoiceField()
        a_zone_choice_field.choices = []

        expected_choices = [
            ("bar_zone", "bar_zone"), ("foo_zone", "foo_zone")
        ]
        a_zone_choice_field.update(request)
        self.assertEqual(expected_choices, a_zone_choice_field.choices)

    @mock.patch.object(fields, 'exceptions')
    @mock.patch.object(fields, 'nova')
    def test_update_except_exception(self, mock_nova, mock_exc):
        mock_nova.novaclient().availability_zones.list.side_effect = Exception
        request = {'request': mock.Mock()}
        a_zone_choice_field = fields.AZoneChoiceField()
        a_zone_choice_field.choices = []

        expected_choices = [
            ("", _("No availability zones available"))
        ]
        a_zone_choice_field.update(request)
        self.assertEqual(expected_choices, a_zone_choice_field.choices)
        mock_exc.handle.assert_called_once_with(request['request'], mock.ANY)


class TestBooleanField(testtools.TestCase):

    def test_boolean_field(self):
        class Widget(object):
            def __init__(self, attrs):
                self.attrs = attrs

        boolean_field = fields.BooleanField(widget=Widget)
        self.assertIsInstance(boolean_field.widget, Widget)
        self.assertEqual({'class': 'checkbox'}, boolean_field.widget.attrs)
        self.assertFalse(boolean_field.required)

        boolean_field = fields.BooleanField()
        self.assertIsInstance(boolean_field.widget, forms.CheckboxInput)
        self.assertEqual({'class': 'checkbox'}, boolean_field.widget.attrs)
        self.assertFalse(boolean_field.required)


class TestDatabaseListField(testtools.TestCase):

    def setUp(self):
        super(TestDatabaseListField, self).setUp()
        self.database_list_field = fields.DatabaseListField()
        self.addCleanup(mock.patch.stopall)

    def test_to_python(self):
        self.assertEqual([], self.database_list_field.to_python(None))
        self.assertEqual(['foo', 'bar'],
                         self.database_list_field.to_python('foo ,bar '))

    def test_validate(self):
        valid_value = ['a123', '_123', 'a123_$#@']
        result = self.database_list_field.validate(valid_value)
        self.assertIsNone(result)

    def test_validate_except_validation_error(self):
        invalid_value = ['123abc']

        expected_error = "First symbol should be latin letter or underscore. "\
                         "Subsequent symbols can be latin letter, numeric, "\
                         "underscore, at sign, number sign or dollar sign"
        e = self.assertRaises(exceptions.ValidationError,
                              self.database_list_field.validate, invalid_value)
        self.assertEqual(expected_error, e.message)


class TestErrorWidget(testtools.TestCase):

    def test_render(self):
        error_widget = fields.ErrorWidget()
        error_widget.message = 'foo_message'
        result = error_widget.render("'foo_name'", None)
        self.assertEqual("<div name='foo_name'>foo_message</div>", result)
