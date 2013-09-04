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

import re
import json
from django import forms
from django.core.validators import RegexValidator, validate_ipv4_address
from netaddr import all_matching_cidrs
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_text
from muranodashboard.panel import api
from horizon import exceptions, messages
from openstack_dashboard.api import glance
from openstack_dashboard.api.nova import novaclient
from muranodashboard.datagrids import DataGridCompound
from django.template.defaultfilters import pluralize
import copy
import types
import logging

log = logging.getLogger(__name__)


def with_request(func):
    def update(self, initial, **kwargs):
        request = initial.get('request')
        if request:
            func(self, request, **kwargs)
        else:
            raise forms.ValidationError("Can't get a request information")
    return update


class CustomPropertiesField(object):
    @classmethod
    def push_properties(cls, kwargs):
        props = {}
        for key, value in kwargs.iteritems():
            if isinstance(value, property):
                props[key] = value
        for key in props.keys():
            del kwargs[key]
        if props:
            return type('cls_with_props', (cls,), props)
        else:
            return cls


class CharField(forms.CharField, CustomPropertiesField):
    pass


class PasswordField(CharField):
    special_characters = '!@#$%^&*()_+|\/.,~?><:{}'
    password_re = re.compile('^.*(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[%s]).*$'
                             % special_characters)
    has_clone = False
    validate_password = RegexValidator(
        password_re, _('The password must contain at least one letter, one   \
                               number and one special character'), 'invalid')

    @staticmethod
    def get_clone_name(name):
        return name + '-clone'

    def compare(self, name, form_data):
        if self.is_original() and self.required:
            # run compare only for original fields
            # do not run compare for hidden fields (they are not required)
            if form_data.get(name) != form_data.get(self.get_clone_name(name)):
                raise forms.ValidationError(_(u"{0}{1} don't match".format(
                    self.label, pluralize(2))))

    class PasswordInput(forms.PasswordInput):
        class Media:
            js = ('muranodashboard/js/passwordfield.js',)

    def __init__(self, label, *args, **kwargs):
        help_text = kwargs.get('help_text')
        if not help_text:
            help_text = _('Enter a complex password with at least one letter, \
                one number and one special character')

        error_messages = {
            'invalid': self.validate_password.message}
        err_msg = kwargs.get('error_messages')
        if err_msg:
            if err_msg.get('required'):
                error_messages['required'] = err_msg.get('required')

        super(PasswordField, self).__init__(
            min_length=7,
            max_length=255,
            validators=[self.validate_password],
            label=label,
            error_messages=error_messages,
            help_text=help_text,
            widget=self.PasswordInput(render_value=True))

    def __deepcopy__(self, memo):
        result = super(PasswordField, self).__deepcopy__(memo)
        result.error_messages = copy.deepcopy(self.error_messages)
        return result

    def is_original(self):
        return hasattr(self, 'original') and self.original

    def clone_field(self):
        self.has_clone = True
        field = copy.deepcopy(self)
        self.original = True
        field.label = _('Confirm password')
        field.error_messages['required'] = _('Please confirm your password')
        field.help_text = _('Retype your password')
        return field


class IntegerField(forms.IntegerField, CustomPropertiesField):
    pass


class InstanceCountField(IntegerField):
    def clean(self, value):
        self.value = super(InstanceCountField, self).clean(value)
        return self.value

    def postclean(self, form, data):
        value = []
        if hasattr(self, 'value'):
            templates = form.get_unit_templates(data)
            for dc in range(self.value):
                if dc < len(templates) - 1:
                    template = templates[dc]
                else:
                    template = templates[-1]
                value.append(self.interpolate_number(template, dc + 1))
            return value

    @staticmethod
    def interpolate_number(spec, number):
        """Replaces all '#' occurrences with given number."""
        def interpolate(spec):
            if isinstance(spec, types.DictType):
                return dict((k, interpolate(v)) for (k, v) in spec.iteritems())
            elif isinstance(spec, basestring) and '#' in spec:
                return spec.replace('#', '{0}').format(number)
            else:
                return spec
        return interpolate(spec)


class DataGridField(forms.MultiValueField, CustomPropertiesField):
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = DataGridCompound
        super(DataGridField, self).__init__(
            (forms.CharField(required=False), forms.CharField()),
            *args, **kwargs)

    def compress(self, data_list):
        return data_list[1]

    @with_request
    def update(self, request, **kwargs):
        self.widget.update_request(request)
        # hack to use json string instead of python dict get by YAQL
        data = kwargs['form'].service.cleaned_data
        if 'clusterConfiguration' in data:
            conf = data['clusterConfiguration']
            conf['dcInstances'] = json.dumps(conf['dcInstances'])


class ChoiceField(forms.ChoiceField, CustomPropertiesField):
    pass


class DomainChoiceField(ChoiceField):
    @with_request
    def update(self, request, **kwargs):
        self.choices = [("", "Not in domain")]
        link = request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search(
            'murano/(\w+)', link).group(0)[7:]
        domains = api.service_list_by_type(request, environment_id,
                                           'activeDirectory')
        self.choices.extend(
            [(domain.name, domain.name) for domain in domains])


class FlavorChoiceField(ChoiceField):
    @with_request
    def update(self, request, **kwargs):
        self.choices = [(flavor.name, flavor.name) for flavor in
                        novaclient(request).flavors.list()]
        for flavor in self.choices:
            if 'medium' in flavor[1]:
                self.initial = flavor[0]
                break


class ImageChoiceField(ChoiceField):
    @with_request
    def update(self, request, **kwargs):
        try:
            # public filter removed
            images, _more = glance.image_list_detailed(request)
        except:
            images = []
            exceptions.handle(request, _("Unable to retrieve public images."))

        image_mapping, image_choices = {}, []
        for image in images:
            murano_property = image.properties.get('murano_image_info')
            if murano_property:
                try:
                    murano_json = json.loads(murano_property)
                except ValueError:
                    messages.error(request, _("Invalid murano image metadata"))
                else:
                    title = murano_json.get('title', image.name)
                    murano_json['name'] = image.name
                    image_mapping[smart_text(title)] = json.dumps(murano_json)

        for name in sorted(image_mapping.keys()):
            image_choices.append((image_mapping[name], name))
        if image_choices:
            image_choices.insert(0, ("", _("Select Image")))
        else:
            image_choices.insert(0, ("", _("No images available")))

        self.choices = image_choices

    def clean(self, value):
        value = super(ImageChoiceField, self).clean(value)
        return json.loads(value) if value else value


class AZoneChoiceField(ChoiceField):
    @with_request
    def update(self, request, **kwargs):
        try:
            availability_zones = novaclient(request).availability_zones.\
                list(detailed=False)
        except:
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
        kwargs['widget'] = forms.CheckboxInput(attrs={'class': 'checkbox'})
        super(BooleanField, self).__init__(*args, **kwargs)


class ClusterIPField(CharField):
    @staticmethod
    def validate_cluster_ip(request, ip_ranges):
        def perform_checking(ip):
            validate_ipv4_address(ip)
            if not all_matching_cidrs(ip, ip_ranges) and ip_ranges:
                raise forms.ValidationError(_('Specified Cluster Static IP is'
                                              ' not in valid IP range'))
            try:
                ip_info = novaclient(request).fixed_ips.get(ip)
            except exceptions.UNAUTHORIZED:
                exceptions.handle(
                    request, _("Unable to retrieve information "
                               "about fixed IP or IP is not valid."),
                    ignore=True)
            except exceptions.NOT_FOUND:
                exceptions.handle(
                    request, _("Could not found fixed ips for ip %s" % (ip,)),
                    ignore=True)
            else:
                if ip_info.hostname:
                    raise forms.ValidationError(
                        _('Specified Cluster Static IP is already in use'))
        return perform_checking

    @with_request
    def update(self, request, **kwargs):
        try:
            network_list = novaclient(request).networks.list()
            ip_ranges = [network.cidr for network in network_list]
            ranges = ', '.join(ip_ranges)
        except StandardError:
            ip_ranges, ranges = [], ''
        if ip_ranges:
            self.help_text = _('Select IP from available range: ' + ranges)
        else:
            self.help_text = _('Specify valid fixed IP')
        self.validators = [self.validate_cluster_ip(request, ip_ranges)]
        self.error_messages['invalid'] = validate_ipv4_address.message


class DatabaseListField(CharField):
    validate_mssql_identifier = RegexValidator(
        re.compile(r'^[a-zA-z_][a-zA-Z0-9_$#@]*$'),
        _((u'First symbol should be latin letter or underscore. Subsequent ' +
           u'symbols can be latin letter, numeric, underscore, at sign, ' +
           u'number sign or dollar sign')))

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
