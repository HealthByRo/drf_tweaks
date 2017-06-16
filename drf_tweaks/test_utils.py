# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.backends.utils import CursorWrapper
from rest_framework.test import APIClient, APITestCase

import warnings


class TooManySQLQueriesException(Exception):
    pass


class TestQueryCounter(object):
    __instance = None

    def __new__(cls, *args, **kwargs):
        if TestQueryCounter.__instance is None:
            TestQueryCounter.__instance = object.__new__(cls)
            TestQueryCounter.__instance.reset()
        return TestQueryCounter.__instance

    def new_query(self, sql, params):
        if "SAVEPOINT" not in sql:
            self._counter += 1
            self._queries_stack.append((sql, params))

    def reset(self):
        self._counter = 0
        self._queries_stack = []

    def get_counter(self):
        return self._counter

    def get_queries_stack(self):
        return self._queries_stack


def hacked_execute(self, sql, params=()):
    TestQueryCounter().new_query(sql, params)
    return self.old_execute(sql, params)


class query_counter(object):
    def __enter__(self):
        # reset counter
        TestQueryCounter().reset()

        # patching CursorWrapper
        CursorWrapper.old_execute = CursorWrapper.execute
        CursorWrapper.execute = hacked_execute

    def __exit__(self, exc_type, exc_val, exc_tb):
        # restore previous function
        CursorWrapper.execute = CursorWrapper.old_execute

        if exc_type is None:
            test_query_counter = TestQueryCounter().get_counter()

            if test_query_counter > getattr(settings, "TEST_QUERY_NUMBER_RAISE_ERROR", 15):
                raise TooManySQLQueriesException("Too many queries executed: %d" % test_query_counter)
            elif test_query_counter > getattr(settings, "TEST_QUERY_NUMBER_SHOW_WARNING", 10):
                warnings.warn("High number of queries executed: %d" % test_query_counter)


class QueryCountingAPIClient(APIClient):
    def get(self, *args, **kwargs):
        with query_counter():
            return super(QueryCountingAPIClient, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        with query_counter():
            return super(QueryCountingAPIClient, self).post(*args, **kwargs)

    def put(self, *args, **kwargs):
        with query_counter():
            return super(QueryCountingAPIClient, self).put(*args, **kwargs)

    def patch(self, *args, **kwargs):
        with query_counter():
            return super(QueryCountingAPIClient, self).patch(*args, **kwargs)


class QueryCountingTestCaseMixin(object):
    client_class = QueryCountingAPIClient


class QueryCountingApiTestCase(QueryCountingTestCaseMixin, APITestCase):
    pass
