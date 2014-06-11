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
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from horizon import tabs

from muranoclient.common import exceptions as exc
from muranodashboard.environments import api
from muranodashboard.environments import consts
from muranodashboard.environments import tables

LOG = logging.getLogger(__name__)


class OverviewTab(tabs.Tab):
    name = _("Component")
    slug = "_service"
    template_name = 'services/_overview.html'

    def get_context_data(self, request):
        """Return application details.

        :param request:
        :return:
        """
        service_data = self.tab_group.kwargs['service']

        status_name = ''
        for id, name in consts.STATUS_DISPLAY_CHOICES:
            if id == service_data['?']['status']:
                status_name = name

        detail_info = SortedDict([
            ('Name', getattr(service_data, 'name', '')),
            ('ID', service_data['?']['id']),
            ('Type', service_data['?'][consts.DASHBOARD_ATTRS_KEY]['name']),
            ('Status', status_name), ])

        if hasattr(service_data, 'domain'):
            if not service_data.domain:
                detail_info['Domain'] = 'Not in domain'
            else:
                detail_info['Domain'] = service_data.domain

        if hasattr(service_data, 'repository'):
            detail_info['Application repository'] = service_data.repository

        if hasattr(service_data, 'uri'):
            detail_info['Load Balancer URI'] = service_data.uri

        if hasattr(service_data, 'floatingip'):
            detail_info['Floating IP'] = service_data.floatingip

        return {'service': detail_info}


class AppActionsTab(tabs.Tab):
    name = _('Actions')
    slug = '_actions'
    template_name = 'services/_actions.html'

    def get_context_data(self, request):
        data = self.tab_group.kwargs['service']
        return {'actions': api.extract_actions_list(data),
                'service_id': self.tab_group.kwargs['service_id'],
                'environment_id': self.tab_group.kwargs['environment_id']}

    def allowed(self, request):
        environment_id = self.tab_group.kwargs['environment_id']
        return api.action_allowed(request, environment_id)


class ServiceLogsTab(tabs.Tab):
    name = _("Logs")
    slug = "service_logs"
    template_name = 'services/_logs.html'
    preload = False

    def get_context_data(self, request):
        service_id = self.tab_group.kwargs['service_id']
        environment_id = self.tab_group.kwargs['environment_id']
        reports = api.get_status_messages_for_service(request, service_id,
                                                      environment_id)
        return {"reports": reports}


class EnvLogsTab(tabs.Tab):
    name = _("Logs")
    slug = "env_logs"
    template_name = 'deployments/_logs.html'
    preload = False

    def get_context_data(self, request):
        reports = self.tab_group.kwargs['logs']
        lines = []
        for r in reports:
            line = format_log(r.created.replace('T', ' ') + ' - ' + r.text,
                              r.level)
            lines.append(line)
        result = '\n'.join(lines)
        if not result:
            result = '\n'
        return {"reports": result}


class EnvConfigTab(tabs.TableTab):
    name = _("Configuration")
    slug = "env_config"
    table_classes = (tables.EnvConfigTable,)
    template_name = 'horizon/common/_detail_table.html'
    preload = False

    def get_environment_configuration_data(self):
        deployment = self.tab_group.kwargs['deployment']
        return deployment.get('services')


class EnvironmentTopologyTab(tabs.Tab):
    name = _("Topology")
    slug = "topology"
    template_name = "services/_detail_topology.html"
    preload = False

    def get_context_data(self, request):
        context = {}
        environment_id = self.tab_group.kwargs['environment_id']
        context['environment_id'] = environment_id
        d3_data = api.load_environment_data(self.request, environment_id)
        context['d3_data'] = d3_data
        return context


class EnvironmentServicesTab(tabs.TableTab):
    name = _("Components")
    slug = "serviceslist"
    table_classes = (tables.ServicesTable,)
    template_name = "services/_service_list.html"
    preload = False

    def get_services_data(self):
        services = []
        self.environment_id = self.tab_group.kwargs['environment_id']
        ns_url = "horizon:murano:environments:index"
        try:
            services = api.services_list(self.request, self.environment_id)
        except exc.HTTPForbidden:
            msg = _('Unable to retrieve list of services. This environment '
                    'is deploying or already deployed by other user.')
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))

        except (exc.HTTPInternalServerError, exc.HTTPNotFound):
            msg = _("Environment with id %s doesn't exist anymore")
            exceptions.handle(self.request,
                              msg % self.environment_id,
                              redirect=reverse(ns_url))
        except exc.HTTPUnauthorized:
            exceptions.handle(self.request)

        return services


class DeploymentTab(tabs.TableTab):
    slug = "deployments"
    name = _("Deployment History")
    table_classes = (tables.DeploymentsTable,)
    template_name = 'horizon/common/_detail_table.html'
    preload = False

    def get_deployments_data(self):
        deployments = []
        self.environment_id = self.tab_group.kwargs['environment_id']
        ns_url = "horizon:murano:environments:index"
        try:
            deployments = api.deployments_list(self.request,
                                               self.environment_id)

        except exc.HTTPForbidden:
            msg = _('Unable to retrieve list of deployments')
            exceptions.handle(self.request, msg, redirect=reverse(ns_url))

        except exc.HTTPInternalServerError:
            msg = _("Environment with id %s doesn't exist anymore")
            exceptions.handle(self.request,
                              msg % self.environment_id,
                              redirect=reverse(ns_url))
        return deployments


class EnvironmentDetailsTabs(tabs.TabGroup):
    slug = "environment_details"
    tabs = (EnvironmentServicesTab, EnvironmentTopologyTab, DeploymentTab)


class ServicesTabs(tabs.TabGroup):
    slug = "services_details"
    tabs = (OverviewTab, AppActionsTab, ServiceLogsTab)


class DeploymentDetailsTabs(tabs.TabGroup):
    slug = "deployment_details"
    tabs = (EnvConfigTab, EnvLogsTab,)


def format_log(message, level):
    if level == 'warning' or level == 'error':
        frm = "<b><span style='color:#{0}' title='{1}'>{2}</span></b>"
        return frm.format(consts.LOG_LEVEL_TO_COLOR[level],
                          consts.LOG_LEVEL_TO_TEXT[level],
                          message)
    else:
        return message
