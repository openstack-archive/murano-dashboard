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
import bunch

from django.conf import settings
from horizon.exceptions import ServiceCatalogException
from muranoclient.common.exceptions import HTTPForbidden, HTTPNotFound
from openstack_dashboard.api.base import url_for
from muranoclient.v1.client import Client
from muranodashboard.panel.services import get_service_name
from consts import STATUS_ID_READY, STATUS_ID_NEW

log = logging.getLogger(__name__)


def get_endpoint(request):
    #prefer location specified in settings for dev purposes
    endpoint = getattr(settings, 'MURANO_API_URL', None)

    if not endpoint:
        try:
            endpoint = url_for(request, 'murano')
        except ServiceCatalogException:
            endpoint = 'http://localhost:8082'
            log.warning('Murano API location could not be found in Service '
                        'Catalog, using default: {0}'.format(endpoint))
    return endpoint


def muranoclient(request):
    endpoint = get_endpoint(request)
    insecure = getattr(settings, 'MURANO_API_INSECURE', False)

    token_id = request.user.token.id
    log.debug('Murano::Client <Url: {0}, '
              'TokenId: {1}>'.format(endpoint, token_id))

    return Client(endpoint=endpoint, token=token_id, insecure=insecure)


def get_status_messages_for_service(request, service_id, environment_id):
    deployments = muranoclient(request).deployments. \
        list(environment_id)
    log.debug('Deployment::List {0}'.format(deployments))

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
                log.debug("The environment is deploying by other user."
                          "Creating a new session "
                          "for the environment {0}".format(environment_id))
                return create_session(request, environment_id)
            else:
                if session_data.state == "deployed":
                    del sessions[environment_id]
                    log.debug("The existent session has status 'deployed'."
                              " Creating a new session "
                              "for the environment {0}".format(environment_id))
                    return create_session(request, environment_id)
        else:
            log.debug("Creating a new session")
            return create_session(request, environment_id)
        log.debug("Found active session "
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
        log.debug("Get session info")

        return sessions[environment_id] if environment_id in sessions else None


def environments_list(request):
    environments = muranoclient(request).environments.list()
    log.debug('Environment::List {0}'.format(environments))
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
    name = parameters['name']
    env = muranoclient(request).environments.create(name)
    log.debug('Environment::Create {0}'.format(env))
    return env


def environment_delete(request, environment_id):
    log.debug('Environment::Delete <Id: {0}>'.format(environment_id))
    return muranoclient(request).environments.delete(environment_id)


def environment_get(request, environment_id):
    session_id = Session.get(request, environment_id)
    log.debug('Environment::Get <Id: {0}>'.format(environment_id))
    env = muranoclient(request).environments.get(environment_id, session_id)
    log.debug('Environment::Get {0}'.format(env))
    return env


def environment_deploy(request, environment_id):
    session_id = Session.get(request, environment_id)
    log.debug('Session::Get <Id: {0}>'.format(session_id))
    env = muranoclient(request).sessions.deploy(environment_id, session_id)
    log.debug('Environment::Deploy <EnvId: {0}, SessionId: {1}>'
              ''.format(environment_id, session_id))
    return env


def environment_update(request, environment_id, name):
    return muranoclient(request).environments.update(environment_id, name)


def get_environment_name(request, environment_id):
    session_id = Session.get(request, environment_id)
    environment = muranoclient(request).environments.get(environment_id,
                                                         session_id)
    log.debug('Return environment name')
    return environment.name


def get_environment_data(request, environment_id, *args):
    """
    For given list of environment attributes return a values
    :return list
    """

    session_id = Session.get(request, environment_id)
    environment = muranoclient(request).environments.get(environment_id,
                                                         session_id)
    result = []
    for attr in args:
        result.append(getattr(environment, attr, None))
    return result


def services_list(request, environment_id):
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
        service_data['full_service_name'] = get_service_name(
            service_data['type'])

        if service_data['id'] in reports and reports[service_data['id']]:
            last_operation = str(reports[service_data['id']].text)
            time = reports[service_data['id']].updated.replace('T', ' ')
        else:
            last_operation = 'Service draft created' \
                if environment.version == 0 else ''
            time = service_data['updated'].replace('T', ' ')[:-7]

        service_data['environment_id'] = environment_id
        service_data['environment_version'] = environment.version
        service_data['operation'] = last_operation
        service_data['operation_updated'] = time
        services.append(service_data)

    log.debug('Service::List')
    return [bunch.bunchify(service) for service in services]


def service_list_by_type(request, environment_id, service_type):
    services = services_list(request, environment_id)
    log.debug('Service::Instances::List')
    return [service for service in services
            if service['type'] == service_type]


def service_create(request, environment_id, parameters):
    # we should be able to delete session
    # if we what add new services to this environment
    session_id = Session.get_or_create_or_delete(request, environment_id)
    log.debug('Service::Create {0}'.format(parameters['type']))
    return muranoclient(request).services.post(environment_id,
                                               path='/',
                                               data=parameters,
                                               session_id=session_id)


def service_delete(request, environment_id, service_id):
    log.debug('Service::Delete <SrvId: {0}>'.format(service_id))
    session_id = Session.get_or_create_or_delete(request, environment_id)
    return muranoclient(request).services.delete(environment_id,
                                                 '/' + service_id,
                                                 session_id)


def service_get(request, environment_id, service_id):
    services = services_list(request, environment_id)
    log.debug("Return service detail for a specified id")
    for service in services:
        if service.id == service_id:
            return service


def deployments_list(request, environment_id):
    log.debug('Deployments::List')
    deployments = muranoclient(request).deployments.list(environment_id)
    for deployment in deployments:
        if deployment.started:
            deployment.started = deployment.started.replace('T', ' ')
        if deployment.finished:
            deployment.finished = deployment.finished.replace('T', ' ')

    log.debug('Environment::List {0}'.format(deployments))
    return deployments


def deployment_reports(request, environment_id, deployment_id):
    log.debug('Deployment::Reports::List')
    reports = muranoclient(request).deployments.reports(environment_id,
                                                        deployment_id)
    log.debug('Deployment::Reports::List {0}'.format(reports))
    return reports


def get_deployment_start(request, environment_id, deployment_id):
    deployments = muranoclient(request).deployments.list(environment_id)
    log.debug('Get deployment start time')
    for deployment in deployments:
        if deployment.id == deployment_id:
            return deployment.started.replace('T', ' ')
    return None


def get_deployment_descr(request, environment_id, deployment_id):
    deployments = muranoclient(request).deployments.list(environment_id)
    log.debug('Get deployment description')
    for deployment in deployments:
        if deployment.id == deployment_id:
            descr = deployment.description
            if 'services' in descr:
                for service in descr['services']:
                    service['full_service_name'] = get_service_name(
                        service['type'])
            return descr
    return None
