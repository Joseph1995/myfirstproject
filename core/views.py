"""
Views for the Document Chat + Crime Prediction Django app.

All REST endpoints use ``@csrf_exempt`` because they are consumed by
browser-side JavaScript that does not supply a CSRF token.
"""

import json
import os
import re

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt

from crime_prediction import predict_crime, CRIME_TYPES, DISTRICTS
from document_processor import process_document, SUPPORTED_EXTENSIONS
from .services import get_kb, UPLOAD_DIR


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_filename(name: str) -> str:
    """Return a sanitised filename that is safe to store on disk."""
    # Strip any directory component first.
    name = os.path.basename(name)
    # Keep only word characters, hyphens, dots and spaces.
    name = re.sub(r"[^\w\s\-.]", "", name).strip()
    return name or "unnamed"


# ── Crime prediction ───────────────────────────────────────────────────────────

def index(request):
    """Serve the crime-prediction UI."""
    return render(request, "index.html")


def meta(request):
    """Return lists of valid districts and crime types."""
    return JsonResponse({"districts": DISTRICTS, "crime_types": CRIME_TYPES})


@csrf_exempt
def predict(request):
    """
    POST /predict
    JSON body example:
    {
        "hour": 22, "day_of_week": 5, "month": 7, "district": "Downtown",
        "population_density": 15000, "poverty_rate": 0.30,
        "unemployment_rate": 0.15, "police_presence": 0.3
    }
    """
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "No JSON body provided"}, status=400)

    required = [
        "hour", "day_of_week", "month", "district",
        "population_density", "poverty_rate", "unemployment_rate", "police_presence",
    ]
    missing = [f for f in required if f not in data]
    if missing:
        return JsonResponse({"error": f"Missing fields: {missing}"}, status=400)

    try:
        result = predict_crime(
            hour=int(data["hour"]),
            day_of_week=int(data["day_of_week"]),
            month=int(data["month"]),
            district=str(data["district"]),
            population_density=float(data["population_density"]),
            poverty_rate=float(data["poverty_rate"]),
            unemployment_rate=float(data["unemployment_rate"]),
            police_presence=float(data["police_presence"]),
        )
        return JsonResponse(result)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=500)


# ── Document management ────────────────────────────────────────────────────────

def chat_page(request):
    """Serve the document-chat UI."""
    return render(request, "chat.html")


def list_documents(request):
    """Return metadata for all uploaded documents."""
    docs = []
    for fname in sorted(os.listdir(UPLOAD_DIR)):
        fpath = os.path.join(UPLOAD_DIR, fname)
        if os.path.isfile(fpath):
            docs.append({"filename": fname, "size": os.path.getsize(fpath)})
    return JsonResponse({"documents": docs})


@csrf_exempt
def upload_documents(request):
    """Upload one or more documents; extract text and add to knowledge base."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    if "files" not in request.FILES:
        return JsonResponse({"error": "No files provided"}, status=400)

    kb = get_kb()
    uploaded = []
    errors = []

    for file in request.FILES.getlist("files"):
        if not file or not file.name:
            continue

        ext = os.path.splitext(file.name)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            errors.append(f"{file.name}: unsupported file type ({ext})")
            continue

        safe_name = _safe_filename(file.name)
        # Ensure the extension is preserved after sanitisation.
        if not safe_name.lower().endswith(ext):
            safe_name = safe_name + ext

        # Avoid overwriting an existing file.
        base, file_ext = os.path.splitext(safe_name)
        counter = 1
        dest = os.path.join(UPLOAD_DIR, safe_name)
        while os.path.exists(dest):
            safe_name = f"{base}_{counter}{file_ext}"
            dest = os.path.join(UPLOAD_DIR, safe_name)
            counter += 1

        with open(dest, "wb") as f:
            for chunk in file.chunks():
                f.write(chunk)

        text = process_document(dest)
        chunks = kb.add_document(text, safe_name)
        uploaded.append(
            {"filename": safe_name, "original": file.name, "chunks": chunks}
        )

    return JsonResponse({"uploaded": uploaded, "errors": errors})


@csrf_exempt
def delete_document(request, filename):
    """Remove an uploaded document and its chunks from the knowledge base."""
    if request.method != "DELETE":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    # Prevent path traversal.
    safe_name = os.path.basename(filename)
    dest = os.path.join(UPLOAD_DIR, safe_name)
    upload_root = os.path.join(os.path.abspath(UPLOAD_DIR), "")
    if not os.path.abspath(dest).startswith(upload_root):
        return JsonResponse({"error": "Invalid filename"}, status=400)
    if not os.path.isfile(dest):
        return JsonResponse({"error": "File not found"}, status=404)

    os.remove(dest)
    get_kb().remove_document(safe_name)
    return JsonResponse({"deleted": safe_name})


# ── Chat ───────────────────────────────────────────────────────────────────────

@csrf_exempt
def chat(request):
    """Answer a question using the uploaded documents as context."""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({"error": "No question provided"}, status=400)

    if not data or not data.get("question", "").strip():
        return JsonResponse({"error": "No question provided"}, status=400)

    question = data["question"].strip()
    kb = get_kb()

    if kb.is_empty():
        return JsonResponse(
            {
                "answer": (
                    "No documents have been uploaded yet. "
                    "Please upload some documents first."
                ),
                "sources": [],
                "chunks": [],
            }
        )

    results = kb.search(question, top_k=5)
    if not results:
        return JsonResponse(
            {
                "answer": (
                    "I could not find relevant information in the uploaded documents "
                    "for your question. Try rephrasing or uploading more documents."
                ),
                "sources": [],
                "chunks": [],
            }
        )

    context_parts = [f"[Source: {r['source']}]\n{r['text']}" for r in results]
    answer = "Based on your documents:\n\n" + "\n\n---\n\n".join(context_parts)
    sources = list(dict.fromkeys(r["source"] for r in results))
    return JsonResponse({"answer": answer, "sources": sources, "chunks": results})
