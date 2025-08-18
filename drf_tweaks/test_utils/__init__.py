from contextlib import contextmanager

from rest_framework.test import APIClient, APITestCase

from drf_tweaks.test_utils.lock_limiter import (
    WouldSelectMultipleTablesForUpdate,  # noqa: F401
    query_lock_limiter,
)
from drf_tweaks.test_utils.query_counter import (
    TestQueryCounter,  # noqa: F401
    TooManySQLQueriesException,  # noqa: F401
    query_counter,
)


class DatabaseAccessLintingAPIClient(APIClient):
    def __init__(self, with_lock_limiter=True, *args, **kwargs):
        self.with_lock_limiter = with_lock_limiter
        super(DatabaseAccessLintingAPIClient, self).__init__(*args, **kwargs)

    def get(self, *args, **kwargs):
        with self.linters():
            return super(DatabaseAccessLintingAPIClient, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        with self.linters():
            return super(DatabaseAccessLintingAPIClient, self).post(*args, **kwargs)

    def put(self, *args, **kwargs):
        with self.linters():
            return super(DatabaseAccessLintingAPIClient, self).put(*args, **kwargs)

    def patch(self, *args, **kwargs):
        with self.linters():
            return super(DatabaseAccessLintingAPIClient, self).patch(*args, **kwargs)

    @contextmanager
    def linters(self):
        if self.with_lock_limiter:
            with query_counter(), query_lock_limiter():
                yield
        else:
            with query_counter():
                yield


class DatabaseAccessLintingApiTestCase(APITestCase):
    client_class = DatabaseAccessLintingAPIClient


# The QueryCountingAPIClient is here for backwards compatibility;
# choose DatabaseAccessLintingAPIClient instead.
class QueryCountingAPIClient(DatabaseAccessLintingAPIClient):
    def __init__(self, *args, **kwargs):
        super(QueryCountingAPIClient, self).__init__(with_lock_limiter=False, *args, **kwargs)


class QueryCountingTestCaseMixin(object):
    client_class = QueryCountingAPIClient


class QueryCountingApiTestCase(QueryCountingTestCaseMixin, APITestCase):
    pass
