import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, request, jsonify, session
from core.model import predict
from features.home.routes import home_bp
from features.detection.routes import detection_bp
from features.dashboard.routes import dashboard_bp
from features.about.routes import about_bp

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "fsmd-secret-2024"

app.register_blueprint(home_bp)
app.register_blueprint(detection_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(about_bp)

# Store result in session history after detection
@app.after_request
def store_history(response):
    if request.path == "/api/detect" and request.method == "POST" and response.status_code == 200:
        try:
            result = response.get_json()
            if result and "label" in result:
                history = session.get("history", [])
                history.insert(0, {
                    "username": request.get_json(silent=True, force=True).get("username", "unknown"),
                    "label": result["label"],
                    "confidence": result["confidence"],
                    "score": result["score"],
                })
                session["history"] = history[:20]
        except Exception:
            pass
    return response

if __name__ == "__main__":
    app.run(debug=True)
