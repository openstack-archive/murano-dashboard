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
from muranoclient.common.exceptions import \
    CommunicationError, HTTPInternalServerError
import re

from django.core.urlresolvers import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.contrib.formtools.wizard.views import SessionWizardView
from django.http import HttpResponseRedirect

from horizon import exceptions
from horizon import tabs
from horizon import tables
from horizon import workflows
from horizon import messages
from horizon.forms.views import ModalFormMixin

from muranodashboard.panel import api

from tables import EnvironmentsTable, ServicesTable
from workflows import CreateEnvironment, UpdateEnvironment
from tabs import ServicesTabs
from forms import WizardFormADConfiguration
from forms import WizardFormIISConfiguration
from forms import WizardFormAspNetAppConfiguration
from forms import WizardFormIISFarmConfiguration
from forms import WizardFormAspNetFarmConfiguration

LOG = logging.getLogger(__name__)


class Wizard(ModalFormMixin, SessionWizardView):
    template_name = 'create_service_wizard.html'

    def done(self, form_list, **kwargs):
        link = self.request.__dict__['META']['HTTP_REFERER']
        environment_id = re.search('murano/(\S+)', link).group(0)[7:-9]

        url = "/project/murano/%s/services" % environment_id
        step0_data = form_list[0].cleaned_data
        step1_data = form_list[1].cleaned_data

        service_type = step0_data.get('service', '')

        parameters = {'service_type': service_type}

        parameters['units'] = []
        parameters['unitNamingPattern'] = step1_data.get(
            'unit_name_template', None)

        if service_type == 'Active Directory':
            parameters['configuration'] = 'standalone'
            parameters['name'] = str(step1_data.get('dc_name', 'noname'))
            parameters['domain'] = parameters['name']  # Fix Me in orchestrator
            parameters['adminPassword'] = \
                str(step1_data.get('adm_password', ''))
            recovery_password = str(step1_data.get('recovery_password', ''))
            parameters['units'].append({'isMaster': True,
                                        'recoveryPassword': recovery_password,
                                        'location': 'west-dc'})
            dc_count = int(step1_data.get('dc_count', 1))
            for dc in range(dc_count - 1):
                parameters['units'].append({
                    'isMaster': False,
                    'recoveryPassword': recovery_password
                })

        elif service_type in ['IIS', 'ASP.NET Application',
                              'IIS Farm', 'ASP.NET Farm']:
            password = step1_data.get('adm_password', '')
            parameters['name'] = str(step1_data.get('iis_name', 'noname'))
            parameters['credentials'] = {'username': 'Administrator',
                                         'password': password}

            parameters['domain'] = str(step1_data.get('iis_domain', ''))
            password = step1_data.get('adm_password', '')
            domain = step1_data.get('iis_domain', '')
            parameters['name'] = str(step1_data.get('iis_name', 'noname'))
            parameters['domain'] = parameters['name']
            parameters['adminPassword'] = password
            parameters['domain'] = str(domain)

            if service_type == 'ASP.NET Application' \
                    or service_type == 'ASP.NET Farm':
                parameters['repository'] = \
                    step1_data.get('repository', '')
            instance_count = 1
            if service_type == 'IIS Farm' or service_type == 'ASP.NET Farm':
                instance_count = int(step1_data.get('instance_count', 1))
                parameters['loadBalancerPort'] =\
                    int(step1_data.get('lb_port', 80))

            for unit in range(instance_count):
                parameters['units'].append({})

        try:
            api.service_create(self.request, environment_id, parameters)
        except:
            msg = _('Sorry, you can\'t create service right now.'
                    ' Try again later')
            redirect = reverse("horizon:project:murano:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        else:
            message = "The %s service successfully created." % service_type
            messages.success(self.request, message)
            return HttpResponseRedirect(url)

    def get_form(self, step=None, data=None, files=None):
        form = super(Wizard, self).get_form(step, data, files)
        if data:
            self.service_type = data.get('0-service', '')
            if self.service_type == 'Active Directory':
                self.form_list['1'] = WizardFormADConfiguration
            elif self.service_type == 'IIS':
                self.form_list['1'] = WizardFormIISConfiguration
            elif self.service_type == 'ASP.NET Application':
                self.form_list['1'] = WizardFormAspNetAppConfiguration
            elif self.service_type == 'IIS Farm':
                self.form_list['1'] = WizardFormIISFarmConfiguration
            elif self.service_type == 'ASP.NET Farm':
                self.form_list['1'] = WizardFormAspNetFarmConfiguration

        return form

    def get_form_kwargs(self, step=None):
        return {'request': self.request} if step == u'1' else {}

    def get_context_data(self, form, **kwargs):
        context = super(Wizard, self).get_context_data(form=form, **kwargs)
        if self.steps.index > 0:
            context.update({'service_type': self.service_type})
        return context


class IndexView(tables.DataTableView):
    table_class = EnvironmentsTable
    template_name = 'index.html'

    def get_data(self):
        environments = []
        try:
            environments = api.environments_list(self.request)
        except CommunicationError:
            messages.error(self.request, 'Could not connect to Murano API '
                                         'Service, check connection details.')
        except HTTPInternalServerError:
            messages.error(self.request, 'Environment doesn\'t exist')
        return environments


class Services(tables.DataTableView):
    table_class = ServicesTable
    template_name = 'services.html'

    def get_context_data(self, **kwargs):
        context = super(Services, self).get_context_data(**kwargs)

        try:
            environment_name = api.get_environment_name(
                self.request,
                self.environment_id)
            context['environment_name'] = environment_name
        except:
            msg = _('Sorry, this environment does\'t exist anymore')
            redirect = reverse("horizon:project:murano:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        return context

    def get_data(self):
        services = []
        self.environment_id = self.kwargs['environment_id']
        try:
            services = api.services_list(self.request, self.environment_id)
        except:
            msg_text = 'Unable to retrieve list of services.'
            msg = _(msg_text)
            try:
                env_status = api.get_environment_status(self.request,
                                                        self.environment_id)
            except:
                exceptions.handle(self.request, ignore=False)

            else:
                if env_status == 'deploying':
                    msg = _(msg_text +
                            'This environment is deploying right now')

                exceptions.handle(self.request, msg)
        return services


class DetailServiceView(tabs.TabView):
    tab_group_class = ServicesTabs
    template_name = 'service_details.html'

    def get_context_data(self, **kwargs):
        context = super(DetailServiceView, self).get_context_data(**kwargs)
        context["service"] = self.get_data()
        context["service_name"] = self.service.name
        return context

    def get_data(self):
        if not hasattr(self, "_service"):
            service_id = self.kwargs['service_id']
            self.environment_id = self.kwargs['environment_id']
            try:
                self.service = api.service_get(self.request,
                                               self.environment_id,
                                               service_id)
            except:
                redirect = reverse('horizon:project:murano:index')
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
    template_name = 'create_dc.html'

    def get_initial(self):
        initial = super(CreateEnvironmentView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


class EditEnvironmentView(workflows.WorkflowView):
    workflow_class = UpdateEnvironment
    template_name = 'update_env.html'
    success_url = reverse_lazy("horizon:project:murano:index")

    def get_context_data(self, **kwargs):
        context = super(EditEnvironmentView, self).get_context_data(**kwargs)
        context["environment_id"] = self.kwargs['environment_id']
        return context

    def get_object(self, *args, **kwargs):
        if not hasattr(self, "_object"):
            environment_id = self.kwargs['environment_id']
            try:
                self._object =                                              \
                    api.environment_get(self.request, environment_id)
            except:
                redirect = reverse("horizon:project:murano:index")
                msg = _('Unable to retrieve environment details.')
                exceptions.handle(self.request, msg, redirect=redirect)
        return self._object

    def get_initial(self):
        initial = super(EditEnvironmentView, self).get_initial()
        initial.update({'environment_id': self.kwargs['environment_id'],
                        'name': getattr(self.get_object(), 'name', '')})
        return initial
