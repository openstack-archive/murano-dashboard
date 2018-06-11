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

from django import http
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from horizon import conf
from horizon import exceptions
from horizon.forms import views
from horizon import tables
from horizon import tabs

from muranoclient.common import exceptions as exc
from muranodashboard import api as api_utils
from muranodashboard.environments import api
from muranodashboard.environments import forms as env_forms
from muranodashboard.environments import tables as env_tables
from muranodashboard.environments import tabs as env_tabs


class IndexView(tables.DataTableView):
    table_class = env_tables.EnvironmentsTable
    template_name = 'environments/index.html'
    page_title = _("Environments")

    def get_data(self):
        environments = []
        try:
            environments = api.environments_list(self.request)
        except exc.CommunicationError:
            exceptions.handle(self.request,
                              'Could not connect to Murano API '
                              'Service, check connection details')
        except exc.HTTPInternalServerError:
            exceptions.handle(self.request,
                              'Murano API Service is not responding. '
                              'Try again later')
        except exc.HTTPUnauthorized:
            exceptions.handle(self.request, ignore=True, escalate=True)

        return environments


class EnvironmentDetails(tabs.TabbedTableView):
    tab_group_class = env_tabs.EnvironmentDetailsTabs
    template_name = 'services/index.html'
    page_title = '{{ environment_name }}'

    def get_context_data(self, **kwargs):
        context = super(EnvironmentDetails, self).get_context_data(**kwargs)

        try:
            self.environment_id = self.kwargs['environment_id']
            env = api.environment_get(self.request, self.environment_id)
            context['environment_name'] = env.name
        except Exception:
            msg = _("Sorry, this environment doesn't exist anymore")
            redirect = self.get_redirect_url()
            exceptions.handle(self.request, msg, redirect=redirect)
            return context
        context['tenant_id'] = self.request.session['token'].tenant['id']
        context["url"] = self.get_redirect_url()
        table = env_tables.EnvironmentsTable(self.request)
        # record the origin row_action for EnvironmentsTable Meta
        ori_row_actions = table._meta.row_actions
        # remove the duplicate 'Manage Components' and 'DeployEnvironment'
        # actions that have already in Environment Details page
        # from table.render_row_actions, so the action render to the detail
        # page will exclude those two actions.
        table._meta.row_actions = filter(
            lambda x: x.name not in ('show', 'deploy'),
            table._meta.row_actions)
        context["actions"] = table.render_row_actions(env)
        # recover the origin row_action for EnvironmentsTable Meta
        table._meta.row_actions = ori_row_actions
        context['poll_interval'] = conf.HORIZON_CONFIG['ajax_poll_interval']
        return context

    def get_tabs(self, request, *args, **kwargs):
        environment_id = self.kwargs['environment_id']
        deployments = []
        try:
            deployments = api.deployments_list(self.request,
                                               environment_id)
        except exc.HTTPException:
            msg = _('Unable to retrieve list of deployments')
            exceptions.handle(self.request,
                              msg,
                              redirect=self.get_redirect_url())

        logs = []
        if deployments:
            last_deployment = deployments[0]
            logs = api.deployment_reports(self.request,
                                          environment_id,
                                          last_deployment.id)
        return self.tab_group_class(request, logs=logs,
                                    **kwargs)

    @staticmethod
    def get_redirect_url():
        return reverse_lazy("horizon:app-catalog:environments:index")


class DetailServiceView(tabs.TabbedTableView):
    tab_group_class = env_tabs.ServicesTabs
    template_name = 'services/details.html'
    page_title = '{{ service_name }}'

    def get_context_data(self, **kwargs):
        context = super(DetailServiceView, self).get_context_data(**kwargs)
        service = self.get_data()
        context["service"] = service
        context["service_name"] = getattr(self.service, 'name', '-')
        env = api.environment_get(self.request, self.environment_id)
        context["environment_name"] = env.name
        breadcrumb = [
            (context["environment_name"],
             reverse("horizon:app-catalog:environments:services",
                     args=[self.environment_id])),
            (_('Applications'), None)]
        context["custom_breadcrumb"] = breadcrumb
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
            redirect = reverse('horizon:app-catalog:environments:index')
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
    form_id = 'create_environment_form'
    modal_header = _('Create Environment')
    template_name = 'environments/create.html'
    page_title = _('Create Environment')
    context_object_name = 'environment'
    submit_label = _('Create')
    submit_url = reverse_lazy(
        'horizon:app-catalog:environments:create_environment')

    def get_form(self, **kwargs):
        if 'next' in self.request.GET:
            self.request.session['next_url'] = self.request.GET['next']
        form_class = kwargs.get('form_class', self.get_form_class())
        return super(CreateEnvironmentView, self).get_form(form_class)

    def get_success_url(self):
        if 'next_url' in self.request.session:
            return self.request.session['next_url']
        env_id = self.request.session.get('env_id')
        if env_id:
            del self.request.session['env_id']
            return reverse("horizon:app-catalog:environments:services",
                           args=[env_id])
        return reverse_lazy('horizon:app-catalog:environments:index')


class DeploymentHistoryView(tables.DataTableView):
    table_class = env_tables.DeploymentHistoryTable
    template_name = 'environments/index.html'
    page_title = _("Deployment History")

    def get_data(self):
        deployment_history = []
        try:
            deployment_history = api.deployment_history(self.request)
        except exc.HTTPUnauthorized:
            exceptions.handle(self.request)
        except exc.HTTPForbidden:
            redirect = reverse('horizon:app-catalog:environments:services',
                               args=[self.environment_id])
            exceptions.handle(self.request,
                              _('Unable to retrieve deployment history.'),
                              redirect=redirect)
        return deployment_history


class DeploymentDetailsView(tabs.TabbedTableView):
    tab_group_class = env_tabs.DeploymentDetailsTabs
    table_class = env_tables.EnvConfigTable
    template_name = 'deployments/reports.html'
    page_title = 'Deployment at {{ deployment_start_time }}'

    def get_context_data(self, **kwargs):
        context = super(DeploymentDetailsView, self).get_context_data(**kwargs)
        context["environment_id"] = self.environment_id
        env = api.environment_get(self.request, self.environment_id)
        context["environment_name"] = env.name
        context["deployment_start_time"] = \
            api.get_deployment_start(self.request,
                                     self.environment_id,
                                     self.deployment_id)
        breadcrumb = [
            (context["environment_name"],
             reverse("horizon:app-catalog:environments:services",
                     args=[self.environment_id])),
            (_('Deployments'), None)]
        context["custom_breadcrumb"] = breadcrumb
        return context

    def get_deployment(self):
        deployment = None
        try:
            deployment = api.get_deployment_descr(self.request,
                                                  self.environment_id,
                                                  self.deployment_id)
        except (exc.HTTPInternalServerError, exc.HTTPNotFound):
            msg = _("Deployment with id %s doesn't exist anymore")
            redirect = reverse("horizon:app-catalog:environments:deployments")
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
            redirect = reverse("horizon:app-catalog:environments:deployments")
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
            url = reverse('horizon:app-catalog:environments:action_result',
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
