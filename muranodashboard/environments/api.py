# Copyright (c) 2013 Mirantis, Inc.
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

from django.utils.translation import ugettext_lazy as _

from oslo_log import log as logging
import six

from muranoclient.common import exceptions as exc
from muranodashboard import api
from muranodashboard.common import utils
from muranodashboard.environments import consts
from muranodashboard.environments import topology


LOG = logging.getLogger(__name__)


def get_status_messages_for_service(request, service_id, environment_id):
    client = api.muranoclient(request)
    deployments = client.deployments.list(environment_id)
    LOG.debug('Deployment::List {0}'.format(deployments))

    result = '\n'
    # TODO(efedorova): Add updated time to logs
    if deployments:
        for deployment in reversed(deployments):
            reports = client.deployments.reports(
                environment_id, deployment.id, service_id)

            for report in reports:
                result += report.created.replace('T', ' ') + ' - ' + \
                    report.text + '\n'
    return result


def create_session(request, environment_id):
    sessions = request.session.get('sessions', {})
    id = api.muranoclient(request).sessions.configure(environment_id).id
    sessions[environment_id] = id
    request.session['sessions'] = sessions
    return id


class Session(object):
    @staticmethod
    def get_or_create(request, environment_id):
        """Get an open session id

        Gets id from already opened session for specified environment,
        otherwise opens new session and returns it's id

        :param request:
        :param environment_id:
        :return: Session Id
        """
        # We store opened sessions for each environment in dictionary per user
        sessions = request.session.get('sessions', {})

        if environment_id in sessions:
            id = sessions[environment_id]
        else:
            id = create_session(environment_id, request)
        return id

    @staticmethod
    def get_or_create_or_delete(request, environment_id):
        """Get an open session id

        Gets id from session in open state for specified environment,
        if state is deployed - this session will be deleted and new
        would be created. If there are no any sessions new would be created.
        Returns if of chosen or created session.

        :param request:
        :param environment_id:
        :return: Session Id
        """

        sessions = request.session.get('sessions', {})
        client = api.muranoclient(request)

        if environment_id in sessions:
            id = sessions[environment_id]
            try:
                session_data = client.sessions.get(environment_id, id)
            except exc.HTTPForbidden:
                del sessions[environment_id]
                LOG.debug("The environment is being deployed by other user."
                          "Creating a new session "
                          "for the environment {0}".format(environment_id))
                return create_session(request, environment_id)
            else:
                if session_data.state in [consts.STATUS_ID_DEPLOY_FAILURE,
                                          consts.STATUS_ID_READY]:
                    del sessions[environment_id]
                    LOG.debug("The existing session has been already deployed."
                              " Creating a new session "
                              "for the environment {0}".format(environment_id))
                    return create_session(request, environment_id)
        else:
            LOG.debug("Creating a new session")
            return create_session(request, environment_id)
        LOG.debug("Found active session "
                  "for the environment {0}".format(environment_id))
        return id

    @staticmethod
    def get(request, environment_id):
        """Get an open session id

        Gets id from already opened session for specified environment,
        otherwise returns None

        :param request:
        :param environment_id:
        :return: Session Id
        """
        # We store opened sessions for each environment in dictionary per user
        sessions = request.session.get('sessions', {})
        session_id = sessions.get(environment_id, '')
        if session_id:
            LOG.debug("Using session_id {0} for the environment {1}".format(
                session_id, environment_id))
        else:
            LOG.debug("Session for the environment {0} not found".format(
                environment_id))
        return session_id

    @staticmethod
    def set(request, environment_id, session_id):
        """Set an open session id

        sets id from already opened session for specified environment.

        :param request:
        :param environment_id:
        :param session_id
        """
        # We store opened sessions for each environment in dictionary per user
        sessions = request.session.get('sessions', {})
        sessions[environment_id] = session_id
        request.session['sessions'] = sessions


def _update_env(env):
    env.has_new_services = False
    if env.services:
        for service in env.services:
            if service['?']['status'] == 'pending':
                env.has_new_services = True

    if not env.has_new_services and env.version == 0:
        if env.status == consts.STATUS_ID_READY:
            env.status = consts.STATUS_ID_NEW
    return env


def environments_list(request):
    environments = []
    client = api.muranoclient(request)
    with api.handled_exceptions(request):
        environments = client.environments.list()
    LOG.debug('Environment::List {0}'.format(environments))
    for index, env in enumerate(environments):
        environments[index] = environment_get(request, env.id)

    return environments


def environment_create(request, parameters):
    # name is required param
    body = {'name': parameters['name']}
    if 'defaultNetworks' in parameters:
        body['defaultNetworks'] = parameters['defaultNetworks']
    env = api.muranoclient(request).environments.create(body)
    LOG.debug('Environment::Create {0}'.format(env))
    return env


def environment_delete(request, environment_id, abandon=False):
    action = 'Abandon' if abandon else 'Delete'
    LOG.debug('Environment::{0} <Id : {1}>'.format(action, environment_id))
    return api.muranoclient(request).environments.delete(
        environment_id, abandon)


def environment_get(request, environment_id):
    session_id = Session.get(request, environment_id)
    LOG.debug('Environment::Get <Id: {0}, SessionId: {1}>'.
              format(environment_id, session_id))
    client = api.muranoclient(request)
    env = client.environments.get(environment_id, session_id)
    acquired = getattr(env, 'acquired_by', None)
    if acquired and acquired != session_id:
        env = client.environments.get(environment_id, acquired)
        Session.set(request, environment_id, acquired)

    env = _update_env(env)

    LOG.debug('Environment::Get {0}'.format(env))
    return env


def environment_deploy(request, environment_id):
    session_id = Session.get_or_create_or_delete(request, environment_id)
    LOG.debug('Session::Get <Id: {0}>'.format(session_id))
    env = api.muranoclient(request).sessions.deploy(environment_id, session_id)
    LOG.debug('Environment::Deploy <EnvId: {0}, SessionId: {1}>'
              ''.format(environment_id, session_id))
    return env


def environment_update(request, environment_id, name):
    return api.muranoclient(request).environments.update(environment_id, name)


def action_allowed(request, environment_id):
    env = environment_get(request, environment_id)
    status = getattr(env, 'status', None)
    return status not in ('deploying',)


def services_list(request, environment_id):
    """Get environment applications.

       This function collects data from Murano API and modifies it only for
       dashboard purposes. Those changes don't impact application
       deployment parameters.
    """
    def strip(msg, to=100):
        return u'%s...' % msg[:to] if len(msg) > to else msg

    services = []
    # need to create new session to see services deployed be other user
    session_id = Session.get(request, environment_id)

    get_environment = api.muranoclient(request).environments.get
    environment = get_environment(environment_id, session_id)
    try:
        client = api.muranoclient(request)
        reports = client.environments.last_status(environment_id, session_id)
    except exc.HTTPNotFound:
        LOG.exception(_('Could not retrieve latest status for '
                        'the {0} environment').format(environment_id))
        reports = {}

    for service_item in environment.services or []:
        service_data = service_item
        service_id = service_data['?']['id']

        if service_id in reports and reports[service_id]:
            last_operation = strip(reports[service_id].text)
            time = reports[service_id].updated
        else:
            last_operation = 'Component draft created' \
                if environment.version == 0 else ''
            try:
                time = service_data['updated'][:-7]
            except KeyError:
                time = None

        service_data['environment_id'] = environment_id
        service_data['environment_version'] = environment.version
        service_data['operation'] = last_operation
        service_data['operation_updated'] = time
        if service_data['?'].get('name'):
            service_data['name'] = service_data['?']['name']

        services.append(service_data)

    LOG.debug('Service::List')
    return [utils.Bunch(**service) for service in services]


def service_list_by_fqns(request, environment_id, fqns):
    if environment_id is None:
        return []
    services = services_list(request, environment_id)
    LOG.debug('Service::Instances::List')
    return [service for service in services if service['?']['type'] in fqns]


def service_create(request, environment_id, parameters):
    # we should be able to delete session
    # if we what add new services to this environment
    session_id = Session.get_or_create_or_delete(request, environment_id)
    LOG.debug('Service::Create {0}'.format(parameters['?']['type']))
    return api.muranoclient(request).services.post(environment_id,
                                                   path='/',
                                                   data=parameters,
                                                   session_id=session_id)


def service_delete(request, environment_id, service_id):
    LOG.debug('Service::Delete <SrvId: {0}>'.format(service_id))
    session_id = Session.get_or_create_or_delete(request, environment_id)
    return api.muranoclient(request).services.delete(environment_id,
                                                     '/' + service_id,
                                                     session_id)


def service_get(request, environment_id, service_id):
    services = services_list(request, environment_id)
    LOG.debug("Return service detail for a specified id")
    for service in services:
        if service['?']['id'] == service_id:
            return service


def extract_actions_list(service):
    actions_data = service['?'].get('_actions', {})

    def make_action_datum(action_id, _action):
        return dict(_action.items() + [('id', action_id)])

    return [make_action_datum(_id, action) for (_id, action) in
            six.iteritems(actions_data) if action.get('enabled')]


def run_action(request, environment_id, action_id):
    mc = api.muranoclient(request)
    return mc.actions.call(environment_id, action_id)


def deployments_list(request, environment_id):
    LOG.debug('Deployments::List')
    deployments = api.muranoclient(request).deployments.list(environment_id)

    LOG.debug('Environment::List {0}'.format(deployments))
    return deployments


def deployment_reports(request, environment_id, deployment_id):
    LOG.debug('Deployment::Reports::List')
    reports = api.muranoclient(request).deployments.reports(environment_id,
                                                            deployment_id)
    LOG.debug('Deployment::Reports::List {0}'.format(reports))
    return reports


def get_deployment_start(request, environment_id, deployment_id):
    deployments = api.muranoclient(request).deployments.list(environment_id)
    LOG.debug('Get deployment start time')
    for deployment in deployments:
        if deployment.id == deployment_id:
            return deployment.started.replace('T', ' ')
    return None


def get_deployment_descr(request, environment_id, deployment_id):
    deployments = api.muranoclient(request).deployments.list(environment_id)
    LOG.debug('Get deployment description')
    for deployment in deployments:
        if deployment.id == deployment_id:
            return deployment.description
    return None


def load_environment_data(request, environment_id):
    environment = environment_get(request, environment_id)
    return topology.render_d3_data(request, environment)
