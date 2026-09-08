"""
Train fake account detection ML model from real dataset.
Run: py -3.11 core/train.py
"""
import os
import re
import numpy as np
import pandas as pd
import joblib
from datetime import datetime, timezone
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report

FEATURES = [
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

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _age_days(created_at):
    if pd.isna(created_at) or not str(created_at).strip():
        return 365
    try:
        dt = datetime.strptime(str(created_at).strip(), "%a %b %d %H:%M:%S +0000 %Y")
        return max(1, (datetime.now(timezone.utc).replace(tzinfo=None) - dt).days)
    except Exception:
        return 365


def _digit_ratio(name):
    name = str(name) if not pd.isna(name) else ""
    return round(sum(c.isdigit() for c in name) / (len(name) + 1), 4)


def _has_random(name):
    name = str(name) if not pd.isna(name) else ""
    return 1 if re.search(r'\d{4,}', name) else 0


def build_features(df, label):
    rows = []
    for _, row in df.iterrows():
        followers  = max(0, float(row.get("followers_count", 0) or 0))
        following  = max(1, float(row.get("friends_count",   0) or 0))
        posts      = max(0, float(row.get("statuses_count",  0) or 0))
        age        = max(1, _age_days(row.get("created_at")))
        bio        = str(row.get("description", "") or "")
        screen     = str(row.get("screen_name", "") or "")
        has_pic    = 0 if float(row.get("default_profile_image", 1) or 1) == 1 else 1
        verified   = 1 if float(row.get("verified", 0) or 0) == 1 else 0

        ffr = round(followers / (following + 1), 4)
        ppd = round(posts / (age + 1), 4)

        rows.append([
            ffr, ppd, len(bio), _digit_ratio(screen), _has_random(screen),
            has_pic, verified, followers, following, posts, age, label
        ])
    return rows


def load_dataset():
    fake_df = pd.read_csv(os.path.join(DATA_DIR, "fake_users.csv"))
    real_df = pd.read_csv(os.path.join(DATA_DIR, "real_users.csv"))

    print(f"Fake users: {len(fake_df)} | Real users: {len(real_df)}")

    fake_rows = build_features(fake_df, label=2)   # 2 = Fake
    real_rows = build_features(real_df, label=0)   # 0 = Genuine

    all_rows = fake_rows + real_rows
    np.random.shuffle(all_rows)

    arr = np.array(all_rows, dtype=float)
    X, y = arr[:, :-1], arr[:, -1].astype(int)
    return X, y


def train():
    print("Loading real dataset...")
    X, y = load_dataset()
    print(f"Total samples: {len(X)} | Features: {X.shape[1]}")
    print(f"Label distribution: Genuine={sum(y==0)} | Fake={sum(y==2)}")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    rf = RandomForestClassifier(
        n_estimators=300, max_depth=15,
        min_samples_leaf=2, random_state=42, n_jobs=-1
    )
    gb = GradientBoostingClassifier(
        n_estimators=200, max_depth=6,
        learning_rate=0.07, random_state=42
    )

    ensemble = VotingClassifier(
        estimators=[("rf", rf), ("gb", gb)],
        voting="soft", weights=[1, 1]
    )

    pipeline = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", ensemble),
    ])

    print("Training RandomForest + GradientBoosting ensemble...")
    pipeline.fit(X_train, y_train)

    cv = cross_val_score(pipeline, X_train, y_train, cv=5, scoring="accuracy")
    print(f"Cross-val accuracy: {cv.mean():.4f} +/- {cv.std():.4f}")

    y_pred = pipeline.predict(X_test)
    print("\nTest set report:")
    # Only labels present in dataset (0=Genuine, 2=Fake, no Suspicious from real data)
    labels_present = sorted(set(y_test))
    names = {0: "Genuine", 1: "Suspicious", 2: "Fake"}
    target_names = [names[l] for l in labels_present]
    print(classification_report(y_test, y_pred, labels=labels_present, target_names=target_names))

    out = os.path.join(os.path.dirname(__file__), "model.pkl")
    joblib.dump({"pipeline": pipeline, "features": FEATURES}, out)
    print(f"Model saved: {out}")


if __name__ == "__main__":
    train()
