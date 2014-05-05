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

import logging

from muranodashboard.common import utils
from muranodashboard.environments import api
from muranodashboard.environments import consts

LOG = logging.getLogger(__name__)


class StatsModel(object):
    def get_api_stats(self, request):
        st_list = api.muranoclient(request).request_statistics.list()
        for srv in st_list:
            srv.max_cpu = srv.cpu_count * 100
        return st_list


class BillingStats(object):
    def get_stats_for_env(self, request, environment_id):
        st_list = api.muranoclient(request).instance_statistics.get(
            environment_id)
        return st_list

    def get_all(self, request):
        env_list = api.environments_list(request)
        stats = []
        LOG.debug('Got env list: {0}'.format(env_list))
        for env in env_list:
            env_entry = utils.Bunch(name=env.name,
                                    id=env.id)
            services = self.build_service_list(request, env)
            LOG.debug('Processing env: {0}'.format(env))
            env_stats = self.get_stats_for_env(request, env.id)
            stats_list = []
            for entry in env_stats:
                instance_id = entry.instance_id
                service = services[instance_id]
                stat_entry = utils.Bunch(**entry.to_dict())
                stat_entry.service = service['name']
                stat_entry.service_type = service['type']
                stats_list.append(stat_entry)
            env_entry.instances = stats_list
            stats.append(env_entry)

        LOG.debug('Created statistics: {0}'.format(stats))
        return stats

    def _get_instances_ids(self, service):
        # TODO(tsufiev): un-hardcode instance id detection
        ids = []

        def _rec(node):
            if isinstance(node, dict) and node.get('?', {}).get('type'):
                _type = node['?']['type']
                if _type.endswith('Instance') or _type.endswith('Host'):
                    ids.append(node['?']['id'])
            if isinstance(node, dict):
                for _node in node.values():
                    _rec(_node)
            elif isinstance(node, list):
                for _node in node:
                    _rec(_node)

        for item in service:
            _rec(item)
        return ids

    def build_service_list(self, request, env):
        serv_list = api.services_list(request, env.id)
        LOG.debug('Got Service List: {0}'.format(serv_list))
        id_list = {}
        for service in serv_list:
            ids = self._get_instances_ids(service)
            storage = service['?'][consts.DASHBOARD_ATTRS_KEY]
            info = {'name': storage['name'], 'type': service['?']['type']}
            id_list.update(dict((_id, info) for _id in ids))
        return id_list


class Stats(object):
    def __init__(self, from_dict):
        for k, v in from_dict.items():
            setattr(self, k, v)
