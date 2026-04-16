"""CI Dashboard (clean) backend configuration."""

import os


class Config:
    # Department targets
    DEPT_TARGETS = {
        "Assembly": {"lipt": 6, "suggestion": 122, "bp": 1, "kaizen": 100, "roadmap": 10},
        "Cutting & LP": {"lipt": 3, "suggestion": 64, "bp": 1, "kaizen": 100, "roadmap": 10},
        "Maintenance": {"lipt": 3, "suggestion": 4, "bp": 1, "kaizen": 100, "roadmap": 10},
        "Logistics": {"lipt": 10, "suggestion": 10, "bp": 1, "kaizen": 100, "roadmap": 10},
        "Engineering": {"lipt": 8, "suggestion": 8, "bp": 1, "kaizen": 100, "roadmap": 10},
        "Quality": {"lipt": 4, "suggestion": 6, "bp": 1, "kaizen": 100, "roadmap": 10},
        "EHS": {"lipt": 1, "suggestion": 1, "bp": 1, "kaizen": 100, "roadmap": 1},
        "HR": {"lipt": 1, "suggestion": 1, "bp": 1, "kaizen": 100, "roadmap": 1},
        "IT": {"lipt": 1, "suggestion": 1, "bp": 1, "kaizen": 100, "roadmap": 1},
        "CI": {"lipt": 1, "suggestion": 1, "bp": 1, "kaizen": 100, "roadmap": 1},
    }

    LIPT_COLUMNS = {
        "dept": [
            "Business Segment",
            "Plant Name",
            "Departement ",
            "Departement",
            "Dept",
            "Department",
            "Site",
            "Unité",
        ],
        "status": ["Status", "Statut", "État"],
        "category": [
            "Improvement Category",
            "Secondary Cost Productivity Category",
            "Catégorie",
            "Category",
        ],
        "savings": ["Annual Savings", "Savings", "Économies"],
        "date": [
            "Creation Date",
            "Date",
            "Date de création",
            "Start Date",
            "Submission Date",
        ],
        "close_date": [
            "Close Date",
            "Date Completed",
            "Completion Date",
            "End Date",
            "Date de clôture",
        ],
        "submitter": [
            "Originator",
            "Project Leader",
            "Owner",
            "Employé",
            "Submitter",
            "Created By",
        ],
    }

    SUGGESTION_COLUMNS = {
        "dept": ["Département", "Departement", "Dept", "Department"],
        "status": ["Statut", "Status", "État"],
        "type": ["Type d'amélioration", "Type", "Improvement Type"],
        "date": ["Date d'envoi", "Date", "Submission Date", "Creation Date"],
        "close_date": ["Date de clôture", "Close Date", "Resolution Date"],
        "employee": ["Employé", "Employee", "Submitter", "Created By"],
    }

    BP_COLUMNS = {
        "dept": [
            "Dept",
            "Department",
            "Département",
            "Business Segment",
            "Plant Name",
            "Site",
        ]
    }

    KAIZEN_COLUMNS = {
        "dept": ["Dept", "Department", "Département"],
        "progress": ["Progress", "Progrès", "Avancement"],
    }

    DEPARTMENT_ALIASES = {
        "assembly": "Assembly",
        "cutting & lp": "Cutting & LP",
        "cutting and lp": "Cutting & LP",
        "cutting lp": "Cutting & LP",
        "maintenance": "Maintenance",
        "logistics": "Logistics",
        "engineering": "Engineering",
        "quality": "Quality",
        "ehs": "EHS",
        "hr": "HR",
        "it": "IT",
        "ci": "CI",
        "e-systems - wire europe": "CI",
    }

    UNKNOWN_DEPT_FALLBACK = "CI"

    STATUS_KEYWORDS = {
        "completed": ["completed", "terminé", "done", "closed", "achevé", "fini"],
        "in_progress": ["in progress", "en cours", "ongoing", "wip", "active"],
        "pending": ["pending", "en attente", "waiting", "open", "ouvert"],
        "approved": ["approved", "approuvé", "validated", "validé"],
        "rejected": ["rejected", "rejeté", "declined", "refusé"],
        "cancelled": ["cancelled", "annulé", "canceled"],
    }

    SECRET_KEY = os.environ.get("SECRET_KEY") or "dev-secret-key"
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    ALLOWED_EXTENSIONS = {"xlsx", "xls"}
