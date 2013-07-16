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
from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from openstack_dashboard.api import glance, nova as novaapi
from muranodashboard.panel import api
from consts import *

log = logging.getLogger(__name__)
CONFIRM_ERR_DICT = {'required': _('Please confirm your password')}


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

        super(PasswordField, self).__init__(
            min_length=7,
            max_length=255,
            validators=[self.validate_password],
            label=label,
            error_messages=error_messages,
            help_text=help_text,
            widget=forms.PasswordInput(render_value=False))


class WizardFormServiceType(forms.Form):
    ad_service = (AD_NAME, 'Active Directory')
    iis_service = (IIS_NAME, 'Internet Information Services')
    asp_service = (ASP_NAME, 'ASP.NET Application')
    iis_farm_service = (IIS_FARM_NAME,
                        'Internet Information Services Web Farm')
    asp_farm_service = (ASP_FARM_NAME, 'ASP.NET Application Web Farm')
    service = forms.ChoiceField(label=_('Service Type'),
                                choices=[
                                    ad_service,
                                    iis_service,
                                    asp_service,
                                    iis_farm_service,
                                    asp_farm_service
                                ])


class ServiceConfigurationForm(forms.Form):
    def clean(self):
        def compare(pwd1, pwd2, admin=True):
            if pwd1 != pwd2:
                pwd_type = 'Administrator'
                if not admin:
                    pwd_type = 'Recovery'
                raise forms.ValidationError(
                    _(' %s passwords don\'t match' % pwd_type))

        form_data = self.cleaned_data
        admin_pwd1 = form_data.get('adm_password')
        admin_pwd2 = form_data.get('adm_password2')
        compare(admin_pwd1, admin_pwd2)

        recovery_pwd1 = form_data.get('recovery_password')
        if recovery_pwd1:
            recovery_pwd2 = form_data.get('recovery_password2')
            compare(recovery_pwd1, recovery_pwd2, admin=False)
        return self.cleaned_data


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
            if field in ['adm_password', 'recovery_password']:
                instance.widget.attrs['class'] = 'password'
            if field in ['adm_password2', 'recovery_password2']:
                instance.widget.attrs['class'] = 'confirm_password'


class WizardFormADConfiguration(ServiceConfigurationForm,
                                CommonPropertiesExtension):
    domain_name_re = re.compile(
        r'^[a-zA-Z0-9][a-zA-Z0-9.-]*[a-zA-Z0-9]$')
    validate_domain_name = RegexValidator(
        domain_name_re, _(u'Name should not contain anything but letters, \
                            numbers and dashes and should not start or end \
                            with a dash'), 'invalid')

    dc_name = forms.CharField(
        label=_('Domain Name'),
        min_length=2,
        max_length=64,
        validators=[validate_domain_name],
        error_messages={'invalid': validate_domain_name.message},
        help_text=_('Just letters, numbers and dashes are allowed.          \
        A dot can be used to create subdomains'))

    dc_count = forms.IntegerField(
        label=_('Instance Count'),
        min_value=1,
        max_value=100,
        initial=1,
        help_text=_('Enter an integer value between 1 and 100'))

    adm_password = PasswordField(_('Administrator password'),)

    adm_password2 = PasswordField(
        _('Confirm password'),
        help_text=_('Retype your password'),
        error_messages=CONFIRM_ERR_DICT)

    recovery_password = PasswordField(_('Recovery password'))

    recovery_password2 = PasswordField(
        _('Confirm password'),
        error_messages=CONFIRM_ERR_DICT,
        help_text=_('Retype your password'))

    def __init__(self, *args, **kwargs):
        super(WizardFormADConfiguration, self).__init__(*args, **kwargs)
        CommonPropertiesExtension.__init__(self)


class WizardFormIISConfiguration(ServiceConfigurationForm,
                                 CommonPropertiesExtension):
    name_re = re.compile(r'^[-\w]+$')
    validate_name = RegexValidator(name_re,
                                   _(u'Just letters, numbers, underscores     \
                                   and hyphens are allowed.'), 'invalid')

    iis_name = forms.CharField(
        label=_('Service Name'),
        min_length=2,
        max_length=64,
        validators=[validate_name],
        error_messages={'invalid': validate_name.message},
        help_text=_('Just letters, numbers, underscores     \
                                   and hyphens are allowed'))

    adm_password = PasswordField(
        _('Administrator password'),
        help_text=_('Enter a complex password with at least one letter, one   \
                                       number and one special character'))
    adm_password2 = PasswordField(
        _('Confirm password'),
        error_messages=CONFIRM_ERR_DICT,
        help_text=_('Retype your password'))

    iis_domain = forms.ChoiceField(
        label=_('Domain'),
        required=False,
        help_text=_('Optional field for a domain to which service can be    \
                    joined '))

    def __init__(self, *args, **kwargs):
        super(WizardFormIISConfiguration, self).__init__(*args, **kwargs)
        request = self.initial.get('request')
        if not request:
            raise forms.ValidationError('Can\'t get a request information')
        link = request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search('murano/(\w+)', link).group(0)[7:]
        domains = api.service_list_by_type(request, environment_id, AD_NAME)

        self.fields['iis_domain'].choices = [("", "Not in domain")] + \
                                            [(domain.name, domain.name)
                                             for domain in domains]
        CommonPropertiesExtension.__init__(self)


class WebFarmExtension(ServiceConfigurationForm):
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


class WizardInstanceConfiguration(forms.Form):
    flavor = forms.ChoiceField(label=_('Instance flavor'),
                               required=False)

    image = forms.ChoiceField(label=_('Instance image'),
                              required=False)

    # az = forms.CharField(label=_('Availability zone'), required=False)

    def __init__(self, *args, **kwargs):
        super(WizardInstanceConfiguration, self).__init__(
            *args, **kwargs)
        request = self.initial.get('request')
        if not request:
            raise forms.ValidationError(
                'Can\'t get a request information')
        flavors = novaapi.flavor_list(request)
        self.fields['flavor'].choices = [(flavor.id, "%s" % flavor.name)
                                         for flavor in flavors]
        try:
            # public filter removed
            public_images, _more = glance.image_list_detailed(request)
        except:
            public_images = []
            exceptions.handle(request,
                              _("Unable to retrieve public images."))

        choices = [(image.id, image.name)
                   for image in public_images
                   if image.properties.get("image_type", '') != "snapshot"]
        if choices:
            choices.insert(0, ("", _("Select Image")))
        else:
            choices.insert(0, ("", _("No images available.")))

        self.fields['image'].choices = choices


FORMS = [('service_choice', WizardFormServiceType),
         (AD_NAME, WizardFormADConfiguration),
         (IIS_NAME, WizardFormIISConfiguration),
         (ASP_NAME, WizardFormAspNetAppConfiguration),
         (IIS_FARM_NAME, WizardFormIISFarmConfiguration),
         (ASP_FARM_NAME, WizardFormAspNetFarmConfiguration),
         ('instance_configuration', WizardInstanceConfiguration)]
