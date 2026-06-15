from django.urls import path

from . import views

urlpatterns = [
    path("health/", views.health, name="health"),
    path("diag/", views.diag, name="diag"),
    path("route/", views.route, name="route"),
    path("trip/", views.trip, name="trip"),
]
