import os
import numpy as np
import joblib
from .feature_engineering import extract_features

FEATURE_NAMES = [
    "follower_following_ratio",
    "posts_per_day",
    "bio_length",
    "username_digit_ratio",
    "username_has_random",
    "has_profile_pic",
    "is_verified",
    "followers",
    "following",
    "posts",
    "account_age_days",
]

LABEL_NAMES = {0: "Genuine", 1: "Suspicious", 2: "Fake"}

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
_artifact = None

def _load():
    global _artifact
    if _artifact is None:
        _artifact = joblib.load(_MODEL_PATH)
    return _artifact


def predict(data: dict) -> dict:
    artifact = _load()
    pipeline = artifact["pipeline"]
    features = extract_features(data)

    X = np.array([[features[f] for f in FEATURE_NAMES]], dtype=float)

    # Get actual classes the model was trained on (e.g. [0, 2] for real dataset)
    classes   = pipeline.classes_  # e.g. [0, 2]
    proba_raw = pipeline.predict_proba(X)[0]  # probabilities for each class

    # Map to full 3-class dict
    proba_map = {int(c): float(p) for c, p in zip(classes, proba_raw)}
    p_genuine    = proba_map.get(0, 0.0)
    p_suspicious = proba_map.get(1, 0.0)
    p_fake       = proba_map.get(2, 0.0)

    # If only 2 classes trained, treat middle ground as suspicious
    if 1 not in proba_map:
        if p_fake > 0.35 and p_fake < 0.65:
            p_suspicious = min(p_fake, p_genuine)
            p_fake       = max(0.0, p_fake - p_suspicious)
            p_genuine    = max(0.0, p_genuine - p_suspicious)

    # Determine label
    best_class = int(classes[int(np.argmax(proba_raw))])
    label      = LABEL_NAMES[best_class]
    confidence = round(float(max(proba_raw)) * 100, 1)

    # Risk score 0-100
    score = round((p_suspicious * 50 + p_fake * 100), 1)
    score = min(score, 100.0)

    reasons    = _explain(features, label, p_genuine, p_suspicious, p_fake)
    age_source = data.get("age_source", "default")

    return {
        "label":      label,
        "confidence": confidence,
        "score":      score,
        "features":   features,
        "reasons":    reasons,
        "age_source": age_source,
        "probabilities": {
            "Genuine":    round(p_genuine    * 100, 1),
            "Suspicious": round(p_suspicious * 100, 1),
            "Fake":       round(p_fake       * 100, 1),
        },
    }


def _explain(f, label, p_genuine, p_suspicious, p_fake):
    reasons = []

    high_followers  = f["followers"] > 500
    celebrity       = f["followers"] > 10000
    mass_following  = f["following"] > 3000
    very_new        = f["account_age_days"] < 30
    established     = f["account_age_days"] > 365
    no_pic          = f["has_profile_pic"] == 0
    no_bio          = f["bio_length"] < 5
    low_ratio       = f["follower_following_ratio"] < 0.1
    spam_posting    = f["posts_per_day"] > 20
    ghost           = f["posts_per_day"] < 0.01 and established
    excessive_digits = f["username_digit_ratio"] > 0.4
    random_username  = f["username_has_random"] == 1

    if no_pic and not high_followers:
        reasons.append("No profile picture")
    if low_ratio and mass_following:
        reasons.append("Following thousands of accounts but has very few followers")
    elif mass_following and f["followers"] < 200:
        reasons.append("Following many accounts but has very few followers")
    if spam_posting:
        reasons.append("Abnormally high posting frequency — possible spam bot")
    if ghost and very_new and f["posts"] == 0:
        reasons.append("New account with zero posts")
    if no_bio and (no_pic or mass_following or very_new or excessive_digits):
        reasons.append("Missing bio combined with other suspicious signals")
    if excessive_digits:
        reasons.append("Username contains excessive digits")
    if random_username and not high_followers:
        reasons.append("Username contains random number sequence")

    if label == "Genuine":
        if celebrity:
            reasons.append(f"High follower count ({f['followers']:,}) — established account")
        if established:
            reasons.append(f"Account active for {f['account_age_days']} days")
        if f["has_profile_pic"] == 1 and high_followers:
            reasons.append("Has profile picture with significant following")
        if not reasons:
            reasons.append("No suspicious signals detected — account appears authentic")

    if not reasons:
        if label == "Fake":
            reasons.append("Multiple fake account patterns detected by ML model")
        else:
            reasons.append("Some weak signals detected — account may need review")

    return reasons
