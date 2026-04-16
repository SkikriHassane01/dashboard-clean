"""Analytics (clean).

Kept compatible with the existing data shapes produced by the processors.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class Analytics:
    def __init__(self, config):
        self.config = config
        self.dept_targets = config.DEPT_TARGETS

    def calculate_department_analytics(
        self, lipt_data: Dict, sugg_data: Dict, bp_data: Dict, kaizen_data: Dict
    ) -> Dict[str, Any]:
        logger.info("Calculating analytics...")

        analytics: Dict[str, Any] = {
            "departments": {},
            "global": {
                "total_lipt": 0,
                "total_suggestions": 0,
                "total_bp": 0,
                "total_kaizen": 0,
                "total_savings": 0.0,
                "total_contributors": 0,
                "lipt_completed": 0,
                "suggestions_approved": 0,
                "avg_dept_score": 0,
                "completion_rate": 0,
            },
            "top_submitters_lipt": {},
            "top_submitters_suggestions": {},
            "time_series_lipt": {},
            "time_series_suggestions": {},
            "time_series_bp": {},
            "time_series_kaizen": {},
            "savings_by_category": {},
            "suggestions_by_type": {},
            "target_vs_real": {"lipt": {}, "suggestions": {}, "bp": {}, "kaizen": {}},
            "pareto_savings": [],
            "kpi_summary": {},
        }

        for dept_name, targets in self.dept_targets.items():
            analytics["departments"][dept_name] = {
                "name": dept_name,
                "targets": targets,
                "lipt": self._init_lipt_metrics(targets["lipt"]),
                "suggestion": self._init_suggestion_metrics(targets["suggestion"]),
                "bp": self._init_bp_metrics(targets["bp"]),
                "kaizen": self._init_kaizen_metrics(targets["kaizen"]),
                "roadmap": {"total": 0, "target": targets["roadmap"], "gap": -targets["roadmap"]},
                "score": 0,
                "detailed_analysis": {
                    "lipt_pareto_savings": [],
                    "top_lipt_submitters": [],
                    "top_suggestion_contributors": [],
                    "avg_savings_per_lipt": 0,
                    "total_projects": 0,
                    "total_ideas": 0,
                    "completion_rate": 0,
                },
            }

        # LIPT
        if lipt_data and "departments" in lipt_data:
            for dept_name, dept_data in lipt_data["departments"].items():
                if dept_name not in analytics["departments"]:
                    continue
                dept = analytics["departments"][dept_name]
                dept["lipt"].update(
                    {
                        "total": dept_data["total"],
                        "completed": dept_data.get("completed", 0),
                        "in_progress": dept_data.get("in_progress", 0),
                        "pending": dept_data.get("pending", 0),
                        "savings": round(dept_data.get("savings", 0.0), 2),
                        "by_category": dept_data.get("by_category", {}),
                        "by_month": dept_data.get("by_month", {}),
                        "top_submitters": dept_data.get("top_submitters", {}),
                        "items": dept_data.get("items", []),
                    }
                )
                dept["lipt"]["gap"] = dept_data["total"] - dept["lipt"]["target"]

                analytics["target_vs_real"]["lipt"][dept_name] = {
                    "target": dept["lipt"]["target"],
                    "real": dept_data["total"],
                    "percentage": round(
                        (dept_data["total"] / dept["lipt"]["target"] * 100)
                        if dept["lipt"]["target"] > 0
                        else 0,
                        1,
                    ),
                }

                dept["detailed_analysis"]["total_projects"] = dept_data["total"]
                if dept_data["total"] > 0:
                    dept["detailed_analysis"]["avg_savings_per_lipt"] = round(
                        dept_data.get("savings", 0.0) / dept_data["total"], 2
                    )
                    dept["detailed_analysis"]["completion_rate"] = round(
                        (dept_data.get("completed", 0) / dept_data["total"]) * 100, 1
                    )

                dept["detailed_analysis"]["top_lipt_submitters"] = sorted(
                    dept_data.get("top_submitters", {}).items(), key=lambda x: x[1], reverse=True
                )[:5]

                savings_by_cat: Dict[str, float] = {}
                for item in dept_data.get("items", []):
                    cat = item.get("category", "Unknown")
                    savings_by_cat[cat] = savings_by_cat.get(cat, 0.0) + float(item.get("savings", 0.0) or 0.0)
                dept["detailed_analysis"]["lipt_pareto_savings"] = sorted(
                    savings_by_cat.items(), key=lambda x: x[1], reverse=True
                )

            analytics["top_submitters_lipt"] = dict(
                sorted(lipt_data.get("top_submitters", {}).items(), key=lambda x: x[1], reverse=True)[:10]
            )
            analytics["time_series_lipt"] = lipt_data.get("time_series", {})
            analytics["savings_by_category"] = lipt_data.get("category_distribution", {})

        # Suggestions
        if sugg_data and "departments" in sugg_data:
            for dept_name, dept_data in sugg_data["departments"].items():
                if dept_name not in analytics["departments"]:
                    continue
                dept = analytics["departments"][dept_name]
                dept["suggestion"].update(
                    {
                        "total": dept_data.get("total", 0),
                        "pending": dept_data.get("pending", 0),
                        "approved": dept_data.get("approved", 0),
                        "rejected": dept_data.get("rejected", 0),
                        "completed": dept_data.get("completed", 0),
                        "cost_saving": dept_data.get("cost_saving", 0),
                        "productivity": dept_data.get("productivity", 0),
                        "quality": dept_data.get("quality", 0),
                        "safety": dept_data.get("safety", 0),
                        "other": dept_data.get("other", 0),
                        "by_month": dept_data.get("by_month", {}),
                        "top_submitters": dept_data.get("top_submitters", {}),
                        "contributors_count": dept_data.get("contributors_count", 0),
                        "items": dept_data.get("items", []),
                    }
                )
                dept["suggestion"]["gap"] = dept_data.get("total", 0) - dept["suggestion"]["target"]

                analytics["target_vs_real"]["suggestions"][dept_name] = {
                    "target": dept["suggestion"]["target"],
                    "real": dept_data.get("total", 0),
                    "percentage": round(
                        (dept_data.get("total", 0) / dept["suggestion"]["target"] * 100)
                        if dept["suggestion"]["target"] > 0
                        else 0,
                        1,
                    ),
                }

                dept["detailed_analysis"]["total_ideas"] = dept_data.get("total", 0)
                dept["detailed_analysis"]["top_suggestion_contributors"] = sorted(
                    dept_data.get("top_submitters", {}).items(), key=lambda x: x[1], reverse=True
                )[:5]

            analytics["top_submitters_suggestions"] = dict(
                sorted(sugg_data.get("top_submitters", {}).items(), key=lambda x: x[1], reverse=True)[:10]
            )
            analytics["time_series_suggestions"] = sugg_data.get("time_series", {})
            analytics["suggestions_by_type"] = sugg_data.get("type_distribution", {})

        # BP
        if bp_data and "departments" in bp_data:
            for dept_name, dept_data in bp_data["departments"].items():
                if dept_name not in analytics["departments"]:
                    continue
                dept = analytics["departments"][dept_name]
                dept["bp"].update({"total": dept_data.get("total", 0), "items": dept_data.get("items", [])})
                dept["bp"]["gap"] = dept_data.get("total", 0) - dept["bp"]["target"]
                analytics["target_vs_real"]["bp"][dept_name] = {
                    "target": dept["bp"]["target"],
                    "real": dept_data.get("total", 0),
                    "percentage": round(
                        (dept_data.get("total", 0) / dept["bp"]["target"] * 100)
                        if dept["bp"]["target"] > 0
                        else 0,
                        1,
                    ),
                }
            analytics["time_series_bp"] = bp_data.get("time_series", {})

        # Kaizen
        if kaizen_data and "departments" in kaizen_data:
            for dept_name, dept_data in kaizen_data["departments"].items():
                if dept_name not in analytics["departments"]:
                    continue
                dept = analytics["departments"][dept_name]
                dept["kaizen"].update(
                    {
                        "count": dept_data.get("count", 0),
                        "avg_progress": dept_data.get("avg_progress", 0.0),
                        "items": dept_data.get("items", []),
                    }
                )
                dept["kaizen"]["gap"] = round(dept_data.get("avg_progress", 0.0) - dept["kaizen"]["target"], 2)
                analytics["target_vs_real"]["kaizen"][dept_name] = {
                    "target": dept["kaizen"]["target"],
                    "real": dept_data.get("avg_progress", 0.0),
                    "percentage": round(
                        (dept_data.get("avg_progress", 0.0) / dept["kaizen"]["target"] * 100)
                        if dept["kaizen"]["target"] > 0
                        else 0,
                        1,
                    ),
                }
            analytics["time_series_kaizen"] = kaizen_data.get("time_series", {})

        for dept_name in analytics["departments"]:
            analytics["departments"][dept_name]["score"] = self._calculate_dept_score(analytics["departments"][dept_name])

        analytics["global"] = self._calculate_global_stats(analytics["departments"])

        # Pareto global savings (rough estimate per category)
        all_savings = []
        for dept in analytics["departments"].values():
            for cat, count in (dept["lipt"].get("by_category") or {}).items():
                if dept["lipt"]["total"] > 0:
                    cat_savings = (count / dept["lipt"]["total"]) * float(dept["lipt"].get("savings", 0.0) or 0.0)
                    all_savings.append({"category": cat, "savings": round(cat_savings, 2)})
        analytics["pareto_savings"] = sorted(all_savings, key=lambda x: x["savings"], reverse=True)[:10]

        analytics["kpi_summary"] = {
            "total_projects": analytics["global"]["total_lipt"],
            "total_ideas": analytics["global"]["total_suggestions"],
            "total_savings": analytics["global"]["total_savings"],
            "total_contributors": analytics["global"]["total_contributors"],
            "completion_rate": analytics["global"]["completion_rate"],
            "avg_score": analytics["global"]["avg_dept_score"],
        }

        return analytics

    def _init_lipt_metrics(self, target: int) -> Dict[str, Any]:
        return {
            "total": 0,
            "target": target,
            "gap": -target,
            "completed": 0,
            "in_progress": 0,
            "pending": 0,
            "savings": 0.0,
            "by_category": {},
            "by_month": {},
            "top_submitters": {},
            "items": [],
        }

    def _init_suggestion_metrics(self, target: int) -> Dict[str, Any]:
        return {
            "total": 0,
            "target": target,
            "gap": -target,
            "pending": 0,
            "approved": 0,
            "rejected": 0,
            "completed": 0,
            "cost_saving": 0,
            "productivity": 0,
            "quality": 0,
            "safety": 0,
            "other": 0,
            "by_month": {},
            "top_submitters": {},
            "contributors_count": 0,
            "items": [],
        }

    def _init_bp_metrics(self, target: int) -> Dict[str, Any]:
        return {"total": 0, "target": target, "gap": -target, "items": []}

    def _init_kaizen_metrics(self, target: int) -> Dict[str, Any]:
        return {"count": 0, "target": target, "gap": -target, "avg_progress": 0.0, "items": []}

    def _calculate_dept_score(self, dept: Dict[str, Any]) -> int:
        scores = []

        if dept["lipt"]["target"] > 0:
            scores.append(min((dept["lipt"]["total"] / dept["lipt"]["target"]) * 100, 100))
        if dept["suggestion"]["target"] > 0:
            scores.append(min((dept["suggestion"]["total"] / dept["suggestion"]["target"]) * 100, 100))
        if dept["bp"]["target"] > 0:
            scores.append(min((dept["bp"]["total"] / dept["bp"]["target"]) * 100, 100))

        scores.append(min(float(dept["kaizen"].get("avg_progress", 0.0) or 0.0), 100))

        if dept["roadmap"]["target"] > 0:
            scores.append(min((dept["roadmap"]["total"] / dept["roadmap"]["target"]) * 100, 100))

        return round(sum(scores) / len(scores)) if scores else 0

    def _calculate_global_stats(self, departments: Dict[str, Any]) -> Dict[str, Any]:
        global_stats = {
            "total_lipt": 0,
            "total_suggestions": 0,
            "total_bp": 0,
            "total_kaizen": 0,
            "total_savings": 0.0,
            "total_contributors": 0,
            "lipt_completed": 0,
            "suggestions_approved": 0,
            "avg_dept_score": 0,
            "completion_rate": 0,
        }

        dept_scores = []
        for dept in departments.values():
            global_stats["total_lipt"] += int(dept["lipt"]["total"])
            global_stats["total_suggestions"] += int(dept["suggestion"]["total"])
            global_stats["total_bp"] += int(dept["bp"]["total"])
            global_stats["total_kaizen"] += int(dept["kaizen"].get("count", 0))
            global_stats["total_savings"] += float(dept["lipt"].get("savings", 0.0) or 0.0)
            global_stats["total_contributors"] += int(dept["suggestion"].get("contributors_count", 0))
            global_stats["lipt_completed"] += int(dept["lipt"].get("completed", 0))
            global_stats["suggestions_approved"] += int(dept["suggestion"].get("approved", 0))
            dept_scores.append(int(dept.get("score", 0)))

        global_stats["total_savings"] = round(global_stats["total_savings"], 2)
        if dept_scores:
            global_stats["avg_dept_score"] = round(sum(dept_scores) / len(dept_scores))
        if global_stats["total_lipt"] > 0:
            global_stats["completion_rate"] = round(
                (global_stats["lipt_completed"] / global_stats["total_lipt"]) * 100, 1
            )

        return global_stats
