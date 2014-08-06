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

from django.contrib.formtools.wizard import views as wizard_views
from django.core.files import storage
from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django import http
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon.forms import views
from horizon import messages
from horizon import tables as horizon_tables
from horizon.utils import functions as utils
from muranoclient.common import exceptions as exc

from muranodashboard import api
from muranodashboard.api import packages as pkg_api
from muranodashboard.catalog import views as catalog_views
from muranodashboard.environments import consts
from muranodashboard.packages import forms
from muranodashboard.packages import tables
LOG = logging.getLogger(__name__)


class PackageDefinitionsView(horizon_tables.DataTableView):
    table_class = tables.PackageDefinitionsTable
    template_name = 'packages/index.html'

    def has_more_data(self, table):
        return self._more

    def get_data(self):
        opts = {
            'include_disabled': True,
            'owned': True
        }
        marker = self.request.GET.get(
            tables.PackageDefinitionsTable._meta.pagination_param, None)

        packages = []
        self._more = False
        page_size = utils.get_page_size(self.request)
        with api.handled_exceptions(self.request):
            packages, self._more = pkg_api.package_list(
                self.request, marker=marker, filters=opts, paginate=True,
                page_size=page_size)

        return packages


class UploadPackageWizard(views.ModalFormMixin,
                          wizard_views.SessionWizardView):
    file_storage = storage.FileSystemStorage(location=consts.CACHE_DIR)
    template_name = 'packages/upload.html'

    def done(self, form_list, **kwargs):
        data = self.get_cleaned_data_for_step('1')
        app_id = self.storage.get_step_data('0')['package'].id

        redirect = reverse('horizon:murano:packages:index')
        try:
            data['tags'] = [t.strip() for t in data['tags'].split(',')]
            api.muranoclient(self.request).packages.update(app_id,
                                                           data)
        except (exc.HTTPException, Exception):
            LOG.exception(_('Modifying package failed'))
            exceptions.handle(self.request,
                              _('Unable to modify package'),
                              redirect=redirect)
        else:
            msg = _('Package parameters successfully updated.')
            LOG.info(msg)
            messages.success(self.request, msg)
            return http.HttpResponseRedirect(redirect)

    def process_step(self, form):
        @catalog_views.update_latest_apps
        def _report_success(request, app_id):
            messages.success(request,
                             _('Package {0} uploaded').format(pkg.name))

        step_data = self.get_form_step_data(form)
        if self.steps.current == '0':
            pkg = form.cleaned_data['package']
            try:
                data = {}
                files = {pkg.name: pkg.file}
                LOG.debug('Uploading {0} package'.format(pkg.name))
                package = api.muranoclient(self.request).packages.create(data,
                                                                         files)
                _report_success(self.request, app_id=package.id)

                step_data['package'] = package
            except (exc.HTTPException, Exception):
                LOG.exception(_('Uploading package failed'))
                redirect = reverse('horizon:murano:packages:index')
                exceptions.handle(self.request,
                                  _('Unable to modify package'),
                                  redirect=redirect)
        return step_data

    def get_form_kwargs(self, step=None):
        kwargs = {}
        if step == '1':
            package = self.storage.get_step_data('0')['package']
            kwargs.update({'request': self.request, 'package': package})
        return kwargs


class ModifyPackageView(views.ModalFormView):
    form_class = forms.ModifyPackageForm
    template_name = 'packages/modify_package.html'
    success_url = reverse_lazy('horizon:murano:packages:index')
    failure_url = reverse_lazy('horizon:murano:packages:index')

    def get_initial(self):
        app_id = self.kwargs['app_id']
        package = api.muranoclient(self.request).packages.get(app_id)
        return {
            'package': package,
            'app_id': app_id,
            'request': self.request
        }

    def get_context_data(self, **kwargs):
        context = super(ModifyPackageView, self).get_context_data(**kwargs)
        context['app_id'] = self.kwargs['app_id']
        return context
