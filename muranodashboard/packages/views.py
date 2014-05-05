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

from django.core.urlresolvers import reverse_lazy
from horizon.forms import views
from horizon import tables as horizon_tables

from muranodashboard.environments import api
from muranodashboard.packages import forms
from muranodashboard.packages import tables

LOG = logging.getLogger(__name__)


class PackageDefinitionsView(horizon_tables.DataTableView):
    table_class = tables.PackageDefinitionsTable
    template_name = 'packages/index.html'

    def get_data(self):
        pkgs = []
        with api.handled_exceptions(self.request):
            pkgs = api.muranoclient(self.request).packages.filter(
                include_disabled=True,
                owned=True
            )
        return pkgs


class UploadPackageView(views.ModalFormView):
    form_class = forms.UploadPackageForm
    template_name = 'packages/upload_package.html'
    context_object_name = 'packages'
    success_url = reverse_lazy('horizon:murano:packages:index')
    failure_url = reverse_lazy('horizon:murano:packages:index')


class ModifyPackageView(views.ModalFormView):
    form_class = forms.ModifyPackageForm
    template_name = 'packages/modify_package.html'
    success_url = reverse_lazy('horizon:murano:packages:index')
    failure_url = reverse_lazy('horizon:murano:packages:index')

    def get_initial(self):
        app_id = self.kwargs['app_id']
        package = api.muranoclient(self.request).packages.get(app_id)
        return {
            'name': package.name,
            'enabled': package.enabled,
            'description': package.description,
            'categories': package.categories,
            'tags': ','.join(package.tags),
            'is_public': package.is_public,
            'app_id': app_id
        }

    def get_context_data(self, **kwargs):
        context = super(ModifyPackageView, self).get_context_data(**kwargs)
        context['app_id'] = self.kwargs['app_id']
        return context
