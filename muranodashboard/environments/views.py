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

import base64
import json
import logging

from django.core.urlresolvers import reverse
from django.core.urlresolvers import reverse_lazy
from django import http
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from horizon import exceptions
from horizon.forms import views
from horizon import tables
from horizon import tabs
from horizon.utils import memoized

from muranoclient.common import exceptions as exc
from muranodashboard import api as api_utils
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
        context['tenant_id'] = self.request.session['token'].tenant['id']
        return context


class DetailServiceView(tabs.TabbedTableView):
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

    def get_form(self, form_class):
        if 'next' in self.request.GET:
            self.request.session['next_url'] = self.request.GET['next']
        return super(CreateEnvironmentView, self).get_form(form_class)

    def get_success_url(self):
        if 'next_url' in self.request.session:
            return self.request.session['next_url']
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


class JSONResponse(http.HttpResponse):
    def __init__(self, content=None, **kwargs):
        if content is None:
            content = {}
        kwargs.pop('content_type', None)
        super(JSONResponse, self).__init__(
            content=json.dumps(content), content_type='application/json',
            **kwargs)


class StartActionView(generic.View):
    @staticmethod
    def post(request, environment_id, action_id):
        if api.action_allowed(request, environment_id):
            task_id = api.run_action(request, environment_id, action_id)
            url = reverse('horizon:murano:environments:action_result',
                          args=(environment_id, task_id))
            return JSONResponse({'url': url})
        else:
            return JSONResponse()


class ActionResultView(generic.View):
    @staticmethod
    def is_file_returned(result):
        try:
            return result['result']['?']['type'] == 'io.murano.File'
        except (KeyError, ValueError, TypeError):
            return False

    @staticmethod
    def compose_response(result, is_file=False, is_exc=False):
        filename = 'exception.json' if is_exc else 'result.json'
        content_type = 'application/octet-stream'
        if is_file:
            filename = result.get('filename') or 'action_result_file'
            content_type = result.get('mimeType') or content_type
            content = base64.b64decode(result['base64Content'])
        else:
            content = json.dumps(result, indent=True)

        response = http.HttpResponse(content_type=content_type)
        response['Content-Disposition'] = (
            'attachment; filename=%s' % filename)
        response.write(content)
        response['Content-Length'] = str(len(response.content))
        return response

    def get(self, request, environment_id, task_id, optional):
        mc = api_utils.muranoclient(request)
        result = mc.actions.get_result(environment_id, task_id)
        if result:
            if result and optional == 'poll':
                if result['result'] is not None:
                    # Remove content from response on first successful poll
                    del result['result']
                return JSONResponse(result)
            return self.compose_response(result['result'],
                                         self.is_file_returned(result),
                                         result['isException'])
        # Polling hasn't returned content yet
        return JSONResponse()
