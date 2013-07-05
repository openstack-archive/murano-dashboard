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
from django.utils.translation import ugettext_lazy as _
from muranodashboard.panel.services import iterate_over_service_forms, \
    get_service_choices

log = logging.getLogger(__name__)

# has to be returned to all forms
# def validate_hostname_template(template, instance_count):
#     if template and instance_count > 1:
#         if not '#' in template:
#             raise forms.ValidationError(
#                 _('Incrementation symbol "#" is '
#                   'required in the Hostname template'))
#
#


class WizardFormServiceType(forms.Form):
    service = forms.ChoiceField(label=_('Service Type'),
                                choices=get_service_choices())


FORMS = [('service_choice', WizardFormServiceType)]
FORMS.extend(iterate_over_service_forms())
