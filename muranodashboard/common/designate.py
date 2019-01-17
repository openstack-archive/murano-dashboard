# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from designateclient import client

from keystoneauth1 import loading
from keystoneauth1 import session

from openstack_dashboard.api import base


def designateclient(request, api_version='2'):
    loader = loading.get_plugin_loader('token')
    auth = loader.load_from_options(
        auth_url=base.url_for(request, 'identity'),
        token=request.user.token.id,
        project_id=request.user.project_id,
        project_domain_id=request.user.token.project.get('domain_id'))

    sess = session.Session(auth=auth)
    return client.Client(api_version, session=sess)


def zone_list(request):
    d_client = designateclient(request)
    if d_client is None:
        return []
    return d_client.zones.list()
