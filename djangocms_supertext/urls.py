"""Optional: ``path("supertext/", include("djangocms_supertext.urls"))`` gives the ping endpoint a
short public address (``/supertext/ping``) outside the admin. Without it the package uses
``<admin>/djangocms_supertext/translation/ping/``."""

from django.urls import path

from . import views

urlpatterns = [path("ping", views.ping, name="djangocms_supertext_ping")]
