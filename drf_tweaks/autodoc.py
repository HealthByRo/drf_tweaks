# -*- coding: utf-8 -*-
""" auto documentation for django-rest-framework

    usage:
        @autodoc("List or create an account")
        class PaginatedVersionedAccountApi(ApiVersionMixin, ListCreateAPIView):
            ...

    you can skip certain classes:
    @autodoc(skip_classess=[PaginationAutodoc])

    or add certain classess:
    @autodoc(add_classess=[CustomAutodoc])

    you can also override autodoc classess
    @autodoc(classess=[PaginationAutodoc])
"""
from __future__ import unicode_literals
from django.conf import settings
from rest_framework.settings import import_from_string

import six


class AutodocBase(object):
    """ base class for autodoc """
    applies_to = ("get", "post", "put", "patch", "delete")

    @classmethod
    def _generate_yaml(cls, documented_cls, method_name):
        raise NotImplementedError

    @classmethod
    def _generate_text(cls, documented_cls, method_name):
        """ text that will be appended to the result """
        raise NotImplementedError

    @classmethod
    def _get_text_and_yaml(cls, docstring):
        if not docstring:
            docstring = ""

        if "---" in docstring:
            text, yaml = docstring.split("---")
        else:
            text, yaml = docstring, ""
        return text.strip(), yaml.strip()

    @classmethod
    def _format_docstring(cls, text, yaml):
        text = text.strip()
        yaml = yaml.strip()
        result = text
        if yaml:
            result += "\n---\n" + yaml
        return result

    @classmethod
    def update_docstring(cls, documented_cls, base_doc, docstring, method_name):
        text, yaml = cls._get_text_and_yaml(docstring)
        text += "\n\n" + cls._generate_text(documented_cls, method_name)
        yaml += "\n\n" + cls._generate_yaml(documented_cls, method_name)
        return cls._format_docstring(text, yaml)


class PaginationAutodoc(AutodocBase):
    """ Autodoc for pagination - applied only when pagination is present. Please not that pagination is present by
        default, so to avoid having pagination params in retrieve-type generics, you have to explicitly put there
        pagination_class = None """
    applies_to = ("get", )

    @classmethod
    def _generate_yaml(cls, documented_cls, method_name):
        return ""

    @classmethod
    def _generate_text(cls, documented_cls, method_name):
        params = []
        if hasattr(documented_cls, "pagination_class"):
            for item_name in dir(documented_cls.pagination_class):
                if item_name.endswith("_query_param") and getattr(documented_cls.pagination_class, item_name, None):
                    params.append("%s -- optional, %s" % (
                        getattr(documented_cls.pagination_class, item_name),
                        item_name.replace("_query_param", "")
                    ))
        return "\n".join(params)


class PermissionsAutodoc(AutodocBase):
    """ Autodoc for permission classes - shows permissions + docstrings for them """
    applies_to = ("get", "post", "put", "patch", "delete")

    @classmethod
    def _generate_yaml(cls, documented_cls, method_name):
        return ""

    @classmethod
    def _generate_text(cls, documented_cls, method_name):
        text = ""
        if hasattr(documented_cls, "permission_classes") and documented_cls.permission_classes:
            text = "<b>Permissions:</b>\n"
            for permission_cls in documented_cls.permission_classes:
                text += "<i>%s</i>\n" % permission_cls.__name__
                if permission_cls.__doc__:
                    text += "%s\n" % permission_cls.__doc__
        return text


class VersioningAutodoc(AutodocBase):
    """ autodoc for versioning - applied only when ApiVersionMixin is present and
        rest_framework.versioning.AcceptHeaderVersioning """
    applies_to = ("get", "post", "put", "patch")

    @classmethod
    def _generate_yaml(cls, documented_cls, method_name):
        versions = []
        if hasattr(documented_cls, "versioning_serializer_classess"):
            for version in sorted(documented_cls.versioning_serializer_classess.keys(), reverse=True):
                versions.append("\t- application/json; version=%d" % version)
        if versions:
            return "produces:\n" + "\n".join(versions)
        return ""

    @classmethod
    def _generate_text(cls, documented_cls, method_name):
        text = ""
        if hasattr(documented_cls, "get_deprecated_and_obsolete_versions"):
            deprecated, obsolete = documented_cls.get_deprecated_and_obsolete_versions()
            if deprecated and deprecated > 0:
                text += "\nVersions lower or equal to %d are <b>deprecated</b>" % deprecated
            if obsolete and obsolete > 0:
                text += "\n\nVersions lower or equal to %d are <b>obsolete</b>" % obsolete
        return text


class OrderingAndFilteringAutodoc(AutodocBase):
    """ Adding ordering & filtering informations """
    applies_to = ("get", )

    @classmethod
    def _generate_yaml(cls, documented_cls, method_name):
        return ""

    @classmethod
    def _generate_text(cls, documented_cls, method_name):
        text = "\n\n<b>Limiting response fields</b>\n\n\twill limit response to only requested fields.\n\n\t"
        text += "usage: ?fields=FIELD_NAME_1,FIELD_NAME_2\n\n\n\n"
        ordering_fields = getattr(documented_cls, "ordering_fields", None)
        if ordering_fields:
            text += "<b>Sorting:</b>\n\n\tusage: ?ordering=FIELD_NAME,-OTHER_FIELD_NAME\n\n\tavailable fields: "
            text += ", ".join(sorted(ordering_fields))

        filter_fields = getattr(documented_cls, "filter_fields", None)
        filter_class = getattr(documented_cls, "filter_class", None)
        if filter_class:
            filter_fields = filter_class.Meta.fields
        if filter_fields:
            if ordering_fields:
                text += "\n\n\n\n"
            text += "<b>Filtering:</b>"
            if isinstance(filter_fields, dict):
                for key in sorted(filter_fields.keys()):
                    text += "\n\n\t%s: %s" % (
                        key, ", ".join(x if x == "exact" else "__" + x for x in filter_fields[key])
                    )
            else:
                for field in sorted(filter_fields):
                    text += "\n\n\t%s: exact" % field

        return text


class BaseInfoAutodoc(AutodocBase):
    """ insert the base docstring to each method - this will be displayed on the swagger folded list """
    @classmethod
    def _generate_yaml(cls, documented_cls, method_name):
        if hasattr(documented_cls, "get_custom_%s_doc_yaml" % method_name):
            return getattr(documented_cls, "get_custom_%s_doc_yaml" % method_name)()
        else:
            return ""

    @classmethod
    def _generate_text(cls, documented_cls, method_name):
        if hasattr(documented_cls, "get_custom_%s_doc" % method_name):
            return getattr(documented_cls, "get_custom_%s_doc" % method_name)()
        else:
            return ""

    @classmethod
    def update_docstring(cls, documented_cls, base_doc, docstring, method_name):
        text, yaml = cls._get_text_and_yaml(docstring)
        if not base_doc:
            base_doc = ""

        text = base_doc + "\n\n" + text + "\n\n" + cls._generate_text(documented_cls, method_name)
        yaml += "\n\n" + cls._generate_yaml(documented_cls, method_name)
        return cls._format_docstring(text, yaml)


if hasattr(settings, "AUTODOC_DEFAULT_CLASSESS"):
    DEFAULT_CLASSESS = [import_from_string(x, "") for x in settings.AUTODOC_DEFAULT_CLASSESS]
else:
    DEFAULT_CLASSESS = (BaseInfoAutodoc, PermissionsAutodoc, OrderingAndFilteringAutodoc, PaginationAutodoc,
                        VersioningAutodoc)


def autodoc(base_doc="", classess=DEFAULT_CLASSESS, add_classess=None, skip_classess=None):
    def copy_method(cls, method_name, method):
        """ create facade for a method with preservation of original docstring """
        def shadow_method(self, *args, **kwargs):
            return method(self, *args, **kwargs)
        shadow_method.__doc__ = method.__doc__
        setattr(cls, method_name, shadow_method)

    def wrapped(cls):
        applies_to = set([])
        classess_to_apply = [c for c in classess if not skip_classess or c not in skip_classess]
        if add_classess:
            classess_to_apply += [c for c in add_classess if not skip_classess or c not in skip_classess]

        for autodoc_class in classess_to_apply:
            applies_to |= set(autodoc_class.applies_to)

        # Create facades for original methods - docstring of methods are immutable, so we need to change docstring of
        # functions. But without shadowing the method.__func__ will point to the same function for classes that
        # inherits them from the same parents.
        for method_name in applies_to:
            method = getattr(cls, method_name, None)
            if method:
                copy_method(cls, method_name, method)

        # update docstrings
        for autodoc_class in classess_to_apply:
            for method_name in autodoc_class.applies_to:
                method = getattr(cls, method_name, None)
                if method:
                    six.get_unbound_function(method).__doc__ = \
                        autodoc_class.update_docstring(cls, base_doc, six.get_unbound_function(method).__doc__,
                                                       method_name)
        return cls
    return wrapped
