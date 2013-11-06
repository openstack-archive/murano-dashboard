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

from django.core.urlresolvers import reverse, reverse_lazy

from horizon import tables
from horizon.workflows import WorkflowView
from horizon.forms.views import ModalFormView

from .tables import ServiceCatalogTable
from .forms import UploadServiceForm
from .workflows import ComposeService

from muranodashboard.environments.services.metadata import metadataclient

LOG = logging.getLogger(__name__)


class ServiceCatalogView(tables.DataTableView):
    table_class = ServiceCatalogTable
    template_name = 'service_catalog/index.html'

    def get_data(self):
        return metadataclient(self.request).metadata_admin.list_services()


class UploadServiceView(ModalFormView):
    form_class = UploadServiceForm
    template_name = 'service_catalog/upload.html'
    context_object_name = 'service_catalog'
    success_url = reverse_lazy("horizon:murano:service_catalog:index")


class ComposeServiceView(WorkflowView):
    workflow_class = ComposeService
    success_url = reverse_lazy("horizon:murano:service_catalog:index")

    def get_context_data(self, **kwargs):
        context = super(ComposeServiceView, self).get_context_data(**kwargs)
        full_service_name = kwargs['full_service_name']
        context['full_service_name'] = full_service_name
        return context

    def get_initial(self):
        full_service_name = self.kwargs['full_service_name']
        objects_list = metadataclient(
            self.request).metadata_admin.get_service_files('ui',
                                                           full_service_name)
        if full_service_name:
            srvs = metadataclient(self.request).metadata_admin.list_services()
            for service in srvs:
                if full_service_name == service.id:
                    return {
                        'full_service_name': service.id,
                        'service_display_name': service.service_display_name,
                        'author': service.author,
                        'version': service.version,
                        'description': service.description,
                        'enabled': service.enabled,
                        'selected_files': objects_list
                    }
            raise RuntimeError('Not found service id')
        else:
            return {'selected_files': objects_list}
