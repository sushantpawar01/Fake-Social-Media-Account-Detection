import os
from flask import Blueprint, render_template, request, jsonify, send_file
from core.model import predict
from core.url_parser import fetch_by_url, parse_url
from core.collector import save as collect_save, csv_path

detection_bp = Blueprint("detection", __name__, template_folder="templates")

@detection_bp.route("/detect", methods=["GET"])
def detect_page():
    return render_template("detection/detect.html")

@detection_bp.route("/api/detect", methods=["POST"])
def api_detect():
    body = request.get_json()
    if not body:
        return jsonify({"error": "No data provided"}), 400

    url = body.get("url", "").strip()
    if not url:
        return jsonify({"error": "Profile URL is required"}), 400

    if not url.startswith("http"):
        url = "https://" + url

    account_data = fetch_by_url(url)
    result = predict(account_data)
    result["url"] = url
    result["platform"] = account_data.get("platform", "unknown")
    result["username"] = account_data.get("username", "")

    # Save pattern to growing dataset
    try:
        collect_save(url, account_data, result)
    except Exception:
        pass

    return jsonify(result)

@detection_bp.route("/api/dataset/download")
def download_dataset():
    path = csv_path()
    if not os.path.exists(path):
        return jsonify({"error": "No data collected yet"}), 404
    return send_file(path, mimetype="text/csv", as_attachment=True,
                     download_name="collected_patterns.csv")

@detection_bp.route("/api/dataset/stats")
def dataset_stats():
    path = csv_path()
    if not os.path.exists(path):
        return jsonify({"total": 0, "genuine": 0, "suspicious": 0, "fake": 0, "platforms": {}})
    import csv as _csv
    counts = {"Genuine": 0, "Suspicious": 0, "Fake": 0}
    platforms = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            counts[row.get("label", "")] = counts.get(row.get("label", ""), 0) + 1
            p = row.get("platform", "unknown")
            platforms[p] = platforms.get(p, 0) + 1
    return jsonify({
        "total":      sum(counts.values()),
        "genuine":    counts["Genuine"],
        "suspicious": counts["Suspicious"],
        "fake":       counts["Fake"],
        "platforms":  platforms,
    })
