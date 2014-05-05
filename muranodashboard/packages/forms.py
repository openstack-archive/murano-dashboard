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

from django.conf import settings
from django.core.files import uploadedfile
from django.core.urlresolvers import reverse
from django import forms
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms as horizon_forms
from horizon import messages

from muranoclient.common import exceptions as exc
from muranodashboard.catalog import views
from muranodashboard.environments import api


LOG = logging.getLogger(__name__)

try:
    MAX_FILE_SIZE_MB = int(getattr(settings, 'MAX_FILE_SIZE_MB', 5))
except ValueError:
    LOG.warning("MAX_FILE_SIZE_MB parameter has the incorrect value.")
    MAX_FILE_SIZE_MB = 5


def split_post_data(post):
    data, files = {}, {}
    for key, value in post.iteritems():
        if isinstance(value, uploadedfile.InMemoryUploadedFile):
            files[key] = value
        else:
            data[key] = value
    return data, files


class UploadPackageForm(horizon_forms.SelfHandlingForm):
    package = forms.FileField(label=_('Application .zip package'),
                              required=True)
    categories = forms.MultipleChoiceField(label=_('Application Category'),
                                           required=True)

    def __init__(self, request, **kwargs):
        super(UploadPackageForm, self).__init__(request, **kwargs)
        categories = api.muranoclient(request).packages.categories()
        self.fields['categories'].choices = [(c, c) for c in categories]

    def clean_package(self):
        package = self.cleaned_data.get('package')
        if package:
            max_size_in_bytes = MAX_FILE_SIZE_MB << 20
            if package.size > max_size_in_bytes:
                msg = _('It is restricted to upload files larger than '
                        '{0} MB.').format(MAX_FILE_SIZE_MB)
                LOG.error(msg)
                raise forms.ValidationError(msg)
        return package

    def handle(self, request, data):
        LOG.debug('Uploading package {0}'.format(data))
        try:
            data, files = split_post_data(data)
            package = api.muranoclient(request).packages.create(data, files)

            @views.update_latest_apps
            def _handle(_request, app_id):
                messages.success(_request, _('Package uploaded.'))
                return package

            return _handle(request, app_id=package.id)

        except exc.HTTPException:
            LOG.exception(_('Uploading package failed'))
            redirect = reverse('horizon:murano:packages:index')
            exceptions.handle(request,
                              _('Unable to upload package'),
                              redirect=redirect)


class CheckboxInput(forms.CheckboxInput):
    def __init__(self):
        super(CheckboxInput, self).__init__(attrs={'class': 'checkbox'})

    class Media:
        css = {'all': ('muranodashboard/css/checkbox.css',)}


class ModifyPackageForm(horizon_forms.SelfHandlingForm):
    name = forms.CharField(label=_('Name'))
    categories = forms.MultipleChoiceField(label=_('Categories'))
    tags = forms.CharField(label=_('Tags'), required=False)
    is_public = forms.BooleanField(label=_('Public'),
                                   required=False,
                                   widget=CheckboxInput)
    enabled = forms.BooleanField(label=_('Active'),
                                 required=False,
                                 widget=CheckboxInput)
    description = forms.CharField(label=_('Description'),
                                  widget=forms.Textarea,
                                  required=False)

    def __init__(self, request, *args, **kwargs):
        super(ModifyPackageForm, self).__init__(request, *args, **kwargs)
        category_values = api.muranoclient(request).packages.categories()
        categories = self.fields['categories']
        categories.choices = [(c, c) for c in category_values]
        categories.initial = kwargs.get('initial', {}).get('categories')

    def handle(self, request, data):
        app_id = self.initial.get('app_id')
        LOG.debug('Updating package {0} with {1}'.format(app_id, data))
        try:
            data['tags'] = [t.strip() for t in data['tags'].split(',')]
            result = api.muranoclient(request).packages.update(app_id, data)
            messages.success(request, _('Package modified.'))
            return result
        except exc.HTTPException:
            LOG.exception(_('Modifying package failed'))
            redirect = reverse('horizon:murano:packages:index')
            exceptions.handle(request,
                              _('Unable to modify package'),
                              redirect=redirect)
