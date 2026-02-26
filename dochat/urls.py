"""
URL configuration for the dochat Django project.
"""

from django.urls import path, include

urlpatterns = [
    path("", include("core.urls")),
]
