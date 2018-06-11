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

from django.conf import settings
from django import forms
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms as horizon_forms
from horizon import messages
from openstack_dashboard.api import glance
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


def filter_murano_images(images, request=None):
    # filter images by project owner
    filter_project = getattr(settings, 'MURANO_IMAGE_FILTER_PROJECT_ID', None)
    if filter_project:
        project_ids = [filter_project]
        if request:
            project_ids.append(request.user.tenant_id)
        images = filter(
            lambda x: getattr(x, 'owner', None) in project_ids, list(images))
    # filter out the snapshot image type
    images = filter(
        lambda x: getattr(x, 'image_type', None) != 'snapshot', list(images))
    marked_images = []
    for image in images:
        # Additional properties, whose value is always a string data type, are
        # only included in the response if they have a value.
        metadata = getattr(image, 'murano_image_info', None)
        if metadata:
            try:
                metadata = json.loads(metadata)
            except ValueError:
                msg = _('Invalid metadata for image: {0}').format(image.id)
                LOG.warning(msg)
                if request:
                    exceptions.handle(request, msg)
                metadata = {}
            image.title = metadata.get('title', 'No Title')
            image.type = metadata.get('type', 'No Type')

            marked_images.append(image)
    return marked_images


class MarkImageForm(horizon_forms.SelfHandlingForm):
    _metadata = {
        'windows.2012': ' Windows Server 2012',
        'linux': 'Generic Linux',
        'cirros.demo': 'CirrOS for Murano Demo',
        'custom': "Custom type"
    }

    image = forms.ChoiceField(label=_('Image'))
    title = forms.CharField(max_length="255", label=_("Title"))
    type = forms.ChoiceField(
        label=_("Type"),
        choices=_metadata.items(),
        initial='custom',
        widget=forms.Select(attrs={
            'class': 'switchable',
            'data-slug': 'type'}))
    custom_type = forms.CharField(
        max_length="255",
        label=_("Custom Type"),
        widget=forms.TextInput(attrs={
            'class': 'switched',
            'data-switch-on': 'type',
            'data-type-custom': _('Custom Type')}),
        required=False)
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

        # filter out the image format aki and ari
        images = filter(
            lambda x: x.container_format not in ('aki', 'ari'), images)

        # filter out the snapshot image type
        images = filter(
            lambda x: x.properties.get("image_type", '') != 'snapshot', images)

        self.fields['image'].choices = [(i.id, i.name) for i in images]
        self.fields['existing_titles'].initial = \
            [image.title for image in filter_murano_images(images)]

    def handle(self, request, data):
        LOG.debug('Marking image with specified metadata: {0}'.format(data))

        image_id = data['image']
        image_type = data['type'] if data['type'] != 'custom' else \
            data['custom_type']
        kwargs = {}
        kwargs['murano_image_info'] = json.dumps({
            'title': data['title'],
            'type': image_type
        })
        try:
            img = glance.image_update_properties(request, image_id, **kwargs)
            messages.success(request, _('Image successfully marked'))
            return img
        except Exception:
            exceptions.handle(request, _('Unable to mark image'),
                              redirect=reverse(
                                  'horizon:app-catalog:images:index'))

    def clean_title(self):
        cleaned_data = super(MarkImageForm, self).clean()
        title = cleaned_data.get('title')
        existing_titles = self.fields['existing_titles'].initial
        if title in existing_titles:
            raise forms.ValidationError(_('Specified title already in use.'
                                          ' Please choose another one.'))

        return title
