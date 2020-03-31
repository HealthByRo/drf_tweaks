from contextlib import contextmanager
from django.conf import settings
from django.db.models.sql.compiler import SQLCompiler


class WouldSelectMultipleTablesForUpdate(Exception):
    pass


def replacement_as_sql(self, *args, **kwargs):
    sql = self.query_lock_limiter_old_as_sql(*args, **kwargs)
    # We're doing this after as_sql because at this point all the
    # processing to gather information about used tables is guaranteed to be done.
    table_names = list(self.query.table_map.keys())
    if self.query.select_for_update and (len(table_names) > 1) and not self.query.select_for_update_of:
        # if select_for_update_of is defined, it means we are locking only explicitly defined rows, so we do not apply
        # the mechanism to detect accidental multi-locks
        whitelisted = sorted(table_names) in self.query_lock_limiter_whitelist
        if not whitelisted:
            raise WouldSelectMultipleTablesForUpdate(
                f"Query would select_for_update more than one table: {sql}.  "
                f"Add {table_names} to settings.TEST_SELECT_FOR_UPDATE_WHITELISTED_TABLE_SETS "
                f"to allow it."
            )
    return sql


def patch_sqlcompiler(whitelisted_table_sets):
    SQLCompiler.query_lock_limiter_old_as_sql = SQLCompiler.as_sql
    SQLCompiler.as_sql = replacement_as_sql
    SQLCompiler.query_lock_limiter_whitelist = [
        sorted(tables) for tables in whitelisted_table_sets
    ]


def unpatch_sqlcompiler():
    SQLCompiler.as_sql = SQLCompiler.query_lock_limiter_old_as_sql
    delattr(SQLCompiler, "query_lock_limiter_old_as_sql")


@contextmanager
def query_lock_limiter(enable=False, whitelisted_table_sets=[]):
    enabled = enable or getattr(
        settings, "TEST_SELECT_FOR_UPDATE_LIMITER_ENABLED", False
    )
    if not enabled:
        yield
        return

    was_already_patched = hasattr(SQLCompiler, "query_lock_limiter_old_as_sql")
    if not was_already_patched:
        whitelist = whitelisted_table_sets or getattr(
            settings, "TEST_SELECT_FOR_UPDATE_WHITELISTED_TABLE_SETS", []
        )
        patch_sqlcompiler(whitelist)
    try:
        yield
    finally:
        if not was_already_patched:
            unpatch_sqlcompiler()
