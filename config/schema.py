"""OpenAPI schema extensions for ShopFlow authentication."""
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from drf_spectacular.openapi import AutoSchema
from drf_spectacular.types import OpenApiTypes
from rest_framework import serializers
from rest_framework.views import APIView


class ApiErrorSerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = serializers.JSONField(required=False)


class ApiResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField()
    data = serializers.JSONField(allow_null=True)
    error = ApiErrorSerializer(allow_null=True)
    meta = serializers.JSONField(required=False, allow_null=True)


class ShopFlowAutoSchema(AutoSchema):
    def _uses_fallback_schema(self):
        return isinstance(self.view, APIView) and not hasattr(
            self.view, "serializer_class"
        )

    def get_request_serializer(self):
        if self._uses_fallback_schema():
            return OpenApiTypes.OBJECT
        return super().get_request_serializer()

    def get_response_serializers(self):
        if self._uses_fallback_schema():
            return ApiResponseSerializer
        return super().get_response_serializers()


class ShopFlowJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.authentication.backends.ShopFlowJWTAuthentication"
    name = "BearerAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
