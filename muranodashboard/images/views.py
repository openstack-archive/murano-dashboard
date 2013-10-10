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

from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _

from openstack_dashboard.api import glance
from horizon import exceptions
from horizon import tables
from horizon import messages
from horizon.forms.views import ModalFormView
from .tables import MarkedImagesTable

from .forms import MarkImageForm

LOG = logging.getLogger(__name__)


class MarkedImagesView(tables.DataTableView):
    table_class = MarkedImagesTable
    template_name = 'images/index.html'

    def get_data(self):
        images = []
        try:
            images, _more = glance.image_list_detailed(self.request)
        except Exception:
            msg = _('Unable to retrieve list of images')
            uri = reverse('horizon:murano:images:index')

            exceptions.handle(self.request, msg, redirect=uri)

        marked_images = []
        for image in images:
            metadata = image.properties.get('murano_image_info')
            if metadata:
                try:
                    metadata = json.loads(metadata)
                except ValueError:
                    msg = _('Invalid metadata for image: {0}'.format(image.id))
                    LOG.warn(msg)
                    messages.error(self.request, msg)
                else:
                    image.title = metadata.get('title', 'No Title')
                    image.type = metadata.get('type', 'No Type')

                marked_images.append(image)
        return marked_images


class MarkImageView(ModalFormView):
    form_class = MarkImageForm
    template_name = 'images/mark.html'
    context_object_name = 'image'
    success_url = reverse_lazy('horizon:murano:images:index')
