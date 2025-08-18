# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django_filters.rest_framework import FilterSet
from rest_framework import filters, serializers
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.test import APITestCase
from rest_framework.versioning import AcceptHeaderVersioning

from drf_tweaks.autodoc import (
    BaseInfoAutodoc,
    OnDemandFieldsAutodoc,
    PaginationAutodoc,
    PermissionsAutodoc,
    autodoc,
)
from drf_tweaks.autofilter import autofilter
from drf_tweaks.pagination import NoCountsLimitOffsetPagination
from drf_tweaks.serializers import ModelSerializer
from drf_tweaks.versioning import ApiVersionMixin
from tests.models import SampleModel, SampleModelForAutofilter


# sample serializers
class SampleVersionedApiSerializerVer1(serializers.Serializer):
    pass


class SampleModelForAutofilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SampleModelForAutofilter
        fields = [
            "id",
            "fk",
            "non_indexed_fk",
            "indexed_int",
            "non_indexed_int",
            "indexed_char",
            "non_indexed_char",
        ]


class SampleOnDemandFieldsSerializer(ModelSerializer):
    on_demand_field = serializers.SerializerMethodField()

    def get_on_demand_field(self, obj):
        return "on_demand"

    class Meta:
        model = SampleModel
        fields = ["a"]
        on_demand_fields = ["b", "on_demand_field"]


class NoDocAllowAny(AllowAny):
    pass


class DocumentedAllowAny(AllowAny):
    """this is some doc for permission that should be added to doc"""

    pass


# sample APIs
@autodoc("Test")
class SampleNotVersionedApi(RetrieveUpdateAPIView):
    permission_classes = (DocumentedAllowAny,)
    pagination_class = None


class SampleVersionedApi(ApiVersionMixin, RetrieveUpdateAPIView):
    permission_classes = (NoDocAllowAny,)
    versioning_class = AcceptHeaderVersioning
    pagination_class = NoCountsLimitOffsetPagination

    # serializer versions
    versioning_serializer_classess = {
        1: SampleVersionedApiSerializerVer1,
        2: SampleVersionedApiSerializerVer1,
    }
    # default serializer class
    serializer_class = SampleVersionedApiSerializerVer1


@autodoc("Test", classess=(BaseInfoAutodoc,))
class SampleVersionedApiT1(SampleVersionedApi):
    permission_classes = (NoDocAllowAny,)

    def put(self, *args, **kwargs):
        """some description
        ---
        some yaml"""
        pass

    def get(self, *args, **kwargs):
        """some description
        ---
        some yaml"""
        pass

    def patch(self, *args, **kwargs):
        """some description
        ---
        some yaml"""
        pass

    @classmethod
    def get_custom_get_doc(cls):
        return "custom doc"

    @classmethod
    def get_custom_patch_doc_yaml(cls):
        return "custom yaml"


@autodoc(skip_classess=(PaginationAutodoc, PermissionsAutodoc))
class SampleVersionedApiT2(SampleVersionedApi):
    permission_classes = (NoDocAllowAny,)
    CUSTOM_DEPRECATED_VERSION = 2
    CUSTOM_OBSOLETE_VERSION = 1


@autodoc("Test", classess=(BaseInfoAutodoc,), add_classess=(PaginationAutodoc,))
class SampleVersionedApiT3(SampleVersionedApi):
    pass


@autodoc("Test")
@autofilter()
class SampleAutofilterApi(ListAPIView):
    queryset = SampleModelForAutofilter.objects.all()
    permission_classes = (NoDocAllowAny,)
    serializer_class = SampleModelForAutofilterSerializer
    filter_backends = (filters.OrderingFilter,)
    pagination_class = None


class SampleFilterClass(FilterSet):
    class Meta:
        model = SampleModelForAutofilter
        fields = []


@autodoc("Test")
@autofilter()
class SampleAutofilterApiV2(ListAPIView):
    queryset = SampleModelForAutofilter.objects.all()
    permission_classes = (NoDocAllowAny,)
    serializer_class = SampleModelForAutofilterSerializer
    filter_backends = (filters.OrderingFilter,)
    filter_class = SampleFilterClass
    pagination_class = None


@autodoc("Test")
class SampleAutofilterApiV3(ListAPIView):
    queryset = SampleModelForAutofilter.objects.all()
    permission_classes = (NoDocAllowAny,)
    serializer_class = SampleModelForAutofilterSerializer
    filter_fields = ("id", "fk")
    ordering_fields = ("id", "fk")
    pagination_class = None


@autodoc(classess=(OnDemandFieldsAutodoc,))
class SampleOnDemandAutodocApi(ListAPIView):
    queryset = SampleModel.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = SampleOnDemandFieldsSerializer


# expected docstrings
BASE_INFO_ONLY = "Test"

BASE_INFO_WITH_PERMISSIONS = """Test

<b>Permissions:</b>
<i>DocumentedAllowAny</i>
this is some doc for permission that should be added to doc



<b>Limiting response fields</b>

\twill limit response to only requested fields.

\tusage: ?fields=FIELD_NAME_1,FIELD_NAME_2"""

BASE_INFO_WITH_DOCSTRING_PUT = """Test

some description
---
some yaml"""

BASE_INFO_WITH_DOCSTRING_AND_CUSTOM_GET = """Test

some description

custom doc
---
some yaml"""

BASE_INFO_WITH_DOCSTRING_AND_CUSTOM_PATCH = """Test

some description
---
some yaml

custom yaml"""

VERSIONING_GET = """<b>Limiting response fields</b>

\twill limit response to only requested fields.

\tusage: ?fields=FIELD_NAME_1,FIELD_NAME_2


Versions lower or equal to 2 are <b>deprecated</b>

Versions lower or equal to 1 are <b>obsolete</b>
---
produces:
\t- application/json; version=2
\t- application/json; version=1"""

PAGINATION_GET = """Test

limit -- optional, limit
offset -- optional, offset"""

AUTOFILTERED_GET = """Test

<b>Permissions:</b>
<i>NoDocAllowAny</i>



<b>Limiting response fields</b>

\twill limit response to only requested fields.

\tusage: ?fields=FIELD_NAME_1,FIELD_NAME_2



<b>Sorting:</b>

\tusage: ?ordering=FIELD_NAME,-OTHER_FIELD_NAME

\tavailable fields: fk, id, indexed_char, indexed_int



<b>Filtering:</b>

\tfk: exact, __gt, __gte, __lt, __lte, __in, __isnull

\tid: exact, __gt, __gte, __lt, __lte, __in, __isnull

\tindexed_char: exact, __gt, __gte, __lt, __lte, __in, __isnull, __icontains, __istartswith

\tindexed_int: exact, __gt, __gte, __lt, __lte, __in, __isnull"""

FILTER_SORTING_GET = """Test

<b>Permissions:</b>
<i>NoDocAllowAny</i>



<b>Limiting response fields</b>

\twill limit response to only requested fields.

\tusage: ?fields=FIELD_NAME_1,FIELD_NAME_2



<b>Sorting:</b>

\tusage: ?ordering=FIELD_NAME,-OTHER_FIELD_NAME

\tavailable fields: fk, id



<b>Filtering:</b>

\tfk: exact

\tid: exact"""


ON_DEMAND_GET = """<b>Access to on demand fields</b>

\tavailable fields: b, on_demand_field"""


class AutodocTestCase(APITestCase):
    def test_base_info_only(self):
        self.assertEqual(SampleNotVersionedApi.get.__doc__, BASE_INFO_WITH_PERMISSIONS)

    def test_base_info_with_custom_data_and_overriding_classes(self):
        self.assertEqual(SampleVersionedApiT1.put.__doc__, BASE_INFO_WITH_DOCSTRING_PUT)
        self.assertEqual(SampleVersionedApiT1.get.__doc__, BASE_INFO_WITH_DOCSTRING_AND_CUSTOM_GET)
        self.assertEqual(
            SampleVersionedApiT1.patch.__doc__,
            BASE_INFO_WITH_DOCSTRING_AND_CUSTOM_PATCH,
        )

    def test_versioning_autodoc_and_skipping_classess(self):
        self.assertEqual(SampleVersionedApiT2.get.__doc__, VERSIONING_GET)

    def test_pagination_autodoc_and_adding_classess(self):
        self.assertEqual(SampleVersionedApiT3.get.__doc__, PAGINATION_GET)
        self.assertEqual(SampleVersionedApiT3.put.__doc__, BASE_INFO_ONLY)

    def test_autodoc_with_existing_docstring(self):
        self.assertEqual(SampleNotVersionedApi.get.__doc__, BASE_INFO_WITH_PERMISSIONS)

    def test_autodoc_with_autofilter(self):
        self.assertEqual(SampleAutofilterApi.get.__doc__, AUTOFILTERED_GET)
        self.assertEqual(SampleAutofilterApiV2.get.__doc__, AUTOFILTERED_GET)

    def test_autodoc_for_filter_and_order(self):
        self.assertEqual(SampleAutofilterApiV3.get.__doc__, FILTER_SORTING_GET)

    def test_autodoc_for_on_demand_fields(self):
        self.assertEqual(SampleOnDemandAutodocApi.get.__doc__, ON_DEMAND_GET)

    def test_autodoc_preserves_wrapped(self):
        self.assertTrue(callable(SampleNotVersionedApi.get.__wrapped__))
