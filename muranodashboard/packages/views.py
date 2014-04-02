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

from django.core.urlresolvers import reverse_lazy, reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from horizon import exceptions
from horizon import tables
from horizon.workflows import WorkflowView
from horizon.forms.views import ModalFormView

from .tables import PackageDefinitionsTable
from .utils import STEP_NAMES
from .forms import UploadPackageForm
from .workflows import ComposeService
from muranodashboard.environments import api
from muranodashboard.dynamic_ui.metadata import metadataclient
from muranodashboard.dynamic_ui.metadata import metadata_exceptions
from metadataclient.common.exceptions import HTTPInternalServerError, NotFound
LOG = logging.getLogger(__name__)


class PackageDefinitionsView(tables.DataTableView):
    table_class = PackageDefinitionsTable
    template_name = 'packages/index.html'

    def get_data(self):
        return api.muranoclient(self.request).packages.list()


class UploadPackageView(ModalFormView):
    form_class = UploadPackageForm
    template_name = 'packages/upload_package.html'
    context_object_name = 'packages'
    success_url = reverse_lazy('horizon:murano:packages:index')


class ModifyPackageView(tables.MultiTableView):
    template_name = 'packages/service_files.html'
    failure_url = reverse_lazy('horizon:murano:packages:index')

    def dispatch(self, request, *args, **kwargs):
        service_id = kwargs['full_service_name']
        for table in self.table_classes:
            data_type = table._meta.name
            table.base_actions['upload_file2'].url = \
                reverse('horizon:murano:service_catalog:upload_file2',
                        args=(data_type, service_id,))
        return super(ModifyPackageView, self).dispatch(request,
                                                       *args,
                                                       **kwargs)

    def _get_data(self, full_service_name):
        info, request = {}, self.request
        with metadata_exceptions(request):
            info = metadataclient(request).metadata_admin.get_service_info(
                full_service_name)

        return info

    def get_context_data(self, **kwargs):
        context = super(ModifyPackageView,
                        self).get_context_data(**kwargs)
        full_service_name = kwargs['full_service_name']
        service_info = self._get_data(full_service_name)
        service_name = service_info.get('service_display_name', '-')
        context['service_name'] = service_name
        detail_info = SortedDict([
            ('Name', service_name),
            ('ID', service_info.get('full_service_name', '-')),
            ('Version', service_info.get('version', '-')),
            ('UI Description', service_info.get('description', '-')),
            ('Author', service_info.get('author', '-')),
            ('Service Version', service_info.get('service_version', '-')),
            ('Active', service_info.get('enabled', '-'))])
        context['service_info'] = detail_info
        return context
