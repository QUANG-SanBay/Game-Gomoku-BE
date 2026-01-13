from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from .models import CustomUser
from .serializers import (
	LeaderboardSerializer,
	LoginSerializer,
	ProfileSerializer,
	ProfileUpdateSerializer,
	PublicProfileSerializer,
	RegisterSerializer,
	UserMeSerializer,
)


class RegisterView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		serializer = RegisterSerializer(data=request.data)
		if serializer.is_valid():
			user = serializer.save()
			tokens = RefreshToken.for_user(user)
			return Response({
				"token": str(tokens.access_token),
				"user_id": user.id,
			}, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		serializer = LoginSerializer(data=request.data)
		if serializer.is_valid():
			return Response({
				"access_token": serializer.validated_data["access"],
				"refresh_token": serializer.validated_data["refresh"],
			}, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		refresh_token = request.data.get("refresh_token")
		if not refresh_token:
			return Response({"detail": "Missing refresh_token"}, status=status.HTTP_400_BAD_REQUEST)
		try:
			token = RefreshToken(refresh_token)
			token.blacklist()
		except Exception:
			return Response({"detail": "Token không hợp lệ."}, status=status.HTTP_400_BAD_REQUEST)
		return Response({"message": "Success"}, status=status.HTTP_200_OK)


class RefreshTokenView(APIView):
	permission_classes = [permissions.AllowAny]

	def post(self, request):
		serializer = TokenRefreshSerializer(data=request.data)
		if serializer.is_valid():
			return Response({"access_token": serializer.validated_data.get("access")}, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MeView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		data = UserMeSerializer(request.user).data
		return Response(data, status=status.HTTP_200_OK)


class ProfileView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		data = ProfileSerializer(request.user).data
		return Response(data, status=status.HTTP_200_OK)


class LeaderboardView(APIView):
	permission_classes = [permissions.AllowAny]

	def get(self, request):
		users = CustomUser.objects.order_by("-elo", "-wins")[:20]
		data = LeaderboardSerializer(users, many=True).data
		return Response(data, status=status.HTTP_200_OK)


class PublicProfileView(APIView):
	permission_classes = [permissions.AllowAny]

	def get(self, request, pk):
		try:
			user = CustomUser.objects.get(pk=pk)
		except CustomUser.DoesNotExist:
			return Response({"detail": "Không tìm thấy người dùng."}, status=status.HTTP_404_NOT_FOUND)
		data = PublicProfileSerializer(user, context={"request": request}).data
		return Response(data, status=status.HTTP_200_OK)


class ProfileUpdateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		data = ProfileSerializer(request.user, context={"request": request}).data
		return Response(data, status=status.HTTP_200_OK)

	def put(self, request):
		serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(ProfileSerializer(request.user, context={"request": request}).data, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
