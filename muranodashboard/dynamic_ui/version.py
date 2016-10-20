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

import semantic_version

LATEST_FORMAT_VERSION = '2.4'


def check_version(version):
    latest = get_latest_version()
    supported = semantic_version.Version(str(latest.major), partial=True)
    requested = semantic_version.Version.coerce(str(version))
    if supported != requested:
        msg = 'Unsupported Dynamic UI format version: ' \
              'requested format version {0} is not compatible with the ' \
              'supported family {1}'
        raise ValueError(msg.format(requested, supported))
    if requested > latest:
        msg = 'Unsupported Dynamic UI format version: ' \
              'requested format version {0} is newer than ' \
              'latest supported {1}'
        raise ValueError(msg.format(requested, latest))


def get_latest_version():
    return semantic_version.Version.coerce(LATEST_FORMAT_VERSION)
