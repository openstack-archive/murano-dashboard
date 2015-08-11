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

from django.core.urlresolvers import reverse
from django import shortcuts
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import messages
from horizon import tables

from muranodashboard.catalog import views as catalog_views
from muranodashboard.environments import api
from muranodashboard.environments import consts

from muranodashboard import api as api_utils
from muranodashboard.api import packages as pkg_api

LOG = logging.getLogger(__name__)


def _get_environment_status_and_version(request, table):
    environment_id = table.kwargs.get('environment_id')
    env = api.environment_get(request, environment_id)
    status = getattr(env, 'status', None)
    version = getattr(env, 'version', None)
    return status, version


class AddApplication(tables.LinkAction):
    name = 'AddApplication'
    verbose_name = _('Add Component')
    icon = 'plus'

    def allowed(self, request, environment):
        status, version = _get_environment_status_and_version(request,
                                                              self.table)
        return status not in consts.NO_ACTION_ALLOWED_STATUSES

    def get_link_url(self, datum=None):
        base_url = reverse('horizon:murano:catalog:switch_env',
                           args=(self.table.kwargs['environment_id'],))
        redirect_url = reverse('horizon:murano:catalog:index')
        return '{0}?next={1}'.format(base_url, redirect_url)


class CreateEnvironment(tables.LinkAction):
    name = 'CreateEnvironment'
    verbose_name = _('Create Environment')
    url = 'horizon:murano:environments:create_environment'
    classes = ('btn-launch', 'add_env')
    redirect_url = "horizon:project:murano:environments"
    icon = 'plus'

    def allowed(self, request, datum):
        return True if self.table.data else False

    def action(self, request, environment):
        try:
            api.environment_create(request, environment)
        except Exception as e:
            msg = (_('Unable to create environment {0}'
                     ' due to: {1}').format(environment, e))
            LOG.info(msg)
            redirect = reverse(self.redirect_url)
            exceptions.handle(request, msg, redirect=redirect)


class DeleteEnvironment(tables.DeleteAction):
    data_type_singular = _('Environment')
    data_type_plural = _('Environments')
    action_past = _('Start Deleting')
    redirect_url = "horizon:project:murano:environments"

    def allowed(self, request, environment):
        if environment:
            return environment.status not in (consts.STATUS_ID_DEPLOYING,
                                              consts.STATUS_ID_DELETING)
        return True

    def action(self, request, environment_id):
        try:
            api.environment_delete(request, environment_id)
        except Exception as e:
            msg = (_('Unable to delete environment {0}'
                     ' due to: {1}').format(environment_id, e))
            LOG.info(msg)
            redirect = reverse(self.redirect_url)
            exceptions.handle(request, msg, redirect=redirect)


class EditEnvironment(tables.LinkAction):
    name = 'edit'
    verbose_name = _('Edit Environment')
    url = 'horizon:murano:environments:update_environment'
    classes = ('ajax-modal', 'btn-edit')
    icon = 'edit'

    def allowed(self, request, environment):
        """Allow edit environment only when status not deploying and deleting.
        """
        status = getattr(environment, 'status', None)
        return status not in [consts.STATUS_ID_DEPLOYING,
                              consts.STATUS_ID_DELETING]


class DeleteService(tables.DeleteAction):
    data_type_singular = _('Component')
    data_type_plural = _('Components')
    action_past = _('Start Deleting')

    def allowed(self, request, service=None):
        status, version = _get_environment_status_and_version(request,
                                                              self.table)
        return status != consts.STATUS_ID_DEPLOYING

    def action(self, request, service_id):
        try:
            environment_id = self.table.kwargs.get('environment_id')
            for service in self.table.data:
                if service['?']['id'] == service_id:
                    api.service_delete(request,
                                       environment_id,
                                       service_id)
        except Exception:
            msg = _('Sorry, you can\'t delete service right now')
            redirect = reverse("horizon:murano:environments:index")
            exceptions.handle(request, msg, redirect=redirect)


class DeployEnvironment(tables.BatchAction):
    name = 'deploy'
    action_present = _('Deploy')
    action_past = _('Deployed')
    data_type_singular = _('Environment')
    data_type_plural = _('Environment')
    classes = ('btn-launch',)

    def allowed(self, request, environment):
        status = getattr(environment, 'status', None)
        if not environment.has_new_services:
            return False
        if status in consts.NO_ACTION_ALLOWED_STATUSES:
            return False
        return True

    def action(self, request, environment_id):
        try:
            api.environment_deploy(request, environment_id)
        except Exception:
            msg = _('Unable to deploy. Try again later')
            redirect = reverse('horizon:murano:environments:index')
            exceptions.handle(request, msg, redirect=redirect)


class DeployThisEnvironment(tables.Action):
    name = 'deploy_env'
    verbose_name = _('Deploy This Environment')
    requires_input = False
    classes = ('btn-launch',)

    def allowed(self, request, service):
        status, version = _get_environment_status_and_version(request,
                                                              self.table)
        if (status in consts.NO_ACTION_ALLOWED_STATUSES
                or status == consts.STATUS_ID_READY):
            return False

        apps = self.table.data
        if version == 0 and not apps:
            return False
        return True

    def single(self, data_table, request, service_id):
        environment_id = data_table.kwargs['environment_id']
        try:
            api.environment_deploy(request, environment_id)
            messages.success(request, _('Deploy started'))
        except Exception:
            msg = _('Unable to deploy. Try again later')
            exceptions.handle(
                request, msg,
                redirect=reverse('horizon:murano:environments:index'))
        return shortcuts.redirect(
            reverse('horizon:murano:environments:services',
                    args=(environment_id,)))


class ShowEnvironmentServices(tables.LinkAction):
    name = 'show'
    verbose_name = _('Manage Components')
    url = 'horizon:murano:environments:services'

    def allowed(self, request, environment):
        return True


class UpdateEnvironmentRow(tables.Row):
    ajax = True

    def get_data(self, request, environment_id):
        return api.environment_get(request, environment_id)


class UpdateServiceRow(tables.Row):
    ajax = True

    def get_data(self, request, service_id):
        environment_id = self.table.kwargs['environment_id']
        return api.service_get(request, environment_id, service_id)


class EnvironmentsTable(tables.DataTable):
    name = tables.Column('name',
                         link='horizon:murano:environments:services',
                         verbose_name=_('Name'))

    status = tables.Column('status',
                           verbose_name=_('Status'),
                           status=True,
                           status_choices=consts.STATUS_CHOICES,
                           display_choices=consts.STATUS_DISPLAY_CHOICES)

    class Meta:
        name = 'murano'
        verbose_name = _('Environments')
        template = 'environments/_data_table.html'
        row_class = UpdateEnvironmentRow
        status_columns = ['status']
        no_data_message = _('NO ENVIRONMENTS')
        table_actions = (CreateEnvironment,)
        row_actions = (ShowEnvironmentServices, DeployEnvironment,
                       EditEnvironment, DeleteEnvironment)
        multi_select = False


def get_service_details_link(service):
    return reverse('horizon:murano:environments:service_details',
                   args=(service.environment_id, service['?']['id']))


def get_service_type(datum):
    return datum['?'].get(consts.DASHBOARD_ATTRS_KEY, {}).get('name')


class ServicesTable(tables.DataTable):
    name = tables.Column('name',
                         verbose_name=_('Name'),
                         link=get_service_details_link)

    _type = tables.Column(get_service_type,
                          verbose_name=_('Type'))

    status = tables.Column(lambda datum: datum['?'].get('status'),
                           verbose_name=_('Status'),
                           status=True,
                           status_choices=consts.STATUS_CHOICES,
                           display_choices=consts.STATUS_DISPLAY_CHOICES)
    operation = tables.Column('operation',
                              verbose_name=_('Last operation'))
    operation_updated = tables.Column('operation_updated',
                                      verbose_name=_('Time updated'))

    def get_object_id(self, datum):
        return datum['?']['id']

    def get_apps_list(self):
        packages = []
        with api_utils.handled_exceptions(self.request):
            packages, self._more = pkg_api.package_list(
                self.request,
                filters={'type': 'Application', 'catalog': True})
        return json.dumps([package.to_dict() for package in packages])

    def actions_allowed(self):
        status, version = _get_environment_status_and_version(
            self.request, self)
        return status not in consts.NO_ACTION_ALLOWED_STATUSES

    def get_categories_list(self):
        return catalog_views.get_categories_list(self.request)

    def get_row_actions(self, datum):
        actions = super(ServicesTable, self).get_row_actions(datum)
        environment_id = self.kwargs['environment_id']
        app_actions = []
        for action_datum in api.extract_actions_list(datum):
            _classes = ('murano_action',)

            class CustomAction(tables.LinkAction):
                name = action_datum['name']
                verbose_name = action_datum['name']
                url = reverse('horizon:murano:environments:start_action',
                              args=(environment_id, action_datum['id']))
                classes = _classes
                table = self

                def allowed(self, request, datum):
                    status, version = _get_environment_status_and_version(
                        request, self.table)
                    if status in consts.NO_ACTION_ALLOWED_STATUSES:
                        return False
                    return True

            bound_action = CustomAction()
            if not bound_action.allowed(self.request, datum):
                continue
            bound_action.datum = datum
            if issubclass(bound_action.__class__, tables.LinkAction):
                bound_action.bound_url = bound_action.get_link_url(datum)
            app_actions.append(bound_action)
        if app_actions:
            # Show native actions first (such as "Delete Component") and
            # then add sorted application actions
            actions.extend(sorted(app_actions, key=lambda x: x.name))
        return actions

    class Meta:
        name = 'services'
        verbose_name = _('Component List')
        template = 'services/_data_table.html'
        no_data_message = _('No components')
        status_columns = ['status']
        row_class = UpdateServiceRow
        table_actions = (AddApplication, DeployThisEnvironment)
        row_actions = (DeleteService,)
        multi_select = False


class ShowDeploymentDetails(tables.LinkAction):
    name = 'show_deployment_details'
    verbose_name = _('Show Details')

    def get_link_url(self, deployment=None):
        kwargs = {'environment_id': deployment.environment_id,
                  'deployment_id': deployment.id}
        return reverse('horizon:murano:environments:deployment_details',
                       kwargs=kwargs)

    def allowed(self, request, environment):
        return True


class DeploymentsTable(tables.DataTable):
    started = tables.Column('started',
                            verbose_name=_('Time Started'))
    finished = tables.Column('finished',
                             verbose_name=_('Time Finished'))

    status = tables.Column(
        'state',
        verbose_name=_('Status'),
        status=True,
        display_choices=consts.DEPLOYMENT_STATUS_DISPLAY_CHOICES)

    class Meta:
        name = 'deployments'
        verbose_name = _('Deployments')
        template = 'common/_data_table.html'
        row_actions = (ShowDeploymentDetails,)


class EnvConfigTable(tables.DataTable):
    name = tables.Column('name',
                         verbose_name=_('Name'))
    _type = tables.Column(
        lambda datum: get_service_type(datum) or 'Unknown',
        verbose_name=_('Type'))

    def get_object_id(self, datum):
        return datum['?']['id']

    class Meta:
        name = 'environment_configuration'
        verbose_name = _('Deployed Components')
        template = 'common/_data_table.html'
