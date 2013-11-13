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
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from django.http import HttpResponse

from horizon import exceptions
from horizon import tables
from horizon import messages
from metadataclient.common.exceptions import HTTPException
from muranodashboard.environments.services.metadata import metadataclient
from muranodashboard.environments.services.fields import Column, CheckColumn


LOG = logging.getLogger(__name__)


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

    def single(self, data_table, request, service_id):
        try:
            body = metadataclient(request).metadata_admin.download_service(
                service_id)
            response = HttpResponse(body,
                                    content_type='application/octet-stream')
            response['Content-Disposition'] = 'filename={name}.tar.gz'.format(
                name=service_id)
            return response
        except HTTPException as e:
            LOG.exception(e)
            redirect = reverse('horizon:murano:service_catalog:index')
            exceptions.handle(request,
                              _('Unable to download service.'),
                              redirect=redirect)


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
            except HTTPException as e:
                LOG.exception(e)
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
        except HTTPException as e:
            LOG.exception(e)
            exceptions.handle(request,
                              _('Unable to remove service.'),
                              redirect='horizon:murano:service_catalog:index')


class ManageFiles(tables.LinkAction):
    name = 'manage_files'
    verbose_name = _('Manage Files')
    url = 'horizon:murano:service_catalog:manage_files'

    def allowed(self, request, environment):
        return True


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
                         DeleteService,
                         ManageFiles)

        row_actions = (ModifyService,
                       DownloadService,
                       ToggleEnabled,
                       DeleteService)


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
            except HTTPException as e:
                LOG.exception(e)
                exceptions.handle(request,
                                  _('Unable to toggle service state.'))
            else:
                obj = table.get_object_by_id(obj_id)
                obj.enabled = not obj.enabled
                messages.success(request,
                                 _("Service '{service} successfully "
                                   "toggled".format(service=obj_id)))


class DeleteFile(tables.DeleteAction):
    name = 'delete_file'
    data_type_singular = _('File')

    def delete(self, request, obj_id):
        #TODO: Unhardcode data_type after other tabs implemented
        try:
            metadataclient(request).metadata_admin.delete('ui', obj_id)
        except HTTPException as e:
            LOG.exception(e)
            redirect = reverse('horizon:murano:service_catalog:manage_files')
            exceptions.handle(
                request,
                _('Unable to remove file: {0}'.format(obj_id)),
                redirect=redirect)


class UploadFile(tables.LinkAction):
    name = 'upload_file'
    verbose_name = _('Upload File')
    url = 'horizon:murano:service_catalog:upload_file'
    classes = ('ajax-modal', 'btn-create')

    def allowed(self, request, image):
        return True


class DownloadFile(tables.Action):
    name = 'download_file'
    verbose_name = _('Download File')

    def allowed(self, request, image):
        return True

    def single(self, data_table, request, obj_id):
        #TODO: Unhardcode data_type after other tabs implemented
        try:
            body = metadataclient(request).metadata_admin.get_file('ui',
                                                                   obj_id)
            response = HttpResponse(body,
                                    content_type='application/octet-stream')
            response['Content-Disposition'] = 'filename={name}'.format(name=
                                                                       obj_id)
            return response
        except HTTPException as e:
            LOG.exception(e)
            redirect = reverse('horizon:murano:service_catalog:manage_files')
            exceptions.handle(
                request,
                _('Unable to download file: {0}'.format(obj_id)),
                redirect=redirect)


def make_table_cls(field_name):
    class MetadataObjectsTableNoActions(tables.DataTable):
        filename = Column('filename', verbose_name=_('File Name'),
                          table_name=field_name)
        path = Column('path', verbose_name=_('Path'), table_name=field_name)
        selected = CheckColumn('selected', verbose_name=_('Selected'),
                               table_name=field_name)

        class Meta:
            template = 'common/form-fields/data-grid/data_table.html'

    return MetadataObjectsTableNoActions


class MetadataObjectsTable(tables.DataTable):
    file_name = tables.Column('filename', verbose_name=_('File Name'))
    path = tables.Column('path', verbose_name=_('Nested Path'))
    selected = tables.Column('selected', verbose_name=_('Used by Service'))

    def get_object_display(self, obj):
        return unicode(obj.filename)

    class Meta:
        name = 'manage_files'
        verbose_name = _('Murano Repository Files')
        table_actions = (UploadFile,
                         DeleteFile,
                         )

        row_actions = (DownloadFile,
                       DeleteFile,
                       )
