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
import logging
import re

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import decorators as auth_dec
from django.contrib.formtools.wizard import views as wizard_views
from django.core import urlresolvers as url
from django import http
from django import shortcuts
from django.utils import decorators as django_dec
from django.utils import http as http_utils
from django.utils.translation import ugettext_lazy as _  # noqa
from django.views.generic import list as list_view
from horizon import messages
from horizon import tabs
from horizon.forms import views
from horizon import exceptions

from muranoclient.common import exceptions as exc
from muranodashboard.catalog import tabs as catalog_tabs
from muranodashboard.common import cache
from muranodashboard.dynamic_ui import helpers
from muranodashboard.dynamic_ui import services
from muranodashboard.environments import api
from muranodashboard.environments import consts
from muranodashboard import utils


LOG = logging.getLogger(__name__)
ALL_CATEGORY_NAME = 'All'
LATEST_APPS_QUEUE_LIMIT = 6


class DictToObj(object):
    def __init__(self, **kwargs):
        for key, value in kwargs.iteritems():
            setattr(self, key, value)


def get_available_environments(request):
    envs = []
    for env in api.environments_list(request):
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


@auth_dec.login_required
def switch(request, environment_id,
           redirect_field_name=auth.REDIRECT_FIELD_NAME):
    redirect_to = request.REQUEST.get(redirect_field_name, '')
    if not http_utils.is_safe_url(url=redirect_to, host=request.get_host()):
        redirect_to = settings.LOGIN_REDIRECT_URL

    for env in get_available_environments(request):
        if env.id == environment_id:
            request.session['environment'] = env
            break
    return shortcuts.redirect(redirect_to)


def create_quick_environment(request):
    quick_env_prefix = 'quick-env-'
    quick_env_re = re.compile('^' + quick_env_prefix + '([\d]+)$')

    def parse_number(env):
        match = re.match(quick_env_re, env.name)
        return int(match.group(1)) if match else 0

    numbers = [parse_number(e) for e in api.environments_list(request)]
    new_env_number = 1
    if numbers:
        numbers.sort()
        new_env_number = numbers[-1] + 1

    params = {'name': quick_env_prefix + str(new_env_number)}
    return api.environment_create(request, params)


def update_latest_apps(func):
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


@update_latest_apps
@auth_dec.login_required
def quick_deploy(request, app_id):
    env = create_quick_environment(request)
    try:
        view = Wizard.as_view(services.get_app_forms,
                              condition_dict=services.condition_getter)
        return view(request, app_id=app_id, environment_id=env.id,
                    do_redirect=True, drop_wm_form=True)
    except:
        api.environment_delete(request, env.id)
        raise


def get_image(request, app_id):
    @cache.with_cache('logo', 'logo.png')
    def _get(_request, _app_id):
        return api.muranoclient(_request).packages.get_logo(_app_id)

    content = _get(request, app_id)
    return http.HttpResponse(content=content, content_type='image/png')


class LazyWizard(wizard_views.SessionWizardView):
    """The class which defers evaluation of form_list and condition_dict
    until view method is called. So, each time we load a page with a dynamic
    UI form, it will have markup/logic from the newest YAML-file definition.
    """
    @django_dec.classonlymethod
    def as_view(cls, initforms, *initargs, **initkwargs):
        """
        Main entry point for a request-response process.
        """
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


class Wizard(views.ModalFormMixin, LazyWizard):
    template_name = 'services/wizard_create.html'
    do_redirect = False

    def get_prefix(self, *args, **kwargs):
        base = super(Wizard, self).get_prefix(*args, **kwargs)
        fmt = utils.BlankFormatter()
        return fmt.format('{0}_{environment_id}_{app_id}', base, **kwargs)

    def done(self, form_list, **kwargs):
        environment_id = kwargs.get('environment_id')
        env_url = url.reverse('horizon:murano:environments:services',
                              args=(environment_id,))
        app_name = services.get_service_name(self.request,
                                             kwargs.get('app_id'))

        service = form_list[0].service
        attributes = service.extract_attributes()
        attributes = helpers.insert_hidden_ids(attributes)

        storage = attributes.setdefault('?', {}).setdefault(
            consts.DASHBOARD_ATTRS_KEY, {})
        storage['name'] = app_name

        wm_form_data = service.cleaned_data.get('workflowManagement')
        if wm_form_data:
            do_redirect = not wm_form_data['StayAtCatalog']
        else:
            do_redirect = self.get_wizard_flag('do_redirect')

        fail_url = url.reverse("horizon:murano:environments:index")
        try:
            srv = api.service_create(self.request, environment_id, attributes)
        except exc.HTTPForbidden:
            msg = _("Sorry, you can't add application right now. "
                    "The environment is deploying.")
            exceptions.handle(self.request, msg, redirect=fail_url)
        except Exception:
            exceptions.handle(self.request,
                              _("Sorry, you can't add application right now."),
                              redirect=fail_url)
        else:
            message = "The '{0}' application successfully " \
                      "added to environment.".format(app_name)

            messages.success(self.request, message)

            if do_redirect:
                return http.HttpResponseRedirect(env_url)
            else:
                srv_id = getattr(srv, '?')['id']
                return self.create_hacked_response(srv_id, attributes['name'])

    def create_hacked_response(self, obj_id, obj_name):
        # copy-paste from horizon.forms.views.ModalFormView; should be done
        # that way until we move here from django Wizard to horizon workflow
        if views.ADD_TO_FIELD_HEADER in self.request.META:
            field_id = self.request.META[views.ADD_TO_FIELD_HEADER]
            response = http.HttpResponse(json.dumps([obj_id, obj_name]))
            response["X-Horizon-Add-To-Field"] = field_id
            return response
        else:
            ns_url = 'horizon:murano:catalog:index'
            return http.HttpResponseRedirect(url.reverse(ns_url))

    def get_form_initial(self, step):
        init_dict = {'request': self.request,
                     'environment_id': self.kwargs.get('environment_id')}

        return self.initial_dict.get(step, init_dict)

    def _get_wizard_param(self, key):
        param = self.kwargs.get(key)
        return param if param is not None else self.request.POST.get(key)

    def get_wizard_flag(self, key):
        value = self._get_wizard_param(key)
        if isinstance(value, basestring):
            return value.lower() == 'true'
        else:
            return value

    def get_context_data(self, form, **kwargs):
        context = super(Wizard, self).get_context_data(form=form, **kwargs)
        app_id = self.kwargs.get('app_id')
        app = api.muranoclient(self.request).packages.get(app_id)

        context['field_descriptions'] = services.get_app_field_descriptions(
            self.request, app_id, self.steps.index)
        context.update({'type': app.fully_qualified_name,
                        'service_name': app.name,
                        'app_id': app_id,
                        'environment_id': self.kwargs.get('environment_id'),
                        'do_redirect': self.get_wizard_flag('do_redirect'),
                        'drop_wm_form': self.get_wizard_flag('drop_wm_form'),
                        'prefix': self.prefix,
                        })
        return context


class IndexView(list_view.ListView):
    paginate_by = 6

    def get_queryset(self):
        category = self.kwargs.get('category', ALL_CATEGORY_NAME)
        query_params = {'type': 'Application'}
        search = self.request.GET.get('search')
        if search:
            query_params['search'] = search
        else:
            if category != ALL_CATEGORY_NAME:
                query_params['category'] = category

        pkgs, self.mappings = [], {}
        with api.handled_exceptions(self.request):
            client = api.muranoclient(self.request)
            pkgs = client.packages.filter(**query_params)

        for pkg in pkgs:
            self.mappings[pkg.id] = pkg

        return pkgs

    def get_template_names(self):
        return ['catalog/index.html']

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)

        app_ids = self.request.session.get('latest_apps', [])
        context['latest_list'] = [self.mappings[app_id] for app_id in app_ids
                                  if app_id in self.mappings]

        categories = []
        with api.handled_exceptions(self.request):
            client = api.muranoclient(self.request)
            categories = client.packages.categories()

        if ALL_CATEGORY_NAME not in categories:
            categories.insert(0, ALL_CATEGORY_NAME)
        current_category = self.kwargs.get('category', categories[0])
        context['categories'] = categories
        context['current_category'] = current_category

        search = self.request.GET.get('search')
        if search:
            context['search'] = search

        context.update(get_environments_context(self.request))

        return context


class AppDetailsView(tabs.TabView):
    tab_group_class = catalog_tabs.ApplicationTabs
    template_name = 'catalog/app_details.html'

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
