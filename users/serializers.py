from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = CustomUser
        fields = ["email", "full_name", "password", "confirm_password"]

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError("Mật khẩu xác nhận không khớp.")
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password")
        password = validated_data.pop("password")
        email = validated_data.get("email")
        username = CustomUser.generate_username_from_email(email)
        user = CustomUser.objects.create(username=username, **validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, attrs):
        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(username=email, password=password)
        if not user:
            raise serializers.ValidationError("Email hoặc mật khẩu không đúng.")
        if not user.is_active:
            raise serializers.ValidationError("Tài khoản đã bị vô hiệu hóa.")

        tokens = RefreshToken.for_user(user)
        attrs["access"] = str(tokens.access_token)
        attrs["refresh"] = str(tokens)
        return attrs


class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "username", "wins", "losses", "elo"]


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["id", "full_name", "username", "email", "wins", "losses", "elo"]


class LeaderboardSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["username", "elo", "wins"]


class PublicProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["username", "elo", "wins", "losses", "draws", "avatar", "full_name"]


class ProfileUpdateSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(source="full_name", required=False)

    class Meta:
        model = CustomUser
        fields = ["first_name", "avatar"]
        extra_kwargs = {
            "avatar": {"required": False, "allow_null": True},
        }
