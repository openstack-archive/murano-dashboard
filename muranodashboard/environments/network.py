# Copyright (c) 2013 Mirantis Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import math
from django.conf import settings
from keystoneclient.v2_0 import client as ksclient
import netaddr
from netaddr.strategy import ipv4
from neutronclient.v2_0 import client as neutronclient
import logging

log = logging.getLogger(__name__)


class NeutronSubnetGetter(object):
    def __init__(self, tenant_id, token, router_id=None):
        conf = getattr(settings, 'ADVANCED_NETWORKING_CONFIG', {})
        self.env_count = conf.get('max_environments', 100)
        self.host_count = conf.get('max_hosts', 250)
        self.address = conf.get('env_ip_template', '10.0.0.0')

        self.tenant_id = tenant_id
        self._router_id = router_id

        cacert = getattr(settings, 'OPENSTACK_SSL_CACERT', None)
        insecure = getattr(settings, 'OPENSTACK_SSL_NO_VERIFY', False)
        endpoint_type = getattr(
            settings, 'OPENSTACK_ENDPOINT_TYPE', 'publicURL')

        keystone_client = ksclient.Client(
            auth_url=settings.OPENSTACK_KEYSTONE_URL,
            tenant_id=tenant_id,
            token=token,
            cacert=cacert,
            insecure=insecure)

        if not keystone_client.authenticate():
            raise ksclient.exceptions.Unauthorized()

        neutron_url = keystone_client.service_catalog.url_for(
            service_type='network', endpoint_type=endpoint_type)
        self.neutron = neutronclient.Client(endpoint_url=neutron_url,
                                            token=token,
                                            ca_cert=cacert,
                                            insecure=insecure)

    def _get_router_id(self):
        routers = self.neutron.list_routers(tenant_id=self.tenant_id).\
            get("routers")
        if not len(routers):
            router_id = None
        else:
            router_id = routers[0]["id"]

            if len(routers) > 1:
                for router in routers:
                    if "murano" in router["name"].lower():
                        router_id = router["id"]
                        break

        return router_id

    def _get_subnet(self, router_id=None, count=1):
        if router_id:
            taken_cidrs = self._get_taken_cidrs_by_router(router_id)
        else:
            taken_cidrs = self._get_all_taken_cidrs()
        results = []
        for i in range(0, count):
            res = self._generate_cidr(taken_cidrs)
            results.append(res)
            taken_cidrs.append(res)
        return results

    def _get_taken_cidrs_by_router(self, router_id):
        ports = self.neutron.list_ports(device_id=router_id)["ports"]
        subnet_ids = []
        for port in ports:
            for fixed_ip in port["fixed_ips"]:
                subnet_ids.append(fixed_ip["subnet_id"])

        all_subnets = self.neutron.list_subnets()["subnets"]
        filtered_cidrs = [subnet["cidr"] for subnet in all_subnets if
                          subnet["id"] in subnet_ids]

        return filtered_cidrs

    def _get_all_taken_cidrs(self):
        return [subnet["cidr"] for subnet in
                self.neutron.list_subnets()["subnets"]]

    def _generate_cidr(self, taken_cidrs):
        bits_for_envs = int(math.ceil(math.log(self.env_count, 2)))
        bits_for_hosts = int(math.ceil(math.log(self.host_count, 2)))
        width = ipv4.width
        mask_width = width - bits_for_hosts - bits_for_envs
        net = netaddr.IPNetwork(self.address + "/" + str(mask_width))
        for subnet in net.subnet(width - bits_for_hosts):
            if str(subnet) in taken_cidrs:
                continue
            return str(subnet)
        return None

    def get_subnet(self, environment_id=None):
        # TODO: should use environment_id for getting cidr in future
        if not self._router_id:
            self._router_id = self._get_router_id()
        return self._get_subnet(self._router_id)[0]

    def get_router_id(self):
        if not self._router_id:
            self._router_id = self._get_router_id()
        return self._router_id


def get_network_params(request):
    network_topology = getattr(settings, 'NETWORK_TOPOLOGY', 'routed')

    if network_topology != 'nova':
        getter = NeutronSubnetGetter(request.user.tenant_id,
                                     request.user.token.id)
        existing_subnet = getter.get_subnet()
        if existing_subnet:
            return {'networking': {'topology': network_topology,
                                   'createNetwork': True,
                                   'cidr': existing_subnet,
                                   'routerId': getter.get_router_id()}}
        else:
            log.error('Cannot get subnet')
            return {'networking': {'topology': network_topology}}
