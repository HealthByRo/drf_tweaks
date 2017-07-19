from django.conf import settings
from rest_framework.permissions import BasePermission
from rest_framework.schemas import SchemaGenerator


class SwaggerAdminPermission(BasePermission):
    def has_permission(self, request, view):
        swagger_settings = getattr(settings, "SWAGGER_SETTINGS", None)
        if swagger_settings and swagger_settings.get("IS_SUPERUSER") and not request.user.is_superuser:
            return False
        return True


class SwaggerSchemaGenerator(SchemaGenerator):
    """
    List all views including the ones that are not compatible with schema generation
    """

    def has_view_permissions(self, path, method, view):
        """
        Overwrite the has_view_permissions to get all links.
        """
        return True

    def get_serializer_fields(self, path, method, view):
        try:
            # check whether serializer is availabe
            view.get_serializer()
        except AssertionError:
            # in case no serializer is specified
            return []
        except AttributeError:
            # in case some data from request is needed to get serializer
            view.get_serializer = lambda: view.get_serializer_class()

        return super(SwaggerSchemaGenerator, self).get_serializer_fields(path, method, view)
