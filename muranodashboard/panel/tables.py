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
from django.core.urlresolvers import reverse
from horizon import exceptions

from horizon import tables
from muranodashboard.panel import api

LOG = logging.getLogger(__name__)

STATUS_ID_READY = 'ready'
STATUS_ID_PENDING = 'pending'
STATUS_ID_DEPLOYING = 'deploying'

STATUS_CHOICES = (
    (None, True),
    ('Ready to configure', True),
    ('Ready', True),
    ('Configuring', False),

)

STATUS_DISPLAY_CHOICES = (
    (STATUS_ID_READY, 'Ready'),
    (STATUS_ID_DEPLOYING, 'Deploy in progress'),
    (STATUS_ID_PENDING, 'Configuring'),
    ('', 'Ready to configure'),
)


class CreateService(tables.LinkAction):
    name = 'CreateService'
    verbose_name = _('Create Service')
    url = 'horizon:project:murano:create'
    classes = ('btn-launch', 'ajax-modal')

    def allowed(self, request, environment):
        status = getattr(environment, 'status', None)
        if status not in [STATUS_ID_DEPLOYING]:
            return True
        return False

    def action(self, request, service):
        try:
            api.service_create(request, service)
        except:
            msg = _('Sorry, you can\'t create service right now')
            redirect = reverse("horizon:project:murano:index")
            exceptions.handle(request, msg, redirect=redirect)


class CreateEnvironment(tables.LinkAction):
    name = 'CreateEnvironment'
    verbose_name = _('Create Environment')
    url = 'horizon:project:murano:create_environment'
    classes = ('btn-launch', 'ajax-modal')

    def allowed(self, request, datum):
        return True

    def action(self, request, environment):
        api.environment_create(request, environment)


class DeleteEnvironment(tables.DeleteAction):
    data_type_singular = _("Environment")
    data_type_plural = _("Environments")

    def allowed(self, request, environment):
        return True

    def action(self, request, environment_id):
        try:
            api.environment_delete(request, environment_id)
        except:
            msg = _('Sorry, you can\'t delete this environment right now')
            exceptions.handle(request, msg)


class DeleteService(tables.DeleteAction):
    data_type_singular = _('Service')
    data_type_plural = _('Services')

    def allowed(self, request, environment):
        status = getattr(environment, 'status', None)
        if status not in [STATUS_ID_DEPLOYING]:
            return True
        return False

    def action(self, request, service_id):
        try:
            api.service_delete(request, service_id)
        except:
            msg = _('Sorry, you can\'t delete service right now')
            redirect = reverse("horizon:project:murano:index")
            exceptions.handle(request, msg, redirect=redirect)


class DeployEnvironment(tables.BatchAction):
    name = 'deploy'
    action_present = _('Deploy')
    action_past = _('Deployed')
    data_type_singular = _('Environment')
    data_type_plural = _('Environments')
    classes = 'btn-launch'

    def allowed(self, request, environment):
        status = getattr(environment, 'status', None)
        services = api.services_list(request, environment.id)

        if status not in [STATUS_ID_DEPLOYING, None] and services:
            return True
        return False

    def action(self, request, environment_id):
        try:
            api.environment_deploy(request, environment_id)
        except:
            msg = _('Unable to deploy. Maybe this environment \
            is already deploying by someone else. Try again later')
            redirect = reverse("horizon:project:murano:index")
            exceptions.handle(request, msg, redirect=redirect)


class ShowEnvironmentServices(tables.LinkAction):
    name = 'edit'
    verbose_name = _('Services')
    url = 'horizon:project:murano:services'

    def allowed(self, request, environment):
        status = getattr(environment, 'status', None)
        if status not in [STATUS_ID_DEPLOYING]:
            return True
        else:
            return False


class UpdateEnvironmentRow(tables.Row):
    ajax = True

    def get_data(self, request, environment_id):
        return api.environment_get(request, environment_id)


class UpdateServiceRow(tables.Row):
    ajax = True

    def get_data(self, request, service_id):
        return api.service_get(request, service_id)


class EnvironmentsTable(tables.DataTable):
    name = tables.Column('name',
                         link='horizon:project:murano:services',
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
        row_actions = (ShowEnvironmentServices, DeployEnvironment,
                       DeleteEnvironment)


class ServicesTable(tables.DataTable):
    name = tables.Column('name', verbose_name=_('Name'),
                         link='horizon:project:murano:service_details')

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
