# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from django.test import override_settings
from rest_framework import serializers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.test import APIRequestFactory
from rest_framework.test import APITestCase

from drf_tweaks.serializers import ModelSerializer
from tests.models import SecondLevelModelForContextPassingTest, TopLevelModelForContextPassingTest


factory = APIRequestFactory()


class SecondLevelSerializer(ModelSerializer):
    context_value = serializers.SerializerMethodField()

    def get_context_value(self, obj):
        if "request" in self.context:
            return self.context["request"].GET.get("test_value", "none") + "_second"
        return "missing"

    class Meta:
        model = SecondLevelModelForContextPassingTest
        fields = ["name", "context_value"]


class TopLevelSerializer(ModelSerializer):
    second_data = SecondLevelSerializer(source="second", required=False)
    context_value = serializers.SerializerMethodField()

    def get_context_value(self, obj):
        if "request" in self.context:
            return self.context["request"].GET.get("test_value", "none")
        return "missing"

    class Meta:
        model = TopLevelModelForContextPassingTest
        fields = ["name", "context_value", "second", "second_data"]


class SampleAPI(RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = TopLevelSerializer
    queryset = TopLevelModelForContextPassingTest.objects.all()


urlpatterns = [
    url(r"^test-context-passing/(?P<pk>[\d]+)$", SampleAPI.as_view(), name="test-context-passing"),
]


@override_settings(ROOT_URLCONF="tests.test_serializers_context_passing")
class ContextPassingTestCase(APITestCase):
    def setUp(self):
        self.second = SecondLevelModelForContextPassingTest.objects.create(name="second")
        self.top = TopLevelModelForContextPassingTest.objects.create(second=self.second, name="top")

    def test_context_passing(self):
        response = self.client.get(reverse("test-context-passing", kwargs={"pk": self.top.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                'name': 'top',
                'context_value': 'none',
                'second': 1,
                'second_data': {
                    'name': 'second',
                    'context_value': 'none_second'
                }
            }
        )

        response = self.client.get(reverse("test-context-passing", kwargs={"pk": self.top.pk}), {"test_value": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                'name': 'top',
                'context_value': 'abc',
                'second': 1,
                'second_data': {
                    'name': 'second',
                    'context_value': 'abc_second'
                }
            }
        )
