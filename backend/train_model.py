"""Train the EduPulse Random Forest early-warning model.

Default mode creates a synthetic pilot artifact for integration testing only.
For institutional use, supply a validated, de-identified CSV with labelled outcomes.
"""
from pathlib import Path
import argparse
import csv
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score

parser = argparse.ArgumentParser()
parser.add_argument("--csv", help="CSV columns: attendance, assignment_avg, assessment_avg, engagement, risk_level")
args = parser.parse_args()

if args.csv:
    with open(args.csv, newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    required = ["attendance", "assignment_avg", "assessment_avg", "engagement", "risk_level"]
    if not rows or any(column not in rows[0] for column in required):
        raise SystemExit("CSV must contain: " + ", ".join(required))
    X = np.array([[float(row[k]) for k in required[:4]] for row in rows], dtype=float)
    labels = np.array([row["risk_level"].strip().title() for row in rows])
    if not set(labels).issubset({"Low", "Moderate", "High"}):
        raise SystemExit("risk_level values must be Low, Moderate or High.")
    if not np.isfinite(X).all() or (X < 0).any() or (X > 100).any():
        raise SystemExit("Feature values must be numeric percentages from 0 to 100.")
else:
    rng = np.random.default_rng(20261101)
    n = 12000
    X = np.column_stack([
        rng.uniform(25, 100, n),
        rng.uniform(20, 100, n),
        rng.uniform(15, 100, n),
        rng.uniform(20, 100, n),
    ])
    risk = (np.maximum(0, 75-X[:,0])*.45 + np.maximum(0, 65-X[:,1])*.22 +
            np.maximum(0, 60-X[:,2])*.25 + np.maximum(0, 60-X[:,3])*.08)
    labels = np.where((risk >= 24) | (X[:,0] < 60) | (X[:,2] < 40), "High",
             np.where((risk >= 10) | (X[:,0] < 75), "Moderate", "Low"))
    noise = rng.random(n) < 0.025
    for i in np.where(noise)[0]:
        labels[i] = rng.choice(["Low", "Moderate", "High"])

X_train, X_test, y_train, y_test = train_test_split(
    X, labels, test_size=.2, random_state=42, stratify=labels
)
model = RandomForestClassifier(
    n_estimators=300, max_depth=10, min_samples_leaf=4,
    class_weight="balanced", random_state=42, n_jobs=-1
)
model.fit(X_train, y_train)
print("Holdout accuracy (only meaningful for the supplied labelled dataset):",
      round(accuracy_score(y_test, model.predict(X_test)), 4))
print(classification_report(y_test, model.predict(X_test)))
out = Path(__file__).parent / "student_risk_model.joblib"
joblib.dump(model, out)
print("Saved:", out)
