# -*- coding: utf-8 -*-


def optimize():
    def wrapped(cls):
        # cls._original_get_queryset = cls.get_queryset

        # def get_queryset(self):
        #     serializer = self.get_serializer_class()()
        #     select_related_set = set()
        #     prefetch_related_set = set()
        #     run_discovery("", select_related_set, prefetch_related_set, serializer, False)
        #     queryset = self._original_get_queryset()
        #     print("-------------------------------------->>>")
        #     print("discovered select related", select_related_set)
        #     print("discovered prefetch related", prefetch_related_set)
        #     print("-------------------------------------->>>")
        #     if select_related_set:
        #         queryset = queryset.select_related(*list(select_related_set))
        #     if prefetch_related_set:
        #         queryset = queryset.prefetch_related(*list(prefetch_related_set))
        #     return queryset
        # cls.get_queryset = get_queryset

        return cls
    return wrapped








# from rest_framework.serializers import Serializer, ListSerializer
# from django.db.models.fields.related_descriptors import (ForwardManyToOneDescriptor, ReverseOneToOneDescriptor,
#                                                          ReverseManyToOneDescriptor)
# from chat_api.models import Question, Answer, Group
# from copy import deepcopy


# def check_if_related_object(model_field):
#     if any(isinstance(model_field, x) for x in (ForwardManyToOneDescriptor, ReverseOneToOneDescriptor)):
#         return True
#     return False


# def check_if_prefetch_object(model_field):
#     if any(isinstance(model_field, x) for x in (ReverseManyToOneDescriptor,)):
#         return True
#     return False


# def run_discovery(select_related_prefix, select_related_set, prefetch_related_set, serializer, is_prefetch):
#     if not hasattr(serializer, "Meta"):
#         return
#     if not hasattr(serializer.Meta, "model"):
#         return
#     model_class = serializer.Meta.model

#     for field_name, field in serializer.fields.items():
#         if isinstance(field, ListSerializer):
#             if "." not in field.source and hasattr(model_class, field.source):
#                 model_field = getattr(model_class, field.source)
#                 if check_if_prefetch_object(model_field):
#                     prefetch_related_set.add(f"{select_related_prefix}{field.source}")
#                     run_discovery(
#                         f"{select_related_prefix}{field_name}__", select_related_set, prefetch_related_set,
#                         field.child, True
#                     )
#         elif isinstance(field, Serializer):
#             if "." not in field.source and hasattr(model_class, field.source):
#                 model_field = getattr(model_class, field.source)
#                 if check_if_related_object(model_field):
#                     if is_prefetch:
#                         prefetch_related_set.add(f"{select_related_prefix}{field.source}")
#                     else:
#                         select_related_set.add(f"{select_related_prefix}{field.source}")
#                     run_discovery(
#                         f"{select_related_prefix}{field_name}__", select_related_set, prefetch_related_set, field,
#                         is_prefetch
#                     )
#         elif "." in field.source:
#             field_name = field.source.split(".", 1)[0]
#             if hasattr(model_class, field_name):
#                 model_field = getattr(model_class, field_name)
#                 if check_if_related_object(model_field):
#                     select_related_set.add(f"{select_related_prefix}{field_name}")
