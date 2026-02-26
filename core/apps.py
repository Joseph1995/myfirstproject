"""
Django AppConfig for the core app.

The ``ready()`` hook is used to initialise the shared knowledge base and
pre-load the crime-prediction model once at server start-up.
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    name = "core"
    verbose_name = "Document Chat + Crime Prediction"

    def ready(self):
        # Guard against double-initialisation (e.g. Django test runner).
        from .services import init_services
        init_services()
