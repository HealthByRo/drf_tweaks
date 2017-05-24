# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.conf.urls import url
from django.test import TestCase
from django.test import override_settings
from django_filters.rest_framework import DjangoFilterBackend
from django_filters.rest_framework import FilterSet
from rest_framework import filters
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse

from drf_tweaks import serializers
from drf_tweaks.autofilter import autofilter
from tests.models import SampleModel
from tests.models import SampleModelForAutofilter


class SampleModelForAutofilterSerializerVer1(serializers.ModelSerializer):
    class Meta:
        model = SampleModelForAutofilter
        fields = ["id", "fk", "non_indexed_fk", "indexed_int", "non_indexed_int", "indexed_char", "non_indexed_char",
                  "indexed_text", "non_indexed_text", "indexed_url", "non_indexed_url", "indexed_email",
                  "non_indexed_email", "nullable_field", "some_property", "unique_text"]


class SampleModelForAutofilterSerializerVer2(serializers.ModelSerializer):
    class Meta:
        model = SampleModelForAutofilter
        fields = ["id", "fk", "non_indexed_fk", "indexed_int", "non_indexed_int", "indexed_char", "non_indexed_char"]


class SampleFilterClass(FilterSet):
    class Meta:
        model = SampleModelForAutofilter
        fields = ("non_indexed_email", )


class SampleFilterClassV2(FilterSet):
    class Meta:
        model = SampleModelForAutofilter
        fields = {"non_indexed_email": ["exact"]}


@autofilter()
class SampleApiV1(ListAPIView):
    queryset = SampleModelForAutofilter.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SampleModelForAutofilterSerializerVer1
    filter_backends = (filters.OrderingFilter,)


@autofilter()
class SampleApiV2(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SampleModelForAutofilterSerializerVer2
    queryset = SampleModelForAutofilter.objects.all()


@autofilter(extra_ordering=("non_indexed_fk", ), extra_filter=("non_indexed_int", "some_property"))
class SampleApiV3(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SampleModelForAutofilterSerializerVer1
    queryset = SampleModelForAutofilter.objects.all()
    ordering_fields = ("non_indexed_char", )
    filter_fields = ("non_indexed_email", )


@autofilter(extra_filter=("non_indexed_int", ))
class SampleApiV4(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SampleModelForAutofilterSerializerVer1
    queryset = SampleModelForAutofilter.objects.all()
    filter_class = SampleFilterClass


@autofilter()
class SampleApiV5(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SampleModelForAutofilterSerializerVer1
    queryset = SampleModelForAutofilter.objects.all()
    filter_class = SampleFilterClass


@autofilter()
class SampleApiV6(ListAPIView):
    permission_classes = (AllowAny,)
    serializer_class = SampleModelForAutofilterSerializerVer1
    queryset = SampleModelForAutofilter.objects.all()
    filter_class = SampleFilterClassV2


urlpatterns = [
    url(r"^autofilter/$", SampleApiV1.as_view(), name="autofilter_test"),
    url(r"^autofilter-with-class/$", SampleApiV1.as_view(), name="autofilter_with_class_test"),
]


@override_settings(ROOT_URLCONF="tests.test_autofilter")
class TestAutoFilter(TestCase):
    def setUp(self):
        self.sm1 = SampleModel.objects.create(a="a", b="b")
        self.sm2 = SampleModel.objects.create(a="b", b="c")
        self.smfa1 = SampleModelForAutofilter.objects.create(
            fk=self.sm1,
            non_indexed_fk=self.sm1,
            indexed_int=1,
            non_indexed_int=1,
            indexed_char="abc",
            non_indexed_char="cde",
            indexed_text="abcd",
            non_indexed_text="cdef",
            indexed_url="https://www.google.com/?q=1",
            non_indexed_url="https://www.google.com/?q=2",
            indexed_email="abc@gmail.com",
            non_indexed_email="cde@gmail.com",
            nullable_field=1,
            unique_text="a",
        )
        self.smfa2 = SampleModelForAutofilter.objects.create(
            fk=self.sm2,
            non_indexed_fk=self.sm2,
            indexed_int=2,
            non_indexed_int=2,
            indexed_char="fgh",
            non_indexed_char="ijk",
            indexed_text="lorem",
            non_indexed_text="lorem 2",
            indexed_url="https://www.google.com/?q=3",
            non_indexed_url="https://www.google.com/?q=4",
            indexed_email="fgh@gmail.com",
            non_indexed_email="ijk@gmail.com",
            unique_text="b",
        )

    def test_adding_filter_backends(self):
        self.assertIn(filters.OrderingFilter, SampleApiV1.filter_backends)
        self.assertIn(DjangoFilterBackend, SampleApiV1.filter_backends)

    def test_adding_filter_backends_with_existing(self):
        self.assertIn(filters.OrderingFilter, SampleApiV2.filter_backends)
        self.assertIn(DjangoFilterBackend, SampleApiV2.filter_backends)

    def test_adding_ordering_fields(self):
        self.assertEqual(set(SampleApiV1.ordering_fields), {"id", "fk", "indexed_int", "indexed_char", "indexed_text",
                                                            "indexed_url", "indexed_email", "nullable_field",
                                                            "unique_text"})
        self.assertEqual(set(SampleApiV2.ordering_fields), {"id", "fk", "indexed_int", "indexed_char"})

    def test_adding_ordering_fields_with_extra_and_explicit(self):
        self.assertEqual(set(SampleApiV3.ordering_fields), {"id", "fk", "indexed_int", "indexed_char", "indexed_text",
                                                            "indexed_url", "indexed_email", "non_indexed_fk",
                                                            "non_indexed_char", "nullable_field", "unique_text"})

    def test_adding_filter_fields(self):
        self.assertEqual(set(SampleApiV1.filter_fields.keys()), {"id", "fk", "indexed_int", "indexed_char",
                                                                 "indexed_text", "indexed_url", "indexed_email",
                                                                 "nullable_field", "unique_text"})
        self.assertEqual(set(SampleApiV2.filter_fields.keys()), {"id", "fk", "indexed_int", "indexed_char"})

        for key in ("id", "fk", "indexed_int"):
            self.assertEqual(SampleApiV1.filter_fields[key], ["exact", "gt", "gte", "lt", "lte", "in", "isnull"])
        for key in ("indexed_char", "indexed_text", "indexed_url", "indexed_email", "unique_text"):
            self.assertEqual(
                SampleApiV1.filter_fields[key],
                ["exact", "gt", "gte", "lt", "lte", "in", "isnull", "icontains", "istartswith"])

    def test_adding_filter_fields_with_extra_and_explicit(self):
        self.assertEqual(set(SampleApiV3.filter_fields.keys()), {"id", "fk", "indexed_int", "indexed_char",
                                                                 "indexed_text", "indexed_url", "indexed_email",
                                                                 "non_indexed_int", "non_indexed_email",
                                                                 "nullable_field", "unique_text"})

    def test_adding_filter_fields_with_extra_andfilter_class(self):
        self.assertNotEqual(SampleApiV4.filter_class, SampleApiV5.filter_class)
        self.assertNotEqual(SampleApiV4.filter_class.Meta, SampleApiV5.filter_class.Meta)

        self.assertEqual(set(SampleApiV4.filter_class.Meta.fields.keys()), {"id", "fk", "indexed_int", "indexed_char",
                                                                            "indexed_text", "indexed_url",
                                                                            "indexed_email", "non_indexed_int",
                                                                            "non_indexed_email", "nullable_field",
                                                                            "unique_text"})

        self.assertEqual(set(SampleApiV5.filter_class.Meta.fields.keys()), {"id", "fk", "indexed_int", "indexed_char",
                                                                            "indexed_text", "indexed_url",
                                                                            "indexed_email", "non_indexed_email",
                                                                            "nullable_field", "unique_text"})

        self.assertEqual(set(SampleApiV6.filter_class.Meta.fields.keys()), {"id", "fk", "indexed_int", "indexed_char",
                                                                            "indexed_text", "indexed_url",
                                                                            "indexed_email", "non_indexed_email",
                                                                            "nullable_field", "unique_text"})

    def test_integration_filtering(self):
        response = self.client.get(reverse("autofilter_test"), data={"id__gt": 0})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        response = self.client.get(reverse("autofilter_test"), data={"nullable_field__isnull": True})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.smfa2.id)
        self.assertIsNone(response.data[0]["nullable_field"])

        response = self.client.get(reverse("autofilter_test"), data={"nullable_field__isnull": False})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.smfa1.id)
        self.assertEqual(response.data[0]["nullable_field"], 1)

        response = self.client.get(reverse("autofilter_test"), data={"id": self.smfa1.id})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.smfa1.id)

        response = self.client.get(reverse("autofilter_with_class_test"), data={"indexed_int__lt": 2})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.smfa1.id)

        response = self.client.get(
            reverse("autofilter_with_class_test"), data={"indexed_int__lte": 2, "indexed__gt": 0}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.data[0]["id"], self.smfa1.id)
        self.assertEqual(response.data[1]["id"], self.smfa2.id)

        response = self.client.get(
            reverse("autofilter_with_class_test"), data={"indexed_int__lte": 2, "indexed_int__gt": 1}
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.smfa2.id)

        response = self.client.get(reverse("autofilter_with_class_test"), data={"indexed_text__icontains": "Orem"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.smfa2.id)

        response = self.client.get(reverse("autofilter_with_class_test"), data={"indexed_text__istartswith": "lOr"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.smfa2.id)

        response = self.client.get(reverse("autofilter_with_class_test"), data={"indexed_text__istartswith": "lr"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

    def test_integration_ordering(self):
        response = self.client.get(reverse("autofilter_test"), data={"ordering": 'id'})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data[1]["id"], response.data[0]["id"])

        response = self.client.get(reverse("autofilter_test"), data={"ordering": '-id'})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data[0]["id"], response.data[1]["id"])

        response = self.client.get(reverse("autofilter_with_class_test"), data={"ordering": 'indexed_int'})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data[1]["id"], response.data[0]["id"])

        response = self.client.get(reverse("autofilter_with_class_test"), data={"ordering": '-indexed_int'})
        self.assertEqual(response.status_code, 200)
        self.assertGreater(response.data[0]["id"], response.data[1]["id"])
