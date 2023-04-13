from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    """Дополнительные параметры к User в основном связанных с параметрами telegram account"""
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
    date_create = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["date_create", "telegram_id"]

    def __str__(self):
        return self.telegram_username


class Sheet(models.Model):
    """Ведётся список листов в Google Sheets к которым привязанны сессии такси"""
    name = models.CharField(
        primary_key=True,
        verbose_name="Name sheet",
        max_length=255,
    )
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        blank=True,
        default=None,
        null=True,
    )

    class Meta:
        ordering = ["name", ]

    def __str__(self):
        return self.name


class SessionTaxi(models.Model):
    """Сессии такси"""

    sheet = models.ForeignKey(
        Sheet,
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

    class Meta:
        ordering = ["date_session", "phone", "price"]

    def __str__(self):
        return self.starting_point

