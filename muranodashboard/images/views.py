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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon.forms import views
from horizon import tables as horizon_tables
from openstack_dashboard.api import glance

from muranodashboard.images import forms
from muranodashboard.images import tables


class MarkedImagesView(horizon_tables.DataTableView):
    table_class = tables.MarkedImagesTable
    template_name = 'images/index.html'

    def get_data(self):
        images = []
        try:
            # https://bugs.launchpad.net/murano/+bug/1339261 - glance
            # client version change alters the API. Other tuple values
            # are _more and _prev (in recent glance client)
            images = glance.image_list_detailed(self.request)[0]
        except Exception:
            msg = _('Unable to retrieve list of images')
            uri = reverse('horizon:murano:images:index')

            exceptions.handle(self.request, msg, redirect=uri)
        return forms.filter_murano_images(images, request=self.request)


class MarkImageView(views.ModalFormView):
    form_class = forms.MarkImageForm
    template_name = 'images/mark.html'
    context_object_name = 'image'
    success_url = reverse_lazy('horizon:murano:images:index')
