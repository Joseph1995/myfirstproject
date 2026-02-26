"""
Shared singleton services: knowledge base and crime-prediction model.

``init_services()`` is called once from ``CoreConfig.ready()``.
"""

import os

from knowledge_base import KnowledgeBase
from document_processor import process_document

# ── Upload directory ───────────────────────────────────────────────────────────
UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads"
)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Shared knowledge base ──────────────────────────────────────────────────────
_kb = KnowledgeBase()
_initialized = False


def init_services() -> None:
    """Initialise KB and ML model.  Safe to call multiple times."""
    global _initialized
    if _initialized:
        return
    _initialized = True
    _load_existing_uploads()
    # Import here to avoid heavy startup cost before Django is fully loaded.
    from crime_prediction import load_model
    load_model()


def _load_existing_uploads() -> None:
    """Re-index any documents that were persisted in a previous session."""
    for fname in sorted(os.listdir(UPLOAD_DIR)):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath):
            text = process_document(fpath)
            _kb.add_document(text, fname)


def get_kb() -> KnowledgeBase:
    """Return the shared KnowledgeBase instance."""
    return _kb
