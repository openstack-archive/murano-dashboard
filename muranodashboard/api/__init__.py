#    Copyright (c) 2014 Mirantis, Inc.
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
from openstack_dashboard.api import base

import muranoclient.client as client
from muranoclient.common import exceptions as exc


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
    except exc.NotFound:
        msg = _('Requested object is not found on murano server.')
        LOG.exception(msg)
        _handle_message(request, msg)


def _get_endpoint(request):
    #prefer location specified in settings for dev purposes
    endpoint = getattr(settings, 'MURANO_API_URL', None)

    if not endpoint:
        try:
            endpoint = base.url_for(request, 'application_catalog')
        except exceptions.ServiceCatalogException:
            endpoint = 'http://localhost:8082'
            LOG.warning('Murano API location could not be found in Service '
                        'Catalog, using default: {0}'.format(endpoint))
    return endpoint


def muranoclient(request):
    endpoint = _get_endpoint(request)
    insecure = getattr(settings, 'MURANO_API_INSECURE', False)

    token_id = request.user.token.id
    LOG.debug('Murano::Client <Url: {0}, '
              'TokenId: {1}>'.format(endpoint, token_id))

    return client.Client(1, endpoint=endpoint, token=token_id,
                         insecure=insecure)
