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
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from horizon import exceptions
from horizon import tables
from horizon import messages

from muranodashboard.environments.services.metadata import metadataclient


class ComposeService(tables.LinkAction):
    name = 'compose_service'
    verbose_name = _('Compose Service')
    url = 'horizon:murano:service_catalog:compose_service'
    classes = ("ajax-modal", "btn-create")

    def allowed(self, request, environment):
        return True


class ModifyService(ComposeService):
    name = 'modify_service'
    verbose_name = _('Modify Service')


class UploadService(tables.LinkAction):
    name = "upload_service"
    verbose_name = _("Upload Service")
    url = "horizon:murano:service_catalog:upload_service"
    classes = ("ajax-modal", "btn-create")

    def allowed(self, request, image):
        return True


class DownloadService(tables.Action):
    name = "download_service"
    verbose_name = _("Download Service")

    def allowed(self, request, image):
        return True

    def single(self, data_table, request, obj_id):
        try:
            body = metadataclient(request).metadata_admin.download_service(
                obj_id)
            response = HttpResponse(body,
                                    content_type='application/octet-stream')
            response['Content-Disposition'] = 'filename=data.tar.gz'
            return response
        except Exception:
            exceptions.handle(request,
                              _('Unable to download service.'),
                              redirect='horizon:murano:service_catalog:index')


class ToggleEnabled(tables.BatchAction):
    name = 'toggle_enabled'
    data_type_singular = _('Active')
    data_type_plural = _('Active')
    action_present = _('Toggle')
    action_past = _('Toggled')

    def handle(self, table, request, obj_ids):
        for obj_id in obj_ids:
            try:
                metadataclient(request).metadata_admin.toggle_enabled(obj_id)
            except Exception:
                exceptions.handle(request,
                                  _('Unable to toggle service state.'))
            else:
                obj = table.get_object_by_id(obj_id)
                obj.enabled = not obj.enabled
                messages.success(
                    request,
                    _("Service '{service} successfully toggled".format(
                        service=obj_id)))


class DeleteService(tables.DeleteAction):
    name = 'delete_service'
    data_type_singular = _('Service')

    def delete(self, request, obj_id):
        try:
            metadataclient(request).metadata_admin.delete_service(obj_id)
        except Exception:
            exceptions.handle(request,
                              _('Unable to remove service.'),
                              redirect='horizon:murano:service_catalog:index')


class ServiceCatalogTable(tables.DataTable):
    service_name = tables.Column('service_display_name',
                                 verbose_name=_('Service Name'))
    service_enabled = tables.Column('enabled', verbose_name=_('Active'))

    service_valid = tables.Column('valid', verbose_name=_('Valid'))
    service_author = tables.Column('author', verbose_name=_('Author'))

    def get_object_display(self, datum):
        return datum.service_display_name

    class Meta:
        name = 'service_catalog'
        verbose_name = _('Service Definitions')
        table_actions = (ComposeService,
                         UploadService,
                         ToggleEnabled,
                         DeleteService)
        row_actions = (ModifyService,
                       DownloadService,
                       ToggleEnabled,
                       DeleteService)


class UploadFile(tables.LinkAction):
    # ToDo: this is a stub. You should add real code here
    name = "upload_file"
    verbose_name = _("Upload File")
    url = "horizon:murano:service_catalog:upload_file"
    classes = ("ajax-modal", "btn-create")

    def allowed(self, request, image):
        return True


class DownloadFile(tables.Action):
    name = "download_file"
    verbose_name = _("Download File")

    def allowed(self, request, image):
        return True

    def single(self, data_table, request, obj_id):
        # ToDo: this is a stub. You should add real code here
        pass


class ToggleSelection(tables.BatchAction):
    name = 'toggle_selection'
    data_type_singular = _('File selection')
    data_type_plural = _('File selection')
    action_present = _('Toggle')
    action_past = _('Toggled')

    def handle(self, table, request, obj_ids):
        # ToDo: this is a stub. You should add real code here
        pass


class DeleteFile(tables.DeleteAction):
    name = 'delete_file'
    data_type_singular = _('File')

    def delete(self, request, obj_id):
        # ToDo: this is a stub. You should add real code here
        pass


class MetadataObjectsTable(tables.DataTable):
    file_name = tables.Column('filename', verbose_name=_('File Name'))
    path = tables.Column('path', verbose_name=_('Path'))
    selected = tables.Column('selected', verbose_name=_('Selected'))

    class Meta:
        name = 'metadata_objects'
        verbose_name = _('Metadata Objects')
        table_actions = (UploadFile, DeleteFile, ToggleSelection)
        row_actions = (ToggleSelection, DownloadFile, DeleteFile)
