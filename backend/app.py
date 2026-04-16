"""CI Dashboard (clean) Flask API.

Focused, predictable endpoints:
- GET  /api/health
- GET  /api/config/targets
- POST /api/upload/<kind>  where kind in {lipt,suggestion,bp,kaizen}
- POST /api/analytics/calculate
- GET  /api/analytics/global
- GET  /api/analytics/department/<dept>
- POST /api/reset
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Callable, Dict, Any

from flask import Flask, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename

from config import Config
from modules.data_processor import DataProcessor
from modules.analytics import Analytics

logger = logging.getLogger("dashboard_clean")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _allowed_file(filename: str, allowed: set[str]) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


def _json_error(message: str, status: int):
    return jsonify({"success": False, "error": message}), status


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    config_obj = Config()
    data_processor = DataProcessor(config_obj)
    analytics_engine = Analytics(config_obj)

    session_data: Dict[str, Any] = {
        "lipt": None,
        "suggestion": None,
        "bp": None,
        "kaizen": None,
        "analytics": None,
        "last_upload": {},
    }

    def handle_upload(kind: str, process: Callable[[str], Dict[str, Any]]):
        if "file" not in request.files:
            return _json_error("No file provided", 400)

        file = request.files["file"]
        if not file or not file.filename:
            return _json_error("No file provided", 400)

        if not _allowed_file(file.filename, app.config["ALLOWED_EXTENSIONS"]):
            return _json_error("Invalid file type (xlsx/xls only)", 400)

        filename = secure_filename(
            f"{kind}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
        )
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)

        try:
            parsed = process(filepath)
        finally:
            try:
                os.remove(filepath)
            except OSError:
                pass

        session_data[kind] = parsed
        session_data["analytics"] = None  # force recalculation
        session_data["last_upload"][kind] = datetime.now().isoformat()

        vr = (parsed or {}).get("validation_report", {})
        return (
            jsonify(
                {
                    "success": True,
                    "message": f"{kind} file processed",
                    "data": {
                        "total_rows": parsed.get("total_rows", 0),
                        "valid_rows": vr.get("valid_rows", 0),
                        "skipped_rows": vr.get("skipped_rows", 0),
                        "unknown_departments": vr.get("unknown_departments", []),
                        "departments": len((parsed or {}).get("departments", {}) or {}),
                        "kpis": (parsed or {}).get("global_kpis", {}),
                    },
                }
            ),
            200,
        )

    @app.get("/api/health")
    def health():
        return (
            jsonify(
                {
                    "success": True,
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "version": "clean-1.0.0",
                }
            ),
            200,
        )

    @app.get("/api/config/targets")
    def targets():
        return jsonify({"success": True, "data": config_obj.DEPT_TARGETS}), 200

    @app.get("/api/session")
    def session_status():
        return (
            jsonify(
                {
                    "success": True,
                    "data": {
                        "uploaded": {
                            "lipt": session_data["lipt"] is not None,
                            "suggestion": session_data["suggestion"] is not None,
                            "bp": session_data["bp"] is not None,
                            "kaizen": session_data["kaizen"] is not None,
                        },
                        "last_upload": session_data.get("last_upload", {}),
                    },
                }
            ),
            200,
        )

    @app.post("/api/upload/lipt")
    def upload_lipt():
        try:
            return handle_upload("lipt", data_processor.process_lipt_file)
        except Exception as e:
            logger.exception("LIPT processing failed")
            return _json_error(str(e), 500)

    @app.post("/api/upload/suggestion")
    def upload_suggestion():
        try:
            return handle_upload("suggestion", data_processor.process_suggestion_file)
        except Exception as e:
            logger.exception("Suggestion processing failed")
            return _json_error(str(e), 500)

    @app.post("/api/upload/bp")
    def upload_bp():
        try:
            return handle_upload("bp", data_processor.process_bp_file)
        except Exception as e:
            logger.exception("BP processing failed")
            return _json_error(str(e), 500)

    @app.post("/api/upload/kaizen")
    def upload_kaizen():
        try:
            return handle_upload("kaizen", data_processor.process_kaizen_file)
        except Exception as e:
            logger.exception("Kaizen processing failed")
            return _json_error(str(e), 500)

    @app.post("/api/analytics/calculate")
    def calculate():
        if not any(
            [
                session_data["lipt"],
                session_data["suggestion"],
                session_data["bp"],
                session_data["kaizen"],
            ]
        ):
            return _json_error("Upload at least one file first", 400)

        try:
            session_data["analytics"] = analytics_engine.calculate_department_analytics(
                lipt_data=session_data["lipt"],
                sugg_data=session_data["suggestion"],
                bp_data=session_data["bp"],
                kaizen_data=session_data["kaizen"],
            )
        except Exception as e:
            logger.exception("Analytics failed")
            return _json_error(str(e), 500)

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Analytics calculated",
                    "data": session_data["analytics"],
                }
            ),
            200,
        )

    @app.get("/api/analytics/global")
    def global_analytics():
        if not session_data["analytics"]:
            return _json_error("No analytics available. Click Analyze.", 400)
        return jsonify({"success": True, "data": session_data["analytics"]["global"]}), 200

    @app.get("/api/analytics/department/<dept_name>")
    def dept_analytics(dept_name: str):
        if not session_data["analytics"]:
            return _json_error("No analytics available. Click Analyze.", 400)

        depts = session_data["analytics"].get("departments", {})
        if dept_name not in depts:
            return _json_error(f"Department '{dept_name}' not found", 404)

        return jsonify({"success": True, "data": depts[dept_name]}), 200

    @app.post("/api/reset")
    def reset():
        session_data["lipt"] = None
        session_data["suggestion"] = None
        session_data["bp"] = None
        session_data["kaizen"] = None
        session_data["analytics"] = None
        session_data["last_upload"] = {}
        return jsonify({"success": True, "message": "Session reset"}), 200

    @app.errorhandler(404)
    def not_found(_):
        return _json_error("Endpoint not found", 404)

    @app.errorhandler(413)
    def too_large(_):
        return _json_error("File too large (max 16 MB)", 413)

    return app


if __name__ == "__main__":
    app = create_app()
    logger.info("Starting clean backend on http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
