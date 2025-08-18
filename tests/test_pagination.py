# -*- coding: utf-8 -*-
"""Tests for NoCounts paginators - based on the tests of original paginators from DRF"""

from __future__ import unicode_literals

from django.test import TestCase
from rest_framework.request import Request
from rest_framework.test import APIRequestFactory

from drf_tweaks.pagination import (
    IncorrectLimitOffsetError,
    NoCountsLimitOffsetPagination,
    NoCountsPageNumberPagination,
    NotFound,
)

factory = APIRequestFactory()


class TestNoCountsLimitOffset(TestCase):
    """Unit tests for NoCountsLimitOffsetPagination."""

    def setUp(self):
        class ExamplePagination(NoCountsLimitOffsetPagination):
            default_limit = 10
            max_limit = 15

        class NoDefaultExamplePagination(NoCountsLimitOffsetPagination):
            default_limit = None
            max_limit = 15

        self.pagination = ExamplePagination()
        self.pagination_no_default = NoDefaultExamplePagination()
        self.queryset = range(1, 101)

    def paginate_queryset(self, request):
        return list(self.pagination.paginate_queryset(self.queryset, request))

    def no_default_paginate_queryset(self, request):
        return list(self.pagination_no_default.paginate_queryset(self.queryset, request))

    def get_paginated_content(self, queryset):
        return self.pagination.get_paginated_response(queryset).data

    def test_no_offset(self):
        request = Request(factory.get("/", {"limit": 5}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [1, 2, 3, 4, 5])
        self.assertEqual(
            content,
            {
                "results": [1, 2, 3, 4, 5],
                "previous": None,
                "next": "http://testserver/?limit=5&offset=5",
            },
        )

    def test_single_offset(self):
        request = Request(factory.get("/", {"limit": 5, "offset": 1}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [2, 3, 4, 5, 6])
        self.assertEqual(
            content,
            {
                "results": [2, 3, 4, 5, 6],
                "previous": "http://testserver/?limit=5",
                "next": "http://testserver/?limit=5&offset=6",
            },
        )

    def test_negative_offset(self):
        request = Request(factory.get("/", {"limit": 5, "offset": -3}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [1, 2])
        self.assertEqual(
            content,
            {
                "results": [1, 2],
                "previous": None,
                "next": "http://testserver/?limit=5&offset=2",
            },
        )

    def test_incorrect_negative_offset(self):
        request = Request(factory.get("/", {"limit": 5, "offset": -6}))
        self.assertRaises(IncorrectLimitOffsetError, self.paginate_queryset, request)

    def test_incorrect_limit(self):
        request = Request(factory.get("/", {"limit": -1, "offset": 0}))
        self.assertRaises(IncorrectLimitOffsetError, self.no_default_paginate_queryset, request)

    def test_middle_offset(self):
        request = Request(factory.get("/", {"limit": 5, "offset": 10}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [11, 12, 13, 14, 15])
        self.assertEqual(
            content,
            {
                "results": [11, 12, 13, 14, 15],
                "previous": "http://testserver/?limit=5&offset=5",
                "next": "http://testserver/?limit=5&offset=15",
            },
        )

    def test_ending_offset(self):
        request = Request(factory.get("/", {"limit": 5, "offset": 96}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [97, 98, 99, 100])
        self.assertEqual(
            content,
            {
                "results": [97, 98, 99, 100],
                "previous": "http://testserver/?limit=5&offset=91",
                "next": None,
            },
        )

    def test_erronous_offset(self):
        request = Request(factory.get("/", {"limit": 5, "offset": 1000}))
        queryset = self.paginate_queryset(request)
        self.get_paginated_content(queryset)

    def test_invalid_offset(self):
        """An invalid offset query param should be treated as 0."""
        request = Request(factory.get("/", {"limit": 5, "offset": "invalid"}))
        queryset = self.paginate_queryset(request)
        self.assertEqual(queryset, [1, 2, 3, 4, 5])


class TestNoCountsPageNumberPagination(TestCase):
    """Unit tests for NoCountsPageNumberPagination."""

    def setUp(self):
        class ExamplePagination(NoCountsPageNumberPagination):
            page_size = 5

        self.pagination = ExamplePagination()
        self.queryset = range(1, 100)

    def paginate_queryset(self, request):
        return list(self.pagination.paginate_queryset(self.queryset, request))

    def get_paginated_content(self, queryset):
        response = self.pagination.get_paginated_response(queryset)
        return response.data

    def test_no_page_number(self):
        request = Request(factory.get("/"))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [1, 2, 3, 4, 5])
        self.assertEqual(
            content,
            {
                "results": [1, 2, 3, 4, 5],
                "previous": None,
                "next": "http://testserver/?page=2",
            },
        )

    def test_second_page(self):
        request = Request(factory.get("/", {"page": 2}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [6, 7, 8, 9, 10])
        self.assertEqual(
            content,
            {
                "results": [6, 7, 8, 9, 10],
                "previous": "http://testserver/",
                "next": "http://testserver/?page=3",
            },
        )

    def test_last_page(self):
        request = Request(factory.get("/", {"page": 20}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [96, 97, 98, 99])
        self.assertEqual(
            content,
            {
                "results": [96, 97, 98, 99],
                "previous": "http://testserver/?page=19",
                "next": None,
            },
        )

    def test_over_last_page(self):
        request = Request(factory.get("/", {"page": 21}))
        queryset = self.paginate_queryset(request)
        content = self.get_paginated_content(queryset)
        self.assertEqual(queryset, [])
        self.assertEqual(
            content,
            {"results": [], "previous": "http://testserver/?page=20", "next": None},
        )

    def test_invalid_page(self):
        request = Request(factory.get("/", {"page": 0}))
        self.assertRaises(NotFound, self.paginate_queryset, request)
