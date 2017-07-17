# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf import settings
from django.conf.urls import url
from django.test import override_settings
from rest_framework import serializers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase
from rest_framework.versioning import AcceptHeaderVersioning

from drf_tweaks.versioning import ApiVersionMixin, VersionedOpenAPIRenderer
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


urlpatterns = [
    url(r"^sample/(?P<pk>[\d]+)$", SampleVersionedApi.as_view(), name="sample_api"),
    url(r"^sample/misconfigured/(?P<pk>[\d]+)$", SampleMisconfiguredApi.as_view(), name="sample_misconfigured_api"),
    url(r"^sample/deprecated-custom/(?P<pk>[\d]+)$", SampleCustomDeprecatedVersionedApi.as_view(),
        name="sample_custom_deprecated_api"),
    url(r"^sample/deprecated-default/(?P<pk>[\d]+)$", SampleDefaultDeprecatedVersionedApi.as_view(),
        name="sample_default_deprecated_api"),
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

    @override_settings(API_VERSIONS_AVAILABLE=["1", "2", "3"])
    def test_versioned_openapi_renderer(self):
        renderer = VersionedOpenAPIRenderer()
        extra = renderer.get_customizations()
        self.assertListEqual(
            extra["produces"], ["application/json; version={}".format(v) for v in ["1", "2", "3"]])
