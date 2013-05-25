# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import re

from django.utils.translation import ugettext_lazy as _
from horizon import messages
from horizon import tables
from muranodashboard.panel import api

LOG = logging.getLogger(__name__)


class CreateService(tables.LinkAction):
    name = 'CreateService'
    verbose_name = _('Create Service')
    url = 'horizon:project:murano:create'
    classes = ('btn-launch', 'ajax-modal')

    def allowed(self, request, datum):
        return True

    def action(self, request, service):
        api.service_create(request, service)


class CreateEnvironment(tables.LinkAction):
    name = 'CreateEnvironment'
    verbose_name = _('Create Environment')
    url = 'horizon:project:murano:create_dc'
    classes = ('btn-launch', 'ajax-modal')

    def allowed(self, request, datum):
        return True

    def action(self, request, environment):
        api.environment_create(request, environment)


class DeleteEnvironment(tables.DeleteAction):
    data_type_singular = _("Environment")
    data_type_plural = _("Environments")

    def allowed(self, request, env=None):
        return True

    def action(self, request, environment_id):
        api.environment_delete(request, environment_id)


class DeleteService(tables.DeleteAction):
    data_type_singular = _('Service')
    data_type_plural = _('Services')

    def allowed(self, request, datum):
        return True

    def action(self, request, service_id):
        api.service_delete(request, service_id)


class DeployEnvironment(tables.BatchAction):
    name = 'deploy'
    action_present = _('Deploy')
    action_past = _('Deployed')
    data_type_singular = _('Environment')
    data_type_plural = _('Environments')
    classes = 'btn-launch'

    def allowed(self, request, environment_id):
        services = api.services_list(request, environment_id)
        return len(services)

    def action(self, request, environment_id):
        api.environment_deploy(request, environment_id)


class ShowEnvironmentServices(tables.LinkAction):
    name = 'edit'
    verbose_name = _('Services')
    url = 'horizon:project:murano:services'

    def allowed(self, request, instance):
        return True


class UpdateEnvironmentRow(tables.Row):
    ajax = True

    def get_data(self, request, environment_id):
        return api.environment_get(request, environment_id)


class UpdateServiceRow(tables.Row):
    ajax = True

    def get_data(self, request, service_id):
        return api.service_get(request, service_id)


STATUS_DISPLAY_CHOICES = (
    ('draft', 'Ready to deploy'),
    ('pending', 'Wait for configuration'),
    ('inprogress', 'Deploy in progress'),
    ('finished', 'Active')
)


class EnvironmentsTable(tables.DataTable):
    STATUS_CHOICES = (
        (None, True),
        ('Ready to deploy', True),
        ('Active', True)
    )

    name = tables.Column('name',
                         link=('horizon:project:murano:services'),
                         verbose_name=_('Name'))

    status = tables.Column('status', verbose_name=_('Status'),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)

    class Meta:
        name = 'murano'
        verbose_name = _('Environments')
        row_class = UpdateEnvironmentRow
        status_columns = ['status']
        table_actions = (CreateEnvironment, DeleteEnvironment)
        row_actions = (ShowEnvironmentServices, DeleteEnvironment,
                       DeployEnvironment)


class ServicesTable(tables.DataTable):
    STATUS_CHOICES = (
        (None, True),
        ('Ready to deploy', True),
        ('Active', True)
    )

    name = tables.Column('name', verbose_name=_('Name'),
                         link=('horizon:project:murano:service_details'))

    _type = tables.Column('service_type', verbose_name=_('Type'))

    status = tables.Column('status', verbose_name=_('Status'),
                           status=True,
                           status_choices=STATUS_CHOICES,
                           display_choices=STATUS_DISPLAY_CHOICES)

    operation = tables.Column('operation', verbose_name=_('Operation'))

    class Meta:
        name = 'services'
        verbose_name = _('Services')
        row_class = UpdateServiceRow
        status_columns = ['status']
        table_actions = (CreateService, DeleteService)
        row_actions = (DeleteService,)
