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

import json
import logging

from django import forms
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms as horizon_forms
from horizon import messages
from openstack_dashboard.api import glance

LOG = logging.getLogger(__name__)


def filter_murano_images(images, request=None):
    marked_images = []
    for image in images:
        metadata = image.properties.get('murano_image_info')
        if metadata:
            try:
                metadata = json.loads(metadata)
            except ValueError:
                msg = _('Invalid metadata for image: {0}').format(image.id)
                LOG.warn(msg)
                if request:
                    exceptions.handle(request, msg)
            else:
                image.title = metadata.get('title', 'No Title')
                image.type = metadata.get('type', 'No Type')

            marked_images.append(image)
    return marked_images


class MarkImageForm(horizon_forms.SelfHandlingForm):
    _metadata = {
        'windows.2012': ' Windows Server 2012',
        'linux': 'Generic Linux',
        'cirros.demo': 'Murano Demo'
    }

    image = forms.ChoiceField(label='Image')
    title = forms.CharField(max_length="255", label=_("Title"))
    type = forms.ChoiceField(label="Type", choices=_metadata.items())
    existing_titles = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, request, *args, **kwargs):
        super(MarkImageForm, self).__init__(request, *args, **kwargs)

        images = []
        try:
            # https://bugs.launchpad.net/murano/+bug/1339261 - glance
            # client version change alters the API. Other tuple values
            # are _more and _prev (in recent glance client)
            images = glance.image_list_detailed(request)[0]
        except Exception:
            LOG.error('Failed to request image list from Glance')
            exceptions.handle(request, _('Unable to retrieve list of images'))

        self.fields['image'].choices = [(i.id, i.name) for i in images]
        self.fields['existing_titles'].initial = \
            [image.title for image in filter_murano_images(images)]

    def handle(self, request, data):
        LOG.debug('Marking image with specified metadata: {0}'.format(data))

        image_id = data['image']
        properties = glance.image_get(request, image_id).properties
        properties['murano_image_info'] = json.dumps({
            'title': data['title'],
            'type': data['type']
        })

        try:
            img = glance.image_update(request, image_id, properties=properties)
            messages.success(request, _('Image successfully marked'))
            return img
        except Exception:
            exceptions.handle(request, _('Unable to mark image'),
                              redirect='horizon:murano:images:index')

    def clean_title(self):
        cleaned_data = super(MarkImageForm, self).clean()
        title = cleaned_data.get('title')
        existing_titles = self.fields['existing_titles'].initial
        if title in existing_titles:
            raise forms.ValidationError(_('Specified title already in use.'
                                          ' Please choose another one.'))

        return title
