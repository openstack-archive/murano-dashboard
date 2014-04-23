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
import copy
from functools import update_wrapper

from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.contrib.formtools.wizard.views import SessionWizardView
from django.http import HttpResponseRedirect  # noqa
from django.http import HttpResponse  # noqa
from django.views import generic
from horizon import exceptions
from horizon import tabs
from horizon import tables
from horizon import workflows
from horizon import messages
from horizon.forms import views as hz_views
from tables import EnvironmentsTable
from tables import DeploymentsTable
from tables import EnvConfigTable
from workflows import CreateEnvironment, UpdateEnvironment
from tabs import ServicesTabs, DeploymentTabs, EnvironmentDetailsTabs
from . import api
from muranoclient.common.exceptions import HTTPUnauthorized, \
    CommunicationError, HTTPInternalServerError, HTTPForbidden, HTTPNotFound
from django.utils.decorators import classonlymethod
from muranodashboard.dynamic_ui.services import get_service_name
from muranodashboard.dynamic_ui.services import get_service_field_descriptions
from muranodashboard.dynamic_ui import helpers
from muranodashboard.environments import consts
from muranodashboard import utils


LOG = logging.getLogger(__name__)


class LazyWizard(SessionWizardView):
    """The class which defers evaluation of form_list and condition_dict
    until view method is called. So, each time we load a page with a dynamic
    UI form, it will have markup/logic from the newest YAML-file definition.
    """
    @classonlymethod
    def as_view(cls, initforms, *initargs, **initkwargs):
        """
        Main entry point for a request-response process.
        """
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(u"You tried to pass in the %s method name as a"
                                u" keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError(u"%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        def view(request, *args, **kwargs):
            forms = initforms
            if hasattr(initforms, '__call__'):
                forms = initforms(request, kwargs)
            _kwargs = copy.copy(initkwargs)

            _kwargs = cls.get_initkwargs(forms, *initargs, **_kwargs)
            self = cls(**_kwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        update_wrapper(view, cls.dispatch, assigned=())
        return view


class Wizard(hz_views.ModalFormMixin, LazyWizard):
    template_name = 'services/wizard_create.html'
    do_redirect = False

    def get_prefix(self, *args, **kwargs):
        base = super(Wizard, self).get_prefix(*args, **kwargs)
        fmt = utils.BlankFormatter()
        return fmt.format('{0}_{environment_id}_{app_id}', base, **kwargs)

    def done(self, form_list, **kwargs):
        environment_id = kwargs.get('environment_id')
        url = reverse('horizon:murano:environments:services',
                      args=(environment_id,))
        app_name = get_service_name(self.request, kwargs.get('app_id'))

        service = form_list[0].service
        attributes = service.extract_attributes()
        attributes = helpers.insert_hidden_ids(attributes)

        storage = attributes.setdefault('?', {}).setdefault(
            consts.DASHBOARD_ATTRS_KEY, {})
        storage['name'] = app_name

        try:
            srv = api.service_create(self.request, environment_id, attributes)
        except HTTPForbidden:
            msg = _("Sorry, you can\'t add application right now."
                    "The environment is deploying.")
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        except Exception:
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request,
                              _("Sorry, you can't add application right now."),
                              redirect=redirect)
        else:
            message = "The '{0}' application successfully " \
                      "added to environment.".format(app_name)

            messages.success(self.request, message)

            if self._get_wizard_flag('do_redirect'):
                return HttpResponseRedirect(url)
            else:
                srv_id = getattr(srv, '?')['id']
                return self.create_hacked_response(srv_id, attributes['name'])

    def create_hacked_response(self, obj_id, obj_name):
        # copy-paste from horizon.forms.views.ModalFormView; should be done
        # that way until we move here from django Wizard to horizon workflow
        if hz_views.ADD_TO_FIELD_HEADER in self.request.META:
            field_id = self.request.META[hz_views.ADD_TO_FIELD_HEADER]
            response = HttpResponse(json.dumps([obj_id, obj_name]))
            response["X-Horizon-Add-To-Field"] = field_id
            return response
        else:
            return HttpResponse('Done')

    def get_form_initial(self, step):
        init_dict = {'request': self.request,
                     'environment_id': self.kwargs.get('environment_id')}

        return self.initial_dict.get(step, init_dict)

    def _get_wizard_param(self, key):
        param = self.kwargs.get(key)
        return param if param is not None else self.request.POST.get(key)

    def _get_wizard_flag(self, key):
        value = self._get_wizard_param(key)
        if isinstance(value, basestring):
            return value.lower() == 'true'
        else:
            return value

    def get_context_data(self, form, **kwargs):
        context = super(Wizard, self).get_context_data(form=form, **kwargs)
        app_id = self.kwargs.get('app_id')
        app = api.muranoclient(self.request).packages.get(app_id)
        context['field_descriptions'] = get_service_field_descriptions(
            self.request, app_id, self.steps.index)
        context.update({'type': app.fully_qualified_name,
                        'service_name': app.name,
                        'app_id': app_id,
                        'environment_id': self.kwargs.get('environment_id'),
                        'do_redirect': self._get_wizard_flag('do_redirect'),
                        'prefix': self.prefix,
                        })
        return context


class IndexView(tables.DataTableView):
    table_class = EnvironmentsTable
    template_name = 'environments/index.html'

    def get_data(self):
        environments = []
        try:
            environments = api.environments_list(self.request)
        except CommunicationError:
            exceptions.handle(self.request,
                              'Could not connect to Murano API \
                              Service, check connection details')
        except HTTPInternalServerError:
            exceptions.handle(self.request,
                              'Murano API Service is not responding. \
                              Try again later')
        except HTTPUnauthorized:
            exceptions.handle(self.request, ignore=True, escalate=True)

        return environments


class EnvironmentDetails(tabs.TabbedTableView):
    tab_group_class = EnvironmentDetailsTabs
    template_name = 'services/index.html'

    def get_context_data(self, **kwargs):
        context = super(EnvironmentDetails, self).get_context_data(**kwargs)

        try:
            self.environment_id = self.kwargs['environment_id']
            env = api.environment_get(self.request, self.environment_id)
            context['environment_name'] = env.name

        except:
            msg = _("Sorry, this environment doesn't exist anymore")
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        return context


class DetailServiceView(tabs.TabView):
    tab_group_class = ServicesTabs
    template_name = 'services/details.html'

    def get_context_data(self, **kwargs):
        context = super(DetailServiceView, self).get_context_data(**kwargs)
        context["service"] = self.get_data()
        context["service_name"] = self.service.name
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
        except HTTPUnauthorized:
            exceptions.handle(self.request)

        except HTTPForbidden:
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


class CreateEnvironmentView(workflows.WorkflowView):
    workflow_class = CreateEnvironment
    template_name = 'environments/create.html'

    def get_initial(self):
        initial = super(CreateEnvironmentView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


class EditEnvironmentView(workflows.WorkflowView):
    workflow_class = UpdateEnvironment
    template_name = 'environments/update.html'
    success_url = reverse_lazy("horizon:murano:environments:index")

    def get_context_data(self, **kwargs):
        context = super(EditEnvironmentView, self).get_context_data(**kwargs)
        context["environment_id"] = self.kwargs['environment_id']
        return context

    def get_object(self, *args, **kwargs):
        if not hasattr(self, "_object"):
            environment_id = self.kwargs['environment_id']
            try:
                self._object = \
                    api.environment_get(self.request, environment_id)
            except:
                redirect = reverse("horizon:murano:environments:index")
                msg = _('Unable to retrieve environment details.')
                exceptions.handle(self.request, msg, redirect=redirect)
        return self._object

    def get_initial(self):
        initial = super(EditEnvironmentView, self).get_initial()
        initial.update({'environment_id': self.kwargs['environment_id'],
                        'name': getattr(self.get_object(), 'name', '')})
        return initial


class DeploymentsView(tables.DataTableView):
    table_class = DeploymentsTable
    template_name = 'deployments/index.html'

    def get_context_data(self, **kwargs):
        context = super(DeploymentsView, self).get_context_data(**kwargs)

        try:
            env = api.environment_get(self.request, self.environment_id)
            context['environment_name'] = env.name
        except:
            msg = _("Sorry, this environment doesn't exist anymore")
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        return context

    def get_data(self):
        deployments = []
        self.environment_id = self.kwargs['environment_id']
        ns_url = "horizon:murano:environments:index"
        try:
            deployments = api.deployments_list(self.request,
                                               self.environment_id)

        except HTTPForbidden:
            msg = _('Unable to retrieve list of deployments')
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))

        except HTTPInternalServerError:
            msg = _("Environment with id %s doesn't exist anymore"
                    % self.environment_id)
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))
        return deployments


class DeploymentDetailsView(tabs.TabbedTableView):
    tab_group_class = DeploymentTabs
    table_class = EnvConfigTable
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
        except (HTTPInternalServerError, HTTPNotFound):
            msg = _("Deployment with id %s doesn't exist anymore"
                    % self.deployment_id)
            redirect = reverse("horizon:murano:environments:deployments")
            exceptions.handle(self.request, msg, redirect=redirect)
        return deployment

    def get_logs(self):
        logs = []
        try:
            logs = api.deployment_reports(self.request,
                                          self.environment_id,
                                          self.deployment_id)
        except (HTTPInternalServerError, HTTPNotFound):
            msg = _('Deployment with id %s doesn\'t exist anymore'
                    % self.deployment_id)
            redirect = reverse("horizon:murano:environments:deployments")
            exceptions.handle(self.request, msg, redirect=redirect)
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
        return HttpResponse(data, content_type='application/json')
