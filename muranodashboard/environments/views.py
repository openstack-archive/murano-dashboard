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

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django import http
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from horizon import exceptions
from horizon.forms import views
from horizon import messages
from horizon import tables
from horizon import tabs
from horizon.utils import memoized

from muranoclient.common import exceptions as exc
from muranodashboard.environments import api
from muranodashboard.environments import forms as env_forms
from muranodashboard.environments import tables as env_tables
from muranodashboard.environments import tabs as env_tabs


LOG = logging.getLogger(__name__)


class IndexView(tables.DataTableView):
    table_class = env_tables.EnvironmentsTable
    template_name = 'environments/index.html'

    def get_data(self):
        environments = []
        try:
            environments = api.environments_list(self.request)
        except exc.CommunicationError:
            exceptions.handle(self.request,
                              'Could not connect to Murano API \
                              Service, check connection details')
        except exc.HTTPInternalServerError:
            exceptions.handle(self.request,
                              'Murano API Service is not responding. \
                              Try again later')
        except exc.HTTPUnauthorized:
            exceptions.handle(self.request, ignore=True, escalate=True)

        return environments


class EnvironmentDetails(tabs.TabbedTableView):
    tab_group_class = env_tabs.EnvironmentDetailsTabs
    template_name = 'services/index.html'

    def get_context_data(self, **kwargs):
        context = super(EnvironmentDetails, self).get_context_data(**kwargs)

        try:
            self.environment_id = self.kwargs['environment_id']
            env = api.environment_get(self.request, self.environment_id)
            context['environment_name'] = env.name

        except Exception:
            msg = _("Sorry, this environment doesn't exist anymore")
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        return context


class ApplicationActions(generic.View):
    @staticmethod
    def get(request, environment_id=None, service_id=None, action_id=None):
        if api.action_allowed(request, environment_id):
            api.run_action(request, environment_id, action_id)
            service = api.service_get(request, environment_id, service_id)
            action_name = api.extract_actions_list(service).get(action_id, '-')
            component_name = getattr(service, 'name', '-')
            msg = _("Action '{0}' was scheduled for component '{1}.").format(
                action_name, component_name)
            messages.success(request, msg)
        else:
            msg = _("There is some action being run in an environment")
            messages.error(request, msg)
        url = reverse('horizon:murano:environments:services',
                      args=(environment_id,))
        return http.HttpResponseRedirect(url)


class DetailServiceView(tabs.TabView):
    tab_group_class = env_tabs.ServicesTabs
    template_name = 'services/details.html'

    def get_context_data(self, **kwargs):
        context = super(DetailServiceView, self).get_context_data(**kwargs)
        context["service"] = self.get_data()
        context["service_name"] = getattr(self.service, 'name', '-')
        env = api.environment_get(self.request, self.environment_id)
        context["environment_name"] = env.name
        return context

    def get_data(self):
        service_id = self.kwargs['service_id']
        self.environment_id = self.kwargs['environment_id']
        try:
            self.service = api.service_get(self.request,
                                           self.environment_id,
                                           service_id)
        except exc.HTTPUnauthorized:
            exceptions.handle(self.request)

        except exc.HTTPForbidden:
            redirect = reverse('horizon:murano:environments:index')
            exceptions.handle(self.request,
                              _('Unable to retrieve details for '
                                'service'),
                              redirect=redirect)
        else:
            self._service = self.service
            return self._service

    def get_tabs(self, request, *args, **kwargs):
        service = self.get_data()
        return self.tab_group_class(request, service=service, **kwargs)


class CreateEnvironmentView(views.ModalFormView):
    form_class = env_forms.CreateEnvironmentForm
    template_name = 'environments/create.html'
    context_object_name = 'environment'

    def get_success_url(self):
        env_id = self.request.session.get('env_id')
        if env_id:
            del self.request.session['env_id']
            return reverse("horizon:murano:environments:services",
                           args=[env_id])
        return reverse_lazy('horizon:murano:environments:index')


class EditEnvironmentView(views.ModalFormView):
    form_class = env_forms.EditEnvironmentView
    template_name = 'environments/update.html'
    context_object_name = 'environment'
    success_url = reverse_lazy('horizon:murano:environments:index')

    def get_context_data(self, **kwargs):
        context = super(EditEnvironmentView, self).get_context_data(**kwargs)
        env_id = getattr(self.get_object(), 'id')
        context["env_id"] = env_id
        return context

    @memoized.memoized_method
    def get_object(self):
        environment_id = self.kwargs['environment_id']
        try:
            return api.environment_get(self.request, environment_id)
        except Exception:
            redirect = reverse("horizon:murano:environments:index")
            msg = _('Unable to retrieve environment details.')
            exceptions.handle(self.request, msg, redirect=redirect)

    def get_initial(self):
        initial = super(EditEnvironmentView, self).get_initial()
        name = getattr(self.get_object(), 'name', '')
        initial.update({'environment_id': self.kwargs['environment_id'],
                        'name': name})
        return initial


class DeploymentDetailsView(tabs.TabbedTableView):
    tab_group_class = env_tabs.DeploymentDetailsTabs
    table_class = env_tables.EnvConfigTable
    template_name = 'deployments/reports.html'

    def get_context_data(self, **kwargs):
        context = super(DeploymentDetailsView, self).get_context_data(**kwargs)
        context["environment_id"] = self.environment_id
        env = api.environment_get(self.request, self.environment_id)
        context["environment_name"] = env.name
        context["deployment_start_time"] = \
            api.get_deployment_start(self.request,
                                     self.environment_id,
                                     self.deployment_id)
        return context

    def get_deployment(self):
        deployment = None
        try:
            deployment = api.get_deployment_descr(self.request,
                                                  self.environment_id,
                                                  self.deployment_id)
        except (exc.HTTPInternalServerError, exc.HTTPNotFound):
            msg = _("Deployment with id %s doesn't exist anymore")
            redirect = reverse("horizon:murano:environments:deployments")
            exceptions.handle(self.request,
                              msg % self.deployment_id,
                              redirect=redirect)
        return deployment

    def get_logs(self):
        logs = []
        try:
            logs = api.deployment_reports(self.request,
                                          self.environment_id,
                                          self.deployment_id)
        except (exc.HTTPInternalServerError, exc.HTTPNotFound):
            msg = _('Deployment with id %s doesn\'t exist anymore')
            redirect = reverse("horizon:murano:environments:deployments")
            exceptions.handle(self.request,
                              msg % self.deployment_id,
                              redirect=redirect)
        return logs

    def get_tabs(self, request, *args, **kwargs):
        self.deployment_id = self.kwargs['deployment_id']
        self.environment_id = self.kwargs['environment_id']
        deployment = self.get_deployment()
        logs = self.get_logs()

        return self.tab_group_class(request, deployment=deployment, logs=logs,
                                    **kwargs)


class JSONView(generic.View):
    @staticmethod
    def get(request, **kwargs):
        data = api.load_environment_data(request, kwargs['environment_id'])
        return http.HttpResponse(data, content_type='application/json')
