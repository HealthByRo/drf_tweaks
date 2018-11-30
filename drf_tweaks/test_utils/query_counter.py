from django.conf import settings
from django.db.backends.utils import CursorWrapper

import contextlib
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
        for pattern in getattr(
            settings, "TEST_QUERY_COUNTER_IGNORE_PATTERNS", [".*SAVEPOINT.*"]
        ):
            if re.match(pattern, sql):
                return

        self._counter += 1
        self._queries_stack.append((sql, params, stack))

    def reset(self):
        self._counter = 0
        self._queries_stack = []
        self._frozen = False

    def get_counter(self):
        return self._counter

    def get_queries_stack(self):
        return self._queries_stack

    @contextlib.contextmanager
    def freeze():
        # having a contextmanager that works nicely as a classmethod turned out
        # to be tricky.
        instance = TestQueryCounter()
        prev_frozen = instance._frozen
        instance._frozen = True
        try:
            yield
        finally:
            instance._frozen = prev_frozen


def hacked_execute(self, sql, params=()):
    counter = TestQueryCounter()
    if not counter._frozen:
        counter.new_query(sql, params, traceback.format_stack(limit=10)[:8])
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

            if test_query_counter > getattr(
                settings, "TEST_QUERY_NUMBER_RAISE_ERROR", 15
            ):
                if getattr(settings, "TEST_QUERY_NUMBER_PRINT_QUERIES", False):
                    print("=================== Query Stack ===================")
                    for query in TestQueryCounter().get_queries_stack():
                        print(query[:2])
                        print("".join(query[2]))
                        print()
                    print("===================================================")
                raise TooManySQLQueriesException(
                    "Too many queries executed: %d" % test_query_counter
                )
            elif test_query_counter > getattr(
                settings, "TEST_QUERY_NUMBER_SHOW_WARNING", 10
            ):
                warnings.warn(
                    "High number of queries executed: %d" % test_query_counter
                )
