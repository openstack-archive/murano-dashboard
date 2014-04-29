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

import contextlib
import logging

from django.conf import settings
from django.contrib.messages import api as msg_api
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from openstack_dashboard.api.base import url_for
import muranoclient.client as client
from muranoclient.common.exceptions import HTTPForbidden, HTTPNotFound
from consts import STATUS_ID_READY, STATUS_ID_NEW
from muranoclient.common import exceptions as exc
from muranodashboard.environments import topology
from muranodashboard.common import utils


LOG = logging.getLogger(__name__)


def _handle_message(request, message):
    def horizon_message_already_queued(_message):
        _message = force_unicode(_message)
        if request.is_ajax():
            for tag, msg, extra in request.horizon['async_messages']:
                if _message == msg:
                    return True
        else:
            for msg in msg_api.get_messages(request):
                if msg.message == _message:
                    return True
        return False

    if horizon_message_already_queued(message):
        exceptions.handle(request, ignore=True)
    else:
        exceptions.handle(request, message=message)


@contextlib.contextmanager
def handled_exceptions(request):
    """Handles all murano-api specific exceptions."""
    try:
        yield
    except exc.CommunicationError:
        msg = _('Unable to communicate to murano-api server.')
        LOG.exception(msg)
        _handle_message(request, msg)
    except exc.Unauthorized:
        msg = _('Check Keystone configuration of murano-api server.')
        LOG.exception(msg)
        _handle_message(request, msg)
    except exc.Forbidden:
        msg = _('Operation is forbidden by murano-api server.')
        LOG.exception(msg)
        _handle_message(request, msg)


def get_endpoint(request):
    #prefer location specified in settings for dev purposes
    endpoint = getattr(settings, 'MURANO_API_URL', None)

    if not endpoint:
        try:
            endpoint = url_for(request, 'murano')
        except exceptions.ServiceCatalogException:
            endpoint = 'http://localhost:8082'
            LOG.warning('Murano API location could not be found in Service '
                        'Catalog, using default: {0}'.format(endpoint))
    return endpoint


def muranoclient(request):
    endpoint = get_endpoint(request)
    insecure = getattr(settings, 'MURANO_API_INSECURE', False)

    token_id = request.user.token.id
    LOG.debug('Murano::Client <Url: {0}, '
              'TokenId: {1}>'.format(endpoint, token_id))

    return client.Client(
        1, endpoint=endpoint, token=token_id, insecure=insecure)


def get_status_messages_for_service(request, service_id, environment_id):
    deployments = muranoclient(request).deployments. \
        list(environment_id)
    LOG.debug('Deployment::List {0}'.format(deployments))

    result = '\n'
    #TODO: Add updated time to logs
    if deployments:
        for deployment in reversed(deployments):
            reports = muranoclient(request).deployments.reports(environment_id,
                                                                deployment.id,
                                                                service_id)

            for report in reports:
                result += report.created.replace('T', ' ') + ' - ' + str(
                    report.text) + '\n'
    return result


class Session(object):
    @staticmethod
    def get_or_create(request, environment_id):
        """
        Gets id from already opened session for specified environment,
        otherwise opens new session and returns it's id

        :param request:
        :param environment_id:
        :return: Session Id
        """
        #We store opened sessions for each environment in dictionary per user
        sessions = request.session.get('sessions', {})

        if environment_id in sessions:
            id = sessions[environment_id]

        else:
            id = muranoclient(request).sessions.configure(environment_id).id

            sessions[environment_id] = id
            request.session['sessions'] = sessions
        return id

    @staticmethod
    def get_or_create_or_delete(request, environment_id):
        """
        Gets id from session in open state for specified environment, if state
        is deployed - this session will be deleted and new would be created.
        If there are no any sessions new would be created.
        Returns if of chosen or created session.

        :param request:
        :param environment_id:
        :return: Session Id
        """

        sessions = request.session.get('sessions', {})

        def create_session(request, environment_id):
            id = muranoclient(request).sessions.configure(environment_id).id
            sessions[environment_id] = id
            request.session['sessions'] = sessions
            return id

        if environment_id in sessions:
            id = sessions[environment_id]
            try:
                session_data = \
                    muranoclient(request).sessions.get(environment_id, id)
            except HTTPForbidden:
                del sessions[environment_id]
                LOG.debug("The environment is deploying by other user."
                          "Creating a new session "
                          "for the environment {0}".format(environment_id))
                return create_session(request, environment_id)
            else:
                if session_data.state == "deployed":
                    del sessions[environment_id]
                    LOG.debug("The existent session has status 'deployed'."
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
        """
        Gets id from already opened session for specified environment,
        otherwise returns None

        :param request:
        :param environment_id:
        :return: Session Id
        """
        #We store opened sessions for each environment in dictionary per user
        sessions = request.session.get('sessions', {})
        session_id = sessions[environment_id] \
            if environment_id in sessions else None
        if session_id:
            LOG.debug("Using session_id {0} for the environment {1}".format(
                session_id, environment_id))
        else:
            LOG.debug("Session for the environment {0} not found".format(
                environment_id))
        return session_id


def environments_list(request):
    environments = []
    with handled_exceptions(request):
        environments = muranoclient(request).environments.list()
    LOG.debug('Environment::List {0}'.format(environments))
    for index, env in enumerate(environments):
        environments[index].has_services = False
        environment = environment_get(request, env.id)
        for service in environment.services:
            if service:
                environments[index].has_services = True
            break
        if not environments[index].has_services:
            if environments[index].status == STATUS_ID_READY:
                environments[index].status = STATUS_ID_NEW
    return environments


def environment_create(request, parameters):
    #name is required param
    body = {'name': parameters['name']}
    env = muranoclient(request).environments.create(body)
    LOG.debug('Environment::Create {0}'.format(env))
    return env


def environment_delete(request, environment_id):
    LOG.debug('Environment::Delete <Id: {0}>'.format(environment_id))
    return muranoclient(request).environments.delete(environment_id)


def environment_get(request, environment_id):
    session_id = Session.get(request, environment_id)
    LOG.debug('Environment::Get <Id: {0}, SessionId: {1}>'.
              format(environment_id, session_id))
    env = muranoclient(request).environments.get(environment_id, session_id)
    LOG.debug('Environment::Get {0}'.format(env))
    return env


def environment_deploy(request, environment_id):
    session_id = Session.get(request, environment_id)
    LOG.debug('Session::Get <Id: {0}>'.format(session_id))
    env = muranoclient(request).sessions.deploy(environment_id, session_id)
    LOG.debug('Environment::Deploy <EnvId: {0}, SessionId: {1}>'
              ''.format(environment_id, session_id))
    return env


def environment_update(request, environment_id, name):
    return muranoclient(request).environments.update(environment_id, name)


def services_list(request, environment_id):
    def strip(msg, to=100):
        return '%s...' % msg[:to] if len(msg) > to else msg

    services = []
    # need to create new session to see services deployed be other user
    session_id = Session.get_or_create(request, environment_id)

    get_environment = muranoclient(request).environments.get
    environment = get_environment(environment_id, session_id)
    try:
        reports = muranoclient(request).environments.last_status(
            environment_id, session_id)
    except HTTPNotFound:
        reports = {}

    for service_item in environment.services:
        service_data = service_item
        service_id = service_data['?']['id']

        if service_id in reports and reports[service_id]:
            last_operation = strip(str(reports[service_id].text))
            time = reports[service_id].updated.replace('T', ' ')
        else:
            last_operation = 'Component draft created' \
                if environment.version == 0 else ''
            try:
                time = service_data['updated'].replace('T', ' ')[:-7]
            except KeyError:
                time = None

        service_data['environment_id'] = environment_id
        service_data['environment_version'] = environment.version
        service_data['operation'] = last_operation
        service_data['operation_updated'] = time
        services.append(service_data)

    LOG.debug('Service::List')
    return [utils.Bunch(**service) for service in services]


def app_id_by_fqn(request, fqn):
    apps = muranoclient(request).packages.filter(fqn=fqn)
    return apps[0].id if apps else None


def service_list_by_fqn(request, environment_id, fqn):
    services = services_list(request, environment_id)
    LOG.debug('Service::Instances::List')
    return [service for service in services if service['?']['type'] == fqn]


def service_create(request, environment_id, parameters):
    # we should be able to delete session
    # if we what add new services to this environment
    session_id = Session.get_or_create_or_delete(request, environment_id)
    LOG.debug('Service::Create {0}'.format(parameters['?']['type']))
    return muranoclient(request).services.post(environment_id,
                                               path='/',
                                               data=parameters,
                                               session_id=session_id)


def service_delete(request, environment_id, service_id):
    LOG.debug('Service::Delete <SrvId: {0}>'.format(service_id))
    session_id = Session.get_or_create_or_delete(request, environment_id)
    return muranoclient(request).services.delete(environment_id,
                                                 '/' + service_id,
                                                 session_id)


def service_get(request, environment_id, service_id):
    services = services_list(request, environment_id)
    LOG.debug("Return service detail for a specified id")
    for service in services:
        if service['?']['id'] == service_id:
            return service


def deployments_list(request, environment_id):
    LOG.debug('Deployments::List')
    deployments = muranoclient(request).deployments.list(environment_id)
    for deployment in deployments:
        if deployment.started:
            deployment.started = deployment.started.replace('T', ' ')
        if deployment.finished:
            deployment.finished = deployment.finished.replace('T', ' ')

    LOG.debug('Environment::List {0}'.format(deployments))
    return deployments


def deployment_reports(request, environment_id, deployment_id):
    LOG.debug('Deployment::Reports::List')
    reports = muranoclient(request).deployments.reports(environment_id,
                                                        deployment_id)
    LOG.debug('Deployment::Reports::List {0}'.format(reports))
    return reports


def get_deployment_start(request, environment_id, deployment_id):
    deployments = muranoclient(request).deployments.list(environment_id)
    LOG.debug('Get deployment start time')
    for deployment in deployments:
        if deployment.id == deployment_id:
            return deployment.started.replace('T', ' ')
    return None


def get_deployment_descr(request, environment_id, deployment_id):
    deployments = muranoclient(request).deployments.list(environment_id)
    LOG.debug('Get deployment description')
    for deployment in deployments:
        if deployment.id == deployment_id:
            return deployment.description
    return None


def load_environment_data(request, environment_id):
    environment = environment_get(request, environment_id)
    return topology.render_d3_data(environment)
