# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from rest_framework import serializers
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import AllowAny
from rest_framework.test import APITestCase
from rest_framework.versioning import AcceptHeaderVersioning

from drf_tweaks.autodoc import BaseInfoAutodoc
from drf_tweaks.autodoc import PaginationAutodoc
from drf_tweaks.autodoc import autodoc
from drf_tweaks.pagination import NoCountsLimitOffsetPagination
from drf_tweaks.versioning import ApiVersionMixin


# sample serializers
class SampleVersionedApiSerializerVer1(serializers.Serializer):
    pass


# sample APIs
@autodoc("Test")
class SampleNotVersionedApi(RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    pagination_class = None


class SampleVersionedApi(ApiVersionMixin, RetrieveUpdateAPIView):
    permission_classes = (AllowAny,)
    versioning_class = AcceptHeaderVersioning
    pagination_class = NoCountsLimitOffsetPagination

    # serializer versions
    versioning_serializer_classess = {
        1: SampleVersionedApiSerializerVer1,
        2: SampleVersionedApiSerializerVer1

    }
    # default serializer class
    serializer_class = SampleVersionedApiSerializerVer1


@autodoc("Test", classess=(BaseInfoAutodoc, ))
class SampleVersionedApiT1(SampleVersionedApi):
    def put(self, *args, **kwargs):
        """ some description
        ---
        some yaml"""
        pass

    def get(self, *args, **kwargs):
        """ some description
        ---
        some yaml"""
        pass

    def patch(self, *args, **kwargs):
        """ some description
        ---
        some yaml"""
        pass

    @classmethod
    def get_custom_get_doc(cls):
        return "custom doc"

    @classmethod
    def get_custom_patch_doc_yaml(cls):
        return "custom yaml"


@autodoc(skip_classess=(PaginationAutodoc, ))
class SampleVersionedApiT2(SampleVersionedApi):
    CUSTOM_DEPRECATED_VERSION = 2
    CUSTOM_OBSOLETE_VERSION = 1


@autodoc("Test", classess=(BaseInfoAutodoc, ), add_classess=(PaginationAutodoc, ))
class SampleVersionedApiT3(SampleVersionedApi):
    pass


# expected docstrings
BASE_INFO_ONLY = "Test"
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

VERSIONING_GET = """Versions lower or equal to 2 are <b>deprecated</b>

Versions lower or equal to 1 are <b>obsolete</b>
---
produces:
\t- application/json; version=2
\t- application/json; version=1"""

PAGINATION_GET = """Test

limit -- optional, limit
offset -- optional, offset"""


class AutodocTestCase(APITestCase):
    def test_base_info_only(self):
        self.assertEqual(SampleNotVersionedApi.get.__doc__, BASE_INFO_ONLY)

    def test_base_info_with_custom_data_and_overriding_classes(self):
        self.assertEqual(SampleVersionedApiT1.put.__doc__, BASE_INFO_WITH_DOCSTRING_PUT)
        self.assertEqual(SampleVersionedApiT1.get.__doc__, BASE_INFO_WITH_DOCSTRING_AND_CUSTOM_GET)
        self.assertEqual(SampleVersionedApiT1.patch.__doc__, BASE_INFO_WITH_DOCSTRING_AND_CUSTOM_PATCH)

    def test_versioning_autodoc_and_skipping_classess(self):
        self.assertEqual(SampleVersionedApiT2.get.__doc__, VERSIONING_GET)

    def test_pagination_autodoc_and_adding_classess(self):
        self.assertEqual(SampleVersionedApiT3.get.__doc__, PAGINATION_GET)
        self.assertEqual(SampleVersionedApiT3.put.__doc__, BASE_INFO_ONLY)

    def test_autodoc_with_existing_docstring(self):
        self.assertEqual(SampleNotVersionedApi.get.__doc__, BASE_INFO_ONLY)
