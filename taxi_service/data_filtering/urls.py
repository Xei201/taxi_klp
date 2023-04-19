from django.urls import path
from . import views


urlpatterns = [
    path('', views.UpdateBot.as_view(), name='update'),
]