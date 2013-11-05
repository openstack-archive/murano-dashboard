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
            if e.code == 400:
                msg = 'File already exists'
            else:
                msg = e.details
            exceptions.handle(request, _('Unable to upload service: '
                                         '{0}'.format(msg)),
                              redirect='horizon:murano:service_catalog:index')
