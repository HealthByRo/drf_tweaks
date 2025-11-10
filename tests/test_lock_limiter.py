# -*- coding: utf-8 -*-
import pytest
from django.http import HttpResponse
from django.test import override_settings
from django.urls import re_path

from drf_tweaks.test_utils import (
    DatabaseAccessLintingApiTestCase,
    WouldSelectMultipleTablesForUpdate,
    query_lock_limiter,
)
from tests.models import SampleModel, SampleModelWithFK


@pytest.mark.django_db
def test_nonlocking_queries():
    with query_lock_limiter(enable=True):
        list(SampleModel.objects.all())
        list(SampleModelWithFK.objects.all().select_related())


@pytest.mark.django_db
def test_queries_locking_single_tables():
    with query_lock_limiter(enable=True):
        list(SampleModel.objects.all().select_for_update())
        list(SampleModelWithFK.objects.all().select_for_update())


@pytest.mark.django_db
def test_query_locking_multiple_tables():
    with pytest.raises(WouldSelectMultipleTablesForUpdate):
        with query_lock_limiter(enable=True):
            list(SampleModelWithFK.objects.filter(parent__a="").select_for_update())


@pytest.mark.django_db
def test_query_locking_whitelisted_multiple_tables():
    whitelist = [["tests_samplemodel", "tests_samplemodelwithfk"]]
    with query_lock_limiter(enable=True, whitelisted_table_sets=whitelist):
        list(SampleModelWithFK.objects.filter(parent__a="").select_for_update())


@pytest.mark.django_db
def test_query_select_related_and_for_update():
    with pytest.raises(WouldSelectMultipleTablesForUpdate):
        with query_lock_limiter(enable=True):
            list(SampleModelWithFK.objects.select_related().select_for_update())


@pytest.mark.django_db
def test_query_select_related_and_for_update_when_using_of():
    with query_lock_limiter(enable=True):
        list(SampleModelWithFK.objects.select_related().select_for_update(of=("self",)))


def grabby_select_view(request):
    list(SampleModelWithFK.objects.select_related().select_for_update())
    return HttpResponse()


urlpatterns = [re_path(r"", grabby_select_view, name="sample")]


class TestLockLimiter(DatabaseAccessLintingApiTestCase):
    @override_settings(ROOT_URLCONF="tests.test_lock_limiter")
    def test_disabled(self):
        for method in ("get", "post", "put", "patch"):
            getattr(self.client, method)("/")

    @override_settings(
        ROOT_URLCONF="tests.test_lock_limiter",
        TEST_SELECT_FOR_UPDATE_LIMITER_ENABLED=True,
    )
    def test_enabled(self):
        for method in ("get", "post", "put", "patch"):
            with pytest.raises(WouldSelectMultipleTablesForUpdate):
                getattr(self.client, method)("/")

    @override_settings(
        ROOT_URLCONF="tests.test_lock_limiter",
        TEST_SELECT_FOR_UPDATE_LIMITER_ENABLED=True,
        TEST_SELECT_FOR_UPDATE_WHITELISTED_TABLE_SETS=[["tests_samplemodel", "tests_samplemodelwithfk"]],
    )
    def test_whitelist(self):
        for method in ("get", "post", "put", "patch"):
            getattr(self.client, method)("/")
