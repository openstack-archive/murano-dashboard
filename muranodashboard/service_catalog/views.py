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
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tables
from horizon.workflows import WorkflowView
from horizon.forms.views import ModalFormView

from .tables import ServiceCatalogTable, MetadataObjectsTable
from .forms import UploadServiceForm, UploadFileForm
from .workflows import ComposeService
from .workflows import STEP_NAMES

from muranodashboard.environments.services.metadata import metadataclient
from metadataclient.common.exceptions import CommunicationError, Unauthorized
from metadataclient.common.exceptions import HTTPInternalServerError, NotFound
LOG = logging.getLogger(__name__)


class ServiceCatalogView(tables.DataTableView):
    table_class = ServiceCatalogTable
    template_name = 'service_catalog/index.html'

    def get_data(self):
        available_services = []
        try:
            available_services = metadataclient(
                self.request).metadata_admin.list_services()
        except CommunicationError:
            LOG.exception(CommunicationError)
            exceptions.handle(self.request,
                              _('Unable to communicate to Murano Metadata '
                              'Repository. Add MURANO_METADATA_URL to local_'
                              'settings'))
        except Unauthorized:
            LOG.exception(Unauthorized)
            exceptions.handle(self.request, _('Configure Keystone in Murano '
                                              'Repository Service'))
        except HTTPInternalServerError:
            LOG.exception(HTTPInternalServerError)
            exceptions.handle(self.request, _('There is a problem with Murano '
                                              'Repository Service'))
        return available_services


class UploadServiceView(ModalFormView):
    form_class = UploadServiceForm
    template_name = 'service_catalog/upload.html'
    context_object_name = 'service_catalog'
    success_url = reverse_lazy('horizon:murano:service_catalog:index')


class ManageFilesView(tables.DataTableView):
    table_class = MetadataObjectsTable
    template_name = 'service_catalog/files.html'

    def get_data(self):
        files = []
        try:
            files = metadataclient(
                self.request).metadata_admin.get_service_files()
        except CommunicationError:
            exceptions.handle(self.request,
                              _('Unable to communicate to Murano Metadata '
                              'Repository. Add MURANO_METADATA_URL to local_'
                              'settings'))
        except Unauthorized:
            exceptions.handle(self.request, _('Configure Keystone in Murano '
                                              'Repository Service'))
        except HTTPInternalServerError:
            exceptions.handle(self.request, _('There is a problem with Murano '
                                              'Repository Service'))
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
                            'version': getattr(service, 'version', 0.1),
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


class UploadFileView(ModalFormView):
    form_class = UploadFileForm
    template_name = 'service_catalog/upload_file.html'
    context_object_name = 'manage_files'
    success_url = reverse_lazy('horizon:murano:service_catalog:manage_files')
