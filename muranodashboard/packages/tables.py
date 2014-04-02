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
from muranodashboard.dynamic_ui.metadata import metadataclient
LOG = logging.getLogger(__name__)


class UploadPackage(tables.LinkAction):
    name = 'upload_package'
    verbose_name = _('Upload Package')
    url = 'horizon:murano:packages:upload'
    classes = ('ajax-modal', 'btn-create')

    def allowed(self, request, image):
        return True


class DownloadPackage(tables.Action):
    name = 'download_package'
    verbose_name = _('Download Package')

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
        except HTTPException:
            LOG.exception(_('Something went wrong during package downloading'))
            redirect = reverse('horizon:murano:packages:index')
            exceptions.handle(request,
                              _('Unable to download package.'),
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
            except HTTPException:
                LOG.exception(_('Toggling package state in package '
                                'repository failed'))
                exceptions.handle(request,
                                  _('Unable to toggle package state.'))
            else:
                obj = table.get_object_by_id(obj_id)
                obj.enabled = not obj.enabled
                messages.success(
                    request,
                    _("Package '{package}' successfully toggled".format(
                        package=obj_id)))


class DeletePackage(tables.DeleteAction):
    name = 'delete_package'
    data_type_singular = _('Package')

    def delete(self, request, obj_id):
        try:
            metadataclient(request).metadata_admin.delete_service(obj_id)
        except HTTPException:
            LOG.exception(_('Unable to delete package in murano-api server'))
            exceptions.handle(request,
                              _('Unable to remove package.'),
                              redirect='horizon:murano:packages:index')


class ModifyPackage(tables.LinkAction):
    name = 'modify_package'
    verbose_name = _('Modify Package')
    url = 'horizon:murano:packages:modify'

    def allowed(self, request, environment):
        return True


class PackageDefinitionsTable(tables.DataTable):
    name = tables.Column('service_display_name',
                         verbose_name=_('Package Name'))
    enabled = tables.Column('enabled', verbose_name=_('Active'))
    type = tables.Column('type', verbose_name=_('Type'))
    author = tables.Column('author', verbose_name=_('Author'))

    def get_object_display(self, datum):
        return datum.service_display_name

    class Meta:
        name = 'packages'
        verbose_name = _('Package Definitions')
        table_actions = (UploadPackage,
                         ToggleEnabled,
                         DeletePackage)

        row_actions = (ModifyPackage,
                       DownloadPackage,
                       ToggleEnabled,
                       DeletePackage)
