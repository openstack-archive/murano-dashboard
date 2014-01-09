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
import tempfile
import re
from django.conf import settings
import os
import tarfile
import logging
import shutil
import hashlib
from muranodashboard.environments.consts import CHUNK_SIZE, CACHE_DIR, \
    ARCHIVE_PKG_NAME

log = logging.getLogger(__name__)


from horizon.exceptions import ServiceCatalogException
from openstack_dashboard.api.base import url_for
from metadataclient.v1.client import Client
from metadataclient.common.exceptions import CommunicationError, Unauthorized
from metadataclient.common.exceptions import HTTPInternalServerError
from horizon import exceptions
from django.utils.translation import ugettext_lazy as _
from contextlib import contextmanager


if not os.path.exists(CACHE_DIR):
    os.mkdir(CACHE_DIR)
    log.info('Creating cache directory located at {dir}'.format(dir=CACHE_DIR))
log.info('Using cache directory located at {dir}'.format(dir=CACHE_DIR))


def get_endpoint(request):
    # prefer location specified in settings for dev purposes
    endpoint = getattr(settings, 'MURANO_METADATA_URL', None)

    if not endpoint:
        try:
            endpoint = url_for(request, 'murano-metadata')
        except ServiceCatalogException:
            endpoint = 'http://localhost:8084/v1'
            log.warning(
                'Murano Metadata API location could not be found in Service '
                'Catalog, using default: {0}'.format(endpoint))
    return endpoint


def metadataclient(request):
    endpoint = get_endpoint(request)
    token_id = request.user.token.id
    log.debug('Murano::Client <Url: {0}, '
              'TokenId: {1}>'.format(endpoint, token_id))

    return Client(endpoint=endpoint, token=token_id)


def get_tenant_dir(tenant_id):
    return os.path.join(CACHE_DIR, tenant_id)


def get_existing_hash(tenant_dir):
    for item in os.listdir(tenant_dir):
        if re.match(r'[a-f0-9]{40}', item):
            return item
    return None


def get_hash(archive_path):
    """Calculate SHA1-hash of archive file.

    SHA-1 take a bit more time than MD5 (see http://tinyurl.com/kpj5jy7),
    but is more secure.
    """
    if os.path.exists(archive_path):
        sha1 = hashlib.sha1()
        with open(archive_path) as f:
            buf = f.read(CHUNK_SIZE)
            while buf:
                sha1.update(buf)
                buf = f.read(CHUNK_SIZE)
        hsum = sha1.hexdigest()
        log.debug("Archive '{0}' has hash-sum {1}".format(archive_path, hsum))
        return hsum
    else:
        log.info("Archive '{0}' doesn't exist, no hash to calculate".format(
            archive_path))
        return None


def unpack_ui_package(archive_path, tenant_dir):
    if not tarfile.is_tarfile(archive_path):
        raise RuntimeError('{0} is not valid tarfile!'.format(archive_path))
    hash = get_hash(archive_path)
    dst_dir = os.path.join(tenant_dir, hash)
    if not os.path.exists(dst_dir):
        os.mkdir(dst_dir)
    else:
        shutil.rmtree(dst_dir)
    tar = tarfile.open(archive_path, 'r:gz')
    try:
        log.debug('Extracting metadata archive')
        tar.extractall(dst_dir)
    finally:
        tar.close()
    return dst_dir


@contextmanager
def metadata_exceptions(request):
    """Handles all metadata-repository specific exceptions."""
    try:
        yield
    except CommunicationError:
        msg = _('Unable to communicate to Murano Metadata Repository. Add '
                'MURANO_METADATA_URL to local_settings')
        log.exception(msg)
        exceptions.handle(request, msg)
    except Unauthorized:
        msg = _('Configure Keystone in Murano Repository Service')
        log.exception(msg)
        exceptions.handle(request, msg)
    except HTTPInternalServerError:
        msg = _('There is a problem with Murano Repository Service')
        log.exception(msg)
        exceptions.handle(request, msg)


def get_ui_metadata(request):
    """Returns directory with unpacked definitions provided by Metadata
    Repository at `endpoint' URL or, if it was not found or some error has
    occurred, returns None.
    """
    log.debug("Retrieving metadata from Repository")
    tenant_dir = get_tenant_dir(request.user.tenant_id)
    if not os.path.exists(tenant_dir):
        os.makedirs(tenant_dir)

    hash = get_existing_hash(tenant_dir)
    metadata_dir = None
    if hash:
        metadata_dir = os.path.join(tenant_dir, hash)

    data = None
    with metadata_exceptions(request):
        data = metadataclient(request).metadata_client.get_ui_data(hash)

    # mimic normal return value in case metadata repository exception has just
    # been handled.
    # TODO: it would be better to use redirect here
    if data is None:
        return None, False
    response, body_iter = data

    code = response.status
    if code == 200:
        with tempfile.NamedTemporaryFile(delete=False) as out:
            for chunk in body_iter:
                out.write(chunk)
        archive_pkg_path = os.path.join(tenant_dir, ARCHIVE_PKG_NAME)
        shutil.move(out.name, archive_pkg_path)
        log.info("Successfully downloaded new metadata package to {0}".format(
            archive_pkg_path))
        if hash:
            log.debug('Removing outdated metadata: {0}'.format(metadata_dir))
            shutil.rmtree(metadata_dir)
        return unpack_ui_package(archive_pkg_path, tenant_dir), True
    elif code == 304:
        log.info("Metadata package hash-sum hasn't changed, doing nothing")
        return metadata_dir, False
    else:
        msg = 'Unexpected response received: {0}'.format(code)
        if metadata_dir:
            log.error('Using existing version of metadata '
                      'which may be outdated due to: {0}'.format(msg))
            return metadata_dir, False
        else:
            log.error('Unable to load any metadata due to: {0}'.format(msg))
            exceptions.handle(
                request,
                _('There is a problem with Murano Repository Service'))
            return None, False
