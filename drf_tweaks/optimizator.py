# -*- coding: utf-8 -*-
from django.db.models.fields.related_descriptors import (ForwardManyToOneDescriptor, ReverseManyToOneDescriptor,
                                                         ReverseOneToOneDescriptor)
from drf_tweaks.serializers import ContextPassing
from rest_framework.serializers import ListSerializer, Serializer


def check_if_related_object(model_field):
    if any(isinstance(model_field, x) for x in (ForwardManyToOneDescriptor, ReverseOneToOneDescriptor)):
        return True
    return False


def check_if_prefetch_object(model_field):
    if any(isinstance(model_field, x) for x in (ReverseManyToOneDescriptor,)):
        return True
    return False


def run_autooptimization_discovery(serializer, prefix, select_related_set, prefetch_related_set, is_prefetch,
                                   fields_to_serialize):
    if not hasattr(serializer, "Meta") or not hasattr(serializer.Meta, "model"):
        return
    model_class = serializer.Meta.model

    def filter_field_name(field_name, fields_to_serialize):
        if fields_to_serialize is not None:
            return ContextPassing.filter_fields(field_name, fields_to_serialize)
        return None

    for field_name, field in serializer.fields.items():
        if fields_to_serialize is not None and field_name not in fields_to_serialize:
            continue

        if isinstance(field, ListSerializer):
            if "." not in field.source and hasattr(model_class, field.source):
                model_field = getattr(model_class, field.source)
                if check_if_prefetch_object(model_field):
                    prefetch_related_set.add(f"{prefix}{field.source}")
                    run_autooptimization_discovery(field.child, f"{prefix}{field.source}__", select_related_set,
                                                   prefetch_related_set, True,
                                                   filter_field_name(field_name, fields_to_serialize))
        elif isinstance(field, Serializer):
            if "." not in field.source and hasattr(model_class, field.source):
                model_field = getattr(model_class, field.source)
                if check_if_related_object(model_field):
                    if is_prefetch:
                        prefetch_related_set.add(f"{prefix}{field.source}")
                    else:
                        select_related_set.add(f"{prefix}{field.source}")
                    run_autooptimization_discovery(field, f"{prefix}{field.source}__", select_related_set,
                                                   prefetch_related_set, is_prefetch,
                                                   filter_field_name(field_name, fields_to_serialize))
        elif "." in field.source:
            field_name = field.source.split(".", 1)[0]
            if hasattr(model_class, field_name):
                model_field = getattr(model_class, field_name)
                if check_if_related_object(model_field):
                    select_related_set.add(f"{prefix}{field_name}")


def optimize():
    def wrapped(cls):
        cls._original_get_queryset = cls.get_queryset

        def get_queryset(self):
            # discover select/prefetch related structure
            serializer = self.get_serializer_class()()
            select_related_set = set()
            prefetch_related_set = set()
            run_autooptimization_discovery(serializer, "", select_related_set, prefetch_related_set, False, None)

            # ammending queryset
            queryset = self._original_get_queryset()
            if select_related_set:
                queryset = queryset.select_related(*list(select_related_set))
            if prefetch_related_set:
                queryset = queryset.prefetch_related(*list(prefetch_related_set))
            return queryset
        cls.get_queryset = get_queryset

        return cls
    return wrapped
