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
import json
from django import forms
from django.utils.translation import ugettext_lazy as _
from .services import get_service_choices
from .services.fields import get_murano_images
log = logging.getLogger(__name__)


def filter_service_by_image_type(service, request):
    def find_image_field():
        for form_cls in service.forms:
            for field in form_cls.fields_template:
                if field.get('type') == 'image':
                    return field
        return None

    filtered = False
    image_field = find_image_field()
    if not image_field:
        message = "Please provide Image field description in UI definition"
        return filtered, message
    specified_image_type = image_field.get('imageType')
    if not specified_image_type:
        message = "Please provide 'imageType' parameter in Image field " \
                  "description in UI definition"
        return filtered, message

    registered_murano_images = []
    available_images = get_murano_images(request)
    for image in available_images:
        registered_murano_images.append(image.murano_property.get('type'))

    if registered_murano_images:
        for type in registered_murano_images:
            if specified_image_type in type:
                filtered = True
            break
    if not filtered:
        message = 'Murano image type "{0}" is not registered'.format(
            specified_image_type)
    else:
        message = ''
    return filtered, message


def ChoiceServiceFormFactory(request):
    filtered, not_filtered = get_service_choices(
        request, filter_service_by_image_type)

    class _Class(forms.Form):
        service = forms.ChoiceField(
            label=_('Service Type'),
            choices=filtered or [("", _("No services available"))])

        description = forms.CharField(widget=forms.HiddenInput,
                                      initial=json.dumps(not_filtered))
    return _Class
