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
from django.conf import settings
import os.path
import os
import tarfile
import logging
import shutil
import hashlib


CHUNK_SIZE = 1 << 20  # 1MB
ARCHIVE_PKG_NAME = 'archive.tar.gz'
CACHE_DIR = getattr(settings, 'UI_METADATA_CACHE_DIR',
                    '/var/lib/murano-dashboard/cache')

ARCHIVE_PKG_PATH = os.path.join(CACHE_DIR, ARCHIVE_PKG_NAME)

log = logging.getLogger(__name__)


from horizon.exceptions import ServiceCatalogException
from openstack_dashboard.api.base import url_for
from metadataclient.v1.client import Client


def get_first_subdir(path):
    for file in os.listdir(path):
        new_path = os.path.join(path, file)
        if os.path.isdir(new_path):
            return new_path
    return None


def get_endpoint(request):
    # prefer location specified in settings for dev purposes
    endpoint = getattr(settings, 'MURANO_METADATA_URL', None)

    if not endpoint:
        try:
            endpoint = url_for(request, 'murano-metadata')
        except ServiceCatalogException:
            endpoint = 'http://localhost:8084'
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


def unpack_ui_package(archive_path):
    if not tarfile.is_tarfile(archive_path):
        raise RuntimeError("{0} is not valid tarfile!".format(archive_path))
    dst_dir = os.path.dirname(os.path.abspath(archive_path))
    tar = tarfile.open(archive_path, 'r:gz')
    try:
        tar.extractall(path=dst_dir)
    finally:
        tar.close()
    return get_first_subdir(dst_dir)


def get_ui_metadata(request):
    """Returns directory with unpacked definitions provided by Metadata
    Repository at `endpoint' URL or, if it was not found or some error has
    occurred, returns None.
    """
    log.debug("Retrieving metadata from Repository")
    response, body_iter = metadataclient(request).metadata_client.get_ui_data(
        get_hash(ARCHIVE_PKG_PATH))
    code = response.status
    if code == 200:
        with tempfile.NamedTemporaryFile(delete=False) as out:
            for chunk in body_iter:
                out.write(chunk)
        if os.path.exists(ARCHIVE_PKG_PATH):
            os.remove(ARCHIVE_PKG_PATH)
        shutil.move(out.name, ARCHIVE_PKG_PATH)
        log.info("Successfully downloaded new metadata package to {0}".format(
            ARCHIVE_PKG_PATH))
        return unpack_ui_package(ARCHIVE_PKG_PATH), True
    elif code == 304:
        log.info("Metadata package hash-sum hasn't changed, doing nothing")
        return get_first_subdir(CACHE_DIR), False
    else:
        raise RuntimeError('Unexpected response received: {0}'.format(code))
