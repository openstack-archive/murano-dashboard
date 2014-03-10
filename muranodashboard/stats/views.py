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


from horizon import tabs

from muranodashboard.stats import tabs as t


class StatsView(tabs.TabView):
    tab_group_class = t.StatsTabs
    template_name = "stats/index.html"

    def get_tabs(self, request, *args, **kwargs):
        return self.tab_group_class(request, **kwargs)
