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

import re
import string
import types
import uuid

from django.core import validators
from yaql import utils

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


def explode(_string):
    """Explodes a string into a list of one-character strings."""
    if not _string or not isinstance(_string, basestring):
        return _string
    else:
        return list(_string)


def prepare_regexp(regexp):
    """Converts regular expression string pattern into RegexValidator object.

    Also /regexp/flags syntax is allowed, where flags is a string of
    one-character flags that will be appended to the compiled regexp.
    """
    if regexp.startswith('/'):
        groups = re.match(r'^/(.*)/([A-Za-z]*)$', regexp).groups()
        regexp, flags_str = groups
        flags = 0
        for flag in explode(flags_str):
            flag = flag.upper()
            if hasattr(re, flag):
                flags |= getattr(re, flag)
        return validators.RegexValidator(re.compile(regexp, flags))
    else:
        return validators.RegexValidator(re.compile(regexp))


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
            return rec(utils.limit(val))
        else:
            return val

    return rec(value)


def evaluate(value, context):
    return recursive_apply(
        lambda v, _ctx: hasattr(v, 'evaluate'),
        lambda v, _ctx: v.evaluate(context=_ctx),
        value, context)


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


def int2base(x, base):
    """Converts decimal integers into another number base
     from base-2 to base-36.

    :param x: decimal integer
    :param base: number base, max value is 36
    :return: integer converted to the specified base
    """
    digs = string.digits + string.lowercase
    if x < 0:
        sign = -1
    elif x == 0:
        return '0'
    else:
        sign = 1
    x *= sign
    digits = []
    while x:
        digits.append(digs[x % base])
        x /= base
    if sign < 0:
        digits.append('-')
    digits.reverse()
    return ''.join(digits)
