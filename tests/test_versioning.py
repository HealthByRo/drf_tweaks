# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json

from django.conf import settings
from django.conf.urls import url
from django.test import override_settings
from django.utils.encoding import force_text
from rest_framework import serializers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework.versioning import AcceptHeaderVersioning

from drf_tweaks.swagger import get_swagger_schema_api_view
from drf_tweaks.versioning import ApiVersionMixin
from tests.models import SampleModel


# sample serializers
class SampleVersionedApiSerializerVer1(serializers.ModelSerializer):
    class Meta:
        model = SampleModel
        fields = ["a"]


class SampleVersionedApiSerializerVer2(serializers.ModelSerializer):

    class Meta:
        model = SampleModel
        fields = ["a", "b"]


# sample APIs
class SampleMisconfiguredApi(ApiVersionMixin, RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    versioning_class = AcceptHeaderVersioning

    # default serializer class
    serializer_class = SampleVersionedApiSerializerVer2
    queryset = SampleModel.objects.all()


class SampleVersionedApi(ApiVersionMixin, RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    versioning_class = AcceptHeaderVersioning

    # serializer versions
    versioning_serializer_classess = {
        1: SampleVersionedApiSerializerVer1,
        2: SampleVersionedApiSerializerVer2

    }
    # default serializer class
    serializer_class = SampleVersionedApiSerializerVer2
    queryset = SampleModel.objects.all()


class SampleDefaultDeprecatedVersionedApi(ApiVersionMixin, RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    versioning_class = AcceptHeaderVersioning

    # serializer versions
    versioning_serializer_classess = {
        1: SampleVersionedApiSerializerVer1,
        2: SampleVersionedApiSerializerVer2,
        3: SampleVersionedApiSerializerVer2
    }
    # default serializer class
    serializer_class = SampleVersionedApiSerializerVer2
    queryset = SampleModel.objects.all()


class SampleCustomDeprecatedVersionedApi(ApiVersionMixin, RetrieveUpdateAPIView):
    CUSTOM_OBSOLETE_VERSION = 1
    CUSTOM_DEPRECATED_VERSION = 2
    permission_classes = (AllowAny,)
    versioning_class = AcceptHeaderVersioning

    # serializer versions
    versioning_serializer_classess = {
        1: SampleVersionedApiSerializerVer1,
        2: SampleVersionedApiSerializerVer2

    }
    # default serializer class
    serializer_class = SampleVersionedApiSerializerVer2
    queryset = SampleModel.objects.all()


class SampleNotVersionedApi(RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SampleVersionedApiSerializerVer2
    queryset = SampleModel.objects.all()


urlpatterns = [
    url(r"^sample/(?P<pk>[\d]+)$", SampleVersionedApi.as_view(), name="sample_api"),
    url(r"^sample/misconfigured/(?P<pk>[\d]+)$", SampleMisconfiguredApi.as_view(), name="sample_misconfigured_api"),
    url(r"^sample/deprecated-custom/(?P<pk>[\d]+)$", SampleCustomDeprecatedVersionedApi.as_view(),
        name="sample_custom_deprecated_api"),
    url(r"^sample/deprecated-default/(?P<pk>[\d]+)$", SampleDefaultDeprecatedVersionedApi.as_view(),
        name="sample_default_deprecated_api"),
    url(r"^sample/not-versioned/(?P<pk>[\d]+)$", SampleNotVersionedApi.as_view(), name="sample_not_versioned_api"),
    url(r"^api-docs$", get_swagger_schema_api_view(), name="api-docs")
]


@override_settings(ROOT_URLCONF="tests.test_versioning",
                   API_VERSION_DEPRECATION_OFFSET=1,
                   API_VERSION_OBSOLETE_OFFSET=2,
                   MIDDLEWARE=settings.MIDDLEWARE + ("drf_tweaks.versioning.DeprecationMiddleware", ),
                   MIDDLEWARE_CLASSES=settings.MIDDLEWARE + ("drf_tweaks.versioning.DeprecationMiddleware", ))
class VersioningApiTestCase(APITestCase):
    def setUp(self):
        self.sample1 = SampleModel.objects.create(a="a", b="b")
        self.sample2 = SampleModel.objects.create(a="a2", b="b2")

    def test_api(self):
        response = self.client.get(reverse("sample_api", kwargs={"pk": self.sample1.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["a"], "a")
        self.assertNotIn("b", response.data)

        response = self.client.get(reverse("sample_api", kwargs={"pk": self.sample1.pk}),
                                   HTTP_ACCEPT="application/json; version=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["a"], "a")
        self.assertEqual(response.data["b"], "b")
        self.assertFalse(response.has_header("Warning"))

        response = self.client.get(reverse("sample_misconfigured_api", kwargs={"pk": self.sample1.pk}),
                                   HTTP_ACCEPT="application/json; version=1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["a"], "a")
        self.assertEqual(response.data["b"], "b")
        self.assertFalse(response.has_header("Warning"))

    def test_default_deprecations(self):
        response = self.client.get(reverse("sample_default_deprecated_api", kwargs={"pk": self.sample1.pk}))
        self.assertEqual(response.status_code, 410)  # obsolete

        response = self.client.get(reverse("sample_default_deprecated_api", kwargs={"pk": self.sample1.pk}),
                                   HTTP_ACCEPT="application/json; version=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["a"], "a")
        self.assertEqual(response.data["b"], "b")
        self.assertTrue(response.has_header("Warning"))

    def test_custom_deprecations(self):
        response = self.client.get(reverse("sample_custom_deprecated_api", kwargs={"pk": self.sample1.pk}))
        self.assertEqual(response.status_code, 410)  # obsolete

        response = self.client.get(reverse("sample_custom_deprecated_api", kwargs={"pk": self.sample1.pk}),
                                   HTTP_ACCEPT="application/json; version=2")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["a"], "a")
        self.assertEqual(response.data["b"], "b")
        self.assertTrue(response.has_header("Warning"))

    def test_incorrect_versions(self):
        response = self.client.get(reverse("sample_api", kwargs={"pk": self.sample1.pk}),
                                   HTTP_ACCEPT="application/json; version=teddybear")
        self.assertEqual(response.status_code, 400)
        response = self.client.get(reverse("sample_api", kwargs={"pk": self.sample1.pk}),
                                   HTTP_ACCEPT="application/json; version=5")
        self.assertEqual(response.status_code, 400)

    def test_versioned_openapi_renderer(self):
        response = self.client.get(reverse("api-docs"))
        self.assertEqual(response.status_code, 200)
        # response.data is a coreapi.Document object
        paths = json.loads(force_text(response.content))["paths"]
        methods = ["put", "patch", "get"]
        # prepare fake schema paths
        endpoints = [
            {"name": u, "path": reverse(u, kwargs={"pk": 1}).replace("1", "{id}")}
            for u in ["sample_api", "sample_custom_deprecated_api", "sample_default_deprecated_api"]
        ]
        for endpoint in endpoints:
            if endpoint["name"] == "sample_default_deprecated_api":
                versions = [3, 2, 1]
            else:
                versions = [2, 1]

            for method in methods:
                self.assertListEqual(paths[endpoint["path"]][method]["produces"], [
                    "application/json; version={}".format(v) for v in versions
                ])

        endpoint = reverse("sample_not_versioned_api", kwargs={"pk": 1}).replace("1", "{id}")
        for method in methods:
            with self.assertRaises(KeyError):
                paths[endpoint][method]["produces"]
