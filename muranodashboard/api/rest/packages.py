# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""API for the murano packages service."""

from django.views import generic
from openstack_dashboard.api.rest import utils as rest_utils

from muranodashboard import api
from openstack_dashboard.api.rest import urls


CLIENT_KEYWORDS = {'marker', 'sort_dir', 'paginate'}


@urls.register
class Packages(generic.View):
    """API for Murano packages."""
    url_regex = r'app-catalog/packages/$'

    @rest_utils.ajax()
    def get(self, request):
        """Get a list of packages.

        The listing result is an object with property "packages".

        Example GET:
        http://localhost/api/app-catalog/packages?sort_dir=desc #flake8: noqa

        The following get parameters may be passed in the GET
        request:

        :param paginate: If true will perform pagination based on settings.
        :param marker: Specifies the namespace of the last-seen package.
             The typical pattern of limit and marker is to make an
             initial limited request and then to use the last
             namespace from the response as the marker parameter
             in a subsequent limited request. With paginate, limit
             is automatically set.
        :param sort_dir: The sort direction ('asc' or 'desc').

        Any additional request parameters will be passed through the API as
        filters.
        """

        filters, kwargs = rest_utils.parse_filters_kwargs(request,
                                                          CLIENT_KEYWORDS)

        packages, has_more_data = api.packages.package_list(
            request, filters=filters, **kwargs)

        return {
            'packages': [p.to_dict() for p in packages],
            'has_more_data': has_more_data,
        }
