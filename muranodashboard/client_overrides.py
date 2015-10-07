#    Copyright (c) 2015 Mirantis, Inc.
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

from muranoclient.common import utils as muranoclient_utils
from oslo_log import log as logging
from oslo_serialization import jsonutils

import os.path

LOG = logging.getLogger(__name__)

Package = muranoclient_utils.Package


# FIXME(kzaitsev): remove this file as soon as client with fix for
# bug 1503593 is globally available

@staticmethod
def from_location(name, base_url='', version='', url='', path=None):
    """Monkey-patching from_location untill a client with fix for #1503593

    If path is supplied search for name file in the path, otherwise
    if url is supplied - open that url and finally search murano
    repository for the package.
    """
    if path:
        pkg_name = os.path.join(path, name)
        file_name = None
        for f in [pkg_name, pkg_name + '.zip']:
            if os.path.exists(f):
                file_name = f
        if file_name:
            return Package.from_file(file_name)
        LOG.error("Couldn't find file for package {0}, tried {1}".format(
            name, [pkg_name, pkg_name + '.zip']))
    if url:
        return Package.from_file(url)
    return Package.from_file(muranoclient_utils.to_url(
        name,
        base_url=base_url,
        version=version,
        path='apps/',
        extension='.zip')
    )


def ensure_images(glance_client, image_specs, base_url, local_path=None):
    """Monkey-patching from_location untill a client with fix for #1503593

    Ensure that images from image_specs are available in glance. If not
    attempts: instructs glance to download the images and sets murano-specific
    metadata for it.
    """

    def _image_valid(image, keys):
        for key in keys:
            if key not in image:
                LOG.warning("Image specification invalid: "
                            "No {0} key in image ".format(key))
                return False
        return True

    keys = ['Name', 'DiskFormat', 'ContainerFormat', ]
    installed_images = []
    for image_spec in image_specs:
        if not _image_valid(image_spec, keys):
            continue
        filters = {
            'name': image_spec["Name"],
            'disk_format': image_spec["DiskFormat"],
            'container_format': image_spec["ContainerFormat"],
        }

        images = glance_client.images.list(filters=filters)
        try:
            img = images.next().to_dict()
        except StopIteration:
            img = None

        update_metadata = False
        if img:
            LOG.info("Found desired image {0}, id {1}".format(
                img['name'], img['id']))
            # check for murano meta-data
            if 'murano_image_info' in img.get('properties', {}):
                LOG.info("Image {0} already has murano meta-data".format(
                    image_spec['Name']))
            else:
                update_metadata = True
        else:
            LOG.info("Desired image {0} not found attempting "
                     "to download".format(image_spec['Name']))
            update_metadata = True

            img_file = None
            if local_path:
                img_file = os.path.join(local_path, image_spec['Name'])

            if img_file and not os.path.exists(img_file):
                LOG.error("Image file {0} does not exist."
                          .format(img_file))

            if img_file and os.path.exists(img_file):
                img = glance_client.images.create(
                    name=image_spec['Name'],
                    container_format=image_spec['ContainerFormat'],
                    disk_format=image_spec['DiskFormat'],
                    data=open(img_file, 'rb'),
                )
                img = img.to_dict()
            else:
                download_url = muranoclient_utils.to_url(
                    image_spec.get("Url", image_spec['Name']),
                    base_url=base_url,
                    path='images/',
                )
                LOG.info("Instructing glance to download image {0}".format(
                    image_spec['Name']))
                img = glance_client.images.create(
                    name=image_spec["Name"],
                    container_format=image_spec['ContainerFormat'],
                    disk_format=image_spec['DiskFormat'],
                    copy_from=download_url)
                img = img.to_dict()
            installed_images.append(img)

            if update_metadata and 'Meta' in image_spec:
                LOG.info("Updating image {0} metadata".format(
                    image_spec['Name']))
                murano_image_info = jsonutils.dumps(image_spec['Meta'])
                glance_client.images.update(
                    img['id'], properties={'murano_image_info':
                                           murano_image_info})
    return installed_images


def override():
    Package.from_location = from_location
    muranoclient_utils.ensure_images = ensure_images
