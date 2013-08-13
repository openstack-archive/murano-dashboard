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
import ast
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


def with_request(func):
    def update(self, initial):
        request = initial.get('request')
        if request:
            func(self, request, initial)
        else:
            raise forms.ValidationError("Can't get a request information")
    return update


class PasswordField(forms.CharField):
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
        if self.is_original():  # run compare only for original fields
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

    def is_original(self):
        return hasattr(self, 'original') and self.original

    def clone_field(self):
        self.has_clone = True
        field = copy.deepcopy(self)
        self.original = True
        field.label = _('Confirm password')
        field.error_messages = {
            'required': _('Please confirm your password')
        }
        field.help_text = _('Retype your password')
        return field


class InstanceCountField(forms.IntegerField):
    def clean(self, value):
        self.value = super(InstanceCountField, self).clean(value)
        return self.value

    def postclean(self, form, data):
        value = []
        for dc in range(self.value):
            templates = form.get_unit_templates(data)
            if dc < len(templates) - 1:
                value.append(templates[dc])
            else:
                value.append(templates[-1])
        return value


class DataGridField(forms.MultiValueField):
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = DataGridCompound
        super(DataGridField, self).__init__(
            (forms.CharField(required=False), forms.CharField()),
            *args, **kwargs)

    def compress(self, data_list):
        return data_list[1]

    @with_request
    def update(self, request, initial):
        self.widget.update_request(request)
        nodes = []
        instance_count = initial.get('instance_count')
        if instance_count:
            for index in xrange(instance_count):
                nodes.append({'name': 'node' + str(index + 1),
                              'is_sync': index < 2,
                              'is_primary': index == 0})
            self.initial = json.dumps(nodes)


class DomainChoiceField(forms.ChoiceField):
    @with_request
    def update(self, request, initial):
        self.choices = [("", "Not in domain")]
        link = request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search(
            'murano/(\w+)', link).group(0)[7:]
        domains = api.service_list_by_type(request, environment_id,
                                           'activeDirectory')
        self.choices.extend(
            [(domain.name, domain.name) for domain in domains])


class FlavorChoiceField(forms.ChoiceField):
    @with_request
    def update(self, request, initial):
        self.choices = [(flavor.name, flavor.name) for flavor in
                        novaclient(request).flavors.list()]
        for flavor in self.choices:
            if 'medium' in flavor[1]:
                self.initial = flavor[0]
                break


class ImageChoiceField(forms.ChoiceField):
    @with_request
    def update(self, request, initial):
        try:
            # public filter removed
            images, _more = glance.image_list_detailed(request)
        except:
            images = []
            exceptions.handle(request,
                              _("Unable to retrieve public images."))

        image_mapping, image_choices = {}, []
        for image in images:
            murano_property = image.properties.get('murano_image_info')
            if murano_property:
                # convert to dict because
                # only string can be stored in image metadata property
                try:
                    murano_json = ast.literal_eval(murano_property)
                except ValueError:
                    messages.error(request,
                                   _("Invalid value in image metadata"))
                else:
                    title = murano_json.get('title')
                    image_id = murano_json.get('id')
                    if title and image_id:
                        image_mapping[smart_text(title)] = smart_text(image_id)

        for name in sorted(image_mapping.keys()):
            image_choices.append((image_mapping[name], name))
        if image_choices:
            image_choices.insert(0, ("", _("Select Image")))
        else:
            image_choices.insert(0, ("", _("No images available")))

        self.choices = image_choices


class AZoneChoiceField(forms.ChoiceField):
    @with_request
    def update(self, request, initial):
        try:
            availability_zones = novaclient(request).availability_zones.\
                list(detailed=False)
        except:
            availability_zones = []
            exceptions.handle(request,
                              _("Unable to retrieve  availability zones."))

        az_choices = [(az.zoneName, az.zoneName)
                      for az in availability_zones if az.zoneState]
        if az_choices:
            az_choices.insert(0, ("", _("Select Availability Zone")))
        else:
            az_choices.insert(0, ("", _("No availability zones available")))

        self.choices = az_choices


class BooleanField(forms.BooleanField):
    def __init__(self, *args, **kwargs):
        kwargs['widget'] = forms.CheckboxInput(attrs={'class': 'checkbox'})
        super(BooleanField, self).__init__(*args, **kwargs)


class ClusterIPField(forms.CharField):
    @staticmethod
    def validate_cluster_ip(request, ip_ranges):
        def perform_checking(ip):
            validate_ipv4_address(ip)
            if not all_matching_cidrs(ip, ip_ranges) and ip_ranges:
                raise forms.ValidationError(_('Specified Cluster Static IP is'
                                              'not in valid IP range'))
            try:
                ip_info = novaclient(request).fixed_ips.get(ip)
            except exceptions.UNAUTHORIZED:
                exceptions.handle(
                    request, _("Unable to retrieve information "
                               "about fixed IP or IP is not valid."),
                    ignore=True)
            else:
                if ip_info.hostname:
                    raise forms.ValidationError(
                        _('Specified Cluster Static IP is already in use'))
        return perform_checking

    @with_request
    def update(self, request, initial):
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
        self.error_messages = {'invalid': validate_ipv4_address.message}

    def postclean(self, form, data):
        # hack to compare two IPs
        ips = []
        for key, field in form.fields.items():
            if isinstance(field, ClusterIPField):
                ips.append(data[key])
        if ips[0] == ips[1]:
            raise forms.ValidationError(_(
                'Listener IP and Cluster Static IP should be different'))


class DatabaseListField(forms.CharField):
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
