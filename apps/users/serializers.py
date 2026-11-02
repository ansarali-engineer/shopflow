"""Serializers for user management endpoints."""
from rest_framework import serializers


class AdminUserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255, required=False)
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(
        max_length=20, required=False, allow_blank=True, allow_null=True
    )
    role = serializers.ChoiceField(
        choices=["customer", "seller", "admin"], required=False
    )
    status = serializers.ChoiceField(
        choices=["active", "suspended", "deleted"], required=False
    )

    def validate_email(self, value):
        return value.strip().lower()