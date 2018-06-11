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

import itertools

from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon.forms import views
from horizon import tables as horizon_tables
from horizon.utils import functions as utils
from openstack_dashboard.api import glance

from muranodashboard.images import forms
from muranodashboard.images import tables


class MarkedImagesView(horizon_tables.DataTableView):
    table_class = tables.MarkedImagesTable
    template_name = 'images/index.html'
    page_title = _("Marked Images")

    def has_prev_data(self, table):
        return self._prev

    def has_more_data(self, table):
        return self._more

    def get_data(self):
        prev_marker = self.request.GET.get(
            tables.MarkedImagesTable._meta.prev_pagination_param, None)

        if prev_marker is not None:
            sort_dir = 'asc'
            marker = prev_marker
        else:
            sort_dir = 'desc'
            marker = self.request.GET.get(
                tables.MarkedImagesTable._meta.pagination_param, None)

        page_size = utils.get_page_size(self.request)

        request_size = page_size + 1
        kwargs = {'filters': {}}
        if marker:
            kwargs['marker'] = marker
        kwargs['sort_dir'] = sort_dir
        images = []
        self._prev = False
        self._more = False

        glance_v2_client = glance.glanceclient(self.request, "2")

        try:
            images_iter = glance_v2_client.images.list(
                **kwargs)
        except Exception:
            msg = _('Unable to retrieve list of images')
            uri = reverse('horizon:app-catalog:catalog:index')

            exceptions.handle(self.request, msg, redirect=uri)

        marked_images_iter = forms.filter_murano_images(
            images_iter,
            request=self.request)
        images = list(itertools.islice(marked_images_iter, request_size))
        # first and middle page condition
        if len(images) > page_size:
            images.pop(-1)
            self._more = True
            # middle page condition
            if marker is not None:
                self._prev = True
        # first page condition when reached via prev back
        elif sort_dir == 'asc' and marker is not None:
            self._more = True
        # last page condition
        elif marker is not None:
            self._prev = True
        if prev_marker is not None:
            images.reverse()
        return images


class MarkImageView(views.ModalFormView):
    form_class = forms.MarkImageForm
    form_id = 'mark_murano_image_form'
    modal_header = _('Add Murano Metadata')
    template_name = 'images/mark.html'
    context_object_name = 'image'
    page_title = _("Update Image")
    success_url = reverse_lazy('horizon:app-catalog:images:index')
    submit_label = _('Mark Image')
    submit_url = reverse_lazy('horizon:app-catalog:images:mark_image')
