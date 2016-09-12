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

from django.conf import settings
from django.contrib.messages import api as msg_api
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from glanceclient.common import exceptions as glance_exc
from horizon import exceptions
import muranoclient.client as client
from muranoclient.common import exceptions as exc
from muranoclient.glance import client as art_client
from openstack_dashboard.api import base
from oslo_log import log as logging


from muranodashboard.common import utils as muranodashboard_utils

LOG = logging.getLogger(__name__)


def _handle_message(request, message):
    def horizon_message_already_queued(_message):
        _message = force_text(_message)
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
    except glance_exc.CommunicationError:
        msg = _('Unable to communicate to glare-api server.')
        LOG.exception(msg)
        _handle_message(request, msg)
    except exc.HTTPUnauthorized:
        msg = _('Check Keystone configuration of murano-api server.')
        LOG.exception(msg)
        _handle_message(request, msg)
    except exc.HTTPForbidden:
        msg = _('Operation is forbidden by murano-api server.')
        LOG.exception(msg)
        _handle_message(request, msg)
    except exc.HTTPNotFound:
        msg = _('Requested object is not found on murano server.')
        LOG.exception(msg)
        _handle_message(request, msg)
    except exc.HTTPConflict:
        msg = _('Requested operation conflicts with an existing object.')
        LOG.exception(msg)
        _handle_message(request, msg)
    except exc.BadRequest as e:
        msg = _('The request data is not acceptable by the server')
        LOG.exception(msg)
        reason = muranodashboard_utils.parse_api_error(
            getattr(e, 'details', ''))
        if not reason:
            reason = msg
        _handle_message(request, reason)
    except (exc.HTTPInternalServerError,
            glance_exc.HTTPInternalServerError) as e:
        msg = _("There was an error communicating with server")
        LOG.exception(msg)
        reason = muranodashboard_utils.parse_api_error(
            getattr(e, 'details', ''))
        if not reason:
            reason = msg
        _handle_message(request, reason)


def _get_endpoint(request):
    # prefer location specified in settings for dev purposes
    endpoint = getattr(settings, 'MURANO_API_URL', None)

    if not endpoint:
        try:
            endpoint = base.url_for(request, 'application-catalog')
        except exceptions.ServiceCatalogException:
            endpoint = 'http://localhost:8082'
            LOG.warning('Murano API location could not be found in Service '
                        'Catalog, using default: {0}'.format(endpoint))
    return endpoint


def _get_glare_endpoint(request):
    endpoint = getattr(settings, 'GLARE_API_URL', None)
    if not endpoint:
        try:
            endpoint = base.url_for(request, "artifact")
        except exceptions.ServiceCatalogException:
            endpoint = 'http://localhost:9494'
            LOG.warning('Glare API location could not be found in Service '
                        'Catalog, using default: {0}'.format(endpoint))
    return endpoint


def artifactclient(request):
    endpoint = _get_glare_endpoint(request)
    insecure = getattr(settings, 'GLARE_API_INSECURE', False)
    token_id = request.user.token.id
    return art_client.Client(endpoint=endpoint, token=token_id,
                             insecure=insecure, type_name='murano',
                             type_version=1)


def muranoclient(request):
    endpoint = _get_endpoint(request)
    insecure = getattr(settings, 'MURANO_API_INSECURE', False)

    use_artifacts = getattr(settings, 'MURANO_USE_GLARE', False)
    if use_artifacts:
        artifacts = artifactclient(request)
    else:
        artifacts = None

    token_id = request.user.token.id
    LOG.debug('Murano::Client <Url: {0}>'.format(endpoint))

    return client.Client(1, endpoint=endpoint, token=token_id,
                         insecure=insecure, artifacts_client=artifacts,
                         tenant=request.user.tenant_id)
