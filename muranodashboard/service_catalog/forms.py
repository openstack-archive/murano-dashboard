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
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from horizon.forms import SelfHandlingForm
from horizon import exceptions
from horizon import messages
from metadataclient.common.exceptions import HTTPException
from muranodashboard.environments.services.metadata import metadataclient

log = logging.getLogger(__name__)


class UploadServiceForm(SelfHandlingForm):
    file = forms.FileField(label=_('Service .tag.gz package'),
                           required=True)

    def handle(self, request, data):
        log.debug('Uploading .tag.gz package {0}'.format(data))
        try:
            result = metadataclient(request).metadata_admin.upload_service(
                data['file'])
            messages.success(request, _('Service uploaded.'))
            return result
        except HTTPException as e:
            log.exception(e)
            redirect = reverse('horizon:murano:service_catalog:index')
            exceptions.handle(request,
                              _('Unable to upload service. '
                                'Error code: {0}'.format(e.code)),
                              redirect=redirect)


class UploadFileToService(SelfHandlingForm):
    file = forms.FileField(label=_('Murano Repository File'),
                           required=True,
                           error_messages=
                           {'required': _('There is no file to upload')})

    def __init__(self, request,
                 data_type=None,
                 full_service_name=None,
                 *args, **kwargs):
        self.data_type = data_type
        self.service_id = full_service_name
        super(UploadFileToService, self).__init__(request, *args, **kwargs)

    def handle(self, request, data):
        filename = data['file'].name
        log.debug('Uploading file to metadata repository {0} and assiging'
                  ' it to {1} service'.format(filename, self.service_id))
        try:
            result = metadataclient(request).metadata_admin.\
                upload_file_to_service(self.data_type,
                                       data['file'],
                                       filename,
                                       self.service_id)
            messages.success(request,
                             _("File '{filename}' uploaded".format(
                                 filename=filename)))
            return result
        except HTTPException as e:
            redirect = reverse('horizon:murano:service_catalog:manage_service',
                               args=(self.service_id,))
            log.exception(e)
            msg = _("Unable to upload {0} file of '{1}' type."
                    " Error code: {2}".format(filename,
                                              self.data_type,
                                              e.code))
            exceptions.handle(request, msg, redirect=redirect)

    def clean_file(self):
        file = self.cleaned_data.get('file')
        if file:
            if file._size > 5 * 1024 * 1024:
                raise forms.ValidationError(_('It is restricted to '
                                              'upload files larger than 5MB.'))
        return file


class UploadFileForm(UploadFileToService):
    supported_data_types = {
        'ui': 'UI Definition (*.yaml)',
        'workflows': 'Murano Conductor Workflow (*xml)',
        'heat': 'Heat template',
        'agent': 'Murano Agent template',
        'scripts': 'Script for agent execution'
    }

    data_type = forms.ChoiceField(label=_('File Type'),
                                  choices=(supported_data_types.items()))

    def handle(self, request, data):
        log.debug('Uploading file to metadata repository {0}'.format(data))
        filename = data['file'].name
        data_type = data['data_type']
        try:
            result = metadataclient(request).metadata_admin.\
                upload_file(data_type, data['file'], filename)
            messages.success(request,
                             _("File '{filename}' uploaded".format(
                                 filename=filename)))
            return result
        except HTTPException as e:
            redirect = reverse('horizon:murano:service_catalog:manage_files')
            log.exception(e)
            msg = _("Unable to upload {0} file of '{1}' type."
                    " Error code: {2}".format(filename,
                                              self.data_type,
                                              e.code))
            exceptions.handle(request, msg, redirect=redirect)
