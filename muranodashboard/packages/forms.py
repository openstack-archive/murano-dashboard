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
from django.core.urlresolvers import reverse
from django import forms
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import forms as horizon_forms
from horizon import messages

from muranoclient.common import exceptions as exc
from muranodashboard import api


LOG = logging.getLogger(__name__)

try:
    MAX_FILE_SIZE_MB = int(getattr(settings, 'MAX_FILE_SIZE_MB', 5))
except ValueError:
    LOG.warning("MAX_FILE_SIZE_MB parameter has the incorrect value.")
    MAX_FILE_SIZE_MB = 5


class UploadPackageFileForm(forms.Form):
    package = forms.FileField(label=_('Application .zip package'))

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


class PackageParamsMixin(forms.Form):
    name = forms.CharField(label=_('Name'))
    tags = forms.CharField(label=_('Tags'),
                           required=False,
                           help_text='Provide comma-separated list of words,'
                                     ' associated with the package')
    is_public = forms.BooleanField(label=_('Public'),
                                   required=False,
                                   widget=forms.CheckboxInput)
    enabled = forms.BooleanField(label=_('Active'),
                                 required=False,
                                 widget=forms.CheckboxInput)
    description = forms.CharField(label=_('Description'),
                                  widget=forms.Textarea,
                                  required=False)

    def set_initial(self, package):
        self.fields['name'].initial = package.name
        self.fields['tags'].initial = ', '.join(package.tags)
        self.fields['is_public'].initial = package.is_public
        self.fields['enabled'].initial = package.enabled
        self.fields['description'].initial = package.description


class UpdatePackageForm(PackageParamsMixin):
    def __init__(self, *args, **kwargs):
        package = kwargs.pop('package')
        super(UpdatePackageForm, self).__init__(*args, **kwargs)

        self.set_initial(package)


class ModifyPackageForm(PackageParamsMixin, horizon_forms.SelfHandlingForm):
    def __init__(self, request, *args, **kwargs):
        super(ModifyPackageForm, self).__init__(request, *args, **kwargs)

        package = kwargs['initial']['package']
        self.set_initial(package)

        if package.type == 'Application':
            self.fields['categories'] = forms.MultipleChoiceField(
                label=_('Application Category'),
                choices=[('', 'No categories available')])
            try:
                categories = api.muranoclient(request).packages.categories()
                if categories:
                    self.fields['categories'].choices = [(c, c)
                                                         for c in categories]
                if package.categories:
                    self.fields['categories'].initial = dict(
                        (key, True) for key in package.categories)
            except (exc.HTTPException, Exception):
                msg = 'Unable to get list of categories'
                LOG.exception(msg)
                redirect = reverse('horizon:murano:packages:index')
                exceptions.handle(request,
                                  _(msg),
                                  redirect=redirect)

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


class SelectCategories(forms.Form):

    categories = forms.MultipleChoiceField(label=_('Application Category'))

    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request')
        super(SelectCategories, self).__init__(*args, **kwargs)

        try:
            categories = api.muranoclient(request).packages.categories()
            if categories:
                self.fields['categories'].choices = [(c, c)
                                                     for c in categories]
        except (exc.HTTPException, Exception):
            msg = 'Unable to get list of categories'
            LOG.exception(msg)
            redirect = reverse('horizon:murano:packages:index')
            exceptions.handle(request,
                              _(msg),
                              redirect=redirect)
