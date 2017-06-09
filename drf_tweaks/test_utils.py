# -*- coding: utf-8 -*-
from django.conf import settings
from django.db.backends.utils import CursorWrapper
from rest_framework.test import APIClient, APITestCase

import warnings


class TooManySQLQueriesException(Exception):
    pass


test_query_counter = 0


def hacked_execute(self, sql, params=()):
    global test_query_counter
    if "SAVEPOINT" not in sql:
        test_query_counter += 1
    return self.old_execute(sql, params)


class query_counter(object):
    def __enter__(self):
        # reset counter
        global test_query_counter
        test_query_counter = 0

        # patching CursorWrapper
        CursorWrapper.old_execute = CursorWrapper.execute
        CursorWrapper.execute = hacked_execute

    def __exit__(self, exc_type, exc_val, exc_tb):
        # restore previous function
        CursorWrapper.execute = CursorWrapper.old_execute

        if exc_type is None:
            global test_query_counter

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


class QueryCountingApiTestCase(APITestCase, QueryCountingTestCaseMixin):
    pass
