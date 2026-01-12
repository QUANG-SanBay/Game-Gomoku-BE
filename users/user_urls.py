from django.urls import path

from .views import LeaderboardView, ProfileUpdateView, PublicProfileView

urlpatterns = [
    path("leaderboard/", LeaderboardView.as_view(), name="leaderboard"),
    path("profile/", ProfileUpdateView.as_view(), name="profile_update"),
    path("<int:pk>/", PublicProfileView.as_view(), name="user_profile"),
]
