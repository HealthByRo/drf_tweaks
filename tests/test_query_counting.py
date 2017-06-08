# -*- coding: utf-8 -*-
import warnings

from django.conf.urls import url
from django.http import HttpResponse
from django.test import override_settings
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from drf_tweaks import test_utils
from tests.models import SampleModel


def custom_view(request):
    SampleModel.objects.create(a="a", b="b")
    return HttpResponse()


def many_calls_view(request, n):
    for i in range(int(n)):
        SampleModel.objects.create(a="a", b="b")
    return HttpResponse()


urlpatterns = [
    url(r"^sample/$", custom_view, name="sample"),
    url(r"^calls/(?P<n>[0-9]+)/$", many_calls_view, name="calls")
]


class TestQueryCounter(APITestCase):
    @override_settings(ROOT_URLCONF="tests.test_query_counting", TEST_QUERY_NUMBER_SHOW_WARNING=2,
                       TEST_QUERY_NUMBER_RAISE_ERROR=3)
    def test_query_counting_client(self):
        client = test_utils.QueryCountingAPIClient()
        for method in ("get", "post", "put", "patch"):
            getattr(client, method)(reverse("sample"))
            self.assertEqual(test_utils.test_query_counter, 1)

        # test sending warning
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client.post(reverse("calls", kwargs={"n": 3}))
            self.assertEqual(len(w), 1)

        # test raising error
        with self.assertRaises(Exception):
            client.post(reverse("calls", kwargs={"n": 4}))
