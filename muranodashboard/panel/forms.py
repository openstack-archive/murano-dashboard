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
import string

from django import forms
from django.utils.translation import ugettext_lazy as _
import re
from muranodashboard.panel import api

log = logging.getLogger(__name__)


class PasswordField(forms.CharField):
    # Setup the Field
    def __init__(self, label, *args, **kwargs):
        super(PasswordField, self).__init__(min_length=7, required=True,
                                            label=label,
                                            widget=forms.PasswordInput(
                                                render_value=False),
                                            *args, **kwargs)

    def clean(self, value):

        # Setup Our Lists of Characters and Numbers
        characters = list(string.letters)
        special_characters = '!@#$%^&*()_+|\/.,~?><:{}'
        numbers = [str(i) for i in range(10)]

        # Assume False until Proven Otherwise
        numCheck = False
        charCheck = False
        specCharCheck = False

        # Loop until we Match
        for char in value:
            if not charCheck:
                if char in characters:
                    charCheck = True
            if not specCharCheck:
                if char in special_characters:
                    specCharCheck = True
            if not numCheck:
                if char in numbers:
                    numCheck = True
            if numCheck and charCheck and specCharCheck:
                break

        if not numCheck or not charCheck or not specCharCheck:
            raise forms.ValidationError(u'Your password must include at least \
                                          one letter, at least one number and \
                                          at least one special character.')

        return super(PasswordField, self).clean(value)


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


class WizardFormADConfiguration(forms.Form, CommonPropertiesExtension):
    dc_name = forms.CharField(label=_('Domain Name'),
                              required=True)

    dc_count = forms.IntegerField(label=_('Instance Count'),
                                  required=True,
                                  min_value=1,
                                  max_value=100,
                                  initial=1)

    adm_password = PasswordField(_('Administrator password'))

    recovery_password = PasswordField(_('Recovery password'))

    def __init__(self, request, *args, **kwargs):
        super(WizardFormADConfiguration, self).__init__(*args, **kwargs)
        CommonPropertiesExtension.__init__(self)


class WizardFormIISConfiguration(forms.Form, CommonPropertiesExtension):
    iis_name = forms.CharField(label=_('Service Name'),
                               required=True)

    adm_password = PasswordField(_('Administrator password'))

    iis_domain = forms.ChoiceField(label=_('Member of the Domain'),
                                   required=False)

    def __init__(self, request, *args, **kwargs):
        super(WizardFormIISConfiguration, self).__init__(*args, **kwargs)

        link = request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search('murano/(\w+)', link).group(0)[7:]

        ad = 'Active Directory'
        domains = api.service_list_by_type(request, environment_id, ad)

        self.fields['iis_domain'].choices = [("", "")] + \
                                            [(domain.name, domain.name)
                                             for domain in domains]
        CommonPropertiesExtension.__init__(self)


class WebFarmExtension(forms.Form):
    instance_count = forms.IntegerField(label=_('Instance Count'),
                                        required=True,
                                        min_value=1,
                                        max_value=10000,
                                        initial=1)
    lb_port = forms.IntegerField(label=_('Load Balancer port'),
                                 required=True,
                                 min_value=1,
                                 max_value=65536,
                                 initial=80)


class WizardFormAspNetAppConfiguration(WizardFormIISConfiguration,
                                       WebFarmExtension,
                                       CommonPropertiesExtension):
    repository = forms.CharField(label=_('Git repository'),
                                 required=True)


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
