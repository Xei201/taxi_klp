from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        blank=True,
        default=None,
        null=True,
    )
    telegram_id = models.IntegerField(
        verbose_name="ID telegram",
    )
    telegram_username = models.CharField(
        verbose_name="Nickname telegram",
        max_length=255,
    )
    name_sheet = models.CharField(
        verbose_name="Name file",
        max_length=255,
        blank=True,
        default=None,
        null=True,
    )
    date_create = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["date_create", "telegram_id"]

    def __str__(self):
        return self.telegram_username


class SessionTaxi(models.Model):
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
    )
    date_session = models.DateTimeField()
    phone = models.CharField(max_length=63)
    time = models.TimeField(
        blank=True,
        default=None,
        null=True,
    )
    starting_point = models.CharField(max_length=255)
    end_point = models.CharField(max_length=255)
    price = models.IntegerField()