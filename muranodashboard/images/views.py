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
from tables import ImagesTable

from forms import AddImageForm
from muranoclient.common.exceptions import HTTPForbidden

LOG = logging.getLogger(__name__)


class MuranoImageView(tables.DataTableView):
    table_class = ImagesTable
    template_name = 'images/index.html'

    def get_data(self):
        images = []
        try:
            images, _more = glance.image_list_detailed(self.request)

        except HTTPForbidden:
            msg = _('Unable to retrieve list of images')
            exceptions.handle(
                self.request, msg,
                redirect=reverse("horizon:murano:images:index"))
        murano_images = []
        for image in images:
            murano_property = image.properties.get('murano_image_info')
            if murano_property:
                try:
                    murano_json = json.loads(murano_property)
                except ValueError:
                    LOG.warning("JSON in image metadata is not valid. "
                                "Check it in glance.")
                    messages.error(self.request,
                                   _("Invalid murano image metadata"))
                else:
                    image.title = murano_json.get('title', 'No title')
                    image.type = murano_json.get('type', 'No title')

                murano_images.append(image)
        return murano_images


class AddMuranoImageView(ModalFormView):
    form_class = AddImageForm
    template_name = 'images/add.html'
    context_object_name = 'image'
    success_url = reverse_lazy("horizon:murano:images:index")
