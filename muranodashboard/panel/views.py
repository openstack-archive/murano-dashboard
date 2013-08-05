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
import re
import json

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
from tables import EnvironmentsTable
from tables import ServicesTable
from tables import DeploymentsTable
from tables import EnvConfigTable
from workflows import CreateEnvironment, UpdateEnvironment
from tabs import ServicesTabs, DeploymentTabs

from muranodashboard.panel import api
from muranoclient.common.exceptions import HTTPUnauthorized, \
    CommunicationError, HTTPInternalServerError, HTTPForbidden, HTTPNotFound

from consts import AD_NAME, IIS_NAME, ASP_NAME, IIS_FARM_NAME, ASP_FARM_NAME, \
    MSSQL_NAME, MSSQL_CLUSTER_NAME, SERVICE_NAME_DICT

LOG = logging.getLogger(__name__)


def get_service_type(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step('service_choice') \
        or {'service': 'none'}
    return cleaned_data.get('service')


def is_service_ad(wizard):
    return get_service_type(wizard) == AD_NAME


def is_service_iis(wizard):
    return get_service_type(wizard) == IIS_NAME


def is_service_asp(wizard):
    return get_service_type(wizard) == ASP_NAME


def is_service_iis_farm(wizard):
    return get_service_type(wizard) == IIS_FARM_NAME


def is_service_asp_farm(wizard):
    return get_service_type(wizard) == ASP_FARM_NAME


def is_service_mssql(wizard):
    return get_service_type(wizard) == MSSQL_NAME


def is_service_mssql_cluster(wizard):
    return get_service_type(wizard) == MSSQL_CLUSTER_NAME


SERVICE_CHECKER = (is_service_ad, is_service_iis,
                   is_service_asp, is_service_iis_farm,
                   is_service_asp_farm, is_service_mssql,
                   is_service_mssql_cluster)


class Wizard(ModalFormMixin, SessionWizardView):
    template_name = 'services/wizard_create.html'

    def done(self, form_list, **kwargs):
        link = self.request.__dict__['META']['HTTP_REFERER']

        environment_id = re.search('murano/(\w+)', link).group(0)[7:]
        url = reverse('horizon:project:murano:services',
                      args=(environment_id,))

        step0_data = form_list[0].cleaned_data
        step1_data = form_list[1].cleaned_data
        last_step_data = form_list[-1].cleaned_data

        service_type = step0_data.get('service', '')
        parameters = {'type': service_type}

        parameters['units'] = []
        parameters['unitNamingPattern'] = step1_data.get('unit_name_template')
        parameters['availabilityZone'] = \
            last_step_data.get('availability_zone')
        parameters['flavor'] = last_step_data.get('flavor')
        parameters['osImage'] = last_step_data.get('image')

        if service_type == AD_NAME:
            parameters['name'] = str(step1_data.get('dc_name', 'noname'))
            parameters['domain'] = parameters['name']  # Fix Me in orchestrator
            parameters['adminPassword'] = \
                str(step1_data.get('adm_password1', ''))
            recovery_password = str(step1_data.get('password_field1', ''))
            parameters['units'].append({'isMaster': True,
                                        'recoveryPassword': recovery_password})
            dc_count = int(step1_data.get('dc_count', 1))
            parameters['adminAccountName'] = step1_data.get('adm_user', '')
            for dc in range(dc_count - 1):
                parameters['units'].append({
                    'isMaster': False,
                    'recoveryPassword': recovery_password
                })

        elif service_type in [IIS_NAME, ASP_NAME,
                              IIS_FARM_NAME, ASP_FARM_NAME, MSSQL_NAME,
                              MSSQL_CLUSTER_NAME]:
            parameters['name'] = str(step1_data.get('service_name', 'noname'))
            parameters['domain'] = str(step1_data.get('domain', ''))
            parameters['adminPassword'] = step1_data.get('adm_password1', '')

            if service_type in [MSSQL_NAME, MSSQL_CLUSTER_NAME]:
                mixed_mode = step1_data.get('mixed_mode', False)
                sa_password = str(
                    step1_data.get('password_field1', ''))
                parameters['saPassword'] = sa_password
                parameters['mixedModeAuth'] = mixed_mode
                if parameters['domain'] == '':
                    parameters['domain'] = None

            if service_type == ASP_NAME or service_type == ASP_FARM_NAME:
                parameters['repository'] = step1_data.get('repository', '')

            if service_type in [IIS_FARM_NAME, ASP_FARM_NAME]:
                parameters['loadBalancerPort'] = step1_data.get('lb_port', 80)

            instance_count = 1
            if service_type in [IIS_FARM_NAME, ASP_FARM_NAME]:
                instance_count = int(step1_data.get('instance_count', 1))

            for unit in range(instance_count):
                parameters['units'].append({})

            if service_type == MSSQL_CLUSTER_NAME:
                parameters['domainAdminUserName'] =  \
                    step1_data.get('ad_user', '')
                parameters['domainAdminPassword'] =  \
                    step1_data.get('ad_password', '')

                step2_data = form_list[2].cleaned_data
                parameters['clusterName'] = step2_data.get('clusterName', '')
                parameters['clusterIP'] = str(step2_data.get('fixed_ip', ''))
                parameters['agGroupName'] = step2_data.get('agGroupName', '')
                parameters['agListenerIP'] = step2_data.get('agListenerIP', '')
                parameters['agListenerName'] = step2_data.get('agListenerName',
                                                              '')
                parameters['sqlServicePassword'] = \
                    step2_data.get('sqlServicePassword1', '')
                parameters['sqlServiceUserName'] = \
                    step2_data.get('sqlServiceUserName', '')

                step3_data = form_list[3].cleaned_data
                parameters['databases'] = step3_data.get('databases')
                form_nodes = step3_data.get('nodes')
                units = []
                if form_nodes:
                    nodes = json.loads(step3_data.get('nodes'))
                    for node in nodes:
                        unit = {}
                        unit['isMaster'] = node['is_primary']
                        unit['isSync'] = node['is_sync']
                        units.append(unit)
                parameters['units'] = units
        try:
            api.service_create(self.request, environment_id, parameters)
        except HTTPForbidden:
            msg = _('Sorry, you can\'t create service right now.'
                    'The environment is deploying.')
            redirect = reverse("horizon:project:murano:index")
            exceptions.handle(self.request, msg, redirect=redirect)
        else:
            message = "The %s service successfully created." \
                      % SERVICE_NAME_DICT[service_type]
            messages.success(self.request, message)
            return HttpResponseRedirect(url)

    def get_form_initial(self, step):
        init_dict = {}
        if step != 'service_choice':
            init_dict['request'] = self.request

        if step == 'mssql_datagrid' and self.storage.current_step_data:
            instance_count = self.storage.current_step_data.get(
                'mssql_ag_configuration-instance_count')
            if instance_count:
                init_dict['instance_count'] = int(instance_count)

        return self.initial_dict.get(step, init_dict)

    def get_context_data(self, form, **kwargs):
        context = super(Wizard, self).get_context_data(form=form, **kwargs)
        if self.steps.index > 0:
            data = self.get_cleaned_data_for_step('service_choice')
            context.update({'type': SERVICE_NAME_DICT[data['service']]})
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


class Services(tables.DataTableView):
    table_class = ServicesTable
    template_name = 'services/index.html'

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
        except HTTPForbidden:
            msg = _('Unable to retrieve list of services. This environment '
                    'is deploying or already deployed by other user.')
            exceptions.handle(self.request, msg,
                              redirect=reverse("horizon:project:murano:index"))

        except HTTPInternalServerError:
            msg = _('Environment with id %s doesn\'t exist anymore'
                    % self.environment_id)
            exceptions.handle(self.request, msg,
                              redirect=reverse("horizon:project:murano:index"))
        except HTTPUnauthorized:
            exceptions.handle(self.request)
        return services


class DetailServiceView(tabs.TabView):
    tab_group_class = ServicesTabs
    template_name = 'services/details.html'

    def get_context_data(self, **kwargs):
        context = super(DetailServiceView, self).get_context_data(**kwargs)
        context["service"] = self.get_data()
        context["service_name"] = self.service.name
        context["environment_name"] = \
            api.get_environment_name(self.request, self.environment_id)
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
    template_name = 'environments/create.html'

    def get_initial(self):
        initial = super(CreateEnvironmentView, self).get_initial()
        initial['project_id'] = self.request.user.tenant_id
        initial['user_id'] = self.request.user.id
        return initial


class EditEnvironmentView(workflows.WorkflowView):
    workflow_class = UpdateEnvironment
    template_name = 'environments/update.html'
    success_url = reverse_lazy("horizon:project:murano:index")

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
                redirect = reverse("horizon:project:murano:index")
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
        deployments = []
        self.environment_id = self.kwargs['environment_id']
        try:
            deployments = api.deployments_list(self.request,
                                               self.environment_id)

        except HTTPForbidden:
            msg = _('Unable to retrieve list of deployments')
            exceptions.handle(self.request, msg,
                              redirect=reverse("horizon:project:murano:index"))

        except HTTPInternalServerError:
            msg = _('Environment with id %s doesn\'t exist anymore'
                    % self.environment_id)
            exceptions.handle(self.request, msg,
                              redirect=reverse("horizon:project:murano:index"))
        return deployments


class DeploymentDetailsView(tabs.TabbedTableView):
    tab_group_class = DeploymentTabs
    table_class = EnvConfigTable
    template_name = 'deployments/reports.html'

    def get_context_data(self, **kwargs):
        context = super(DeploymentDetailsView, self).get_context_data(**kwargs)
        context["environment_id"] = self.environment_id
        context["environment_name"] = \
            api.get_environment_name(self.request, self.environment_id)
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
            msg = _('Deployment with id %s doesn\'t exist anymore'
                    % self.deployment_id)
            redirect = reverse("horizon:project:murano:deployments")
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
            redirect = reverse("horizon:project:murano:deployments")
            exceptions.handle(self.request, msg, redirect=redirect)
        return logs

    def get_tabs(self, request, *args, **kwargs):
        self.deployment_id = self.kwargs['deployment_id']
        self.environment_id = self.kwargs['environment_id']
        deployment = self.get_deployment()
        logs = self.get_logs()

        return self.tab_group_class(request, deployment=deployment, logs=logs,
                                    **kwargs)
