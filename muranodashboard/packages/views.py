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

import json
import logging
import sys

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
from muranoclient.common import utils as muranoclient_utils
from openstack_dashboard.api import glance

from muranodashboard import api
from muranodashboard.api import packages as pkg_api
from muranodashboard.catalog import views as catalog_views
from muranodashboard.common import utils as muranodashboard_utils
from muranodashboard.environments import consts
from muranodashboard.packages import consts as packages_consts
from muranodashboard.packages import forms
from muranodashboard.packages import tables

LOG = logging.getLogger(__name__)

FORMS = [('upload', forms.ImportPackageForm),
         ('modify', forms.UpdatePackageForm),
         ('add_category', forms.SelectCategories)]

BUNDLE_FORMS = [('upload', forms.ImportBundleForm), ]


def is_app(wizard):
    """Return true if uploading package is an application.
       In that case, category selection from need to be shown.
    """
    step_data = wizard.storage.get_step_data('upload')
    if step_data:
        return step_data['package'].type == 'Application'
    return False


class PackageDefinitionsView(horizon_tables.DataTableView):
    table_class = tables.PackageDefinitionsTable
    template_name = 'packages/index.html'

    _more = False
    _prev = False

    def has_more_data(self, table):
        return self._more

    def has_prev_data(self, table):
        return self._prev

    def get_data(self):
        sort_dir = self.request.GET.get('sort_dir', 'asc')
        opts = {
            'include_disabled': True,
            'sort_dir': sort_dir,
        }
        marker = self.request.GET.get(
            tables.PackageDefinitionsTable._meta.pagination_param, None)

        packages = []
        page_size = utils.get_page_size(self.request)
        with api.handled_exceptions(self.request):
            packages, extra = pkg_api.package_list(
                self.request, marker=marker, filters=opts, paginate=True,
                page_size=page_size)

            if sort_dir == 'asc':
                self._more = extra
            else:
                packages = list(reversed(packages))
                self._prev = extra

            if packages:
                if sort_dir == 'asc':
                    backward_marker = packages[0].id
                    opts['sort_dir'] = 'desc'
                else:
                    backward_marker = packages[-1].id
                    opts['sort_dir'] = 'asc'

                __, extra = pkg_api.package_list(
                    self.request, filters=opts, paginate=True,
                    marker=backward_marker, page_size=0)

                if sort_dir == 'asc':
                    self._prev = extra
                else:
                    self._more = extra

        return packages

    def get_context_data(self, **kwargs):
        context = super(PackageDefinitionsView,
                        self).get_context_data(**kwargs)
        context['tenant_id'] = self.request.session['token'].tenant['id']
        return context


class ImportBundleWizard(views.ModalFormMixin,
                         wizard_views.SessionWizardView):
    template_name = 'packages/import_bundle.html'

    def get_context_data(self, **kwargs):
        context = super(ImportBundleWizard, self).get_context_data(**kwargs)
        context['murano_repo_url'] = packages_consts.MURANO_REPO_URL
        return context

    def process_step(self, form):
        @catalog_views.update_latest_apps
        def _update_latest_apps(request, app_id):
            LOG.info('Adding {0} application to the'
                     ' latest apps list'.format(app_id))

        step_data = self.get_form_step_data(form)
        if self.steps.current == 'upload':
            import_type = form.cleaned_data['import_type']
            data = {}
            f = None
            base_url = packages_consts.MURANO_REPO_URL

            if import_type == 'by_url':
                f = form.cleaned_data['url']
            elif import_type == 'by_name':
                f = muranoclient_utils.to_url(
                    form.cleaned_data['name'],
                    path='/bundles/',
                    base_url=base_url,
                    extension='.bundle',
                )

            try:
                bundle = muranoclient_utils.Bundle.from_file(f)
            except Exception as e:
                msg = _("Bundle creation failed"
                        "Reason: {0}").format(e)
                LOG.exception(msg)
                messages.error(self.request, msg)
                raise exceptions.Http302(
                    reverse('horizon:murano:packages:index'))

            glance_client = glance.glanceclient(self.request, version='1')

            for package_spec in bundle.package_specs():

                try:
                    package = muranoclient_utils.Package.from_location(
                        package_spec['Name'],
                        version=package_spec.get('Version'),
                        url=package_spec.get('Url'),
                        base_url=base_url,
                        path=None,
                    )
                except Exception as e:
                    msg = _("Error {0} occurred while parsing package {1}")\
                        .format(e, package_spec.get('Name'))
                    messages.error(self.request, msg)
                    LOG.exception(msg)
                    continue

                reqs = package.requirements(base_url=base_url)
                for dep_name, dep_package in reqs.iteritems():
                    try:
                        imgs = muranoclient_utils.ensure_images(
                            glance_client=glance_client,
                            image_specs=dep_package.images(),
                            base_url=base_url)
                        for img in imgs:
                            msg = _("Added {0}, {1} image to glance").format(
                                img['name'], img['id'],
                            )
                            messages.success(self.request, msg)
                            LOG.info(msg)
                    except Exception as e:
                        msg = _("Error {0} occurred while installing "
                                "images for {1}").format(e, dep_name)
                        messages.error(self.request, msg)
                        LOG.exception(msg)
                    try:
                        files = {dep_name: dep_package.file()}
                        package = api.muranoclient(
                            self.request).packages.create(data, files)
                        messages.success(
                            self.request,
                            _('Package {0} uploaded').format(dep_name)
                        )
                        _update_latest_apps(
                            request=self.request, app_id=package.id)
                    except exc.HTTPConflict:
                        msg = _("Package {0} already registered.").format(
                            dep_name)
                        messages.warning(self.request, msg)
                        LOG.exception(msg)
                    except exc.HTTPException as e:
                        reason = muranodashboard_utils.parse_api_error(
                            getattr(e, 'details', ''))
                        if not reason:
                            raise
                        msg = _("Package {0} upload failed. {1}").format(
                            dep_name, reason)
                        messages.warning(self.request, msg)
                        LOG.exception(msg)
                    except Exception as e:
                        msg = _("Importing package {0} failed. "
                                "Reason: {1}").format(dep_name, e)
                        messages.warning(self.request, msg)
                        LOG.exception(msg)
                        continue

        return step_data

    def done(self, form_list, **kwargs):
        redirect = reverse('horizon:murano:packages:index')
        msg = _('Bundle successfully imported.')
        LOG.info(msg)
        messages.success(self.request, msg)
        return http.HttpResponseRedirect(redirect)


class ImportPackageWizard(views.ModalFormMixin,
                          wizard_views.SessionWizardView):
    file_storage = storage.FileSystemStorage(location=consts.CACHE_DIR)
    template_name = 'packages/upload.html'
    condition_dict = {'add_category': is_app}

    def get_context_data(self, **kwargs):
        context = super(ImportPackageWizard, self).get_context_data(**kwargs)
        context['murano_repo_url'] = packages_consts.MURANO_REPO_URL
        return context

    def done(self, form_list, **kwargs):
        data = self.get_all_cleaned_data()
        app_id = self.storage.get_step_data('upload')['package'].id
        # Remove package file from result data
        for key in ('package', 'import_type', 'url',
                    'repo_version', 'repo_name'):
            del data[key]

        dep_pkgs = self.storage.get_step_data('upload').get(
            'dependencies', [])

        redirect = reverse('horizon:murano:packages:index')
        dep_data = {'enabled': data['enabled'],
                    'is_public': data['is_public']}
        murano_client = api.muranoclient(self.request)
        for dep_pkg in dep_pkgs:
            try:
                murano_client.packages.update(dep_pkg.id, dep_data)
            except Exception as e:
                msg = _("Couldn't update package {0} parameters. Error: {1}")\
                    .format(dep_pkg.fully_qualified_name, e)
                LOG.warning(msg)
                messages.warning(self.request, msg)

        try:
            data['tags'] = [t.strip() for t in data['tags'].split(',')]
            murano_client.packages.update(app_id, data)
        except exc.HTTPForbidden:
            msg = _("You are not allowed to change"
                    " this properties of the package")
            LOG.exception(msg)
            exceptions.handle(
                self.request, msg,
                redirect=reverse('horizon:murano:packages:index'))
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
        def _update_latest_apps(request, app_id):
            LOG.info('Adding {0} application to the'
                     ' latest apps list'.format(app_id))

        step_data = self.get_form_step_data(form)
        if self.steps.current == 'upload':
            import_type = form.cleaned_data['import_type']
            data = {}
            f = None
            base_url = packages_consts.MURANO_REPO_URL

            if import_type == 'upload':
                pkg = form.cleaned_data['package']
                f = pkg.file
            elif import_type == 'by_url':
                f = form.cleaned_data['url']
            elif import_type == 'by_name':
                name = form.cleaned_data['repo_name']
                version = form.cleaned_data['repo_version']
                f = muranoclient_utils.to_url(
                    name, version=version,
                    path='/apps/',
                    extension='.zip',
                    base_url=base_url,
                )

            try:
                package = muranoclient_utils.Package.from_file(f)
                name = package.manifest['FullName']
            except Exception as e:
                msg = _("Package creation failed"
                        "Reason: {0}").format(e)
                LOG.exception(msg)
                messages.error(self.request, msg)
                raise exceptions.Http302(
                    reverse('horizon:murano:packages:index'))

            def _ensure_images(name, package):
                try:
                    imgs = muranoclient_utils.ensure_images(
                        glance_client=glance_client,
                        image_specs=package.images(),
                        base_url=base_url)
                    for img in imgs:
                        msg = _("Added {0}, {1} image to glance").format(
                            img['name'], img['id'],
                        )
                        messages.success(self.request, msg)
                        LOG.info(msg)
                except Exception as e:
                    msg = _("Error {0} occurred while installing "
                            "images for {1}").format(e, name)
                    messages.error(self.request, msg)
                    LOG.exception(msg)

            reqs = package.requirements(base_url=base_url)
            glance_client = glance.glanceclient(self.request, version='1')
            original_package = reqs.pop(name)
            step_data['dependencies'] = []
            for dep_name, dep_package in reqs.iteritems():
                _ensure_images(dep_name, dep_package)
                try:
                    files = {dep_name: dep_package.file()}
                    package = api.muranoclient(self.request).packages.create(
                        data, files)
                    messages.success(
                        self.request,
                        _('Package {0} uploaded').format(dep_name)
                    )
                    _update_latest_apps(
                        request=self.request, app_id=package.id)
                    step_data['dependencies'].append(package)
                except exc.HTTPConflict:
                    msg = _("Package {0} already registered.").format(
                        dep_name)
                    messages.warning(self.request, msg)
                    LOG.exception(msg)
                except Exception as e:
                    msg = _("Error {0} occurred while "
                            "installing package {1}").format(e, dep_name)
                    messages.error(self.request, msg)
                    LOG.exception(msg)
                    continue

            # add main packages images
            _ensure_images(name, original_package)

            # import main package itself
            try:
                files = {name: original_package.file()}
                package = api.muranoclient(self.request).packages.create(
                    data, files)
                messages.success(self.request,
                                 _('Package {0} uploaded').format(name))
                _update_latest_apps(request=self.request, app_id=package.id)

                step_data['package'] = package

            except exc.HTTPConflict:
                msg = _("Package with specified name already exists")
                LOG.exception(msg)
                exceptions.handle(
                    self.request,
                    msg,
                    redirect=reverse('horizon:murano:packages:index'))
            except exc.HTTPException as e:
                reason = muranodashboard_utils.parse_api_error(
                    getattr(e, 'details', ''))
                if not reason:
                    raise
                LOG.exception(reason)
                exceptions.handle(
                    self.request,
                    reason,
                    redirect=reverse('horizon:murano:packages:index'))

            except Exception as original_e:
                exc_info = sys.exc_info()
                reason = ''
                if hasattr(original_e, 'details'):
                    try:
                        error = json.loads(original_e.details).get('error')
                        if error:
                            reason = error.get('message')
                    except ValueError:
                        # Let horizon operate with original exception
                        raise exc_info[0], exc_info[1], exc_info[2]

                msg = _('Uploading package failed. {0}').format(reason)
                LOG.exception(msg)
                exceptions.handle(
                    self.request,
                    msg,
                    redirect=reverse('horizon:murano:packages:index'))
        return step_data

    def get_form_kwargs(self, step=None):
        kwargs = {}
        if step == 'add_category':
            kwargs.update({'request': self.request})
        if step == 'modify':
            package = self.storage.get_step_data('upload').get('package')
            kwargs.update({'package': package})
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
        }

    def get_context_data(self, **kwargs):
        context = super(ModifyPackageView, self).get_context_data(**kwargs)
        context['app_id'] = self.kwargs['app_id']
        return context
