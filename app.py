"""
Flask API — Criminal Prediction System + Document Chat Assistant.
Run with:  python app.py
The API will be available at http://localhost:5000

Routes (existing):
  GET  /          → index.html (crime prediction UI)
  POST /predict   → crime type prediction
  GET  /meta      → districts / crime-type enumerations

Routes (new — document chat):
  GET  /chat                         → chat.html
  GET  /api/documents                → list uploaded documents
  POST /api/documents/upload         → upload one or more documents
  DELETE /api/documents/<filename>   → remove a document
  POST /api/chat                     → ask a question against the knowledge base
"""

import os

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename

from crime_prediction import predict_crime, CRIME_TYPES, DISTRICTS, load_model
from document_processor import process_document, SUPPORTED_EXTENSIONS
from knowledge_base import KnowledgeBase

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

# ── Upload folder ──────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024  # 50 MB — adjust as needed

# ── Shared knowledge base (in-memory) ─────────────────────────────────────────
_kb = KnowledgeBase()


def _load_existing_uploads() -> None:
    """Index any documents that were uploaded in a previous session."""
    for fname in sorted(os.listdir(UPLOAD_FOLDER)):
        fpath = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isfile(fpath):
            text = process_document(fpath)
            _kb.add_document(text, fname)


_load_existing_uploads()

# Pre-load crime model at startup
load_model()


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/predict", methods=["POST"])
def predict():
    """
    POST /predict
    JSON body:
    {
        "hour": 22,
        "day_of_week": 5,
        "month": 7,
        "district": "Downtown",
        "population_density": 15000,
        "poverty_rate": 0.30,
        "unemployment_rate": 0.15,
        "police_presence": 0.3
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    required = [
        "hour",
        "day_of_week",
        "month",
        "district",
        "population_density",
        "poverty_rate",
        "unemployment_rate",
        "police_presence",
    ]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": f"Missing fields: {missing}"}), 400

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
        return jsonify(result)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/meta", methods=["GET"])
def meta():
    """Return lists of valid districts and crime types."""
    return jsonify({"districts": DISTRICTS, "crime_types": CRIME_TYPES})


# ── Document Chat routes ───────────────────────────────────────────────────────

@app.route("/chat")
def chat_page():
    """Serve the document-chat UI."""
    return send_from_directory(".", "chat.html")


@app.route("/api/documents", methods=["GET"])
def list_documents():
    """Return metadata for all uploaded documents."""
    docs = []
    for fname in sorted(os.listdir(UPLOAD_FOLDER)):
        fpath = os.path.join(UPLOAD_FOLDER, fname)
        if os.path.isfile(fpath):
            docs.append({"filename": fname, "size": os.path.getsize(fpath)})
    return jsonify({"documents": docs})


@app.route("/api/documents/upload", methods=["POST"])
def upload_documents():
    """Upload one or more documents; extract text and add to knowledge base."""
    if "files" not in request.files:
        return jsonify({"error": "No files provided"}), 400

    uploaded = []
    errors = []

    for file in request.files.getlist("files"):
        if not file or not file.filename:
            continue

        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in SUPPORTED_EXTENSIONS:
            errors.append(f"{file.filename}: unsupported file type ({ext})")
            continue

        safe_name = secure_filename(file.filename)
        if not safe_name:
            safe_name = "unnamed" + ext

        # Avoid overwriting an existing file
        base, file_ext = os.path.splitext(safe_name)
        counter = 1
        dest = os.path.join(UPLOAD_FOLDER, safe_name)
        while os.path.exists(dest):
            safe_name = f"{base}_{counter}{file_ext}"
            dest = os.path.join(UPLOAD_FOLDER, safe_name)
            counter += 1

        file.save(dest)
        text = process_document(dest)
        chunks = _kb.add_document(text, safe_name)
        uploaded.append(
            {"filename": safe_name, "original": file.filename, "chunks": chunks}
        )

    return jsonify({"uploaded": uploaded, "errors": errors})


@app.route("/api/documents/<path:filename>", methods=["DELETE"])
def delete_document(filename):
    """Remove an uploaded document and its chunks from the knowledge base."""
    # Prevent path traversal
    safe_name = os.path.basename(filename)
    dest = os.path.join(UPLOAD_FOLDER, safe_name)
    upload_root = os.path.join(os.path.abspath(UPLOAD_FOLDER), "")
    if not os.path.abspath(dest).startswith(upload_root):
        return jsonify({"error": "Invalid filename"}), 400
    if not os.path.isfile(dest):
        return jsonify({"error": "File not found"}), 404
    os.remove(dest)
    _kb.remove_document(safe_name)
    return jsonify({"deleted": safe_name})


@app.route("/api/chat", methods=["POST"])
def chat():
    """Answer a question using the uploaded documents as context."""
    data = request.get_json()
    if not data or not data.get("question", "").strip():
        return jsonify({"error": "No question provided"}), 400

    question = data["question"].strip()

    if _kb.is_empty():
        return jsonify(
            {
                "answer": (
                    "No documents have been uploaded yet. "
                    "Please upload some documents first."
                ),
                "sources": [],
                "chunks": [],
            }
        )

    results = _kb.search(question, top_k=5)
    if not results:
        return jsonify(
            {
                "answer": (
                    "I could not find relevant information in the uploaded documents "
                    "for your question. Try rephrasing or uploading more documents."
                ),
                "sources": [],
                "chunks": [],
            }
        )

    # Build a readable answer from the top retrieved chunks
    context_parts = []
    for r in results:
        context_parts.append(f"[Source: {r['source']}]\n{r['text']}")
    answer = "Based on your documents:\n\n" + "\n\n---\n\n".join(context_parts)

    sources = list(dict.fromkeys(r["source"] for r in results))
    return jsonify({"answer": answer, "sources": sources, "chunks": results})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
