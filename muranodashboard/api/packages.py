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
import yaml

from muranodashboard import api
from muranodashboard.common import cache
from muranodashboard.dynamic_ui import yaql_expression


def package_list(request, marker=None, filters=None, paginate=False,
                 page_size=20, sort_dir=None, limit=None):
    limit = limit or getattr(settings, 'PACKAGES_LIMIT', 100)
    filters = filters or {}

    if paginate:
        request_size = page_size + 1
    else:
        request_size = limit

    if marker:
        filters['marker'] = marker
    if sort_dir:
        filters['sort_dir'] = sort_dir

    client = api.muranoclient(request)

    packages_iter = client.packages.filter(limit=request_size,
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


def apps_that_inherit(request, fqn):
    glare = getattr(settings, 'MURANO_USE_GLARE', False)
    if not glare:
        return []
    apps = api.muranoclient(request).packages.filter(inherits=fqn)
    return apps


def app_by_fqn(request, fqn, catalog=True, version=None):
    kwargs = {'fqn': fqn, 'catalog': catalog}
    glare = getattr(settings, 'MURANO_USE_GLARE', False)
    if glare and version:
        kwargs['version'] = version
    apps = api.muranoclient(request).packages.filter(**kwargs)
    try:
        return next(apps)
    except StopIteration:
        return None


def make_loader_cls():
    class Loader(yaml.SafeLoader):
        pass

    def yaql_constructor(loader, node):
        value = loader.construct_scalar(node)
        return yaql_expression.YaqlExpression(value)

    # workaround for PyYAML bug: http://pyyaml.org/ticket/221
    resolvers = {}
    for k, v in yaml.SafeLoader.yaml_implicit_resolvers.items():
        resolvers[k] = v[:]
    Loader.yaml_implicit_resolvers = resolvers

    Loader.add_constructor(u'!yaql', yaql_constructor)
    Loader.add_implicit_resolver(
        u'!yaql', yaql_expression.YaqlExpression, None)

    return Loader


# Here are cached some data calls to api; note that not every package attribute
# getter should be cached - only immutable ones could be safely cached. E.g.,
# it would be a mistake to cache Application Name because it is mutable and can
# be changed in Manage -> Packages while cache is immutable (i.e. it
# its contents are obtained from the api only the first time).
@cache.with_cache('ui', 'ui.yaml')
def get_app_ui(request, app_id):
    return api.muranoclient(request).packages.get_ui(app_id, make_loader_cls())


@cache.with_cache('logo', 'logo.png')
def get_app_logo(request, app_id):
    return api.muranoclient(request).packages.get_logo(app_id)


@cache.with_cache('supplier_logo', 'supplier_logo.png')
def get_app_supplier_logo(request, app_id):
    return api.muranoclient(request).packages.get_supplier_logo(app_id)


def get_app_fqn(request, app_id):
    return get_package_details(request, app_id).fully_qualified_name


def get_service_name(request, app_id):
    return get_package_details(request, app_id).name


@cache.with_cache('package_details')
def get_package_details(request, app_id):
    return api.muranoclient(request).packages.get(app_id)
