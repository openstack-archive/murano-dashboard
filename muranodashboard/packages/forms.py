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
from django.core.files import uploadedfile
from django.utils.translation import ugettext_lazy as _
from django.core.urlresolvers import reverse
from horizon.forms import SelfHandlingForm
from horizon import exceptions
from horizon import messages
from metadataclient.common.exceptions import HTTPException
from muranodashboard.environments import api

log = logging.getLogger(__name__)


MAX_FILE_SIZE_SPEC = (5 * 1024 * 1024, '5', _('MB'))


def split_post_data(post):
    data, files = {}, {}
    for key, value in post.iteritems():
        if isinstance(value, uploadedfile.InMemoryUploadedFile):
            files[key] = value
        else:
            data[key] = value
    return data, files


class UploadPackageForm(SelfHandlingForm):
    package = forms.FileField(label=_('Application .zip package'),
                              required=True)
    categories = forms.ChoiceField(label=_('Application Category'))

    def __init__(self, request, **kwargs):
        super(UploadPackageForm, self).__init__(request, **kwargs)
        categories = api.muranoclient(request).packages.categories()
        self.fields['categories'].choices = [(c, c) for c in categories]

    def clean_package(self):
        package = self.cleaned_data.get('package')
        if package:
            max_size, size_in_units, unit_spec = MAX_FILE_SIZE_SPEC
            if package.size > max_size:
                msg = _('It is restricted to upload files larger than '
                        '{0}{1}.'.format(size_in_units, unit_spec))
                log.error(msg)
                raise forms.ValidationError(msg)
        return package

    def handle(self, request, data):
        log.debug('Uploading package {0}'.format(data))
        try:
            data['categories'] = [data['categories']]
            data, files = split_post_data(data)
            result = api.muranoclient(request).packages.create(data, files)
            messages.success(request, _('Package uploaded.'))
            return result
        except HTTPException:
            log.exception(_('Uploading package failed'))
            redirect = reverse('horizon:murano:packages:index')
            exceptions.handle(request,
                              _('Unable to upload package'),
                              redirect=redirect)
