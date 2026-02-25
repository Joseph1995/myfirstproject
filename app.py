"""
Flask API for the Criminal Prediction System.
Run with:  python app.py
The API will be available at http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from crime_prediction import predict_crime, CRIME_TYPES, DISTRICTS, load_model

app = Flask(__name__, static_folder=".")
CORS(app)

# Pre-load model at startup
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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
