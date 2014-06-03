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

import itertools

from django.conf import settings

from muranodashboard import api


def package_list(request, marker=None, filters=None, paginate=False,
                 page_size=20):
    limit = getattr(settings, 'PACKAGES_LIMIT', 100)
    filters = filters or {}

    if paginate:
        request_size = page_size + 1
    else:
        request_size = limit

    if marker:
        filters['marker'] = marker

    client = api.muranoclient(request)
    packages_iter = client.packages.filter(page_size=request_size,
                                           limit=limit,
                                           **filters)

    has_more_data = False
    if paginate:
        packages = list(itertools.islice(packages_iter, request_size))
        if len(packages) > page_size:
            packages.pop()
            has_more_data = True
    else:
        packages = list(packages_iter)

    return packages, has_more_data
