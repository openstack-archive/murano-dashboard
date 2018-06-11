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

from django import http as django_http
from django import template
from django.template import defaultfilters
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ungettext_lazy

from horizon import exceptions
from horizon import forms
from horizon import messages
from horizon import tables
from horizon.utils import filters
from muranoclient.common import exceptions as exc
from openstack_dashboard import policy
from oslo_log import log as logging

from muranodashboard import api as api_utils
from muranodashboard.api import packages as pkg_api
from muranodashboard.catalog import views as catalog_views
from muranodashboard.common import utils as md_utils
from muranodashboard.environments import api
from muranodashboard.environments import consts
from muranodashboard.packages import consts as pkg_consts

LOG = logging.getLogger(__name__)


def _get_environment_status_and_version(request, table):
    environment_id = table.kwargs.get('environment_id')
    env = api.environment_get(request, environment_id)
    status = getattr(env, 'status', None)
    version = getattr(env, 'version', None)
    return status, version


def _check_row_actions_allowed(action, request):
    envs = action.table.data
    if not envs:
        return False
    for env in envs:
        if action.allowed(request, env):
            return True
    return False


def _environment_has_deployed_services(request, environment_id):
    deployments = api.deployments_list(request, environment_id)
    if not deployments:
        return False
    if not deployments[0].description['services']:
        return False
    return True


class AddApplication(tables.LinkAction):
    name = 'AddApplication'
    verbose_name = _('Add Component')
    icon = 'plus'

    def allowed(self, request, environment):
        status, version = _get_environment_status_and_version(request,
                                                              self.table)
        return status not in consts.NO_ACTION_ALLOWED_STATUSES

    def get_link_url(self, datum=None):
        base_url = reverse('horizon:app-catalog:catalog:switch_env',
                           args=(self.table.kwargs['environment_id'],))
        redirect_url = reverse('horizon:app-catalog:catalog:index')
        return '{0}?next={1}'.format(base_url, redirect_url)


class CreateEnvironment(tables.LinkAction):
    name = 'CreateEnvironment'
    verbose_name = _('Create Environment')
    url = 'horizon:app-catalog:environments:create_environment'
    classes = ('btn-launch', 'add_env')
    redirect_url = "horizon:app-catalog:environments:index"
    icon = 'plus'
    policy_rules = (("murano", "create_environment"),)

    def allowed(self, request, datum):
        return True if self.table.data else False

    def action(self, request, environment):
        try:
            api.environment_create(request, environment)
        except Exception as e:
            msg = (_('Unable to create environment {0}'
                     ' due to: {1}').format(environment, e))
            LOG.error(msg)
            redirect = reverse(self.redirect_url)
            exceptions.handle(request, msg, redirect=redirect)


class DeploymentHistory(tables.LinkAction):
    name = 'DeploymentHistory'
    verbose_name = _('Deployment History')
    url = 'horizon:app-catalog:environments:deployment_history'
    classes = ('deployment-history')
    redirect_url = "horizon:app-catalog:environments:index"
    icon = 'history'
    policy_rules = (("murano", "list_deployments_all_environments"),)

    def allowed(self, request, datum):
        return True


class DeleteEnvironment(policy.PolicyTargetMixin, tables.DeleteAction):
    redirect_url = "horizon:app-catalog:environments:index"
    policy_rules = (("murano", "delete_environment"),)

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Environment",
            u"Delete Environments",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Started Deleting Environment",
            u"Started Deleting Environments",
            count
        )

    def allowed(self, request, environment):
        # table action case: action allowed if any row action allowed
        if not environment:
            return _check_row_actions_allowed(self, request)

        # row action case
        return environment.status not in (consts.STATUS_ID_DEPLOYING,
                                          consts.STATUS_ID_DELETING)

    def action(self, request, environment_id):
        try:
            api.environment_delete(request, environment_id)
        except Exception as e:
            msg = (_('Unable to delete environment {0}'
                     ' due to: {1}').format(environment_id, e))
            LOG.error(msg)
            redirect = reverse(self.redirect_url)
            exceptions.handle(request, msg, redirect=redirect)


class AbandonEnvironment(tables.DeleteAction):
    help_text = _("This action cannot be undone. Any resources created by "
                  "this environment will have to be released manually.")
    name = 'abandon'
    redirect_url = "horizon:app-catalog:environments:index"
    policy_rules = (("murano", "delete_environment"),)

    def __init__(self, **kwargs):
        super(AbandonEnvironment, self).__init__(**kwargs)
        self.icon = 'stop'

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Abandon Environment",
            u"Abandon Environments",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Abandoned Environment",
            u"Abandoned Environments",
            count
        )

    def allowed(self, request, environment):
        """Limit when 'Abandon Environment' button is shown

        'Abandon Environment' button is hidden in several cases:
         * environment is new
         * app added to env, but not deploy is not started
        """

        # table action case: action allowed if any row action allowed
        if not environment:
            return _check_row_actions_allowed(self, request)

        # row action case
        status = getattr(environment, 'status', None)
        if status in [consts.STATUS_ID_NEW, consts.STATUS_ID_PENDING]:
            return False
        return True

    def action(self, request, environment_id):
        try:
            api.environment_delete(request, environment_id, True)
        except Exception as e:
            msg = (_('Unable to abandon an environment {0}'
                     ' due to: {1}').format(environment_id, e))
            LOG.error(msg)
            redirect = reverse(self.redirect_url)
            exceptions.handle(request, msg, redirect=redirect)


class DeleteService(tables.DeleteAction):

    @staticmethod
    def action_present(count):
        return ungettext_lazy(
            u"Delete Component",
            u"Delete Components",
            count
        )

    @staticmethod
    def action_past(count):
        return ungettext_lazy(
            u"Started Deleting Component",
            u"Started Deleting Components",
            count
        )

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
            redirect = reverse("horizon:app-catalog:environments:index")
            exceptions.handle(request, msg, redirect=redirect)


class DeployEnvironment(tables.BatchAction):
    name = 'deploy'
    classes = ('btn-launch',)
    icon = "play"

    @staticmethod
    def action_present_deploy(count):
        return ungettext_lazy(
            u"Deploy Environment",
            u"Deploy Environments",
            count
        )

    @staticmethod
    def action_past_deploy(count):
        return ungettext_lazy(
            u"Started deploying Environment",
            u"Started deploying Environments",
            count
        )

    @staticmethod
    def action_present_update(count):
        return ungettext_lazy(
            u"Update Environment",
            # there can be cases when some of the envs are new and some are not
            # so it is better to just leave "Deploy" for multiple envs
            u"Deploy Environments",
            count
        )

    @staticmethod
    def action_past_update(count):
        return ungettext_lazy(
            u"Updated Environment",
            u"Deployed Environments",
            count
        )

    action_present = action_present_deploy
    action_past = action_past_deploy

    def allowed(self, request, environment):
        """Limit when 'Deploy Environment' button is shown

        'Deploy environment' is shown when set of environment's services
        changed or previous deploy failed.
        If environment has already deployed services,
        button is shown as 'Update environment'
        """

        # table action case: action allowed if any row action allowed
        if not environment:
            return _check_row_actions_allowed(self, request)

        # row action case
        if _environment_has_deployed_services(request, environment.id):
            self.action_present = self.action_present_update
            self.action_past = self.action_past_update
        else:
            self.action_present = self.action_present_deploy
            self.action_past = self.action_past_deploy

        status = getattr(environment, 'status', None)
        if status in (consts.STATUS_ID_PENDING,
                      consts.STATUS_ID_DEPLOY_FAILURE):
            return True
        return False

    def action(self, request, environment_id):
        try:
            api.environment_deploy(request, environment_id)
        except Exception:
            msg = _('Unable to deploy. Try again later')
            redirect = reverse('horizon:app-catalog:environments:index')
            exceptions.handle(request, msg, redirect=redirect)


class DeployThisEnvironment(tables.Action):
    name = 'deploy_env'
    verbose_name = _('Deploy This Environment')
    requires_input = False
    classes = ('btn-launch',)
    icon = "play"

    def allowed(self, request, service):
        """Limit when 'Deploy This Environment' button is shown

        'Deploy environment' is not shown in several cases:
        * when deploy is already in progress
        * delete is in progress
        * env was just created and no apps added
        * previous deployment finished successfully
        If environment has already deployed services, button is shown
        as 'Update This Environment'
        """
        environment_id = self.table.kwargs['environment_id']
        if _environment_has_deployed_services(request, environment_id):
            self.verbose_name = _('Update This Environment')
        else:
            self.verbose_name = _('Deploy This Environment')

        status, version = _get_environment_status_and_version(request,
                                                              self.table)
        if (status in consts.NO_ACTION_ALLOWED_STATUSES or
                status == consts.STATUS_ID_READY):
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
                redirect=reverse('horizon:app-catalog:environments:index'))
        redirect_to = reverse('horizon:app-catalog:environments:services',
                              args=(environment_id,))
        return django_http.HttpResponseRedirect(bytes(redirect_to))


class ShowEnvironmentServices(tables.LinkAction):
    name = 'show'
    verbose_name = _('Manage Components')
    url = 'horizon:app-catalog:environments:services'

    def allowed(self, request, environment):
        return True


class UpdateEnvironmentRow(tables.Row):
    ajax = True

    def __init__(self, table, datum=None):
        super(UpdateEnvironmentRow, self).__init__(table, datum)
        if hasattr(datum, 'status'):
            self.attrs['status'] = datum.status

    def get_data(self, request, environment_id):
        try:
            return api.environment_get(request, environment_id)
        except exc.HTTPNotFound:
            # returning 404 to the ajax call removes the
            # row from the table on the ui
            raise django_http.Http404
        except Exception:
            # let our unified handler take care of errors here
            with api_utils.handled_exceptions(request):
                raise


class UpdateServiceRow(tables.Row):
    ajax = True

    def get_data(self, request, service_id):
        environment_id = self.table.kwargs['environment_id']
        return api.service_get(request, environment_id, service_id)


class UpdateEnvMetadata(tables.LinkAction):
    name = "update_env_metadata"
    verbose_name = _("Update Metadata")
    ajax = False
    icon = "pencil"
    attrs = {"ng-controller": "MetadataModalHelperController as modal"}

    def __init__(self, attrs=None, **kwargs):
        kwargs['preempt'] = True
        self.session_id = None
        super(UpdateEnvMetadata, self).__init__(attrs, **kwargs)

    def get_link_url(self, environment):
        target = json.dumps({
            'environment': environment.id,
            'session': self.session_id
        })
        self.attrs['ng-click'] = (
            "modal.openMetadataModal('muranoenv', %s, true)" % target)
        return "javascript:void(0);"

    def allowed(self, request, environment=None):
        return environment.status not in (consts.STATUS_ID_DEPLOYING,
                                          consts.STATUS_ID_DELETING)

    def update(self, request, datum):
        if datum:
            env_id = datum.id
            self.session_id = api.Session.get_if_available(request, env_id)


class EnvironmentsTable(tables.DataTable):
    name = md_utils.Column(
        'name',
        link='horizon:app-catalog:environments:services',
        verbose_name=_('Name'),
        form_field=forms.CharField(required=False))

    status = tables.Column('status',
                           verbose_name=_('Status'),
                           status=True,
                           status_choices=consts.STATUS_CHOICES,
                           display_choices=consts.STATUS_DISPLAY_CHOICES)

    def get_env_detail_link(self, environment):
        # NOTE: using the policy check for show_environment
        if policy.check((("murano", "show_environment"),),
                        self.request, target={"environment": environment}):
            return reverse("horizon:app-catalog:environments:services",
                           args=(environment.id,))
        return None

    def __init__(self, request, data=None, needs_form_wrapper=None, **kwargs):
        super(EnvironmentsTable,
              self).__init__(request, data=data,
                             needs_form_wrapper=needs_form_wrapper,
                             **kwargs)
        self.columns['name'].get_link_url = self.get_env_detail_link

    class Meta(object):
        name = 'environments'
        verbose_name = _('Environments')
        template = 'environments/_data_table.html'
        row_class = UpdateEnvironmentRow
        status_columns = ['status']
        no_data_message = _('NO ENVIRONMENTS')
        table_actions_menu = (AbandonEnvironment,
                              DeploymentHistory)
        table_actions = (CreateEnvironment, DeployEnvironment,
                         DeleteEnvironment)
        row_actions = (ShowEnvironmentServices, DeployEnvironment,
                       DeleteEnvironment, AbandonEnvironment,
                       UpdateEnvMetadata)


def get_service_details_link(service):
    return reverse('horizon:app-catalog:environments:service_details',
                   args=(service.environment_id, service['?']['id']))


def get_service_type(datum):
    return datum['?'].get(consts.DASHBOARD_ATTRS_KEY, {}).get('name')


class UpdateMetadata(tables.LinkAction):
    name = "update_metadata"
    verbose_name = _("Update Metadata")
    ajax = False
    icon = "pencil"
    attrs = {"ng-controller": "MetadataModalHelperController as modal"}

    def __init__(self, attrs=None, **kwargs):
        kwargs['preempt'] = True
        self.session_id = None
        super(UpdateMetadata, self).__init__(attrs, **kwargs)

    def get_link_url(self, service):
        env_id = self.table.kwargs.get('environment_id')
        comp_id = service['?']['id']
        target = json.dumps({
            'environment': env_id,
            'component': comp_id,
            'session': self.session_id,
        })
        self.attrs['ng-click'] = (
            "modal.openMetadataModal('muranoapp', %s, true)" % target)
        return "javascript:void(0);"

    def allowed(self, request, service=None):
        status, version = _get_environment_status_and_version(request,
                                                              self.table)
        return status != consts.STATUS_ID_DEPLOYING

    def update(self, request, datum):
        env_id = self.table.kwargs.get('environment_id')
        self.session_id = api.Session.get_if_available(request, env_id)


class ServicesTable(tables.DataTable):
    name = md_utils.Column(
        'name',
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
                              verbose_name=_('Last operation'),
                              filters=(defaultfilters.urlize, ))
    operation_updated = tables.Column('operation_updated',
                                      verbose_name=_('Time updated'),
                                      filters=(filters.parse_isotime,))

    def get_object_id(self, datum):
        return datum['?']['id']

    def get_apps_list(self):
        packages = []
        with api_utils.handled_exceptions(self.request):
            packages, self._more = pkg_api.package_list(
                self.request,
                filters={'type': 'Application', 'catalog': True})
        return [package.to_dict() for package in packages]

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
                verbose_name = action_datum.get('title') or name
                url = reverse('horizon:app-catalog:environments:start_action',
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

    def get_repo_url(self):
        return pkg_consts.DISPLAY_MURANO_REPO_URL

    def get_pkg_def_url(self):
        return reverse('horizon:app-catalog:packages:index')

    class Meta(object):
        name = 'services'
        verbose_name = _('Component List')
        no_data_message = _('No components')
        status_columns = ['status']
        row_class = UpdateServiceRow
        table_actions = (AddApplication, DeployThisEnvironment)
        row_actions = (DeleteService, UpdateMetadata)
        multi_select = False


class ShowDeploymentDetails(tables.LinkAction):
    name = 'show_deployment_details'
    verbose_name = _('Show Details')

    def get_link_url(self, deployment=None):
        kwargs = {'environment_id': deployment.environment_id,
                  'deployment_id': deployment.id}
        return reverse('horizon:app-catalog:environments:deployment_details',
                       kwargs=kwargs)

    def allowed(self, request, environment):
        return True


class DeploymentsTable(tables.DataTable):
    started = tables.Column('started',
                            verbose_name=_('Time Started'),
                            filters=(filters.parse_isotime,))
    finished = tables.Column('finished',
                             verbose_name=_('Time Finished'),
                             filters=(filters.parse_isotime,))

    status = tables.Column(
        'state',
        verbose_name=_('Status'),
        status=True,
        status_choices=consts.DEPLOYMENT_STATUS_CHOICES,
        display_choices=consts.DEPLOYMENT_STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = 'deployments'
        verbose_name = _('Deployments')
        row_actions = (ShowDeploymentDetails,)


class EnvConfigTable(tables.DataTable):
    name = md_utils.Column('name', verbose_name=_('Name'))
    _type = tables.Column(
        lambda datum: get_service_type(datum) or 'Unknown',
        verbose_name=_('Type'))

    def get_object_id(self, datum):
        return datum['?']['id']

    class Meta(object):
        name = 'environment_configuration'
        verbose_name = _('Deployed Components')


def get_deployment_history_reports(deployment):
    template_name = 'deployments/_cell_reports.html'
    context = {
        "reports": deployment.reports,
    }
    return template.loader.render_to_string(template_name, context)


def get_deployment_history_services(deployment):
    template_name = 'deployments/_cell_services.html'
    services = {}
    for service in deployment.description['services']:
        service_type = service['?']['type']
        if service_type.find('/') != -1:
            service_type = service_type[:service_type.find('/')]
        services[service.get('name', service['?']['name'])] = service_type
    context = {
        "services": services,
    }
    return template.loader.render_to_string(template_name, context)


class DeploymentHistoryTable(tables.DataTable):
    environment_name = tables.WrappingColumn(
        lambda d: d.description['name'],
        verbose_name=_('Environment'))
    logs = tables.Column(get_deployment_history_reports,
                         verbose_name=_('Logs (Created, Message)'))
    services = tables.Column(get_deployment_history_services,
                             verbose_name=_('Services (Name, Type)'))
    status = tables.Column(
        'state',
        verbose_name=_('Status'),
        status=True,
        status_choices=consts.DEPLOYMENT_STATUS_CHOICES,
        display_choices=consts.DEPLOYMENT_STATUS_DISPLAY_CHOICES)

    class Meta(object):
        name = 'deployment_history'
        verbose_name = _('Deployment History')
        row_actions = (ShowDeploymentDetails,)
