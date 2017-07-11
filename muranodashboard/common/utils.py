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

try:
    import cPickle as pickle
except ImportError:
    import pickle
import bs4
import string

import iso8601
from muranodashboard.dynamic_ui import yaql_expression
import pytz
import six
import yaql

from horizon.utils import functions as utils

# WrappingColumn is only available in N-horizon
# This make murano-dashboard compatible with Mitaka-horizon
try:
    from horizon.tables import WrappingColumn as Column
except ImportError:
    from horizon.tables import Column as Column  # noqa


def parse_api_error(api_error_html):
    error_html = bs4.BeautifulSoup(api_error_html, "html.parser")
    body = error_html.find('body')
    if (not body or not body.text):
        return None
    h1 = body.find('h1')
    if h1:
        h1.replace_with('')
    return body.text.strip()


def ensure_python_obj(obj):
    mappings = {'True': True, 'False': False, 'None': None}
    return mappings.get(obj, obj)


def adjust_datestr(request, datestr):
    tz = pytz.timezone(utils.get_timezone(request))
    dt = iso8601.parse_date(datestr).astimezone(tz)
    return dt.strftime('%Y-%m-%d %H:%M:%S')


class Bunch(object):
    """Bunch dict/object-like container.

    Bunch container provides both dictionary-like and
    object-like attribute access.
    """
    def __init__(self, **kwargs):
        for key, value in six.iteritems(kwargs):
            setattr(self, key, value)

    def __getitem__(self, item):
        return getattr(self, item)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __delitem__(self, key):
        delattr(self, key)

    def __contains__(self, item):
        return hasattr(self, item)

    def __iter__(self):
        return iter(six.itervalues(self.__dict__))


class BlankFormatter(string.Formatter):
    """Utility class aimed to provide empty string for non-existent keys."""
    def __init__(self, default=''):
        self.default = default

    def get_value(self, key, args, kwargs):
        if isinstance(key, str):
            return kwargs.get(key, self.default)
        else:
            return string.Formatter.get_value(self, key, args, kwargs)


class CustomPickler(object):
    """Custom pickle object to perform correct serializing.

    YAQL Engine is not serializable and it's not necessary to store
    it in cache. This class replace YAQL Engine instance to string.
    """

    def __init__(self, file, protocol=0):
        pickler = pickle.Pickler(file, protocol)
        pickler.persistent_id = self.persistent_id
        self.dump = pickler.dump
        self.clear_memo = pickler.clear_memo

    def persistent_id(self, obj):
        if isinstance(obj, yaql.factory.YaqlEngine):
            return "filtered:YaqlEngine"
        else:
            return None


class CustomUnpickler(object):
    """Custom pickle object to perform correct deserializing.

    This class replace filtered YAQL Engine to the real instance.
    """
    def __init__(self, file):
        unpickler = pickle.Unpickler(file)
        unpickler.persistent_load = self.persistent_load
        self.load = unpickler.load
        self.noload = getattr(unpickler, 'noload', None)

    def persistent_load(self, obj_id):
        if obj_id == 'filtered:YaqlEngine':
            return yaql_expression.YAQL
        else:
            raise pickle.UnpicklingError('Invalid persistent id')
