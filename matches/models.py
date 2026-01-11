from django.db import models
from django.conf import settings

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
    
    # JSONField lưu tọa độ các nước đi: [[0,0], [1,1], ...]
    board_state = models.JSONField(default=list, verbose_name="Trạng thái bàn cờ")
    
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="Thời gian bắt đầu")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="Thời gian kết thúc")

    class Meta:
        verbose_name_plural = "Matches"

    def __str__(self):
        return f"Match {self.id}: {self.player_x} vs {self.player_o}"