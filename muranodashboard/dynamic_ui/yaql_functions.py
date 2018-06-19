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

import random
import string
import time

from yaql.language import specs
from yaql.language import yaqltypes

from muranodashboard.catalog import forms as catalog_forms
from muranodashboard.dynamic_ui import helpers

from castellan.common import exception as castellan_exception
from castellan.common.objects import opaque_data
from castellan import key_manager
from castellan import options

from keystoneauth1 import identity
from keystoneauth1 import session

from django.conf import settings

from oslo_config import cfg
from oslo_context import context as _oslo_context
from oslo_log import log as logging

LOG = logging.getLogger(__name__)


@specs.parameter('times', int)
def _repeat(context, template, times):
    for i in range(times):
        context['index'] = i + 1
        yield helpers.evaluate(template, context)


_random_string_counter = None


@specs.parameter('pattern', yaqltypes.String())
@specs.parameter('number', int)
def _generate_hostname(pattern, number):
    """Generates hostname based on pattern

    Replaces '#' char in pattern with supplied number, if no pattern is
    supplied generates short and unique name for the host.

    :param pattern: hostname pattern
    :param number: number to replace with in pattern
    :return: hostname
    """
    global _random_string_counter

    if pattern:
        # NOTE(kzaitsev) works both for unicode and simple strings in py2
        # and works as expected in py3
        return pattern.replace('#', str(number))

    counter = _random_string_counter or 1
    # generate first 5 random chars
    prefix = ''.join(random.choice(string.ascii_lowercase) for _ in range(5))
    # convert timestamp to higher base to shorten hostname string
    # (up to 8 chars)
    timestamp = helpers.int2base(int(time.time() * 1000), 36)[:8]
    # third part of random name up to 2 chars
    # (1295 is last 2-digit number in base-36, 1296 is first 3-digit number)
    suffix = helpers.int2base(counter, 36)
    _random_string_counter = (counter + 1) % 1296
    return prefix + timestamp + suffix


def _name(context):
    name = context.get_data[
        catalog_forms.WF_MANAGEMENT_NAME]['application_name']
    return name


@specs.parameter('template_name', yaqltypes.String())
@specs.parameter('parameter_name', yaqltypes.String(nullable=True))
@specs.parameter('id_only', yaqltypes.PythonType(bool, nullable=True))
def _ref(context, template_name, parameter_name=None, id_only=None):
    service = context['?service']
    data = None
    if not parameter_name:
        parameter_name = template_name
    # add special symbol to avoid collisions with regular parameters
    # and prevent it from overwriting '?service' context variable
    parameter_name = '#' + parameter_name
    if parameter_name in service.parameters:
        data = service.parameters[parameter_name]
    elif template_name in service.templates:
        data = helpers.evaluate(service.templates[template_name], context)
        service.parameters[parameter_name] = data
    if not isinstance(data, dict):
        return None
    if not isinstance(data.get('?', {}).get('id'), helpers.ObjectID):
        data.setdefault('?', {})['id'] = helpers.ObjectID()
        if id_only is None:
            id_only = False
    elif id_only is None:
        id_only = True

    if id_only:
        return data['?']['id']
    else:
        return data


@specs.parameter('data', yaqltypes.String())
def _encrypt_data(context, data):
    try:
        # TODO(pbourke): move auth construction into common area if it ends up
        # been required in other areas
        auth = identity.V3Password(
            auth_url=settings.KEY_MANAGER['auth_url'],
            username=settings.KEY_MANAGER['username'],
            user_domain_name=settings.KEY_MANAGER['user_domain_name'],
            password=settings.KEY_MANAGER['password'],
            project_name=settings.KEY_MANAGER['project_name'],
            project_domain_name=settings.KEY_MANAGER['project_domain_name']
        )
    except (KeyError, AttributeError) as e:
        LOG.exception(e)
        msg = ('Could not find valid key manager credentials in the '
               'murano-dashboard config. encryptData yaql function not '
               'available')
        raise castellan_exception.KeyManagerError(message_arg=msg)
    sess = session.Session(auth=auth)
    auth_context = _oslo_context.RequestContext(
        auth_token=auth.get_token(sess), tenant=auth.get_project_id(sess))
    options.set_defaults(cfg.CONF,
                         auth_endpoint=settings.KEY_MANAGER['auth_url'])
    options.set_defaults(cfg.CONF,
                         barbican_endpoint_type='internal')

    manager = key_manager.API()
    try:
        # TODO(pbourke): while we feel opaque data should cover the most common
        # use case, we may want to add support for other secret types in the
        # future (see https://goo.gl/tZhfqe)
        stored_key_id = manager.store(auth_context,
                                      opaque_data.OpaqueData(data))
    except castellan_exception.KeyManagerError as e:
        LOG.exception(e)
        raise
    return stored_key_id


def register(context):
    context.register_function(_repeat, 'repeat')
    context.register_function(_generate_hostname, 'generateHostname')
    context.register_function(_name, 'name')
    context.register_function(_ref, 'ref')
    context.register_function(_encrypt_data, 'encryptData')
