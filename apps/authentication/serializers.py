"""Serializers for authentication endpoints."""
from rest_framework import serializers


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(min_length=8, max_length=128, write_only=True)
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)
    role = serializers.ChoiceField(choices=["customer", "seller", "admin"], default="customer")
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(max_length=255)
    password = serializers.CharField(max_length=128, write_only=True)


class RefreshTokenSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=512)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128, write_only=True)
    new_password = serializers.CharField(min_length=8, max_length=128, write_only=True)


class UpdateProfileSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=100, required=False)
    last_name = serializers.CharField(max_length=100, required=False)
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
