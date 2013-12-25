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

from .tables import ServiceCatalogTable, MetadataObjectsTable
from .utils import define_tables
from .utils import STEP_NAMES
from .forms import UploadServiceForm, UploadFileForm, UploadFileToService
from .workflows import ComposeService
from muranodashboard.dynamic_ui.metadata import metadataclient
from muranodashboard.dynamic_ui.metadata import metadata_exceptions
from metadataclient.common.exceptions import HTTPInternalServerError, NotFound
LOG = logging.getLogger(__name__)


class ServiceCatalogView(tables.DataTableView):
    table_class = ServiceCatalogTable
    template_name = 'service_catalog/index.html'

    def get_data(self):
        services, request = [], self.request
        with metadata_exceptions(request):
            services = metadataclient(request).metadata_admin.list_services()

        return services


class UploadServiceView(ModalFormView):
    form_class = UploadServiceForm
    template_name = 'service_catalog/upload_service.html'
    context_object_name = 'service_catalog'
    success_url = reverse_lazy('horizon:murano:service_catalog:index')


class ManageFilesView(tables.DataTableView):
    table_class = MetadataObjectsTable
    template_name = 'service_catalog/files.html'

    def get_data(self):
        files, request = [], self.request
        with metadata_exceptions(request):
            files = metadataclient(request).metadata_admin.get_service_files()

        return files


class ComposeServiceView(WorkflowView):
    workflow_class = ComposeService
    success_url = reverse_lazy('horizon:murano:service_catalog:index')

    def get_context_data(self, **kwargs):
        context = super(ComposeServiceView, self).get_context_data(**kwargs)
        full_service_name = kwargs['full_service_name']
        context['full_service_name'] = full_service_name
        return context

    def get_initial(self):
        try:
            full_service_name = self.kwargs['full_service_name']
            metadata = metadataclient(self.request).metadata_admin
            files_dict = {}
            # FixME: get all services with a single call, should be faster
            for field_name, ignorable in STEP_NAMES:
                files_dict[field_name] = metadata.get_service_files(
                    field_name, full_service_name)

            if full_service_name:
                srvs = metadataclient(
                    self.request).metadata_admin.list_services()
                for service in srvs:
                    if full_service_name == service.id:
                        # we know for sure 2 first params are always present
                        files_dict.update({
                            'full_service_name': service.id,
                            'service_display_name':
                            service.service_display_name,
                            'author': getattr(service, 'author', ''),
                            'service_version': getattr(service,
                                                       'service_version', 0),
                            'description': getattr(service, 'description', ''),
                            'enabled': getattr(service, 'enabled', False)
                        })
                        return files_dict
                raise RuntimeError('Not found service id')
            else:
                return files_dict
        except (HTTPInternalServerError, NotFound) as e:
            LOG.exception(e)
            msg = _('Error with Murano Metadata Repository')
            redirect = reverse_lazy('horizon:murano:service_catalog:index')
            exceptions.handle(self.request, msg, redirect)


class UploadFileView2(ModalFormView):
    template_name = 'service_catalog/upload_file2.html'
    form_class = UploadFileToService
    success_url = 'horizon:murano:service_catalog:manage_service'

    def get_success_url(self):
        return reverse(self.success_url,
                       args=(self.kwargs['full_service_name'],))

    def get_form_kwargs(self):
        kwargs = super(UploadFileView2, self).get_form_kwargs()
        kwargs.update(self.kwargs)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super(UploadFileView2, self).get_context_data(**kwargs)
        context['data_type'] = self.kwargs['data_type']
        context['service_id'] = self.kwargs['full_service_name']
        return context


class UploadFileView(ModalFormView):
    form_class = UploadFileForm
    template_name = 'service_catalog/upload_file.html'
    context_object_name = 'manage_files'
    success_url = reverse_lazy('horizon:murano:service_catalog:manage_files')


class ManageServiceView(tables.MultiTableView):
    template_name = 'service_catalog/service_files.html'
    failure_url = reverse_lazy('horizon:murano:service_catalog:index')

    def dispatch(self, request, *args, **kwargs):
        service_id = kwargs['full_service_name']
        for table in self.table_classes:
            data_type = table._meta.name
            table.base_actions['upload_file2'].url = \
                reverse('horizon:murano:service_catalog:upload_file2',
                        args=(data_type, service_id,))
        return super(ManageServiceView, self).dispatch(request,
                                                       *args,
                                                       **kwargs)

    def __init__(self, *args, **kwargs):
        # here we should move table_classes assignment into __init__ method
        # because otherwise reverse() call inside define_tables() won't work
        # (cannot query URL while they are being populated)
        self.table_classes = tuple(
            [define_tables(name, step_verbose_name)
             for (name, step_verbose_name) in STEP_NAMES])
        super(ManageServiceView, self).__init__(*args, **kwargs)

    def _get_data(self, full_service_name):
        info, request = {}, self.request
        with metadata_exceptions(request):
            info = metadataclient(request).metadata_admin.get_service_info(
                full_service_name)

        return info

    def get_context_data(self, **kwargs):
        context = super(ManageServiceView,
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

    def get_file_list(self, data_type):
        full_service_name = self.kwargs['full_service_name']

        files, request = [], self.request
        with metadata_exceptions(request):
            files = metadataclient(request).metadata_admin.get_service_files(
                data_type, full_service_name)

        return [file for file in files if file.selected]

    def get_ui_data(self):
        return self.get_file_list('ui')

    def get_scripts_data(self):
        return self.get_file_list('scripts')

    def get_heat_data(self):
        return self.get_file_list('heat')

    def get_agent_data(self):
        return self.get_file_list('agent')

    def get_workflows_data(self):
        return self.get_file_list('workflows')
