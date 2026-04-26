from django.urls import path

from . import api, views

app_name = "pets"

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("api/pet/", api.state, name="api_state"),
    path("api/pet/feed/", api.feed, name="api_feed"),
    path("api/pet/play/", api.play, name="api_play"),
    path("api/pet/sleep/", api.sleep, name="api_sleep"),
    path("api/pet/heal/", api.heal, name="api_heal"),
    path("api/pet/rename/", api.rename, name="api_rename"),
]
