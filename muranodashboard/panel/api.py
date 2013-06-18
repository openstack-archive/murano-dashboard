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

from openstack_dashboard.api.base import url_for
from muranodashboard import settings
from muranoclient.v1.client import Client

log = logging.getLogger(__name__)


def muranoclient(request):
    url = getattr(settings, 'MURANO_API_URL')
    if not url:
        url = url_for(request, 'murano')

    token_id = request.user.token.token['id']
    log.debug('Murano::Client <Url: {0}, TokenId: {1}>'.format(url, token_id))

    return Client(endpoint=url, token=token_id)


def get_status_message_for_service(request, service_id, environment_id):
    session_id = Session.get(request, environment_id)
    reports = muranoclient(request).sessions.reports(environment_id,
                                                     session_id,
                                                     service_id)

    result = 'Initialization.... \n'
    for report in reports:
        result += '  ' + str(report.text) + '\n'

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

        return sessions[environment_id] if environment_id in sessions else None


def environments_list(request):
    log.debug('Environment::List')
    environments = muranoclient(request).environments.list()

    for index, env in enumerate(environments):
        environments[index].has_services = False
        environment = environment_get(request, env.id)
        for service_name, instance in environment.services.iteritems():
            if instance:
                environments[index].has_services = True
                break
        if not environments[index].has_services:
            if environments[index].status == u'ready':
                environments[index].status = u'new'

    log.debug('Environment::List {0}'.format(environments))
    return environments


def environment_create(request, parameters):
    #name is required param
    name = parameters['name']
    log.debug('Environment::Create <Name: {0}>'.format(name))

    env = muranoclient(request).environments.create(name)
    log.debug('Environment::Create {0}'.format(env))
    return env


def environment_delete(request, environment_id):
    log.debug('Environment::Delete <Id: {0}>'.format(environment_id))
    muranoclient(request).environments.delete(environment_id)


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
    return environment.name


def get_environment_status(request, environment_id):
    session_id = Session.get(request, environment_id)
    environment = muranoclient(request).environments.get(environment_id,
                                                         session_id)
    return environment.status


def get_service_client(request, service_type):
    if service_type == 'Active Directory':
        return muranoclient(request).activeDirectories
    elif service_type == 'IIS':
        return muranoclient(request).webServers
    elif service_type == 'ASP.NET Application':
        return muranoclient(request).aspNetApps
    elif service_type == 'IIS Farm':
        return muranoclient(request).webServerFarms
    elif service_type == 'ASP.NET Farm':
        return muranoclient(request).aspNetAppFarms
    else:
        raise NameError('Unknown service type: {0}'.format(service_type))


def services_list(request, environment_id):
    services = []

    session_id = Session.get_or_create(request, environment_id)
    get_environment = muranoclient(request).environments.get

    environment = get_environment(environment_id, session_id)

    for service_name, instance in environment.services.iteritems():
        if instance:
            service_data = instance[0]
            reports = muranoclient(request).sessions.reports(
                environment_id, session_id, service_data['id'])
            if reports:
                last_operation = str(reports[-1].text)
            else:
                last_operation = ''

            service_data['operation'] = last_operation
            service_data['environment_id'] = environment_id
            services += instance

    log.debug('Service::List')
    return [bunch.bunchify(srv) for srv in services]


def service_list_by_type(request, environment_id, service_type):
    session_id = Session.get(request, environment_id)

    service_client = get_service_client(request, service_type)
    instances = service_client.list(environment_id, session_id)

    log.debug('Service::Instances::List')
    return instances


def service_create(request, environment_id, parameters):
    session_id = Session.get_or_create(request, environment_id)
    service_client = get_service_client(request, parameters['service_type'])
    log.debug('Service::Create {0}'.format(service_client))
    return service_client.create(environment_id, session_id, parameters)


def service_delete(request, service_id, environment_id, service_type):
    log.debug('Service::Delete <SrvId: {0}>'.format(service_id))

    session_id = Session.get_or_create(request, environment_id)
    service_client = get_service_client(request, service_type)
    service_client.delete(environment_id, service_id, session_id)


def service_get(request, environment_id, service_id):
    environment = environment_get(request, environment_id)
    for service_name, instance in environment.services.iteritems():
        if instance:
            service_data = instance[0]
            if service_data['id'] == service_id:
                reports = muranoclient(request).sessions.reports(
                    environment_id, Session.get(request, environment_id),
                    service_data['id'])
                if reports:
                    last_operation = str(reports[-1].text)
                else:
                    last_operation = ''

                service_data['operation'] = last_operation
                service_data['environment_id'] = environment_id
                return bunch.bunchify(service_data)


def check_for_services(request, environment_id):
    environment = environment_get(request, environment_id)
    for service_name, instance in environment.services.iteritems():
        if instance:
            return True
    return False
