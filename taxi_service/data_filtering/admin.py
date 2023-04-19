from django_admin_inline_paginator.admin import TabularInlinePaginated

from data_filtering.models import Profile, SessionTaxi, Sheet
from django.contrib import admin


class SessionTaxiInLine(TabularInlinePaginated):
    model = SessionTaxi
    per_page = 50


class SheetInLine(TabularInlinePaginated):
    model = Sheet
    per_page = 50


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "telegram_id", "telegram_username", "date_create")
    list_filter = ("user", "telegram_id", "telegram_username", "date_create")
    # inlines = [SheetInLine]
    list_per_page = 10
    search_fields = ("name", )


@admin.register(SessionTaxi)
class SessionTaxiAdmin(admin.ModelAdmin):
    list_display = ("sheet", "date_session", "phone", "time", "starting_point", "end_point", "price")
    list_filter = ("sheet", "date_session", "phone", "price")
    list_per_page = 50


@admin.register(Sheet)
class SheetAdmin(admin.ModelAdmin):
    list_display = ("name", "profile")
    list_filter = ("name", "profile")
    list_per_page = 50
    inlines = [SessionTaxiInLine]
