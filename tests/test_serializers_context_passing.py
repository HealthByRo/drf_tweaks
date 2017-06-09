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
from tests.models import (SecondLevelModelForContextPassingTest, TopLevelModelForContextPassingTest,
                          ThirdLevelModelForNestedFilteringTest)


factory = APIRequestFactory()


class ThirdLevelSerializer(ModelSerializer):
    on_demand_field = serializers.SerializerMethodField()

    def get_on_demand_field(self, obj):
        return "on_demand_third"

    class Meta:
        model = ThirdLevelModelForNestedFilteringTest
        fields = ["name", "on_demand_field"]
        on_demand_fields = ["on_demand_field"]


class SecondLevelSerializer(ModelSerializer):
    context_value = serializers.SerializerMethodField()
    on_demand_field = serializers.SerializerMethodField()
    third_data = ThirdLevelSerializer(source="third")

    def get_context_value(self, obj):
        if "request" in self.context:
            return self.context["request"].GET.get("test_value", "none") + "_second"
        return "missing"

    def get_on_demand_field(self, obj):
        return "on_demand"

    class Meta:
        model = SecondLevelModelForContextPassingTest
        fields = ["name", "context_value", "on_demand_field", "third_data"]
        on_demand_fields = ["on_demand_field", "third_data"]


class TopLevelSerializer(ModelSerializer):
    second_data = SecondLevelSerializer(source="second", required=False)
    context_value = serializers.SerializerMethodField()
    on_demand_field = serializers.SerializerMethodField()
    second_on_demand_field = serializers.SerializerMethodField()

    def get_context_value(self, obj):
        if "request" in self.context:
            return self.context["request"].GET.get("test_value", "none")
        return "missing"

    def get_on_demand_field(self, obj):
        return "on_demand"

    def get_second_on_demand_field(self, obj):
        return "second_on_demand"

    class Meta:
        model = TopLevelModelForContextPassingTest
        fields = ["name", "context_value", "second", "second_data", "on_demand_field", "second_on_demand_field"]
        on_demand_fields = ["on_demand_field", "second_on_demand_field"]


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
                "name": "top",
                "context_value": "none",
                "second": 1,
                "second_data": {
                    "name": "second",
                    "context_value": "none_second"
                }
            }
        )

        response = self.client.get(reverse("test-context-passing", kwargs={"pk": self.top.pk}), {"test_value": "abc"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                "name": "top",
                "context_value": "abc",
                "second": 1,
                "second_data": {
                    "name": "second",
                    "context_value": "abc_second"
                }
            }
        )


@override_settings(ROOT_URLCONF="tests.test_serializers_context_passing")
class OnDemandFieldsAndNestedFieldsFilteringTestCase(APITestCase):
    def setUp(self):
        self.third = ThirdLevelModelForNestedFilteringTest.objects.create(name="third")
        self.second = SecondLevelModelForContextPassingTest.objects.create(name="second", third=self.third)
        self.top = TopLevelModelForContextPassingTest.objects.create(second=self.second, name="top")

    def test_on_demand_field(self):
        # w/o specifying on demand fields - fields are not included
        cp_url = reverse("test-context-passing", kwargs={"pk": self.top.pk})
        response = self.client.get(cp_url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                "name": "top",
                "context_value": "none",
                "second": 1,
                "second_data": {
                    "name": "second",
                    "context_value": "none_second"
                }
            }
        )

        # when added "include_fields=on_demand_fields - field is included
        response = self.client.get(cp_url, {"include_fields": "on_demand_field"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                "name": "top",
                "context_value": "none",
                "second": 1,
                "on_demand_field": "on_demand",
                "second_data": {
                    "name": "second",
                    "context_value": "none_second"
                }
            }
        )

        # using fields
        response = self.client.get(cp_url, {"fields": "name,on_demand_field,second_on_demand_field"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                "name": "top",
                "on_demand_field": "on_demand",
                "second_on_demand_field": "second_on_demand"
            }
        )

        # nested include_fields
        response = self.client.get(cp_url, {
            "include_fields": "on_demand_field,second_on_demand_field,second_data__on_demand_field"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                "name": "top",
                "context_value": "none",
                "second": 1,
                "on_demand_field": "on_demand",
                "second_on_demand_field": "second_on_demand",
                "second_data": {
                    "name": "second",
                    "context_value": "none_second",
                    "on_demand_field": "on_demand",
                }
            }
        )

        # using fields: nested
        response = self.client.get(cp_url, {
            "fields": "name,on_demand_field,second_data__name,second_data__on_demand_field"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                "name": "top",
                "on_demand_field": "on_demand",
                "second_data": {
                    "name": "second",
                    "on_demand_field": "on_demand",
                }
            }
        )

        # using fields & include_fields (on different levels) & on three levels
        response = self.client.get(cp_url, {
            "fields": "name,second_data,second_data__third_data",
            "include_fields": "second_data__third_data__on_demand_field"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.data, {
                "name": "top",
                "second_data": {
                    "third_data": {
                        "name": "third",
                        "on_demand_field": "on_demand_third"
                    }
                }
            }
        )
