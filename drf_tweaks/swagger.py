from django.conf import settings
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.schemas import SchemaGenerator
from rest_framework.views import APIView

from drf_tweaks.versioning import VersionedOpenAPIRenderer


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


def get_swagger_schema_api_view(permissions=None, renderers=None):
    if not permissions:
        permissions = [AllowAny, SwaggerAdminPermission]

    if not renderers:
        renderers = [VersionedOpenAPIRenderer]

    class SwaggerSchemaView(APIView):
        permission_classes = permissions
        _ignore_model_permissions = True
        exclude_from_schema = True
        renderer_classes = renderers

        def get(self, request):
            generator = SwaggerSchemaGenerator()
            # disable versioning when schema is being generated
            request.version = None
            schema = generator.get_schema(request=request)
            return Response(schema)

    return SwaggerSchemaView
