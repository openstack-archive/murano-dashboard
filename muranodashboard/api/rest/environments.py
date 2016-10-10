#    Copyright (c) 2016 Mirantis, Inc.
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


from django.views import generic

from openstack_dashboard.api.rest import urls
from openstack_dashboard.api.rest import utils as rest_utils

from muranodashboard import api
from muranodashboard.environments import api as env_api


@urls.register
class ComponentsMetadata(generic.View):
    """API for Murano components Metadata"""

    url_regex = r'app-catalog/environments/(?P<environment>[^/]+)' \
                r'/components/(?P<component>[^/]+)/metadata/$'

    @rest_utils.ajax()
    def get(self, request, environment, component):
        """Get a metadata object for a component in a given environment

        Example GET:
        http://localhost/api/app-catalog/environments/123/components/456/metadata

        The following get parameters may be passed in the GET
        request:

        :param environment: identifier of the environment
        :param component: identifier of the component

        Any additionally a "session" parameter should be passed through the API
        as a keyword.
        """
        filters, keywords = rest_utils.parse_filters_kwargs(request,
                                                            ['session'])
        session = keywords.get('session')
        if not session:
            session = env_api.Session.get_or_create_or_delete(request,
                                                              environment)
        component = api.muranoclient(request).services.get(
            environment, '/' + component, session)
        if component:
            return component.to_dict()['?'].get('metadata', {})
        return {}

    @rest_utils.ajax(data_required=True)
    def post(self, request, environment, component):
        """Set a metadata object for a component in a given environment

        Example POST:
        http://localhost/api/app-catalog/environments/123/components/456/metadata

        The following get parameters may be passed in the GET
        request:

        :param environment: identifier of the environment
        :param component: identifier of the component

        Any additionally a "session" parameter should be passed through the API
        as a keyword. Request body should contain 'updated' keyword, contain
        all the updated metadata attributes. If it is empty, the metadata is
        considered to be deleted.
        """
        client = api.muranoclient(request)
        filters, keywords = rest_utils.parse_filters_kwargs(request,
                                                            ['session'])
        session = keywords.get('session')
        if not session:
            session = env_api.Session.get_or_create_or_delete(request,
                                                              environment)
        updated = request.DATA.get('updated', {})
        path = '/{0}/%3F/metadata'.format(component)

        if updated:
            client.services.put(environment, path, updated, session)
        else:
            client.services.delete(environment, path, session)


@urls.register
class EnvironmentsMetadata(generic.View):
    """API for Murano components Metadata"""

    url_regex = r'app-catalog/environments/(?P<environment>[^/]+)/metadata/$'

    @rest_utils.ajax()
    def get(self, request, environment):
        """Get a metadata object for an environment

        Example GET:
        http://localhost/api/app-catalog/environments/123/metadata

        The following get parameters may be passed in the GET
        request:

        :param environment: identifier of the environment

        Any additionally a "session" parameter should be passed through the API
        as a keyword.
        """
        filters, keywords = rest_utils.parse_filters_kwargs(request,
                                                            ['session'])
        session = keywords.get('session')
        if not session:
            session = env_api.Session.get_or_create_or_delete(request,
                                                              environment)
        env = api.muranoclient(request).environments.get_model(
            environment, '/', session)
        if env:
            return env['?'].get('metadata', {})
        return {}

    @rest_utils.ajax(data_required=True)
    def post(self, request, environment):
        """Set a metadata object for a given environment

        Example POST:
        http://localhost/api/app-catalog/environments/123/metadata

        The following get parameters may be passed in the GET
        request:

        :param environment: identifier of the environment

        Any additionally a "session" parameter should be passed through the API
        as a keyword. Request body should contain 'updated' keyword, contain
        all the updated metadata attributes. If it is empty, the metadata is
        considered to be deleted.
        """
        client = api.muranoclient(request)
        filters, keywords = rest_utils.parse_filters_kwargs(request,
                                                            ['session'])

        session = keywords.get('session')
        if not session:
            session = env_api.Session.get_or_create_or_delete(request,
                                                              environment)
        updated = request.DATA.get('updated', {})
        patch = {
            "op": "replace",
            "path": "/?/metadata",
            "value": updated
        }
        client.environments.update_model(environment, [patch], session)
