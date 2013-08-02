"""
Stub file to work around django bug: https://code.djangoproject.com/ticket/7198
"""
from django.db import models
from django.db.models.query import EmptyQuerySet
import copy


class FakeQuerySet(EmptyQuerySet):
    """Turn a list into a Django QuerySet... kind of."""
    def __init__(self, model=None, query=None, using=None, items=[]):
        super(FakeQuerySet, self).__init__(model, query, using)
        self._result_cache = items

    def __getitem__(self, k):
        if isinstance(k, slice):
            obj = self._clone()
            obj._result_cache = super(FakeQuerySet, self).__getitem__(k)
            return obj
        else:
            return super(FakeQuerySet, self).__getitem__(k)

    def count(self):
        return len(self)

    def _clone(self, klass=None, setup=False, **kwargs):
        c = super(FakeQuerySet, self)._clone(klass, setup=setup, **kwargs)
        c._result_cache = copy.copy(self._result_cache)
        return c

    def iterator(self):
        # This slightly odd construction is because we need an empty generator
        # (it raises StopIteration immediately).
        yield iter(self._result_cache).next()

    def order_by(self, *fields):
        obj = self._clone()
        cache = obj._result_cache
        for field in fields:
            reverse = False
            if field[0] == '-':
                reverse = True
                field = field[1:]
            cache = sorted(cache, None, lambda item: getattr(item, field),
                           reverse=reverse)
        obj._result_cache = cache
        return obj

    def distinct(self, *fields):
        obj = self._clone()
        return obj

    def values_list(self, *fields, **kwargs):
        obj = self._clone()
        cache = []
        for item in self._result_cache:
            value = []
            for field in fields:
                value.append(getattr(item, field))
            cache.append(tuple(value))
        if kwargs.get('flat', False) and len(fields) == 1:
            cache = [item[0] for item in cache]
        obj._result_cache = cache
        return obj

    def add(self, item):
        self._result_cache.append(item)

    def remove(self):
        self._result_cache.pop()


class Node(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=20)
    is_primary = models.BooleanField(default=False)
    is_sync = models.BooleanField(default=False)
    is_async = models.BooleanField(default=False)
