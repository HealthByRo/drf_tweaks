# -*- coding: utf-8 -*-
from copy import copy
from django.db import models
from django.db.models.fields import FieldDoesNotExist
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters


def autofilter(extra_ordering=None, extra_filter=None):
    def wrapped(cls):
        # get indexed fields
        serializer_class = cls().get_serializer_class()
        model_cls = serializer_class.Meta.model
        fields = set([])
        for serializer_field in serializer_class()._readable_fields:
            name = serializer_field.field_name
            try:
                if name == "id" or getattr(model_cls._meta.get_field(name), "db_index", False) \
                        or getattr(model_cls._meta.get_field(name), "unique", False):
                    fields.add(name)
            except FieldDoesNotExist:
                pass

        # add ordering & filtering backends
        if getattr(cls, "filter_backends", None):
            cls.filter_backends = list(set(cls.filter_backends) | {DjangoFilterBackend, filters.OrderingFilter})
        else:
            cls.filter_backends = [DjangoFilterBackend, filters.OrderingFilter]

        # update ordering
        new_ordering = copy(fields)
        if extra_ordering:
            new_ordering |= set(extra_ordering)
        if getattr(cls, "ordering_fields", None):
            new_ordering |= set(cls.ordering_fields)
        cls.ordering_fields = list(new_ordering)

        # update filter fields
        new_filters = {}
        new_filter_keys = copy(fields)
        if extra_filter:
            new_filter_keys |= set(extra_filter)

        update_class = False
        explicit_filters = None
        if hasattr(cls, "filter_class"):
            update_class = True
            if hasattr(cls.filter_class, "Meta"):
                explicit_filters = getattr(cls.filter_class.Meta, "fields", None)
        else:
            explicit_filters = getattr(cls, "filter_fields", None)

        if explicit_filters:
            if isinstance(explicit_filters, dict):
                new_filters = explicit_filters
            else:
                for key in explicit_filters:
                    new_filters[key] = ["exact"]

        for key in new_filter_keys:
            try:
                field = model_cls._meta.get_field(key)
                new_filters[key] = ["exact", "gt", "gte", "lt", "lte", "in", "isnull"]
                if isinstance(field, models.CharField) or isinstance(field, models.TextField):
                    new_filters[key] += ["icontains", "istartswith"]
            except FieldDoesNotExist:
                pass

        if update_class:
            class new_filter_class(cls.filter_class):
                class Meta(cls.filter_class.Meta):
                    fields = new_filters
            cls.filter_class = new_filter_class
        else:
            cls.filter_fields = new_filters

        return cls
    return wrapped
