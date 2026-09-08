from flask import Blueprint, render_template, session

dashboard_bp = Blueprint("dashboard", __name__, template_folder="templates")

@dashboard_bp.route("/dashboard")
def dashboard():
    history = session.get("history", [])
    stats = {
        "total": len(history),
        "fake": sum(1 for h in history if h["label"] == "Fake"),
        "suspicious": sum(1 for h in history if h["label"] == "Suspicious"),
        "genuine": sum(1 for h in history if h["label"] == "Genuine"),
    }
    return render_template("dashboard/dashboard.html", history=history, stats=stats)
