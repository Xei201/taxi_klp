from django_admin_inline_paginator.admin import TabularInlinePaginated

from data_filtering.models import Profile, SessionTaxi
from django.contrib import admin


class SessionTaxiInLine(TabularInlinePaginated):
    model = SessionTaxi
    per_page = 50


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_id", "telegram_username", "date_create")
    list_filter = ("user", "telegram_id", "telegram_username", "date_create")
    # Разобраться в чём проблема с инлайном
    # inlines = [SessionTaxiInLine]
    list_per_page = 10
    search_fields = ("name", )


@admin.register(SessionTaxi)
class SessionTaxiAdmin(admin.ModelAdmin):
    list_display = ("profile", "date_session", "phone", "time", "starting_point", "end_point", "price")
    list_filter = ("profile", "date_session", "phone", "price")
    list_per_page = 50
