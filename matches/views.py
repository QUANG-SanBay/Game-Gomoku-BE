from django.db.models import Q
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Match, Room
from .serializers import MatchHistorySerializer, RoomSerializer


class RoomListCreateView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		Room.prune_stale()
		rooms = Room.objects.filter(status=Room.Status.WAITING).order_by("-created_at")
		serializer = RoomSerializer(rooms, many=True)
		return Response(serializer.data, status=status.HTTP_200_OK)

	def post(self, request):
		serializer = RoomSerializer(data=request.data, context={"request": request})
		if serializer.is_valid():
			room = serializer.save()
			return Response({"room_id": room.id, "room_name": room.room_name}, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RoomJoinView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		room_id = request.data.get("room_id")
		password = request.data.get("password")
		try:
			room = Room.objects.get(id=room_id)
		except Room.DoesNotExist:
			return Response({"detail": "Room không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

		if room.host is None:
			room.delete()
			return Response({"detail": "Room không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

		if room.status != Room.Status.WAITING:
			return Response({"detail": "Phòng không ở trạng thái chờ."}, status=status.HTTP_400_BAD_REQUEST)
		if room.player_2 and room.player_2_id == request.user.id:
			return Response({"detail": "Bạn đã ở trong phòng."}, status=status.HTTP_400_BAD_REQUEST)
		if room.host_id == request.user.id:
			return Response({"detail": "Bạn là chủ phòng."}, status=status.HTTP_400_BAD_REQUEST)

		if room.has_password:
			if not password or password != room.password:
				return Response({"detail": "Sai mật khẩu phòng."}, status=status.HTTP_403_FORBIDDEN)

		room.player_2 = request.user
		room.status = Room.Status.PLAYING
		room.save(update_fields=["player_2", "status"])

		return Response(RoomSerializer(room).data, status=status.HTTP_200_OK)


class RoomLeaveView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def post(self, request):
		room_id = request.data.get("room_id")
		try:
			room = Room.objects.get(id=room_id)
		except Room.DoesNotExist:
			return Response({"detail": "Room không tồn tại."}, status=status.HTTP_404_NOT_FOUND)

		user = request.user

		if room.host_id == user.id:
			room.delete()
			return Response({"detail": "Phòng đã bị xóa do host rời."}, status=status.HTTP_200_OK)

		if room.player_2_id == user.id:
			room.player_2 = None
			room.status = Room.Status.WAITING
			room.save(update_fields=["player_2", "status"])
			return Response({"detail": "Bạn đã rời phòng."}, status=status.HTTP_200_OK)

		# Nếu vì lý do nào đó không còn người chơi nào, dọn phòng zombie
		if room.current_players == 0:
			room.delete()
			return Response({"detail": "Phòng đã bị xóa."}, status=status.HTTP_200_OK)

		return Response({"detail": "Bạn không ở trong phòng này."}, status=status.HTTP_400_BAD_REQUEST)


class MatchHistoryView(APIView):
	permission_classes = [permissions.IsAuthenticated]

	def get(self, request):
		user = request.user
		matches = Match.objects.filter(Q(player_x=user) | Q(player_o=user)).order_by("-end_time", "-start_time")

		data = [MatchHistorySerializer.from_match(match, user) for match in matches]
		return Response(data, status=status.HTTP_200_OK)
