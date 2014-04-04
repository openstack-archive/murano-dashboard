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

from muranodashboard.environments import api


class StatsModel(object):
    def get_api_stats(self, request):
        #st_list = api.muranoclient(request).statistics.list()
        st_list = []
        for i in range(1, 4):
            fdict = {
                "host": "API-%s" % str(i),
                "request_count": "100",
                "error_count": "2",
                "average_response_time": "0.22",
                "requests_per_second": "2.1",
                "errors_per_second": "0.001",
                "max_cpu": "800",
                "cpu_percent": "150"}
            st_list.append(Stats(fdict))
        return st_list


class Stats(object):
    def __init__(self, from_dict):
        for k, v in from_dict.items():
            setattr(self, k, v)
