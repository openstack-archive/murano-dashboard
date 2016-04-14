#    Copyright (c) 2013 Mirantis, Inc.
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

import ast
import copy
import json
import re

from django.core.urlresolvers import reverse
from django.core import validators as django_validator
from django import forms
from django.http import Http404
from django.template import defaultfilters
from django.utils.encoding import force_text
from django.utils import html
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms as hz_forms
from horizon import messages
from openstack_dashboard.api import glance
from openstack_dashboard.api import nova
from oslo_log import log as logging
import six
from yaql import legacy

from muranodashboard.api import packages as pkg_api
from muranodashboard.common import net
from muranodashboard.environments import api as env_api

from oslo_log import versionutils


LOG = logging.getLogger(__name__)


def with_request(func):
    """Injects request into func

    The decorator is meant to be used together with `UpdatableFieldsForm':
    apply it to the `update' method of fields inside that form.
    """
    def update(self, initial, request=None, **kwargs):
        initial_request = initial.get('request')
        for key, value in six.iteritems(initial):
            if key != 'request' and key not in kwargs:
                kwargs[key] = value

        if initial_request:
            LOG.debug("Using 'request' value from initial dictionary")
            func(self, initial_request, **kwargs)
        elif request:
            LOG.debug("Using direct 'request' value")
            func(self, request, **kwargs)
        else:
            LOG.error("No 'request' value passed neither via initial "
                      "dictionary, nor directly")
            raise forms.ValidationError("Can't get a request information")
    return update


def make_yaql_validator(validator_property):
    """Field-level validator uses field's value as its '$' root object."""
    expr = validator_property['expr'].spec
    message = validator_property.get('message', '')

    def validator_func(value):
        context = legacy.create_context()
        context['$'] = value
        if not expr.evaluate(context=context):
            raise forms.ValidationError(message)

    return validator_func


def get_regex_validator(expr):
    try:
        validator = expr['validators'][0]
        if isinstance(validator, django_validator.RegexValidator):
            return validator
    except (TypeError, KeyError, IndexError):
        pass
    return None


# This function is needed if we don't want to change existing services
# regexpValidators
def wrap_regex_validator(validator, message):
    def _validator(value):
        try:
            validator(value)
        except forms.ValidationError:
            # provide our own message
            raise forms.ValidationError(message)
    return _validator


def get_murano_images(request):
    images = []
    try:
        # https://bugs.launchpad.net/murano/+bug/1339261 - glance
        # client version change alters the API. Other tuple values
        # are _more and _prev (in recent glance client)
        images = glance.image_list_detailed(request)[0]
    except Exception:
        LOG.error("Error to request image list from glance ")
        exceptions.handle(request, _("Unable to retrieve public images."))
    murano_images = []
    for image in images:
        murano_property = image.properties.get('murano_image_info')
        if murano_property:
            try:
                murano_metadata = json.loads(murano_property)
            except ValueError:
                LOG.warning("JSON in image metadata is not valid. "
                            "Check it in glance.")
                messages.error(request, _("Invalid murano image metadata"))
            else:
                image.murano_property = murano_metadata
                murano_images.append(image)
    return murano_images


class RawProperty(object):
    def __init__(self, key, spec):
        self.key = key
        self.spec = spec

    def finalize(self, form_name, service):
        def _get(field):
            data_ready, value = service.get_data(form_name, self.spec)
            return value if data_ready else field.__dict__[self.key]

        def _set(field, value):
            field.__dict__[self.key] = value

        def _del(field):
            del field.__dict__[self.key]
        return property(_get, _set, _del)


FIELD_ARGS_TO_ESCAPE = ['help_text', 'initial', 'description', 'label']


class CustomPropertiesField(forms.Field):
    def __init__(self, description=None, description_title=None,
                 *args, **kwargs):
        self.description = description
        self.description_title = (description_title or
                                  force_text(kwargs.get('label', '')))

        for arg in FIELD_ARGS_TO_ESCAPE:
            if kwargs.get(arg):
                kwargs[arg] = html.escape(force_text(kwargs[arg]))

        validators = []
        for validator in kwargs.get('validators', []):
            if hasattr(validator, '__call__'):  # single regexpValidator
                validators.append(validator)
            else:  # mixed list of regexpValidator-s and YAQL validators
                expr = validator.get('expr')
                regex_validator = get_regex_validator(expr)
                if regex_validator:
                    validators.append(wrap_regex_validator(
                        regex_validator, validator.get('message', '')))
                elif isinstance(expr, RawProperty):
                    validators.append(validator)
        kwargs['validators'] = validators

        super(CustomPropertiesField, self).__init__(*args, **kwargs)

    def clean(self, value):
        """Skip all validators if field is disabled."""
        # form is assigned in ServiceConfigurationForm.finalize_fields()
        form = self.form
        # the only place to ensure that Service object has up-to-date
        # cleaned_data
        form.service.update_cleaned_data(form.cleaned_data, form=form)
        if getattr(self, 'enabled', True):
            return super(CustomPropertiesField, self).clean(value)
        else:
            return super(CustomPropertiesField, self).to_python(value)

    @classmethod
    def finalize_properties(cls, kwargs, form_name, service):
        props = {}
        for key, value in kwargs.items():
            if isinstance(value, RawProperty):
                props[key] = value.finalize(form_name, service)
                del kwargs[key]
        if props:
            return type(cls.__name__, (cls,), props)
        else:
            return cls


class CharField(forms.CharField, CustomPropertiesField):
    pass


class PasswordField(CharField):
    special_characters = '!@#$%^&*()_+|\/.,~?><:{}'
    password_re = re.compile('^.*(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[%s]).*$'
                             % special_characters)
    has_clone = False
    original = True
    validate_password = django_validator.RegexValidator(
        password_re, _('The password must contain at least one letter, one   \
                               number and one special character'), 'invalid')

    @staticmethod
    def get_clone_name(name):
        return name + '-clone'

    def compare(self, name, form_data):
        if self.original and self.required:
            # run compare only for original fields
            # do not run compare for hidden fields (they are not required)
            if form_data.get(name) != form_data.get(self.get_clone_name(name)):
                raise forms.ValidationError(_(u"{0}{1} don't match").format(
                    self.label, defaultfilters.pluralize(2)))

    class PasswordInput(forms.PasswordInput):
        class Media(object):
            js = ('muranodashboard/js/passwordfield.js',)

    def __init__(self, label, *args, **kwargs):
        self.confirm_input = kwargs.pop('confirm_input', True)

        kwargs.update({'label': label,
                       'error_messages': kwargs.get('error_messages', {}),
                       'widget': forms.PasswordInput(render_value=True)})

        validators = kwargs.get('validators')
        help_text = kwargs.get('help_text')

        if not validators:
            # No custom validators, using default validator
            validators = [self.validate_password]
            if not help_text:
                help_text = _(
                    'Enter a complex password with at least one letter, '
                    'one number and one special character')

            kwargs['error_messages'].setdefault(
                'invalid', self.validate_password.message)
            kwargs['min_length'] = kwargs.get('min_length', 7)
            kwargs['max_length'] = kwargs.get('max_length', 255)
            kwargs['widget'] = self.PasswordInput(render_value=True)
        else:
            if not help_text:
                # NOTE(kzaitsev) There are custom validators for password,
                # but no help text let's leave only a generic message,
                # since we do not know exact constraints
                help_text = _('Enter a password')

        kwargs.update({'validators': validators,
                       'help_text': help_text})

        super(PasswordField, self).__init__(*args, **kwargs)

    def __deepcopy__(self, memo):
        result = super(PasswordField, self).__deepcopy__(memo)
        result.error_messages = copy.deepcopy(self.error_messages)
        return result

    def clone_field(self):
        self.has_clone = True

        field = copy.deepcopy(self)
        field.original = False
        field.label = _('Confirm password')
        field.error_messages['required'] = _('Please confirm your password')
        field.help_text = _('Retype your password')
        return field


class IntegerField(forms.IntegerField, CustomPropertiesField):
    pass


class ChoiceField(forms.ChoiceField, CustomPropertiesField):
    pass


class DynamicChoiceField(hz_forms.DynamicChoiceField, CustomPropertiesField):
    pass


class FlavorChoiceField(ChoiceField):
    def __init__(self, *args, **kwargs):
        if 'requirements' in kwargs:
            self.requirements = kwargs.pop('requirements')
        super(FlavorChoiceField, self).__init__(*args, **kwargs)

    @with_request
    def update(self, request, **kwargs):
        self.choices = []
        flavors = nova.novaclient(request).flavors.list()

        # If no requirements are present, return all the flavors.
        if not hasattr(self, 'requirements'):
            self.choices = [(flavor.name, flavor.name) for flavor in flavors]
        else:
            for flavor in flavors:
                # If a flavor doesn't meet a minimum requirement,
                # do not add it to the options list and skip to the
                # next flavor.
                if flavor.vcpus < self.requirements.get('min_vcpus', 0):
                    continue
                if flavor.disk < self.requirements.get('min_disk', 0):
                    continue
                if flavor.ram < self.requirements.get('min_memory_mb', 0):
                    continue
                if 'max_vcpus' in self.requirements:
                    if flavor.vcpus > self.requirements['max_vcpus']:
                        continue
                if 'max_disk' in self.requirements:
                    if flavor.disk > self.requirements['max_disk']:
                        continue
                if 'max_memory_mb' in self.requirements:
                    if flavor.ram > self.requirements['max_memory_mb']:
                        continue
                self.choices.append((flavor.name, flavor.name))
        # Search through selected flavors
        for flavor_name, flavor_name in self.choices:
            if 'medium' in flavor_name:
                self.initial = flavor_name
                break


class KeyPairChoiceField(DynamicChoiceField):
    " This widget allows to select keypair for VMs "
    @with_request
    def update(self, request, **kwargs):
        self.choices = [('', _('No keypair'))]
        for keypair in nova.novaclient(request).keypairs.list():
            self.choices.append((keypair.name, keypair.name))


# NOTE(kzaitsev): for transform to work correctly on horizon SelectWidget
# Choice has to be non-string
class Choice(object):
    """A choice that allows disabling specific choices in a SelectWidget."""
    def __init__(self, title, enabled):
        self.title = title
        self.enabled = enabled


def _get_title(data):
    if isinstance(data, Choice):
        return data.title
    return data


def _disable_non_ready(data):
    if getattr(data, 'enabled', True):
        return {}
    else:
        return {'disabled': 'disabled'}


class ImageChoiceField(ChoiceField):
    widget = hz_forms.SelectWidget(transform=_get_title,
                                   transform_html_attrs=_disable_non_ready)

    def __init__(self, *args, **kwargs):
        self.image_type = kwargs.pop('image_type', None)
        super(ImageChoiceField, self).__init__(*args, **kwargs)

    @with_request
    def update(self, request, **kwargs):
        image_map, image_choices = {}, []
        murano_images = get_murano_images(request)
        for image in murano_images:
            murano_data = image.murano_property
            title = murano_data.get('title', image.name)

            if image.status == 'active':
                title = Choice(title, enabled=True)
            else:
                title = Choice("{} ({})".format(title, image.status),
                               enabled=False)
            if self.image_type is not None:
                itype = murano_data.get('type')

                if not self.image_type and itype is None:
                    continue

                prefix = '{type}.'.format(type=self.image_type)
                if (not itype.startswith(prefix) and
                        not self.image_type == itype):
                    continue
            image_map[image.id] = title

        for id_, title in sorted(six.iteritems(image_map), key=lambda e: e[1]):
            image_choices.append((id_, title))
        if image_choices:
            image_choices.insert(0, ("", _("Select Image")))
        else:
            image_choices.insert(0, ("", _("No images available")))

        self.choices = image_choices


class NetworkChoiceField(ChoiceField):
    def __init__(self,
                 include_subnets=True,
                 filter=None,
                 murano_networks=None,
                 allow_auto=True,
                 *args,
                 **kwargs):
        self.filter = filter
        if murano_networks:
            if murano_networks.lower() not in ["exclude", "translate"]:
                raise ValueError(_("Invalid value of 'murano_nets' option"))
        self.murano_networks = murano_networks
        self.include_subnets = include_subnets
        self.allow_auto = allow_auto
        super(NetworkChoiceField, self).__init__(*args,
                                                 **kwargs)

    @with_request
    def update(self, request, **kwargs):
        """Populates available networks in the control

        This method is called automatically when the form which contains it is
        rendered
        """
        network_choices = net.get_available_networks(request,
                                                     self.include_subnets,
                                                     self.filter,
                                                     self.murano_networks)
        if self.allow_auto:
            network_choices.insert(0, ((None, None), _('Auto')))
        self.choices = network_choices or []

    def to_python(self, value):
        """Converts string representation of widget to tuple value

        Is called implicitly during form cleanup phase
        """
        if value:
            return ast.literal_eval(value)
        else:  # may happen if no networks are available and "Auto" is disabled
            return None, None


class AZoneChoiceField(ChoiceField):
    @with_request
    def update(self, request, **kwargs):
        try:
            availability_zones = nova.novaclient(
                request).availability_zones.list(detailed=False)
        except Exception:
            availability_zones = []
            exceptions.handle(request,
                              _("Unable to retrieve  availability zones."))

        az_choices = [(az.zoneName, az.zoneName)
                      for az in availability_zones if az.zoneState]
        if not az_choices:
            az_choices.insert(0, ("", _("No availability zones available")))

        self.choices = az_choices


class BooleanField(forms.BooleanField, CustomPropertiesField):
    def __init__(self, *args, **kwargs):
        if 'widget' in kwargs:
            widget = kwargs['widget']
            if isinstance(widget, type):
                widget = widget(attrs={'class': 'checkbox'})
        else:
            widget = forms.CheckboxInput(attrs={'class': 'checkbox'})
        kwargs['widget'] = widget
        kwargs['required'] = False
        super(BooleanField, self).__init__(*args, **kwargs)


@versionutils.deprecated(
    as_of=versionutils.deprecated.JUNO,
    in_favor_of='type boolean (regular BooleanField)',
    remove_in=1)
class FloatingIpBooleanField(BooleanField):
    pass


class ClusterIPField(forms.GenericIPAddressField, CustomPropertiesField):
    def __init__(self, *args, **kwargs):
        super(ClusterIPField, self).__init__(protocol='ipv4', *args, **kwargs)


class DatabaseListField(CharField):
    validate_mssql_identifier = django_validator.RegexValidator(
        re.compile(r'^[a-zA-z_][a-zA-Z0-9_$#@]*$'),
        _(u'First symbol should be latin letter or underscore. Subsequent '
          u'symbols can be latin letter, numeric, underscore, at sign, '
          u'number sign or dollar sign'))

    default_error_messages = {'invalid': validate_mssql_identifier.message}

    def to_python(self, value):
        """Normalize data to a list of strings."""
        if not value:
            return []
        return [name.strip() for name in value.split(',')]

    def validate(self, value):
        """Check if value consists only of valid names."""
        super(DatabaseListField, self).validate(value)
        for db_name in value:
            self.validate_mssql_identifier(db_name)


def make_select_cls(fqns):
    if not isinstance(fqns, (tuple, list)):
        fqns = (fqns,)

    class Widget(hz_forms.fields.DynamicSelectWidget):
        def __init__(self, attrs=None, **kwargs):
            if attrs is None:
                attrs = {'class': 'murano_add_select'}
            else:
                attrs.setdefault('class', '')
                attrs['class'] += ' murano_add_select'
            super(Widget, self).__init__(attrs=attrs, **kwargs)

        class Media(object):
            js = ('muranodashboard/js/add-select.js',)

    class DynamicSelect(hz_forms.DynamicChoiceField, CustomPropertiesField):
        widget = Widget

        def __init__(self, empty_value_message=None, *args, **kwargs):
            super(DynamicSelect, self).__init__(*args, **kwargs)
            if empty_value_message is not None:
                self.empty_value_message = empty_value_message
            else:
                self.empty_value_message = _('Select Application')

        @with_request
        def update(self, request, environment_id, **kwargs):
            def _make_link():
                ns_url = 'horizon:murano:catalog:add'

                def _reverse(_fqn):
                    _app = pkg_api.app_by_fqn(request, _fqn)
                    if _app is None:
                        msg = "Application with FQN='{0}' doesn't exist"
                        messages.error(request, msg.format(_fqn))
                        raise Http404(msg.format(_fqn))
                    args = (_app.id, environment_id, False, True)
                    return _app.name, reverse(ns_url, args=args)
                return json.dumps([_reverse(cls) for cls in fqns])

            self.widget.add_item_link = _make_link
            apps = env_api.service_list_by_fqns(request, environment_id, fqns)
            choices = [('', self.empty_value_message)]
            choices.extend([(app['?']['id'],
                             html.escape(app.name)) for app in apps])
            self.choices = choices
            # NOTE(tsufiev): streamline the drop-down UX: auto-select the
            # single available option in a drop-down
            if len(choices) == 2:
                self.initial = choices[1][0]

        def clean(self, value):
            value = super(DynamicSelect, self).clean(value)
            return None if value == '' else value

    return DynamicSelect


@versionutils.deprecated(
    as_of=versionutils.deprecated.JUNO,
    in_favor_of='type io.murano.windows.ActiveDirectory with a custom '
                'emptyValueMessage attribute',
    remove_in=1)
class DomainChoiceField(make_select_cls('io.murano.windows.ActiveDirectory')):
    def __init__(self, *args, **kwargs):
        super(DomainChoiceField, self).__init__(*args, **kwargs)
        self.choices = [('', _('Not in domain'))]
