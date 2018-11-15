# -*- coding: utf-8 -*-
from contextlib import contextmanager
from django.conf import settings
from django.db.backends.utils import CursorWrapper
from django.db.models.sql.compiler import SQLCompiler
from rest_framework.test import APIClient, APITestCase

import re
import traceback
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

    def new_query(self, sql, params, stack):
        for pattern in getattr(settings, "TEST_QUERY_COUNTER_IGNORE_PATTERNS", [".*SAVEPOINT.*"]):
            if re.match(pattern, sql):
                return

        self._counter += 1
        self._queries_stack.append((sql, params, stack))

    def reset(self):
        self._counter = 0
        self._queries_stack = []

    def get_counter(self):
        return self._counter

    def get_queries_stack(self):
        return self._queries_stack


def hacked_execute(self, sql, params=()):
    TestQueryCounter().new_query(sql, params, traceback.format_stack(limit=10)[:8])
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
                if getattr(settings, "TEST_QUERY_NUMBER_PRINT_QUERIES", False):
                    print("=================== Query Stack ===================")
                    for query in TestQueryCounter().get_queries_stack():
                        print(query[:2])
                        print("".join(query[2]))
                        print()
                    print("===================================================")
                raise TooManySQLQueriesException("Too many queries executed: %d" % test_query_counter)
            elif test_query_counter > getattr(settings, "TEST_QUERY_NUMBER_SHOW_WARNING", 10):
                warnings.warn("High number of queries executed: %d" % test_query_counter)


class WouldSelectMultipleTablesForUpdate(Exception):
    pass


def replacement_get_from_clause(self):
    from_, f_params = self.query_lock_limiter_old_get_from_clause()
    if self.query.select_for_update and (len(from_) > 1):
        raise WouldSelectMultipleTablesForUpdate()
    return from_, f_params


def patch_sqlcompiler():
    SQLCompiler.query_lock_limiter_old_get_from_clause = SQLCompiler.get_from_clause
    SQLCompiler.get_from_clause = replacement_get_from_clause


def unpatch_sqlcompiler():
    SQLCompiler.get_from_clause = SQLCompiler.query_lock_limiter_old_get_from_clause
    delattr(SQLCompiler, 'query_lock_limiter_old_get_from_clause')


@contextmanager
def query_lock_limiter(enable=False):
    enabled = enable or getattr(settings, "TEST_DISALLOW_SELECT_MULTIPLE_FOR_UPDATE", False)
    if not enabled:
        yield
        return

    was_already_patched = hasattr(SQLCompiler, 'query_lock_limiter_old_get_from_clause')
    if not was_already_patched:
        patch_sqlcompiler()
    try:
        yield
    finally:
        if not was_already_patched:
            unpatch_sqlcompiler()


class QueryCountingAPIClient(APIClient):
    def get(self, *args, **kwargs):
        with query_counter(), query_lock_limiter():
            return super(QueryCountingAPIClient, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        with query_counter(), query_lock_limiter():
            return super(QueryCountingAPIClient, self).post(*args, **kwargs)

    def put(self, *args, **kwargs):
        with query_counter(), query_lock_limiter():
            return super(QueryCountingAPIClient, self).put(*args, **kwargs)

    def patch(self, *args, **kwargs):
        with query_counter(), query_lock_limiter():
            return super(QueryCountingAPIClient, self).patch(*args, **kwargs)


class QueryCountingTestCaseMixin(object):
    client_class = QueryCountingAPIClient


class QueryCountingApiTestCase(QueryCountingTestCaseMixin, APITestCase):
    pass
