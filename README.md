# Criminal Prediction System

A machine-learning powered crime risk analysis tool that predicts the most likely crime type for a given set of contextual factors.

## Features

- **Random Forest Classifier** trained on synthetic crime data
- **8 crime categories**: Theft, Assault, Burglary, Vandalism, Drug Offense, Robbery, Fraud, No Crime Expected
- **Web UI** with real-time predictions via a REST API
- **Top-3 predictions** with confidence probabilities

## Project Structure

```
.
├── crime_prediction.py   # ML model – training & prediction logic
├── app.py                # Flask REST API
├── requirements.txt      # Python dependencies
├── index.html            # Web frontend
├── index.css             # Styles
└── index.js              # Frontend JavaScript
```

## Input Features

| Feature | Description |
|---|---|
| Hour of day | 0–23 |
| Day of week | 0 (Monday) – 6 (Sunday) |
| Month | 1–12 |
| District | Downtown / Northside / Eastside / Westside / Southside / Suburbs |
| Population density | People per km² (1 000–20 000) |
| Poverty rate | 5 %–45 % |
| Unemployment rate | 2 %–20 % |
| Police presence | 10 %–100 % |

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Train the model (optional – auto-trains on first API call)
python crime_prediction.py

# 3. Start the API server
python app.py

# 4. Open index.html in a browser (or visit http://localhost:5000)
```

## API

### `POST /predict`

```json
{
  "hour": 22,
  "day_of_week": 5,
  "month": 7,
  "district": "Downtown",
  "population_density": 15000,
  "poverty_rate": 0.30,
  "unemployment_rate": 0.15,
  "police_presence": 0.30
}
```

**Response**

```json
{
  "predicted_crime": "Assault",
  "confidence": 34.5,
  "top_predictions": [
    { "crime_type": "Assault",     "probability": 34.5 },
    { "crime_type": "Robbery",     "probability": 22.1 },
    { "crime_type": "Vandalism",   "probability": 15.3 }
  ]
}
```

### `GET /meta`

Returns the list of valid districts and crime types.

## Disclaimer

This system is a **demonstration** built on **synthetic data**.  
It is not intended to be used for real law-enforcement decisions.
