# Copyright (c) 2015 Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


import re
import uuid

from django.utils.translation import ugettext_lazy as _
from horizon import exceptions
from openstack_dashboard.api import neutron
from oslo_log import log as logging

from muranodashboard.environments import api as env_api

LOG = logging.getLogger(__name__)

NEUTRON_NET_HELP = _("The VMs of the applications in this environment will "
                     "join this net by default, unless configured "
                     "individually. Choosing 'Create New' will generate a new "
                     "Network with a Subnet having an IP range allocated "
                     "among the ones available for the default Murano Router "
                     "of this project")
NN_HELP = _("OpenStack Networking (Neutron) is not available in current "
            "environment. Custom Network Settings cannot be applied")


def get_available_networks(request, include_subnets=True,
                           filter=None, murano_networks=None):
    if murano_networks:
        env_names = [e.name for e in env_api.environments_list(request)]

        def get_net_env(name):
            for env_name in env_names:
                if name.startswith(env_name + '-network'):
                    return env_name

    network_choices = []
    tenant_id = request.user.tenant_id
    try:
        networks = neutron.network_list_for_tenant(request,
                                                   tenant_id=tenant_id)
    except exceptions.ServiceCatalogException:
        LOG.warning("Neutron not found. Assuming Nova Network usage")
        return None

    # Remove external networks
    networks = [network for network in networks
                if network.router__external is False]
    if filter:
        networks = [network for network in networks
                    if re.match(filter, network.name) is not None]

    for net in networks:
        env = None
        netname = None

        if murano_networks and len(net.subnets) == 1:
            env = get_net_env(net.name)
        if env:
            if murano_networks == 'exclude':
                continue
            else:
                netname = _("Network of '%s'") % env

        if include_subnets:
            for subnet in net.subnets:
                if not netname:
                    full_name = (
                        "%(net)s: %(cidr)s %(subnet)s" %
                        dict(net=net.name_or_id,
                             cidr=subnet.cidr,
                             subnet=subnet.name_or_id))

                network_choices.append(
                    ((net.id, subnet.id), netname or full_name))

        else:
            netname = netname or net.name_or_id
            network_choices.append(((net.id, None), netname))
    return network_choices


def generate_join_existing_net(net_config):
    res = {
        "defaultNetworks": {
            'environment': {
                '?': {
                    'id': uuid.uuid4().hex,
                    'type': 'io.murano.resources.ExistingNeutronNetwork'
                },
                'internalNetworkName': net_config[0],
                'internalSubnetworkName': net_config[1]
            },
            'flat': None
        }
    }
    return res
