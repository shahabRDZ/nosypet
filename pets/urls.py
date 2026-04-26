from django.urls import path

from . import views

app_name = "pets"

urlpatterns = [
    path("", views.home, name="home"),
]
