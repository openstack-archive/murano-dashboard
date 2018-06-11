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

import collections
import copy
import functools
import json
import re
import uuid

from castellan.common import exception as castellan_exception

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import decorators as auth_dec
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.urls import reverse
# django.contrib.formtools migration to django 1.8
# https://docs.djangoproject.com/en/1.8/ref/contrib/formtools/
try:
    from django.contrib.formtools.wizard import views as wizard_views
except ImportError:
    from formtools.wizard import views as wizard_views
from django import http
from django import shortcuts
from django.utils import decorators as django_dec
from django.utils import html
from django.utils import http as http_utils
from django.utils.translation import ugettext_lazy as _
from django.views.generic import list as list_view
from horizon import exceptions
from horizon.forms import views
from horizon import messages
from horizon import tabs
from horizon import views as generic_views
from novaclient import exceptions as nova_exceptions
from openstack_dashboard.api import nova
from openstack_dashboard.usage import quotas
from oslo_log import log as logging
import six

from muranoclient.common import exceptions as exc
from muranodashboard import api
from muranodashboard.api import packages as pkg_api
from muranodashboard.catalog import tabs as catalog_tabs
from muranodashboard.common import utils
from muranodashboard.dynamic_ui import helpers
from muranodashboard.dynamic_ui import services
from muranodashboard.environments import api as env_api
from muranodashboard.environments import consts
from muranodashboard.packages import consts as pkg_consts

LOG = logging.getLogger(__name__)
ALL_CATEGORY_NAME = 'All'
LATEST_APPS_QUEUE_LIMIT = 3


class DictToObj(object):
    def __init__(self, **kwargs):
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)


def get_available_environments(request):
    envs = []
    for env in env_api.environments_list(request):
        obj = DictToObj(id=env.id, name=env.name, status=env.status)
        envs.append(obj)

    return envs


def is_valid_environment(environment, valid_environments):
    for env in valid_environments:
        if environment.id == env.id:
            return True
    return False


def get_environments_context(request):
    envs = get_available_environments(request)
    context = {'available_environments': envs}
    environment = request.session.get('environment')
    if environment and is_valid_environment(environment, envs):
        context['environment'] = environment
    elif envs:
        context['environment'] = envs[0]
    return context


def get_categories_list(request):
    """Returns a list of categories, sorted.

    Categories with packages come first, categories without
    packages come second. both groups alphabetically sorted.
    """

    categories = []
    with api.handled_exceptions(request):
        client = api.muranoclient(request)
        categories = client.categories.list()

    # NOTE(kzaitsev) We rely here on tuple comparison and ascending order of
    # sorted(). i.e. (False, 'a') < (False, 'b') < (True, 'a') < (True, 'b')
    # So to make order more human-friendly we sort based on
    # package_count == 0, pushing categories without packages in front and
    # and then sorting them alphabetically
    categories = [cat for cat in sorted(
        categories, key=lambda c: (c.package_count == 0, c.name))]
    # TODO(kzaitsev): add sorting options to category API

    return categories


@auth_dec.login_required
def switch(request, environment_id,
           redirect_field_name=auth.REDIRECT_FIELD_NAME):
    redirect_to = request.GET.get(redirect_field_name, '')
    if not http_utils.is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = settings.LOGIN_REDIRECT_URL

    for env in get_available_environments(request):
        if env.id == environment_id:
            request.session['environment'] = env
            break
    return shortcuts.redirect(redirect_to)


def get_next_quick_environment_name(request):
    quick_env_prefix = 'quick-env-'
    quick_env_re = re.compile('^' + quick_env_prefix + '([\d]+)$')

    def parse_number(env):
        match = re.match(quick_env_re, env.name)
        return int(match.group(1)) if match else 0

    numbers = [parse_number(e) for e in env_api.environments_list(request)]
    new_env_number = 1
    if numbers:
        numbers.sort()
        new_env_number = numbers[-1] + 1

    return quick_env_prefix + str(new_env_number)


def create_quick_environment(request):
    params = {'name': get_next_quick_environment_name(request)}
    return env_api.environment_create(request, params)


def update_latest_apps(func):
    """Update 'app_id's in session

    Adds package id to a session queue with Applications which were
    recently added to an environment or to the Catalog itself. Thus it is
    used as decorator for views adding application to an environment or
    uploading new package definition to a catalog.
    """
    @functools.wraps(func)
    def __inner(request, **kwargs):
        apps = request.session.setdefault('latest_apps', collections.deque())
        app_id = kwargs['app_id']
        if app_id in apps:  # move recent app to the beginning
            apps.remove(app_id)

        apps.appendleft(app_id)
        if len(apps) > LATEST_APPS_QUEUE_LIMIT:
            apps.pop()

        return func(request, **kwargs)

    return __inner


def cleaned_latest_apps(request):
    """Returns a list of recently used apps

    Verifies, that apps in the list are either public or belong to current
    project.
    """
    id_param = "in:" + ",".join(request.session.get('latest_apps', []))
    query_params = {'type': 'Application', 'catalog': True, 'id': id_param}
    user_apps = list(api.muranoclient(request).packages.filter(**query_params))
    request.session['latest_apps'] = collections.deque([app.id
                                                        for app in user_apps])
    return user_apps


def clear_forms_data(func):
    """Removes form data from session

    Clears user's session from a data for a specific application. It
    guarantees that previous additions of that application won't interfere
    with the next ones. Should be used as a decorator for entry points for
    adding an application in an environment.
    """
    @functools.wraps(func)
    def __inner(request, **kwargs):
        app_id = kwargs['app_id']
        fqn = pkg_api.get_app_fqn(request, app_id)
        LOG.debug('Clearing forms data for application {0}.'.format(fqn))
        services.get_apps_data(request)[app_id] = {}
        LOG.debug('Clearing any leftover wizard step data.')
        for key in request.session.keys():
            # TODO(tsufiev): unhardcode the prefix for wizard step data
            if key.startswith('wizard_wizard'):
                request.session.pop(key)
        return func(request, **kwargs)

    return __inner


def clear_quick_env_id(func):
    @functools.wraps(func)
    def __inner(request, **kwargs):
        request.session.pop('quick_env_id', None)
        return func(request, **kwargs)

    return __inner


@update_latest_apps
@clear_forms_data
@auth_dec.login_required
def deploy(request, environment_id, app_id,
           do_redirect=False, drop_wm_form=False):
    view = Wizard.as_view(services.get_app_forms,
                          condition_dict=services.condition_getter)
    return view(request, app_id=app_id, environment_id=environment_id,
                do_redirect=do_redirect, drop_wm_form=drop_wm_form)


@clear_quick_env_id
@update_latest_apps
@clear_forms_data
@auth_dec.login_required
def quick_deploy(request, app_id):
    return deploy(request, app_id=app_id, environment_id=None,
                  do_redirect=True, drop_wm_form=True)


def get_image(request, app_id):
    try:
        content = pkg_api.get_app_logo(request, app_id)
    except (AttributeError, exc.HTTPNotFound):
        message = _("Can not get logo for {0}.").format(app_id)
        LOG.warning(message)
        content = None
    if content:
        return http.HttpResponse(content=content, content_type='image/png')
    else:
        universal_logo = static('muranodashboard/images/icon.png')
        return http.HttpResponseRedirect(universal_logo)


def get_supplier_image(request, app_id):
    try:
        content = pkg_api.get_app_supplier_logo(request, app_id)
    except (AttributeError, exc.HTTPNotFound):
        message = _("Can not get supplier logo for {0}.").format(app_id)
        LOG.warning(message)
        content = None
    if content:
        return http.HttpResponse(content=content, content_type='image/png')
    else:
        universal_logo = static('muranodashboard/images/icon.png')
        return http.HttpResponseRedirect(universal_logo)


class LazyWizard(wizard_views.SessionWizardView):
    """Lazy version of SessionWizardView

    The class which defers evaluation of form_list and condition_dict
    until view method is called. So, each time we load a page with a dynamic
    UI form, it will have markup/logic from the newest YAML-file definition.
    """
    @django_dec.classonlymethod
    def as_view(cls, initforms, *initargs, **initkwargs):
        """Main entry point for a request-response process."""
        # sanitize keyword arguments
        for key in initkwargs:
            if key in cls.http_method_names:
                raise TypeError(u"You tried to pass in the %s method name as a"
                                u" keyword argument to %s(). Don't do that."
                                % (key, cls.__name__))
            if not hasattr(cls, key):
                raise TypeError(u"%s() received an invalid keyword %r" % (
                    cls.__name__, key))

        @update_latest_apps
        def view(request, *args, **kwargs):
            forms = initforms
            if hasattr(initforms, '__call__'):
                forms = initforms(request, kwargs)
            _kwargs = copy.copy(initkwargs)

            _kwargs = cls.get_initkwargs(forms, *initargs, **_kwargs)

            cdict = _kwargs.get('condition_dict')
            if cdict and hasattr(cdict, '__call__'):
                _kwargs['condition_dict'] = cdict(request, kwargs)

            self = cls(**_kwargs)
            if hasattr(self, 'get') and not hasattr(self, 'head'):
                self.head = self.get
            self.request = request
            self.args = args
            self.kwargs = kwargs
            return self.dispatch(request, *args, **kwargs)

        # take name and docstring from class
        functools.update_wrapper(view, cls, updated=())

        # and possible attributes set by decorators
        # like csrf_exempt from dispatch
        functools.update_wrapper(view, cls.dispatch, assigned=())
        return view


class Wizard(generic_views.PageTitleMixin, views.ModalFormMixin, LazyWizard):
    template_name = 'services/wizard_create.html'
    do_redirect = False
    page_title = _("Add Application")

    def get_prefix(self, *args, **kwargs):
        base = super(Wizard, self).get_prefix(*args, **kwargs)
        fmt = utils.BlankFormatter()
        return fmt.format('{0}_{app_id}', base, **kwargs)

    def get_form_prefix(self, step=None, form=None):
        if step is None:
            return self.steps.step0
        else:
            index0 = self.steps.all.index(step)
            return str(index0)

    def done(self, form_list, **kwargs):
        app_name = self.storage.extra_data['app'].name
        service = tuple(form_list)[0].service
        try:
            attributes = service.extract_attributes()
        except castellan_exception.KeyManagerError as e:
            msg = _("This Application requires encryption, please contact "
                    "your administrator to configure this.")
            messages.error(self.request, msg)
            LOG.exception(e)
            raise
        attributes = helpers.insert_hidden_ids(attributes)

        storage = attributes.setdefault('?', {}).setdefault(
            consts.DASHBOARD_ATTRS_KEY, {})
        storage['name'] = app_name
        attributes['?']['resourceUsages'] = self.aggregate_usages(
            self.init_usages()[1:])

        do_redirect = self.get_wizard_flag('do_redirect')
        wm_form_data = service.cleaned_data.get('workflowManagement')
        if wm_form_data:
            do_redirect = do_redirect or not wm_form_data.get(
                'stay_at_the_catalog', True)

        fail_url = reverse("horizon:app-catalog:environments:index")
        environment_id = utils.ensure_python_obj(kwargs.get('environment_id'))
        quick_environment_id = self.request.session.get('quick_env_id')
        try:
            # NOTE (tsufiev): create new quick environment only if we came
            # here after pressing 'Quick Deploy' button and quick environment
            # wasn't created yet during addition of some referred App
            if environment_id is None:
                if quick_environment_id is None:
                    env = create_quick_environment(self.request)
                    self.request.session['quick_env_id'] = env.id
                    environment_id = env.id
                else:
                    environment_id = quick_environment_id
            env_url = reverse('horizon:app-catalog:environments:services',
                              args=(environment_id,))

            srv = env_api.service_create(
                self.request, environment_id, attributes)
        except exc.HTTPForbidden:
            msg = _("Sorry, you can't add application right now. "
                    "The environment is deploying.")
            exceptions.handle(self.request, msg, redirect=fail_url)
        except Exception:
            message = _('Adding application to an environment failed.')
            LOG.exception(message)
            if quick_environment_id:
                env_api.environment_delete(self.request, quick_environment_id)
                fail_url = reverse('horizon:app-catalog:catalog:index')
            exceptions.handle(self.request, message, redirect=fail_url)
        else:
            message = _("The '{0}' application successfully added to "
                        "environment.").format(app_name)
            LOG.info(message)
            messages.success(self.request, message)

            if do_redirect:
                return http.HttpResponseRedirect(bytes(env_url))
            else:
                srv_id = getattr(srv, '?')['id']
                return self.create_hacked_response(
                    srv_id,
                    attributes['?'].get('name') or attributes.get('name'))

    def create_hacked_response(self, obj_id, obj_name):
        # copy-paste from horizon.forms.views.ModalFormView; should be done
        # that way until we move here from django Wizard to horizon workflow
        if views.ADD_TO_FIELD_HEADER in self.request.META:
            field_id = self.request.META[views.ADD_TO_FIELD_HEADER]
            response = http.HttpResponse(json.dumps(
                [obj_id, html.escape(obj_name)]
            ))
            response["X-Horizon-Add-To-Field"] = field_id
            return response
        else:
            return http.HttpResponse()

    def get_form_initial(self, step):
        env_id = utils.ensure_python_obj(self.kwargs.get('environment_id'))
        if env_id is None:
            env_id = self.request.session.get('quick_env_id')
        init_dict = {'request': self.request,
                     'app_id': self.kwargs['app_id'],
                     'environment_id': env_id}

        return self.initial_dict.get(step, init_dict)

    def _get_wizard_param(self, key):
        param = self.kwargs.get(key)
        return param if param is not None else self.request.POST.get(key)

    def get_wizard_flag(self, key):
        value = self._get_wizard_param(key)
        return utils.ensure_python_obj(value)

    def get_flavors(self):
        try:
            flavors = nova.flavor_list(self.request)
        except nova_exceptions.ClientException:
            message = _("Failed to get list of flavors.")
            exceptions.handle(self.request, message)
            LOG.exception(message)
            flavors = []

        def extract(flavor):
            info = flavor._info
            return {k: v for (k, v) in info.items() if k != 'links'}
        flavors = [extract(f) for f in flavors]
        self.storage.extra_data['flavors'] = flavors
        return json.dumps(flavors)

    def get_flavor_usages(self, form):
        selected_flavor = form.cleaned_data['flavor']
        for flavor in self.storage.extra_data['flavors']:
            if flavor['name'] == selected_flavor:
                return {'ram': flavor['ram'],
                        'vcpus': flavor['vcpus'],
                        'instances': 1}

    def init_usages(self):
        stored_data = self.storage.extra_data
        step_usages = stored_data.get('step_usages')
        if step_usages is None:
            step_usages = [
                collections.defaultdict(dict)
                for step in self.steps.all
            ]
            stored_data['step_usages'] = step_usages

            environment_id = self.kwargs.get('environment_id')
            environment_id = utils.ensure_python_obj(environment_id)
            if environment_id is not None:
                session_id = env_api.Session.get(self.request, environment_id)
                client = api.muranoclient(self.request)
                all_services = client.environments.get(
                    environment_id, session_id).services
                env_usages = self.aggregate_usages(map(
                    lambda svc: svc['?'].get('resourceUsages', {}),
                    all_services))
            else:
                env_usages = collections.defaultdict(dict)
            step_usages.insert(0, env_usages)

        return step_usages

    def process_step(self, form):
        data = super(Wizard, self).process_step(form)
        region = form.region or self.request.user.services_region
        step_usages = self.init_usages()
        if 'flavor' in form.cleaned_data:
            usages = self.get_flavor_usages(form)
            step_usages[self.steps.step0 + 1][region].update({
                'ram': usages['ram'],
                'vcpus': usages['vcpus'],
                'instances': usages['instances']
            })
        else:
            step_usages[self.steps.step0 + 1][region].update({
                'ram': 0,
                'vcpus': 0,
                'instances': 0
            })

        return data

    def update_usages(self, form, context):
        data = self.init_usages()
        usages = quotas.tenant_quota_usages(self.request).usages
        region = self.request.user.services_region
        inf = float('inf')

        def get_usage(group, name, default):
            return usages.get(group, {}).get(name, default)

        context.update({
            'usages': {
                'maxTotalInstances': get_usage('instances', 'quota', inf),
                'totalInstancesUsed': get_usage('instances', 'used', 0),
                'maxTotalCores': get_usage('cores', 'quota', inf),
                'totalCoresUsed': get_usage('cores', 'used', 0),
                'maxTotalRAMSize': get_usage('ram', 'quota', inf),
                'totalRAMUsed': get_usage('ram', 'used', 0),
            },
            'other_usages': {},
            'flavors': self.get_flavors(),
            'contexts': ['', 'info', 'success']
        })
        for step in range(self.steps.step0 + 1):

            def sum_usage(context_key, data_key):
                if context_key not in context['other_usages']:
                    context['other_usages'][context_key] = 0
                context['other_usages'][context_key] += \
                    data[step][region].get(data_key, 0)
            sum_usage('totalInstancesUsed', 'instances')
            sum_usage('totalCoresUsed', 'vcpus')
            sum_usage('totalRAMUsed', 'ram')

        return context

    @staticmethod
    def aggregate_usages(steps):
        result = collections.defaultdict(dict)
        for step in steps:
            for region, region_usages in six.iteritems(step):
                for metric, value in six.iteritems(region_usages):
                    if metric not in result[region]:
                        result[region][metric] = 0
                    result[region][metric] += value
        return result

    def get_context_data(self, form, **kwargs):
        context = super(Wizard, self).get_context_data(form=form, **kwargs)
        mc = api.muranoclient(self.request)
        app_id = self.kwargs.get('app_id')
        app = self.storage.extra_data.get('app')

        # Save extra data to prevent extra API calls
        if not app:
            app = mc.packages.get(app_id)
            self.storage.extra_data['app'] = app

        wizard_id = self.request.POST.get('wizard_id')
        if wizard_id is None:
            wizard_id = uuid.uuid4()

        environment_id = self.kwargs.get('environment_id')
        environment_id = utils.ensure_python_obj(environment_id)
        if environment_id is not None:
            env_name = mc.environments.get(environment_id).name
        else:
            env_name = get_next_quick_environment_name(self.request)

        field_descr, extended_descr = services.get_app_field_descriptions(
            self.request, app_id, self.steps.index)

        context.update({'type': app.fully_qualified_name,
                        'service_name': app.name,
                        'app_id': app_id,
                        'environment_id': environment_id,
                        'environment_name': env_name,
                        'do_redirect': self.get_wizard_flag('do_redirect'),
                        'drop_wm_form': self.get_wizard_flag('drop_wm_form'),
                        'prefix': self.prefix,
                        'wizard_id': wizard_id,
                        'field_descriptions': field_descr,
                        'extended_descriptions': extended_descr,
                        })
        with helpers.current_region(self.request, form.region):
            context = self.update_usages(form, context)
        return context


class IndexView(generic_views.PageTitleMixin, list_view.ListView):
    paginate_by = 6
    page_title = _("Browse")

    def __init__(self, **kwargs):
        super(IndexView, self).__init__(**kwargs)
        self._more = None

    @staticmethod
    def get_object_id(datum):
        return datum.id

    def get_marker(self, index=-1):
        """Get the pagination marker

        Returns the identifier for the object indexed by ``index`` in the
        current data set for APIs that use marker/limit-based paging.
        """
        data = self.object_list
        if data:
            return http_utils.urlquote_plus(self.get_object_id(data[index]))
        else:
            return ''

    def get_query_params(self, internal_query=False):
        if internal_query:
            query_params = {'type': 'Application'}
        else:
            query_params = {}
        category = self.get_current_category()
        search = self.request.GET.get('search')

        if search:
            query_params['search'] = search
        else:
            if category != ALL_CATEGORY_NAME:
                query_params['category'] = category

        query_params['order_by'] = self.request.GET.get('order_by', 'name')
        query_params['sort_dir'] = self.request.GET.get('sort_dir', 'asc')
        return query_params

    def get_queryset(self):
        query_params = self.get_query_params(internal_query=True)
        marker = self.request.GET.get('marker')

        sort_dir = query_params['sort_dir']

        packages = []
        with api.handled_exceptions(self.request):
            query_params['catalog'] = True
            packages, self._more = pkg_api.package_list(
                self.request, filters=query_params, paginate=True,
                marker=marker, page_size=self.paginate_by, sort_dir=sort_dir,
                limit=self.paginate_by)

        if sort_dir == 'desc':
            packages = list(reversed(packages))

        return packages

    def get_template_names(self):
        return ['catalog/index.html']

    def has_next_page(self):
        if self.request.GET.get('sort_dir', 'asc') == 'asc':
            return self._more
        else:
            query_params = self.get_query_params(internal_query=True)
            query_params['sort_dir'] = 'asc'
            query_params['catalog'] = True
            packages, more = pkg_api.package_list(
                self.request, filters=query_params, paginate=True,
                marker=self.get_marker(), page_size=1)
            return len(packages) > 0

    def has_prev_page(self):
        if self.request.GET.get('sort_dir', 'asc') == 'desc':
            return self._more
        else:
            return self.request.GET.get('marker') is not None

    def paginate_queryset(self, queryset, page_size):
        # override this method explicitly to skip unnecessary calculations
        # during call to parent's get_context_data() method
        return None, None, queryset, None

    def get_current_category(self):
        return self.request.GET.get('category', ALL_CATEGORY_NAME)

    def current_page_url(self):
        query_params = self.get_query_params()
        marker = self.request.GET.get('marker')
        sort_dir = self.request.GET.get('sort_dir')
        if marker:
            query_params['marker'] = marker
        if sort_dir:
            query_params['sort_dir'] = sort_dir
        return '{0}?{1}'.format(reverse('horizon:app-catalog:catalog:index'),
                                http_utils.urlencode(query_params))

    def prev_page_url(self):
        query_params = self.get_query_params()
        query_params['marker'] = self.get_marker(0)
        query_params['sort_dir'] = 'desc'
        return '{0}?{1}'.format(reverse('horizon:app-catalog:catalog:index'),
                                http_utils.urlencode(query_params))

    def next_page_url(self):
        query_params = self.get_query_params()
        query_params['marker'] = self.get_marker()
        query_params['sort_dir'] = 'asc'
        return '{0}?{1}'.format(reverse('horizon:app-catalog:catalog:index'),
                                http_utils.urlencode(query_params))

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        context.update({
            'ALL_CATEGORY_NAME': ALL_CATEGORY_NAME,
            'categories': get_categories_list(self.request),
            'current_category': self.get_current_category(),
            'latest_list': cleaned_latest_apps(self.request)
        })

        search = self.request.GET.get('search')
        if search:
            context['search'] = search

        context['tenant_id'] = self.request.session['token'].tenant['id']
        context.update(get_environments_context(self.request))
        context['display_repo_url'] = pkg_consts.DISPLAY_MURANO_REPO_URL
        context['pkg_def_url'] = reverse('horizon:app-catalog:packages:index')
        context['no_apps'] = True
        if self.get_current_category() != ALL_CATEGORY_NAME or search:
            context['no_apps'] = False
        context['MURANO_USE_GLARE'] = getattr(settings, 'MURANO_USE_GLARE',
                                              False)
        return context


class AppDetailsView(tabs.TabView):
    tab_group_class = catalog_tabs.ApplicationTabs
    template_name = 'catalog/app_details.html'
    page_title = '{{ app.name }}'

    app = None

    def get_data(self, **kwargs):
        LOG.debug(('AppDetailsView get_data: {0}'.format(kwargs)))
        app_id = kwargs.get('application_id')
        self.app = api.muranoclient(self.request).packages.get(app_id)
        return self.app

    def get_context_data(self, **kwargs):
        context = super(AppDetailsView, self).get_context_data(**kwargs)
        LOG.debug('AppDetailsView get_context called with kwargs: {0}'.
                  format(kwargs))
        context['app'] = self.app

        context.update(get_environments_context(self.request))

        return context

    def get_tabs(self, request, *args, **kwargs):
        app = self.get_data(**kwargs)
        return self.tab_group_class(request, application=app, **kwargs)
