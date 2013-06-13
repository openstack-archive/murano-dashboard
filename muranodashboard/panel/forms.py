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

from django import forms
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _
import re
from muranodashboard.panel import api

log = logging.getLogger(__name__)


class PasswordField(forms.CharField):
    special_characters = '!@#$%^&*()_+|\/.,~?><:{}'
    password_re = re.compile('^.*(?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[%s]).*$'
                             % special_characters)
    validate_password = RegexValidator(
        password_re, _('The password must contain at least one letter, one   \
                               number and one special character'), 'invalid')

    def __init__(self, label, *args, **kwargs):
        super(PasswordField, self).__init__(
            min_length=7,
            max_length=255,
            validators=[self.validate_password],
            label=label,
            error_messages={'invalid': self.validate_password.message},
            widget=forms.PasswordInput(render_value=False), *args, **kwargs)


class WizardFormServiceType(forms.Form):

    ad_service = ('Active Directory', 'Active Directory')
    iis_service = ('IIS', 'Internet Information Services')
    asp_service = ('ASP.NET Application', 'ASP.NET Application')
    iis_farm_service = ('IIS Farm', 'Internet Information Services Web Farm')
    asp_farm_service = ('ASP.NET Farm', 'ASP.NET Application Web Farm')
    service = forms.ChoiceField(label=_('Service Type'),
                                choices=[
                                    ad_service,
                                    iis_service,
                                    asp_service,
                                    iis_farm_service,
                                    asp_farm_service
                                ])


class WizardFormConfiguration(forms.Form):
    #The functions for this class will dynamically create in views.py
    pass


class CommonPropertiesExtension(object):
    def __init__(self):
        self.fields.insert(
            len(self.fields), 'unit_name_template',
            forms.CharField(label=_('Hostname template'), required=False))

        for field, instance in self.fields.iteritems():
            if not instance.required:
                instance.widget.attrs['placeholder'] = 'Optional'


class WizardFormADConfiguration(forms.Form, CommonPropertiesExtension):
    domain_name_re = re.compile(
        r'^[a-zA-Z0-9][a-zA-Z0-9.-]+[a-zA-Z0-9]$')
    validate_domain_name = RegexValidator(domain_name_re,
                                          _(u'Enter a valid domain name:    \
                                            just letters, numbers, dashes and \
                                            one dot are allowed'), 'invalid')

    dc_name = forms.CharField(
        label=_('Domain Name'),
        min_length=2,
        max_length=64,
        validators=[validate_domain_name],
        error_messages={'invalid': validate_domain_name.message})

    dc_count = forms.IntegerField(
        label=_('Instance Count'),
        min_value=1,
        max_value=100,
        initial=1)

    adm_password = PasswordField(_('Administrator password'))

    recovery_password = PasswordField(_('Recovery password'))

    def __init__(self, request, *args, **kwargs):
        super(WizardFormADConfiguration, self).__init__(*args, **kwargs)
        CommonPropertiesExtension.__init__(self)


class WizardFormIISConfiguration(forms.Form, CommonPropertiesExtension):
    name_re = re.compile(r'^[-\w]+$')
    validate_name = RegexValidator(name_re,
                                   _(u'Just letters, numbers, underscores     \
                                   or hyphens are allowed.'), 'invalid')

    iis_name = forms.CharField(
        label=_('Service Name'),
        min_length=2,
        max_length=64,
        validators=[validate_name],
        error_messages={'invalid': validate_name.message})

    adm_password = PasswordField(_('Administrator password'))

    iis_domain = forms.ChoiceField(
        label=_('Domain'),
        required=False)

    def __init__(self, request, *args, **kwargs):
        super(WizardFormIISConfiguration, self).__init__(*args, **kwargs)

        link = request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search('murano/(\w+)', link).group(0)[7:]

        ad = 'Active Directory'
        domains = api.service_list_by_type(request, environment_id, ad)

        self.fields['iis_domain'].choices = [("", "Not in domain")] + \
                                            [(domain.name, domain.name)
                                             for domain in domains]
        CommonPropertiesExtension.__init__(self)


class WebFarmExtension(forms.Form):
    instance_count = forms.IntegerField(
        label=_('Instance Count'),
        min_value=1,
        max_value=10000,
        initial=1)

    lb_port = forms.IntegerField(
        label=_('Load Balancer port'),
        min_value=1,
        max_value=65536,
        initial=80)


class WizardFormAspNetAppConfiguration(WizardFormIISConfiguration,
                                       CommonPropertiesExtension):
    git_repo_re = re.compile(r'(\w+://)(.+@)*([\w\d\.]+)(:[\d]+)?/*(.*)',
                             re.IGNORECASE)
    validate_git = RegexValidator(
        git_repo_re, _('Enter correct git repository url'), 'invalid')

    repository = forms.CharField(
        label=_('Git repository'),
        validators=[validate_git],
        error_messages={'invalid': validate_git.message})


class WizardFormIISFarmConfiguration(WizardFormIISConfiguration,
                                     WebFarmExtension,
                                     CommonPropertiesExtension):
    def __init__(self, request, *args, **kwargs):
        super(WizardFormIISFarmConfiguration, self).__init__(
            request, *args, **kwargs)
        CommonPropertiesExtension.__init__(self)


class WizardFormAspNetFarmConfiguration(WizardFormAspNetAppConfiguration,
                                        WebFarmExtension,
                                        CommonPropertiesExtension):
    def __init__(self, request, *args, **kwargs):
        super(WizardFormAspNetFarmConfiguration, self).__init__(
            request, *args, **kwargs)
        CommonPropertiesExtension.__init__(self)
