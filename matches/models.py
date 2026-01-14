from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Room(models.Model):
    class Status(models.TextChoices):
        WAITING = "waiting", "Đang chờ"
        PLAYING = "playing", "Đang chơi"
        FULL = "full", "Đầy phòng"
    
    class BoardSize(models.IntegerChoices):
        SMALL = 15, "15x15"
        LARGE = 19, "19x19"

    room_name = models.CharField(max_length=100)
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hosted_rooms"
    )
    # Người chơi thứ 2 (Player O), cho phép null khi mới tạo
    player_2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="joined_rooms"
    )

    password = models.CharField(max_length=50, null=True, blank=True)
    board_size = models.IntegerField(choices=BoardSize.choices, default=BoardSize.SMALL)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.WAITING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.room_name} ({self.host.username})"

    @property
    def has_password(self) -> bool:
        return bool(self.password)

    @property
    def current_players(self) -> int:
        count = 1 if self.host else 0
        if self.player_2:
            count += 1
        return count

    @classmethod
    def prune_stale(cls, hours: int = 24):
        cutoff = timezone.now() - timedelta(hours=hours)
        cls.objects.filter(status=cls.Status.WAITING, player_2__isnull=True, created_at__lt=cutoff).delete()


class Match(models.Model):
    # Dùng settings.AUTH_USER_MODEL để trỏ tới CustomUser một cách an toàn
    player_x = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='matches_as_x'
    )
    player_o = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='matches_as_o'
    )
    # Winner để null nếu hòa hoặc trận đấu chưa kết thúc
    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='won_matches'
    )
    
    room = models.ForeignKey(Room, on_delete=models.SET_NULL, null=True, blank=True, related_name='matches')
    board_size = models.IntegerField(default=15)
    # JSONField lưu tọa độ các nước đi: [[row, col, player], ...] player: 'X' hoặc 'O'
    board_state = models.JSONField(default=list, verbose_name="Trạng thái bàn cờ")
    current_turn = models.CharField(max_length=1, default='X')  # 'X' hoặc 'O'
    
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian bắt đầu")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian kết thúc")

    class Meta:
        verbose_name_plural = "Matches"

    def __str__(self):
        return f"Match {self.id}: {self.player_x} vs {self.player_o}"