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

import logging

import re
import ast
from netaddr import all_matching_cidrs
from django import forms
from django.core.validators import RegexValidator, validate_ipv4_address
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import smart_text
from openstack_dashboard.api import glance
from horizon import exceptions, messages
from openstack_dashboard.api.nova import novaclient
from muranodashboard.panel import api
from consts import *

log = logging.getLogger(__name__)
CONFIRM_ERR_DICT = {'required': _('Please confirm your password')}


def perform_password_check(password1, password2, type):
    if password1 != password2:
        raise forms.ValidationError(
            _(' %s passwords don\'t match' % type))


def validate_domain_name(name_to_check):
    subdomain_list = name_to_check.split('.')
    if len(subdomain_list) == 1:
        raise forms.ValidationError(
            _('Single-level domain is not appropriate. '))
    domain_name_re = re.compile(r'^[a-zA-Z0-9][a-zA-Z0-9-]*[a-zA-Z0-9]$')
    for subdomain in subdomain_list:
        if not domain_name_re.match(subdomain):
            raise forms.ValidationError(
                _('Only letters, numbers and dashes in the middle are allowed.'
                  ' Period characters are allowed only when they are used to '
                  'delimit the components of domain style names.'))


def validate_cluster_ip(request, ip_ranges):

    def perform_checking(ip):
        validate_ipv4_address(ip)
        try:
            ip_info = novaclient(request).fixed_ips.get(ip)
        except:
            exceptions.handle(request, _("Unable to retrieve information "
                                         "about fixed IP or IP is not valid."))
        else:
            if ip_info.hostname:
                raise forms.ValidationError(_('Specified Cluster Static IP '
                                              'is already in use'))

        if not all_matching_cidrs(ip, ip_ranges):
            raise forms.ValidationError(_('Specified Cluster Static IP is'
                                          'not in valid IP range'))
    return perform_checking


class PasswordField(forms.CharField):
    special_characters = '!@#$%^&*()_+|\/.,~?><:{}'
    password_re = re.compile('^.*(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[%s]).*$'
                             % special_characters)
    validate_password = RegexValidator(
        password_re, _('The password must contain at least one letter, one   \
                               number and one special character'), 'invalid')

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

        required = kwargs.get('required')
        if required is None:
            required = True

        super(PasswordField, self).__init__(
            min_length=7,
            max_length=255,
            validators=[self.validate_password],
            label=label,
            required=required,
            error_messages=error_messages,
            help_text=help_text,
            widget=forms.PasswordInput(render_value=True))


class WizardFormServiceType(forms.Form):
    ad_service = (AD_NAME, 'Active Directory')
    iis_service = (IIS_NAME, 'Internet Information Services')
    asp_service = (ASP_NAME, 'ASP.NET Application')
    iis_farm_service = (IIS_FARM_NAME,
                        'Internet Information Services Web Farm')
    asp_farm_service = (ASP_FARM_NAME, 'ASP.NET Application Web Farm')
    ms_sql_service = (MSSQL_NAME, 'MS SQL Server')
    ms_sql_cluster = (MSSQL_CLUSTER_NAME, 'MS SQL Cluster Server')
    service = forms.ChoiceField(label=_('Service Type'),
                                choices=[
                                    ad_service,
                                    iis_service,
                                    asp_service,
                                    iis_farm_service,
                                    asp_farm_service,
                                    ms_sql_service,
                                    ms_sql_cluster
                                ])


class CommonPropertiesExtension(object):

    hostname_re = re.compile(
        r'^(([a-zA-Z0-9#][a-zA-Z0-9-#]*[a-zA-Z0-9#])\.)'
        r'*([A-Za-z0-9#]|[A-Za-z0-9#][A-Za-z0-9-#]*[A-Za-z0-9#])$')
    validate_hostname = RegexValidator(hostname_re, _('text'))

    def __init__(self):
        self.fields.insert(
            len(self.fields), 'unit_name_template',
            forms.CharField(
                label=_('Hostname template'),
                required=False,
                validators=[self.validate_hostname],
                help_text='Optional field for a machine hostname template.'))

        for field, instance in self.fields.iteritems():
            if not instance.required:
                instance.widget.attrs['placeholder'] = 'Optional'
            if field in ['adm_password1', 'password_field1']:
                instance.widget.attrs['class'] = 'password'
            if field in ['adm_password2', 'password_field2']:
                instance.widget.attrs['class'] = 'confirm_password'


class WizardFormADConfiguration(forms.Form,
                                CommonPropertiesExtension):

    dc_name = forms.CharField(
        label=_('Domain Name'),
        min_length=2,
        max_length=64,
        validators=[validate_domain_name],
        help_text=_('Just letters, numbers and dashes are allowed.          \
        Single-level domain is not appropriate.'))

    dc_count = forms.IntegerField(
        label=_('Instance Count'),
        min_value=1,
        max_value=100,
        initial=1,
        help_text=_('Enter an integer value between 1 and 100'))

    adm_password1 = PasswordField(_('Administrator password'),)

    adm_password2 = PasswordField(
        _('Confirm password'),
        help_text=_('Retype your password'),
        error_messages=CONFIRM_ERR_DICT)

    password_field1 = PasswordField(_('Recovery password'))

    password_field2 = PasswordField(
        _('Confirm password'),
        error_messages=CONFIRM_ERR_DICT,
        help_text=_('Retype your password'))

    def clean(self):
        admin_password1 = self.cleaned_data.get('adm_password1')
        admin_password2 = self.cleaned_data.get('adm_password2')
        perform_password_check(admin_password1,
                               admin_password2,
                               'Administrator')
        recovery_password1 = self.cleaned_data.get('password_field1')
        recovery_password2 = self.cleaned_data.get('password_field2')
        perform_password_check(recovery_password1,
                               recovery_password2,
                               'Recovery')
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(WizardFormADConfiguration, self).__init__(*args, **kwargs)
        CommonPropertiesExtension.__init__(self)


class WizardFormIISConfiguration(forms.Form,
                                 CommonPropertiesExtension):
    name_re = re.compile(r'^[-\w]+$')
    validate_name = RegexValidator(name_re,
                                   _(u'Just letters, numbers, underscores     \
                                   and hyphens are allowed.'), 'invalid')

    service_name = forms.CharField(
        label=_('Service Name'),
        min_length=2,
        max_length=64,
        validators=[validate_name],
        error_messages={'invalid': validate_name.message},
        help_text=_('Just letters, numbers, underscores     \
                                   and hyphens are allowed'))

    adm_password1 = PasswordField(
        _('Administrator password'),
        help_text=_('Enter a complex password with at least one letter, one   \
                                       number and one special character'))
    adm_password2 = PasswordField(
        _('Confirm password'),
        error_messages=CONFIRM_ERR_DICT,
        help_text=_('Retype your password'))

    domain = forms.ChoiceField(
        label=_('Active Directory Domain'),
        required=False,
        help_text=_('Optional field for a domain to which service can be    \
                    joined '))

    def clean(self):
        admin_password1 = self.cleaned_data.get('adm_password1')
        admin_password2 = self.cleaned_data.get('adm_password2')
        perform_password_check(admin_password1,
                               admin_password2,
                               'Administrator')
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(WizardFormIISConfiguration, self).__init__(*args, **kwargs)
        request = self.initial.get('request')
        if not request:
            raise forms.ValidationError('Can\'t get a request information')
        link = request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search('murano/(\w+)', link).group(0)[7:]
        domains = api.service_list_by_type(request, environment_id, AD_NAME)

        self.fields['domain'].choices = \
            [("", "Not in domain")] + [(domain.name, domain.name)
                                       for domain in domains]
        CommonPropertiesExtension.__init__(self)


class WebFarmExtension(forms.Form):
    instance_count = forms.IntegerField(
        label=_('Instance Count'),
        min_value=1,
        max_value=100,
        initial=2,
        help_text=_('Enter an integer value between 1 and 100'))

    lb_port = forms.IntegerField(
        label=_('Load Balancer port'),
        min_value=1,
        max_value=65536,
        initial=80,
        help_text=_('Enter an integer value from 1 to 65536'))


class WizardFormAspNetAppConfiguration(WizardFormIISConfiguration,
                                       CommonPropertiesExtension):
    git_repo_re = re.compile(r'(\w+://)(.+@)*([\w\d\.]+)(:[\d]+)?/*(.*)',
                             re.IGNORECASE)
    validate_git = RegexValidator(
        git_repo_re, _('Enter correct git repository url'), 'invalid')

    repository = forms.CharField(
        label=_('Git repository'),
        validators=[validate_git],
        error_messages={'invalid': validate_git.message},
        help_text='Enter a valid git repository URL')


class WizardFormIISFarmConfiguration(WizardFormIISConfiguration,
                                     WebFarmExtension,
                                     CommonPropertiesExtension):
    def __init__(self, *args, **kwargs):
        super(WizardFormIISFarmConfiguration, self).__init__(
            *args, **kwargs)
        CommonPropertiesExtension.__init__(self)


class WizardFormAspNetFarmConfiguration(WizardFormAspNetAppConfiguration,
                                        WebFarmExtension,
                                        CommonPropertiesExtension):
    def __init__(self, *args, **kwargs):
        super(WizardFormAspNetFarmConfiguration, self).__init__(
            *args, **kwargs)
        CommonPropertiesExtension.__init__(self)


class WizardFormMSSQLConfiguration(WizardFormIISConfiguration,
                                   CommonPropertiesExtension):
    mixed_mode = forms.BooleanField(
        label=_('Mixed-mode Authentication '),
        initial=True,
        required=False)
    mixed_mode.widget.attrs['class'] = 'checkbox mixed-mode'
    password_field1 = PasswordField(
        _('SA password'),
        help_text=_('SQL server System Administrator account'))

    password_field2 = PasswordField(
        _('Confirm password'),
        error_messages=CONFIRM_ERR_DICT,
        help_text=_('Retype your password'))

    def clean(self):
        mixed_mode = self.cleaned_data.get('mixed_mode')
        if not mixed_mode:
            for i in xrange(1, 3, 1):
                self.fields['password_field' + str(i)].required = False
                if self.errors.get('password_field' + str(i)):
                    del self.errors['password_field' + str(i)]

        admin_password1 = self.cleaned_data.get('adm_password1')
        admin_password2 = self.cleaned_data.get('adm_password2')
        perform_password_check(admin_password1,
                               admin_password2,
                               'Administrator')
        sa_password1 = self.cleaned_data.get('password_field1')
        sa_password2 = self.cleaned_data.get('password_field2')
        perform_password_check(sa_password1,
                               sa_password2,
                               'Recovery')
        return self.cleaned_data

    def __init__(self, *args, **kwargs):
        super(WizardFormMSSQLConfiguration, self).__init__(*args, **kwargs)
        CommonPropertiesExtension.__init__(self)


class WizardFormMSSQLClusterConfiguration(WizardFormMSSQLConfiguration):
    def __init__(self, *args, **kwargs):
        super(WizardFormMSSQLClusterConfiguration, self).__init__(*args,
                                                                  **kwargs)
        request = self.initial.get('request')
        CommonPropertiesExtension.__init__(self)
        self.fields.insert(3, 'external_ad', forms.BooleanField(
            label=_('Active Directory is configured '
                    'by the System Administrator'),
            required=False))
        self.fields['external_ad'].widget.attrs['class'] = \
            'checkbox external-ad'
        try:
            network_list = novaclient(request).networks.list()
        except:
            network_list = []
            exceptions.handle(request,
                              _("Unable to retrieve list of networks."))
        ip_ranges = [network.cidr for network in network_list]
        ranges = ''
        for cidr in ip_ranges:
            ranges += cidr
            if cidr != ip_ranges[-1]:
                ranges += ', '

        self.fields.insert(5, 'fixed_ip', forms.CharField(
            label=_('Cluster Static IP'),
            required=True,
            validators=[validate_cluster_ip(request, ip_ranges)],
            help_text=_('Select IP from available range: ' + ranges),
            error_messages={'invalid': validate_ipv4_address.message}))

    instance_count = forms.IntegerField(
        label=_('Instance Count'),
        min_value=1,
        max_value=100,
        initial=1,
        help_text=_('Enter an integer value between 1 and 100'))

    def clean(self):
        super(WizardFormMSSQLClusterConfiguration, self).clean()
        if not self.cleaned_data.get('external_ad'):
            if not self.cleaned_data.get('domain'):
                raise forms.ValidationError(
                    _('Domain for MS SQL Cluster is required. '
                      'Configure Active Directory service first.'))
        return self.cleaned_data


class WizardInstanceConfiguration(forms.Form):
    flavor = forms.ChoiceField(label=_('Instance flavor'))

    image = forms.ChoiceField(label=_('Instance image'),
                              required=False)

    availability_zone = forms.ChoiceField(label=_('Availability zone'),
                                          required=False)

    def __init__(self, *args, **kwargs):
        super(WizardInstanceConfiguration, self).__init__(
            *args, **kwargs)
        request = self.initial.get('request')
        if not request:
            raise forms.ValidationError(
                'Can\'t get a request information')
        flavors = novaclient(request).flavors.list()
        flavor_choices = [(flavor.name, flavor.name) for flavor in flavors]

        self.fields['flavor'].choices = flavor_choices
        for flavor in flavor_choices:
            if 'medium' in flavor[1]:
                self.fields['flavor'].initial = flavor[0]
                break
        try:
            images, _more = glance.image_list_detailed(request)
        except:
            images = []
            exceptions.handle(request,
                              _("Unable to retrieve public images."))

        image_mapping = {}
        image_choices = []
        for image in images:
            murano_property = image.properties.get('murano_image_info')
            if murano_property:
                #convert to dict because
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

        self.fields['image'].choices = image_choices

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

        self.fields['availability_zone'].choices = az_choices


FORMS = [('service_choice', WizardFormServiceType),
         (AD_NAME, WizardFormADConfiguration),
         (IIS_NAME, WizardFormIISConfiguration),
         (ASP_NAME, WizardFormAspNetAppConfiguration),
         (IIS_FARM_NAME, WizardFormIISFarmConfiguration),
         (ASP_FARM_NAME, WizardFormAspNetFarmConfiguration),
         (MSSQL_NAME, WizardFormMSSQLConfiguration),
         (MSSQL_CLUSTER_NAME, WizardFormMSSQLClusterConfiguration),
         ('instance_configuration', WizardInstanceConfiguration)]
