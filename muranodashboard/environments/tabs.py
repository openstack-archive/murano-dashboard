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

import collections
import json

from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from heat_dashboard.api import heat as heat_api

from horizon import exceptions
from horizon import tabs

from openstack_dashboard.api import nova as nova_api
from openstack_dashboard import policy

from muranoclient.common import exceptions as exc
from muranodashboard.common import utils
from muranodashboard.environments import api
from muranodashboard.environments import consts
from muranodashboard.environments import tables


class OverviewTab(tabs.Tab):
    name = _("Component")
    slug = "_service"
    template_name = 'services/_overview.html'

    def get_context_data(self, request):
        """Return application details.

        :param request:
        :return:
        """
        def find_stack(name, **kwargs):
            stacks, has_more, has_prev = heat_api.stacks_list(
                request, sort_dir='asc', **kwargs)
            for stack in stacks:
                if name in stack.stack_name:
                    stack_data = {'id': stack.id,
                                  'name': stack.stack_name}
                    return stack_data
            if has_more:
                return find_stack(name, marker=stacks[-1].id)
            return {}

        def get_instance_and_stack(instance_data, request):
            instance_name = instance_data['name']
            nova_openstackid = instance_data['openstackId']
            stack_name = ''
            instance_result_data = {}
            stack_result_data = {}
            instances, more = nova_api.server_list(request)

            for instance in instances:
                if nova_openstackid in instance.id:
                    instance_result_data = {'name': instance.name,
                                            'id': instance.id}
                    stack_name = instance.name.split('-' + instance_name)[0]
                    break
            # Add link to stack details page
            if stack_name:
                stack_result_data = find_stack(stack_name)
            return instance_result_data, stack_result_data

        service_data = self.tab_group.kwargs['service']

        status_name = ''
        for id, name in consts.STATUS_DISPLAY_CHOICES:
            if id == service_data['?']['status']:
                status_name = name

        detail_info = collections.OrderedDict([
            ('Name', getattr(service_data, 'name', '')),
            ('ID', service_data['?']['id']),
            ('Type', tables.get_service_type(service_data) or 'Unknown'),
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

        # TODO(efedorova): Need to determine Instance subclass
        # after it would be possible
        if hasattr(service_data,
                   'instance') and service_data['instance'] is not None:
                instance, stack = get_instance_and_stack(
                    service_data['instance'], request)
                if instance:
                    detail_info['Instance'] = instance
                if stack:
                    detail_info['Stack'] = stack

        if hasattr(service_data,
                   'instances') and service_data['instances'] is not None:
                instances_for_template = []
                stacks_for_template = []
                for instance in service_data['instances']:
                    instance, stack = get_instance_and_stack(instance, request)
                    instances_for_template.append(instance)
                    if stack:
                        stacks_for_template.append(stack)
                if instances_for_template:
                    detail_info['Instances'] = instances_for_template
                if stacks_for_template:
                    detail_info['Stacks'] = stacks_for_template

        return {'service': detail_info}


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
        for report in reports:
            report.created = utils.adjust_datestr(request, report.created)
        return {"reports": reports}


class LatestLogsTab(EnvLogsTab):
    name = _("Latest Deployment Log")

    def allowed(self, request):
        return self.data.get('reports')


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

    def allowed(self, request):
        if self.data.get('d3_data'):
            if json.loads(self.data['d3_data'])['environment']['status']:
                return True
        return False

    def get_context_data(self, request):
        context = {}
        environment_id = self.tab_group.kwargs['environment_id']
        context['environment_id'] = environment_id
        d3_data = api.load_environment_data(self.request, environment_id)
        context['d3_data'] = d3_data
        return context


class EnvironmentServicesTab(tabs.TableTab):
    name = _("Components")
    slug = "services"
    table_classes = (tables.ServicesTable,)
    template_name = "services/_service_list.html"
    preload = False

    def get_services_data(self):
        services = []
        self.environment_id = self.tab_group.kwargs['environment_id']
        ns_url = "horizon:app-catalog:environments:index"
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

    def get_context_data(self, request, **kwargs):
        context = super(EnvironmentServicesTab,
                        self).get_context_data(request, **kwargs)
        context['MURANO_USE_GLARE'] = getattr(settings, 'MURANO_USE_GLARE',
                                              False)
        return context


class DeploymentTab(tabs.TableTab):
    slug = "deployments"
    name = _("Deployment History")
    table_classes = (tables.DeploymentsTable,)
    template_name = 'horizon/common/_detail_table.html'
    preload = False

    def allowed(self, request):
        return policy.check((("murano", "list_deployments"),), request)

    def get_deployments_data(self):
        deployments = []
        self.environment_id = self.tab_group.kwargs['environment_id']
        ns_url = "horizon:app-catalog:environments:index"
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
    tabs = (EnvironmentServicesTab, EnvironmentTopologyTab,
            DeploymentTab, LatestLogsTab)
    sticky = True


class ServicesTabs(tabs.TabGroup):
    slug = "services_details"
    tabs = (OverviewTab, ServiceLogsTab)
    sticky = True


class DeploymentDetailsTabs(tabs.TabGroup):
    slug = "deployment_details"
    tabs = (EnvConfigTab, EnvLogsTab,)
    sticky = True
