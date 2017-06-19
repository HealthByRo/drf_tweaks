# -*- coding: utf-8 -*-
from distutils.version import LooseVersion
from django import get_version
from drf_tweaks.serializers import ContextPassing
from rest_framework.serializers import ListSerializer, Serializer

try:
    from django.db.models.fields import related_descriptors
except ImportError:
    from django.db.models.fields import related as related_descriptors


def check_if_related_object(model_field):
    if LooseVersion(get_version()) >= LooseVersion("1.9"):
        return any(isinstance(model_field, x) for x in (related_descriptors.ForwardManyToOneDescriptor,
                                                        related_descriptors.ReverseOneToOneDescriptor))
    else:
        return any(isinstance(model_field, x) for x in (related_descriptors.SingleRelatedObjectDescriptor,
                                                        related_descriptors.ReverseSingleRelatedObjectDescriptor))


def check_if_prefetch_object(model_field):
    if LooseVersion(get_version()) >= LooseVersion("1.9"):
        return any(isinstance(model_field, x) for x in (related_descriptors.ManyToManyDescriptor,
                                                        related_descriptors.ReverseManyToOneDescriptor))
    else:
        return any(isinstance(model_field, x) for x in (related_descriptors.ManyRelatedObjectsDescriptor,
                                                        related_descriptors.ForeignRelatedObjectsDescriptor,
                                                        related_descriptors.ReverseManyRelatedObjectsDescriptor))


def run_autooptimization_discovery(serializer, prefix, select_related_set, prefetch_related_set, is_prefetch,
                                   only_fields, include_fields):
    if not hasattr(serializer, "Meta") or not hasattr(serializer.Meta, "model"):
        return
    model_class = serializer.Meta.model

    if hasattr(serializer, "get_on_demand_fields"):
        on_demand_fields = serializer.get_on_demand_fields()
    else:
        on_demand_fields = set()

    def filter_field_name(field_name, fields_to_serialize):
        if fields_to_serialize is not None:
            return ContextPassing.filter_fields(field_name, fields_to_serialize)
        return None

    for field_name, field in serializer.fields.items():
        if hasattr(serializer, "check_if_needs_serialization"):
            if not serializer.check_if_needs_serialization(field_name, only_fields, include_fields, on_demand_fields):
                continue

        if isinstance(field, ListSerializer):
            if "." not in field.source and hasattr(model_class, field.source):
                model_field = getattr(model_class, field.source)
                if check_if_prefetch_object(model_field):
                    prefetch_related_set.add(prefix + field.source)
                    run_autooptimization_discovery(field.child, prefix + field.source + "__", select_related_set,
                                                   prefetch_related_set, True,
                                                   filter_field_name(field_name, only_fields),
                                                   filter_field_name(field_name, include_fields))
        elif isinstance(field, Serializer):
            if "." not in field.source and hasattr(model_class, field.source):
                model_field = getattr(model_class, field.source)
                if check_if_related_object(model_field):
                    if is_prefetch:
                        prefetch_related_set.add(prefix + field.source)
                    else:
                        select_related_set.add(prefix + field.source)
                    run_autooptimization_discovery(field, prefix + field.source + "__", select_related_set,
                                                   prefetch_related_set, is_prefetch,
                                                   filter_field_name(field_name, only_fields),
                                                   filter_field_name(field_name, include_fields))
        elif "." in field.source:
            field_name = field.source.split(".", 1)[0]
            if hasattr(model_class, field_name):
                model_field = getattr(model_class, field_name)
                if check_if_related_object(model_field):
                    select_related_set.add(prefix + field_name)


class AutoOptimeMixin(object):
    def get_queryset(self):
        # discover select/prefetch related structure
        serializer = self.get_serializer_class()(context=self.get_serializer_context())

        if hasattr(serializer, "get_only_fields_and_include_fields"):
            only_fields, include_fields = serializer.get_only_fields_and_include_fields()
        else:
            only_fields, include_fields = set(), set()

        select_related_set = set()
        prefetch_related_set = set()
        run_autooptimization_discovery(
            serializer, "", select_related_set, prefetch_related_set, False, only_fields, include_fields
        )

        # ammending queryset
        queryset = super(AutoOptimeMixin, self).get_queryset()
        if select_related_set:
            queryset = queryset.select_related(*list(select_related_set))
        if prefetch_related_set:
            queryset = queryset.prefetch_related(*list(prefetch_related_set))
        return queryset
