"""
Criminal Prediction System using Machine Learning
Uses a Random Forest Classifier to predict crime type based on
contextual features such as time, location, and socioeconomic indicators.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, accuracy_score
import pickle
import os

# Crime types used for prediction
CRIME_TYPES = [
    "Theft",
    "Assault",
    "Burglary",
    "Vandalism",
    "Drug Offense",
    "Robbery",
    "Fraud",
    "No Crime Expected",
]

DISTRICTS = ["Downtown", "Northside", "Eastside", "Westside", "Southside", "Suburbs"]

MODEL_FILE = "crime_model.pkl"


def generate_synthetic_data(n_samples: int = 5000) -> pd.DataFrame:
    """Generate synthetic crime dataset for training."""
    np.random.seed(42)

    data = {
        "hour": np.random.randint(0, 24, n_samples),
        "day_of_week": np.random.randint(0, 7, n_samples),  # 0=Mon, 6=Sun
        "month": np.random.randint(1, 13, n_samples),
        "district_code": np.random.randint(0, len(DISTRICTS), n_samples),
        "population_density": np.random.uniform(1000, 20000, n_samples),
        "poverty_rate": np.random.uniform(0.05, 0.45, n_samples),
        "unemployment_rate": np.random.uniform(0.02, 0.20, n_samples),
        "police_presence": np.random.uniform(0.1, 1.0, n_samples),
    }

    df = pd.DataFrame(data)

    # Simulate realistic crime-type assignments based on features
    labels = []
    for _, row in df.iterrows():
        score_theft = (
            0.3 * (row["hour"] >= 8 and row["hour"] <= 20)
            + 0.2 * (row["poverty_rate"] > 0.25)
            + 0.1 * (row["district_code"] in [0, 2])
        )
        score_assault = (
            0.4 * (row["hour"] >= 20 or row["hour"] <= 4)
            + 0.2 * (row["day_of_week"] >= 5)
            + 0.2 * (row["unemployment_rate"] > 0.12)
        )
        score_burglary = (
            0.35 * (row["hour"] >= 1 and row["hour"] <= 6)
            + 0.3 * (row["police_presence"] < 0.4)
            + 0.1 * (row["poverty_rate"] > 0.30)
        )
        score_vandalism = (
            0.25 * (row["hour"] >= 18 or row["hour"] <= 2)
            + 0.2 * (row["day_of_week"] >= 5)
        )
        score_drug = (
            0.3 * (row["poverty_rate"] > 0.30)
            + 0.2 * (row["unemployment_rate"] > 0.15)
            + 0.2 * (row["district_code"] in [1, 3])
        )
        score_robbery = (
            0.35 * (row["hour"] >= 19 or row["hour"] <= 5)
            + 0.25 * (row["poverty_rate"] > 0.35)
        )
        score_fraud = (
            0.3 * (row["hour"] >= 9 and row["hour"] <= 17)
            + 0.2 * (row["district_code"] == 0)
        )
        score_none = 0.4 * (row["police_presence"] > 0.7) + 0.2 * (
            row["poverty_rate"] < 0.10
        )

        scores = [
            score_theft,
            score_assault,
            score_burglary,
            score_vandalism,
            score_drug,
            score_robbery,
            score_fraud,
            score_none,
        ]
        # Add small noise and pick highest score
        scores = [s + np.random.uniform(0, 0.15) for s in scores]
        labels.append(CRIME_TYPES[int(np.argmax(scores))])

    df["crime_type"] = labels
    return df


def train_model():
    """Train the Random Forest model and save it to disk."""
    print("Generating training data...")
    df = generate_synthetic_data(5000)

    features = [
        "hour",
        "day_of_week",
        "month",
        "district_code",
        "population_density",
        "poverty_rate",
        "unemployment_rate",
        "police_presence",
    ]

    X = df[features]
    le = LabelEncoder()
    y = le.fit_transform(df["crime_type"])

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("Training Random Forest classifier...")
    clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    clf.fit(X_train, y_train)

    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"Model accuracy: {acc * 100:.2f}%")
    print("\nClassification Report:")
    print(
        classification_report(
            y_test, y_pred, target_names=le.classes_, zero_division=0
        )
    )

    model_data = {"model": clf, "label_encoder": le, "features": features}
    with open(MODEL_FILE, "wb") as f:
        pickle.dump(model_data, f)
    print(f"\nModel saved to {MODEL_FILE}")
    return model_data


def load_model():
    """Load the trained model from disk, training if not found."""
    if not os.path.exists(MODEL_FILE):
        return train_model()
    with open(MODEL_FILE, "rb") as f:
        return pickle.load(f)


def predict_crime(
    hour: int,
    day_of_week: int,
    month: int,
    district: str,
    population_density: float,
    poverty_rate: float,
    unemployment_rate: float,
    police_presence: float,
) -> dict:
    """
    Predict crime type and return top-3 probabilities.

    Parameters
    ----------
    hour : int          Hour of day (0-23)
    day_of_week : int   Day of week (0=Mon … 6=Sun)
    month : int         Month (1-12)
    district : str      District name (one of DISTRICTS)
    population_density  People per sq-km
    poverty_rate        Fraction 0-1
    unemployment_rate   Fraction 0-1
    police_presence     Fraction 0-1 (0=none, 1=heavy)
    """
    model_data = load_model()
    clf = model_data["model"]
    le = model_data["label_encoder"]

    district_code = DISTRICTS.index(district) if district in DISTRICTS else 0

    sample = pd.DataFrame(
        [
            {
                "hour": hour,
                "day_of_week": day_of_week,
                "month": month,
                "district_code": district_code,
                "population_density": population_density,
                "poverty_rate": poverty_rate,
                "unemployment_rate": unemployment_rate,
                "police_presence": police_presence,
            }
        ]
    )

    proba = clf.predict_proba(sample)[0]
    top3_idx = np.argsort(proba)[::-1][:3]

    return {
        "predicted_crime": le.classes_[top3_idx[0]],
        "confidence": round(float(proba[top3_idx[0]]) * 100, 1),
        "top_predictions": [
            {
                "crime_type": le.classes_[i],
                "probability": round(float(proba[i]) * 100, 1),
            }
            for i in top3_idx
        ],
    }


if __name__ == "__main__":
    # Train the model when run directly
    train_model()

    # Example prediction
    result = predict_crime(
        hour=22,
        day_of_week=5,
        month=7,
        district="Downtown",
        population_density=15000,
        poverty_rate=0.30,
        unemployment_rate=0.15,
        police_presence=0.3,
    )
    print("\nExample Prediction:")
    print(f"Predicted crime: {result['predicted_crime']} ({result['confidence']}% confidence)")
    print("Top predictions:")
    for p in result["top_predictions"]:
        print(f"  {p['crime_type']}: {p['probability']}%")
