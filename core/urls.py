"""URL patterns for the core app."""

from django.urls import path

from . import views

urlpatterns = [
    # ── Crime prediction UI & API ─────────────────────────────────────────────
    path("", views.index, name="index"),
    path("predict", views.predict, name="predict"),
    path("meta", views.meta, name="meta"),

    # ── Document chat UI & API ────────────────────────────────────────────────
    path("chat", views.chat_page, name="chat"),
    path("api/documents", views.list_documents, name="list_documents"),
    path("api/documents/upload", views.upload_documents, name="upload_documents"),
    path("api/documents/<path:filename>", views.delete_document, name="delete_document"),
    path("api/chat", views.chat, name="chat_api"),
]
