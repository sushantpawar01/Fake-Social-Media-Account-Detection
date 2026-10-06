import csv
import os
import shutil
from datetime import datetime, timezone

_DEFAULT_CSV_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "data", "collected_patterns.csv"))


def _get_target_csv_path() -> str:
    """Return a writable CSV path (uses /tmp on serverless environments like Vercel)."""
    if os.path.exists(_DEFAULT_CSV_PATH):
        if os.access(_DEFAULT_CSV_PATH, os.W_OK):
            return _DEFAULT_CSV_PATH
    else:
        parent = os.path.dirname(_DEFAULT_CSV_PATH)
        if os.path.exists(parent) and os.access(parent, os.W_OK):
            return _DEFAULT_CSV_PATH

    # Serverless / Read-only fallback -> write to /tmp
    tmp_path = os.path.join("/tmp", "collected_patterns.csv")
    if not os.path.exists(tmp_path) and os.path.exists(_DEFAULT_CSV_PATH):
        try:
            shutil.copyfile(_DEFAULT_CSV_PATH, tmp_path)
        except Exception:
            pass
    return tmp_path


# All columns saved per detection
_COLUMNS = [
    "timestamp", "url", "platform", "username",
    # raw profile signals
    "followers", "following", "posts", "account_age_days",
    "has_profile_pic", "is_verified", "bio_length", "age_source",
    # derived features
    "follower_following_ratio", "posts_per_day",
    "username_digit_ratio", "username_has_random",
    # model output
    "label", "confidence", "score",
    "prob_genuine", "prob_suspicious", "prob_fake",
]


def save(url: str, account_data: dict, result: dict):
    """Append one detection row to collected_patterns.csv."""
    features = result.get("features", {})
    probs    = result.get("probabilities", {})

    row = {
        "timestamp":               datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "url":                     url,
        "platform":                account_data.get("platform", ""),
        "username":                account_data.get("username", ""),
        "followers":               features.get("followers", 0),
        "following":               features.get("following", 0),
        "posts":                   features.get("posts", 0),
        "account_age_days":        features.get("account_age_days", 0),
        "has_profile_pic":         features.get("has_profile_pic", 0),
        "is_verified":             features.get("is_verified", 0),
        "bio_length":              features.get("bio_length", 0),
        "age_source":              result.get("age_source", ""),
        "follower_following_ratio":features.get("follower_following_ratio", 0),
        "posts_per_day":           features.get("posts_per_day", 0),
        "username_digit_ratio":    features.get("username_digit_ratio", 0),
        "username_has_random":     features.get("username_has_random", 0),
        "label":                   result.get("label", ""),
        "confidence":              result.get("confidence", 0),
        "score":                   result.get("score", 0),
        "prob_genuine":            probs.get("Genuine", 0),
        "prob_suspicious":         probs.get("Suspicious", 0),
        "prob_fake":               probs.get("Fake", 0),
    }

    target_path = _get_target_csv_path()
    write_header = not os.path.exists(target_path) or os.path.getsize(target_path) == 0
    with open(target_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_COLUMNS)
        if write_header:
            writer.writeheader()
        writer.writerow(row)


def csv_path() -> str:
    target = _get_target_csv_path()
    if os.path.exists(target):
        return target
    return _DEFAULT_CSV_PATH
