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

import copy
import re
import uuid
from django.core.validators import RegexValidator
import types
import yaql
import yaql.context as ctx
from yaql import utils as yaql_utils

_LOCALIZABLE_KEYS = set(['label', 'help_text', 'error_messages'])


def is_localizable(keys):
    return set(keys).intersection(_LOCALIZABLE_KEYS)


def camelize(name):
    """Turns snake_case name into SnakeCase."""
    return ''.join([bit.capitalize() for bit in name.split('_')])


def decamelize(name):
    """Turns CamelCase/camelCase name into camel_case."""
    pat = re.compile(r'([A-Z]*[^A-Z]*)(.*)')
    bits = []
    while True:
        head, tail = re.match(pat, name).groups()
        bits.append(head)
        if tail:
            name = tail
        else:
            break
    return '_'.join([bit.lower() for bit in bits])


def explode(string):
    """Explodes a string into a list of one-character strings."""
    if not string:
        return string
    bits = []
    while True:
        head, tail = string[0], string[1:]
        bits.append(head)
        if tail:
            string = tail
        else:
            break
    return bits


def prepare_regexp(regexp):
    """Converts regular expression string pattern into RegexValidator object.

    Also /regexp/flags syntax is allowed, where flags is a string of
    one-character flags that will be appended to the compiled regexp."""
    if regexp.startswith('/'):
        groups = re.match(r'^/(.*)/([A-Za-z]*)$', regexp).groups()
        regexp, flags_str = groups
        flags = 0
        for flag in explode(flags_str):
            flag = flag.upper()
            if hasattr(re, flag):
                flags |= getattr(re, flag)
        return RegexValidator(re.compile(regexp, flags))
    else:
        return RegexValidator(re.compile(regexp))


def get_yaql_expr(expr):
    return isinstance(expr, types.DictType) and expr.get('YAQL', None)


def recursive_apply(predicate, transformer, value, *args):
    def rec(val):
        if predicate(val, *args):
            return rec(transformer(val, *args))
        elif isinstance(val, types.DictType):
            return dict((rec(k), rec(v)) for (k, v) in val.iteritems())
        elif isinstance(val, types.ListType):
            return [rec(v) for v in val]
        elif isinstance(val, types.TupleType):
            return tuple([rec(v) for v in val])
        elif isinstance(val, types.GeneratorType):
            return rec(yaql_utils.limit(val))
        else:
            return val

    return rec(value)


def evaluate(value, context):
    return recursive_apply(
        lambda v, _ctx: hasattr(v, 'evaluate'),
        lambda v, _ctx: v.evaluate(context=_ctx),
        value, context)


def parse(value):
    return recursive_apply(
        get_yaql_expr,
        lambda v: yaql.parse(get_yaql_expr(v)),
        value)


def insert_hidden_ids(application):
    def wrap(k, v):
        if k == '?':
            v['id'] = str(uuid.uuid4())
            return k, v
        else:
            return rec(k), rec(v)

    def rec(val):
        if isinstance(val, types.DictType):
            return dict(wrap(k, v) for k, v in val.iteritems())
        elif isinstance(val, types.ListType):
            return [rec(v) for v in val]
        else:
            return val

    return rec(application)


@ctx.ContextAware()
def _repeat(context, template, start, end):
    # context.data = copy.deepcopy(context.parent_context.data)
    for i in xrange(start(), end()):
        context.set_data(i, '$index')
        yield evaluate(template(), context)


def _interpolate(template, number):
    return template().replace('#', '{0}').format(number())


def _coalesce(arg, *args):
    arg = arg()
    if arg is None:
        for arg in args:
            arg = arg()
            if arg is not None:
                return arg
    else:
        return arg


YAQL_FUNCTIONS = [
    ('test', lambda self, pattern: re.match(pattern(), self()) is not None,),
    ('repeat', _repeat,),
    ('interpolate', _interpolate),
    ('coalesce', _coalesce),
]


def create_yaql_context(functions=YAQL_FUNCTIONS):
    context = yaql.create_context()
    for name, func in functions:
        context.register_function(func, name)
    return context
