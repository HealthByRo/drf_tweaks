# -*- coding: utf-8 -*-
from coreapi.compat import force_bytes, force_text
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.renderers import JSONRenderer
from rest_framework.schemas import EndpointInspector
from rest_framework_swagger.renderers import OpenAPICodec, OpenAPIRenderer

import json
import six

try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # Not required for Django <= 1.9, see:
    # https://docs.djangoproject.com/en/1.10/topics/http/middleware/#upgrading-pre-django-1-10-style-middleware
    MiddlewareMixin = object


class IncorrectVersionException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("This API Version is Incorrect.")


class ObsoleteVersionException(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = _("This API Version is Obsolete.")


class ApiVersionMixin(object):
    """
        Use this as first in inheritance chain when creating own API classes
        Returns serializer depending on versioning_serializer_classess and version

        versioning_serializer_classess = {
            1: "x",
            2: "x",
        }

        You can set custom deprecated/obsolete versions
        CUSTOM_DEPRECATED_VERSION = X
        CUSTOM_OBSOLETE_VERSION = Y

        It can be also configured on the settings level as a fixed version
        API_DEPRECATED_VERSION = X
        API_OBSOLETE_VERSION = Y

        or as an offset - for example:
        API_VERSION_DEPRECATION_OFFSET = 6
        API_VERSION_OBSOLETE_OFFSET = 10

        Offset is calculated using the highest version number:
        deprecated = max(self.versioning_serializer_classess.keys() - API_VERSION_DEPRECATION_OFFSET)
        obsolete = max(self.versioning_serializer_classess.keys() - API_VERSION_OBSOLETE_OFFSET)

        If neither is set, deprecation/obsolete will not work. Only the first applicable setting is taken into account
        (in the order as presented above).
    """

    @classmethod
    def get_deprecated_and_obsolete_versions(cls):
        deprecated = getattr(settings, "API_DEPRECATED_VERSION", getattr(cls, "CUSTOM_DEPRECATED_VERSION", None))
        obsolete = getattr(settings, "API_OBSOLETE_VERSION", getattr(cls, "CUSTOM_OBSOLETE_VERSION", None))

        if deprecated is None or obsolete is None:
            API_VERSION_DEPRECATION_OFFSET = getattr(settings, "API_VERSION_DEPRECATION_OFFSET", None)
            API_VERSION_OBSOLETE_OFFSET = getattr(settings, "API_VERSION_OBSOLETE_OFFSET", None)

            if hasattr(cls, "versioning_serializer_classess"):
                max_version = max(cls.versioning_serializer_classess.keys())
                if deprecated is None and API_VERSION_DEPRECATION_OFFSET is not None:
                    deprecated = max_version - API_VERSION_DEPRECATION_OFFSET
                if obsolete is None and API_VERSION_OBSOLETE_OFFSET is not None:
                    obsolete = max_version - API_VERSION_OBSOLETE_OFFSET

        return deprecated, obsolete

    def get_version(self):
        if hasattr(self.request, "version") and self.request.version is not None:
            try:
                version = int(self.request.version)
            except ValueError:
                raise IncorrectVersionException

            return version

    def get_serializer_class(self):
        if hasattr(self.request, "version") and self.request.version is not None:
            # handling deprecate & obsolete versions
            version = self.get_version()
            deprecated, obsolete = self.get_deprecated_and_obsolete_versions()
            if obsolete and version <= obsolete:
                raise ObsoleteVersionException
            elif deprecated and version <= deprecated:
                self.request._request.deprecated = True

            # choosing serializer class
            if hasattr(self, "versioning_serializer_classess"):
                try:
                    return self.versioning_serializer_classess[version]
                except KeyError:
                    raise IncorrectVersionException

        return self.serializer_class


class DeprecationMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        """ Adds deprecation warning - if applicable """
        if getattr(request, "deprecated", False):
            response["Warning"] = "299 - \"This Api Version is Deprecated\""

        return response


class VersionedOpenAPICodec(OpenAPICodec):
    def get_path_customizations(self):
        data = {}
        endpoints = EndpointInspector().get_api_endpoints()
        for endpoint in endpoints:
            # replace {pk} with {id}, as rest framework does in schema generation
            path = endpoint[0].replace("{pk}", "{id}")
            view = endpoint[2]
            view_cls = getattr(view, "cls", None)
            if not view_cls:
                continue

            versioning_classes = getattr(view_cls, "versioning_serializer_classess", None)
            if not versioning_classes:
                continue

            content_type = getattr(settings, "API_DEFAULT_CONTENT_TYPE", "application/json")
            accept_headers = [
                "{}; version={}".format(content_type, v) for v in sorted(versioning_classes.keys(), reverse=True)
            ]
            data[path] = {"produces": accept_headers}

        return data

    def encode(self, document, extra=None, **options):
        result = super(VersionedOpenAPICodec, self).encode(document, extra, **options)
        data = json.loads(force_text(result))

        for path, path_data in six.iteritems(self.get_path_customizations()):
            if path in data["paths"]:
                for method in data["paths"][path].keys():
                    data["paths"][path][method].update(path_data)

        return force_bytes(json.dumps(data))


class VersionedOpenAPIRenderer(OpenAPIRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        if renderer_context["response"].status_code != status.HTTP_200_OK:
            return JSONRenderer().render(data)

        extra = self.get_customizations()
        return VersionedOpenAPICodec().encode(data, extra=extra)
