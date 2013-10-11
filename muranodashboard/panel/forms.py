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

from muranodashboard.panel.services import get_service_choices

log = logging.getLogger(__name__)


class WizardFormServiceType(forms.Form):
    service = forms.ChoiceField(label=_('Service Type'),
                                choices=get_service_choices())


class AddImageForm(SelfHandlingForm):
    title = forms.CharField(max_length="255",
                            label=_("Image Title"))

    image_choices = forms.ChoiceField(label='Images')

    windows_image = ('ws-2012-std', ' Windows Server 2012 Desktop')
    demo_image = ('murano_demo', 'Murano Demo Image')

    image_type = forms.ChoiceField(label="Murano Type",
                                   choices=[windows_image, demo_image])

    def __init__(self, request, *args, **kwargs):
        super(AddImageForm, self).__init__(request, *args, **kwargs)
        try:
            images, _more = glance.image_list_detailed(request)
        except Exception:
            log.error("Failed to request image list from glance ")
            images = []
            exceptions.handle(request, _("Unable to retrieve public images."))
        self.fields['image_choices'].choices = [(image.id, image.name)
                                                for image in images]

    def handle(self, request, data):
        log.debug('Adding new murano using data {0}'.format(data))
        murano_properties = {'murano_image_info': json.dumps(
            {'title': data['title'], 'type': data['image_type']})}
        try:
            image = glance.image_update(request, data['image_choices'],
                                        properties=murano_properties)

            messages.success(request, _('Image added to Murano'))
            return image
        except Exception:
            exceptions.handle(request, _('Unable to update image.'))
