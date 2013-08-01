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

from django.utils.translation import ugettext_lazy as _
from django.utils.datastructures import SortedDict
from horizon import tabs
from openstack_dashboard.api import nova as nova_api

from muranodashboard.panel import api
from muranodashboard.panel.tables import STATUS_DISPLAY_CHOICES, EnvConfigTable

LOG = logging.getLogger(__name__)


class OverviewTab(tabs.Tab):
    name = _("Service")
    slug = "_service"
    template_name = 'services/_overview.html'

    def get_context_data(self, request):
        """

        :param request:
        :return:
        """
        service_data = self.tab_group.kwargs['service']
        environment_id = self.tab_group.kwargs['environment_id']

        for id, name in STATUS_DISPLAY_CHOICES:
            if id == service_data.status:
                status_name = name

        detail_info = SortedDict([
            ('Name', service_data.name),
            ('ID', service_data.id),
            ('Type', service_data.full_service_name),
            ('Status', status_name), ])

        if hasattr(service_data, 'unitNamingPattern'):
            if service_data.unitNamingPattern:
                text = service_data.unitNamingPattern
                name_incrementation = True if '#' in text else False
                if name_incrementation:
                    text += '    (# transforms into index number)'
                detail_info['Hostname template'] = text

        if not service_data.domain:
            detail_info['Domain'] = 'Not in domain'
        else:
            detail_info['Domain'] = service_data.domain

        if hasattr(service_data, 'repository'):
            detail_info['Application repository'] = service_data.repository

        if hasattr(service_data, 'uri'):
            detail_info['Load Balancer URI'] = service_data.uri

        #check for deployed services so additional information can be added
        units = []
        instance_name = None
        for unit in service_data.units:
            if hasattr(unit, 'state'):
                # unit_detail = {'Name': unit.name}
                unit_detail = SortedDict()
                instance_hostname = unit.state.hostname
                if 'Hostname template' in detail_info:
                    del detail_info['Hostname template']
                unit_detail['Hostname'] = instance_hostname
                instances = nova_api.server_list(request)

                # HEAT always adds e before instance name
                instance_name = 'e' + environment_id + '.' + instance_hostname

                for instance in instances:
                    if instance._apiresource.name == instance_name:
                        unit_detail['instance'] = {
                            'id': instance._apiresource.id,
                            'name': instance_name
                        }
                        break

                if len(service_data.units) > 1:
                    units.append(unit_detail)
                else:
                    detail_info.update(unit_detail)

        return {'service': detail_info, 'units': units}


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
            line = r.created.replace('T', ' ') + ' - ' + r.text
            if r.details and request.user.is_superuser:
                line += '\n' + r.details
            lines.append(line)
        result = '\n'.join(lines)
        if not result:
            result = '\n'
        return {"reports": result}


class EnvConfigTab(tabs.TableTab):
    name = _("Configuration")
    slug = "env_config"
    table_classes = (EnvConfigTable,)
    template_name = 'horizon/common/_detail_table.html'
    preload = False

    def get_environment_configuration_data(self):
        deployment = self.tab_group.kwargs['deployment']
        return deployment.get('services')


class ServicesTabs(tabs.TabGroup):
    slug = "services_details"
    tabs = (OverviewTab, ServiceLogsTab)


class DeploymentTabs(tabs.TabGroup):
    slug = "deployment_details"
    tabs = (EnvConfigTab, EnvLogsTab,)
