# -*- coding: utf-8 -*-
import pytest
from contextlib import contextmanager
from django.db.models.sql.compiler import SQLCompiler
from tests.models import SampleModel, SampleModelWithFK


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
def query_lock_limiter():
    was_already_patched = hasattr(SQLCompiler, 'query_lock_limiter_old_get_from_clause')
    if not was_already_patched:
        patch_sqlcompiler()
    try:
        yield
    finally:
        if not was_already_patched:
            unpatch_sqlcompiler()


@pytest.mark.django_db
def test_nonlocking_queries():
    with query_lock_limiter():
        list(SampleModel.objects.all())
        list(SampleModelWithFK.objects.all().select_related())


@pytest.mark.django_db
def test_queries_locking_single_tables():
    with query_lock_limiter():
        list(SampleModel.objects.all().select_for_update())
        list(SampleModelWithFK.objects.all().select_for_update())


@pytest.mark.django_db
def test_query_locking_multiple_tables():
    with pytest.raises(WouldSelectMultipleTablesForUpdate):
        with query_lock_limiter():
            list(SampleModelWithFK.objects.filter(parent__a="").select_for_update())


@pytest.mark.django_db
def test_query_select_related_and_for_udpate():
    with pytest.raises(WouldSelectMultipleTablesForUpdate):
        with query_lock_limiter():
            list(SampleModelWithFK.objects.select_related().select_for_update())
