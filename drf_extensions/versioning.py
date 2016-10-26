# -*- coding: utf-8 -*-
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException


try:
    from django.utils.deprecation import MiddlewareMixin
except ImportError:
    # Not required for Django <= 1.9, see:
    # https://docs.djangoproject.com/en/1.10/topics/http/middleware/#upgrading-pre-django-1-10-style-middleware
    MiddlewareMixin = object


class IncorrectVersionException(APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _('This API Version is Incorrect.')


class ObsoleteVersionException(APIException):
    status_code = status.HTTP_410_GONE
    default_detail = _('This API Version is Obsolete.')


class ApiVersionMixin(object):
    """
        Use this as first in inheritance chain when creating own API classes
        Returns serializer depending on versioning_serializer_classess and version

        versioning_serializer_classess = {
            1: 'x',
            2: 'x',
        }

        You can set custom deprecated/obsolete versions
        CUSTOM_DEPRECATED_VERSION = X
        CUSTOM_OBSOLETE_VERSION = Y

        It can be also configured on the settings level, for example:
        API_VERSION_DEPRECATION_OFFSET = 6
        API_VERSION_OBSOLETE_OFFSET = 10

        If neither is set, deprecation/obsolete will not work. Only one of the aboce may be defined

        This is calculated using the highest version number:
        deprecated = max(self.versioning_serializer_classess.keys() - API_VERSION_DEPRECATION_OFFSET)
        obsolete = max(self.versioning_serializer_classess.keys() - API_VERSION_OBSOLETE_OFFSET)
    """

    @classmethod
    def get_deprecated_and_obsolete_versions(cls):
        deprecated = getattr(cls, 'CUSTOM_DEPRECATED_VERSION', None)
        obsolete = getattr(cls, 'CUSTOM_OBSOLETE_VERSION', None)

        if deprecated is None or obsolete is None:
            API_VERSION_DEPRECATION_OFFSET = getattr(settings, "API_VERSION_DEPRECATION_OFFSET", None)
            API_VERSION_OBSOLETE_OFFSET = getattr(settings, "API_VERSION_OBSOLETE_OFFSET", None)

            max_version = max(cls.versioning_serializer_classess.keys())
            if deprecated is None and API_VERSION_DEPRECATION_OFFSET is not None:
                deprecated = max_version - API_VERSION_DEPRECATION_OFFSET
            if obsolete is None and API_VERSION_OBSOLETE_OFFSET is not None:
                obsolete = max_version - API_VERSION_OBSOLETE_OFFSET

        return deprecated, obsolete

    def get_serializer_class(self):
        if hasattr(self, 'versioning_serializer_classess') and hasattr(self.request, 'version')\
                and self.request.version is not None:
            try:
                version = int(self.request.version)
                deprecated, obsolete = self.get_deprecated_and_obsolete_versions()
                if version <= obsolete:
                    raise ObsoleteVersionException
                elif version <= deprecated:
                    self.request._request.deprecated = True

                return self.versioning_serializer_classess[version]
            except ValueError:
                raise IncorrectVersionException
            except KeyError:
                raise IncorrectVersionException
        else:
            return self.serializer_class


class DeprecationMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        """ Adds deprecation warning - if applicable """
        if getattr(request, 'deprecated', False):
            response['Warning'] = '299 - "This Api Version is Deprecated"'

        return response
