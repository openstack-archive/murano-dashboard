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
from horizon.forms import SelfHandlingForm
from horizon import messages, exceptions
from openstack_dashboard.api import glance
import json

from muranodashboard.panel.services import iterate_over_service_forms
from muranodashboard.panel.services import get_service_choices

log = logging.getLogger(__name__)


class WizardFormServiceType(forms.Form):
    service = forms.ChoiceField(label=_('Service Type'),
                                choices=get_service_choices())


FORMS = [('service_choice', WizardFormServiceType)]
FORMS.extend(iterate_over_service_forms())


class MarkImageForm(SelfHandlingForm):
    _metadata = {
        'windows.2012': ' Windows Server 2012',
        'linux': 'Generic Linux',
        'cirros.demo': 'Murano Demo'
    }

    image = forms.ChoiceField(label='Image')
    title = forms.CharField(max_length="255", label=_("Title"))
    type = forms.ChoiceField(label="Type", choices=_metadata.items())

    def __init__(self, request, *args, **kwargs):
        super(MarkImageForm, self).__init__(request, *args, **kwargs)

        images = []
        try:
            images, _more = glance.image_list_detailed(request)
        except Exception:
            log.error('Failed to request image list from Glance')
            exceptions.handle(request, _('Unable to retrieve list of images'))

        self.fields['image'].choices = [(i.id, i.name) for i in images]

    def handle(self, request, data):
        log.debug('Marking image with specified metadata: {0}'.format(data))

        image_id = data['image']
        properties = {
            'murano_image_info': json.dumps({
                'title': data['title'],
                'type': data['type']
            })
        }

        try:
            img = glance.image_update(request, image_id, properties=properties)
            messages.success(request, _('Image successfully marked'))
            return img
        except Exception:
            exceptions.handle(request, _('Unable to mark image'))
