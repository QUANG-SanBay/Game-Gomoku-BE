from django.urls import path

from .views import MatchHistoryView, RoomJoinView, RoomLeaveView, RoomListCreateView

urlpatterns = [
    path("rooms/", RoomListCreateView.as_view(), name="rooms"),
    path("rooms/join/", RoomJoinView.as_view(), name="rooms_join"),
    path("rooms/leave/", RoomLeaveView.as_view(), name="rooms_leave"),
    path("matches/history/", MatchHistoryView.as_view(), name="match_history"),
]
