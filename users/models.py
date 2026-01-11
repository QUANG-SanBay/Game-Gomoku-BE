from django.contrib.auth.models import AbstractUser
from django.db import models
from uuid import uuid4


class CustomUser(AbstractUser):
    # Giữ username làm định danh chính, email vẫn unique để đăng ký/khôi phục
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)

    elo = models.IntegerField(default=1000, verbose_name="Điểm xếp hạng")
    wins = models.PositiveIntegerField(default=0, verbose_name="Số trận thắng")
    losses = models.PositiveIntegerField(default=0, verbose_name="Số trận thua")
    draws = models.PositiveIntegerField(default=0, verbose_name="Số trận hòa")
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name="Ảnh đại diện")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return f"{self.username} ({self.elo})"

    @staticmethod
    def generate_username_from_email(email: str) -> str:
        local_part = email.split("@", 1)[0]
        # đảm bảo unique bằng cách gắn chuỗi ngắn ngẫu nhiên
        return f"{local_part}_{uuid4().hex[:6]}"