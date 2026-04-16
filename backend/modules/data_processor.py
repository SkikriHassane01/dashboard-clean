"""Excel data processors (clean).

This keeps the same output structure as the original project so analytics and UI
stay stable.
"""

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class DataProcessor:
    def __init__(self, config):
        self.config = config
        self.dept_targets = config.DEPT_TARGETS

    # ---------- small helpers ----------
    def _normalize_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip().lower()
        text = unicodedata.normalize("NFKD", text)
        text = "".join(ch for ch in text if not unicodedata.combining(ch))
        text = re.sub(r"\s+", " ", text)
        return text

    def normalize_department_name(self, raw_name: Any) -> Optional[str]:
        normalized = self._normalize_text(raw_name)
        if not normalized or normalized == "nan":
            return None

        aliases = {
            self._normalize_text(k): v
            for k, v in getattr(self.config, "DEPARTMENT_ALIASES", {}).items()
        }
        if normalized in aliases:
            return aliases[normalized]

        for dept in self.dept_targets.keys():
            if normalized == self._normalize_text(dept):
                return dept

        relaxed = normalized.replace("&", "and")
        relaxed = re.sub(r"\s+", " ", relaxed).strip()
        for dept in self.dept_targets.keys():
            target = self._normalize_text(dept).replace("&", "and")
            if relaxed == target:
                return dept

        return None

    def find_column(self, df: pd.DataFrame, possible_names: List[str]) -> Optional[str]:
        df_cols = {str(col).strip().lower(): col for col in df.columns}
        for name in possible_names:
            key = str(name).strip().lower()
            if key in df_cols:
                return df_cols[key]
        return None

    def find_best_department_column(
        self, df: pd.DataFrame, possible_names: List[str]
    ) -> Optional[str]:
        df_cols = {str(col).strip().lower(): col for col in df.columns}
        candidates: List[str] = []
        for name in possible_names:
            key = str(name).strip().lower()
            if key in df_cols and df_cols[key] not in candidates:
                candidates.append(df_cols[key])
        if not candidates:
            return None

        best_col = candidates[0]
        best_matches = -1
        best_total = 1

        for col in candidates:
            sample = df[col].dropna()
            total = len(sample)
            matches = 0
            if total > 0:
                for v in sample:
                    if self.normalize_department_name(v):
                        matches += 1
            if matches > best_matches:
                best_col = col
                best_matches = matches
                best_total = max(total, 1)

        logger.info(
            "Department column selected '%s' (%s/%s mappable)",
            best_col,
            best_matches,
            best_total,
        )
        return best_col

    def detect_status(self, status_str: Any) -> str:
        if pd.isna(status_str) or status_str == "":
            return "unknown"
        status_lower = str(status_str).lower().strip()
        for status_type, keywords in self.config.STATUS_KEYWORDS.items():
            for keyword in keywords:
                if keyword in status_lower:
                    return status_type
        return "other"

    def safe_float(self, value: Any, default: float = 0.0) -> float:
        if pd.isna(value) or value == "" or value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            clean = re.sub(r"[$€,\s]", "", value.strip())
            multiplier = 1
            if clean.lower().endswith("k"):
                multiplier = 1000
                clean = clean[:-1]
            try:
                return float(clean) * multiplier
            except (ValueError, TypeError):
                return default
        return default

    def calculate_duration(self, start_date: Any, end_date: Any) -> Optional[int]:
        try:
            if pd.isna(start_date) or pd.isna(end_date):
                return None
            start = pd.to_datetime(start_date)
            end = pd.to_datetime(end_date)
            duration = (end - start).days
            if 0 <= duration <= 3650:
                return int(duration)
            return None
        except Exception:
            return None

    def extract_time_series(self, dates: List[Any]) -> Dict[str, int]:
        ts: Dict[str, int] = {}
        for d in dates:
            try:
                if pd.isna(d):
                    continue
                dt = pd.to_datetime(d)
                key = dt.strftime("%Y-%m")
                ts[key] = ts.get(key, 0) + 1
            except Exception:
                continue
        return dict(sorted(ts.items()))

    def _read_excel_first_sheet(self, file_path: str) -> pd.DataFrame:
        xl = pd.ExcelFile(file_path)
        try:
            sheet = xl.sheet_names[0]
            df = pd.read_excel(file_path, sheet_name=sheet)
            return df
        finally:
            xl.close()

    # ---------- processors ----------
    def process_lipt_file(self, file_path: str) -> Dict[str, Any]:
        df = self._read_excel_first_sheet(file_path)
        df = df.dropna(how="all")
        df.columns = df.columns.str.strip()

        dept_col = self.find_best_department_column(df, self.config.LIPT_COLUMNS["dept"])
        if not dept_col:
            raise ValueError("Department column is mandatory but not found")

        status_col = self.find_column(df, self.config.LIPT_COLUMNS["status"])
        savings_col = self.find_column(df, self.config.LIPT_COLUMNS["savings"])
        date_col = self.find_column(df, self.config.LIPT_COLUMNS["date"])
        close_col = self.find_column(df, self.config.LIPT_COLUMNS["close_date"])
        submitter_col = self.find_column(df, self.config.LIPT_COLUMNS["submitter"])
        category_col = self.find_column(df, self.config.LIPT_COLUMNS["category"])

        data: Dict[str, Any] = {
            "total_rows": len(df),
            "columns_detected": list(df.columns),
            "departments": {},
            "raw_data": [],
            "global_kpis": {},
            "time_series": {},
            "top_submitters": {},
            "status_distribution": {},
            "category_distribution": {},
            "durations": [],
            "validation_report": {
                "total_rows": len(df),
                "valid_rows": 0,
                "skipped_rows": 0,
                "unknown_departments": [],
            },
        }

        all_dates: List[Any] = []
        rows_processed = 0
        rows_skipped = 0

        for idx, row in df.iterrows():
            try:
                dept_raw = row[dept_col] if pd.notna(row[dept_col]) else ""
                dept_name = self.normalize_department_name(dept_raw)
                if not dept_name:
                    fallback = getattr(self.config, "UNKNOWN_DEPT_FALLBACK", None)
                    if fallback in self.dept_targets:
                        dept_name = fallback

                if dept_name not in self.dept_targets:
                    label = str(dept_raw).strip()
                    if label and label not in data["validation_report"]["unknown_departments"]:
                        data["validation_report"]["unknown_departments"].append(label)
                    rows_skipped += 1
                    continue

                if dept_name not in data["departments"]:
                    data["departments"][dept_name] = {
                        "total": 0,
                        "completed": 0,
                        "in_progress": 0,
                        "pending": 0,
                        "approved": 0,
                        "rejected": 0,
                        "other": 0,
                        "savings": 0.0,
                        "by_category": {},
                        "by_month": {},
                        "top_submitters": {},
                        "items": [],
                        "durations": [],
                        "avg_duration": 0,
                    }

                dept = data["departments"][dept_name]
                dept["total"] += 1
                rows_processed += 1

                status = "unknown"
                if status_col and pd.notna(row[status_col]):
                    status = self.detect_status(row[status_col])
                    dept[status] = dept.get(status, 0) + 1
                    data["status_distribution"][status] = data["status_distribution"].get(status, 0) + 1

                savings_value = 0.0
                if savings_col and pd.notna(row[savings_col]):
                    savings_value = self.safe_float(row[savings_col], 0.0)
                    if savings_value > 0:
                        dept["savings"] += savings_value

                category = "Unknown"
                if category_col and pd.notna(row[category_col]):
                    category = str(row[category_col]).strip() or "Unknown"
                dept["by_category"][category] = dept["by_category"].get(category, 0) + 1
                data["category_distribution"][category] = data["category_distribution"].get(category, 0) + 1

                if date_col and pd.notna(row[date_col]):
                    all_dates.append(row[date_col])
                    try:
                        dt = pd.to_datetime(row[date_col])
                        month_key = dt.strftime("%Y-%m")
                        dept["by_month"][month_key] = dept["by_month"].get(month_key, 0) + 1
                    except Exception:
                        pass

                submitter = ""
                if submitter_col and pd.notna(row[submitter_col]):
                    submitter = str(row[submitter_col]).strip()
                    if submitter:
                        dept["top_submitters"][submitter] = dept["top_submitters"].get(submitter, 0) + 1
                        data["top_submitters"][submitter] = data["top_submitters"].get(submitter, 0) + 1

                if date_col and close_col and pd.notna(row.get(date_col)) and pd.notna(row.get(close_col)):
                    duration = self.calculate_duration(row[date_col], row[close_col])
                    if duration and duration > 0:
                        dept["durations"].append(duration)
                        data["durations"].append(duration)

                item = {
                    "department": dept_name,
                    "status": status,
                    "savings": savings_value,
                    "category": category,
                    "submitter": submitter,
                }
                dept["items"].append(item)
                data["raw_data"].append(item)

            except Exception:
                rows_skipped += 1
                continue

        data["time_series"] = self.extract_time_series(all_dates)

        if data["durations"]:
            data["global_kpis"]["avg_duration_days"] = round(float(np.mean(data["durations"])), 1)
            data["global_kpis"]["min_duration_days"] = int(np.min(data["durations"]))
            data["global_kpis"]["max_duration_days"] = int(np.max(data["durations"]))
            data["global_kpis"]["median_duration_days"] = round(float(np.median(data["durations"])), 1)

        for dept in data["departments"].values():
            if dept["durations"]:
                dept["avg_duration"] = round(float(np.mean(dept["durations"])), 1)

        total = sum(data["status_distribution"].values())
        completed = data["status_distribution"].get("completed", 0)
        data["global_kpis"]["completion_rate"] = round((completed / total * 100) if total > 0 else 0, 1)

        data["validation_report"]["valid_rows"] = rows_processed
        data["validation_report"]["skipped_rows"] = rows_skipped

        return data

    def process_suggestion_file(self, file_path: str) -> Dict[str, Any]:
        df = self._read_excel_first_sheet(file_path)
        df = df.dropna(how="all")
        df.columns = df.columns.str.strip()

        dept_col = self.find_best_department_column(df, self.config.SUGGESTION_COLUMNS["dept"])
        if not dept_col:
            raise ValueError("Department column not found in Suggestions file")

        status_col = self.find_column(df, self.config.SUGGESTION_COLUMNS["status"])
        type_col = self.find_column(df, self.config.SUGGESTION_COLUMNS["type"])
        date_col = self.find_column(df, self.config.SUGGESTION_COLUMNS["date"])
        close_col = self.find_column(df, self.config.SUGGESTION_COLUMNS["close_date"])
        employee_col = self.find_column(df, self.config.SUGGESTION_COLUMNS["employee"])

        data: Dict[str, Any] = {
            "total_rows": len(df),
            "columns_detected": list(df.columns),
            "departments": {},
            "raw_data": [],
            "global_kpis": {},
            "time_series": {},
            "top_submitters": {},
            "status_distribution": {},
            "type_distribution": {},
            "durations": [],
            "validation_report": {"total_rows": len(df), "valid_rows": 0, "skipped_rows": 0},
        }

        all_dates: List[Any] = []
        rows_processed = 0
        rows_skipped = 0

        for _, row in df.iterrows():
            try:
                dept_raw = row[dept_col] if pd.notna(row[dept_col]) else ""
                dept_name = self.normalize_department_name(dept_raw)
                if not dept_name:
                    fallback = getattr(self.config, "UNKNOWN_DEPT_FALLBACK", None)
                    if fallback in self.dept_targets:
                        dept_name = fallback

                if dept_name not in self.dept_targets:
                    rows_skipped += 1
                    continue

                if dept_name not in data["departments"]:
                    data["departments"][dept_name] = {
                        "total": 0,
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
                        "contributors": set(),
                        "items": [],
                        "durations": [],
                        "avg_duration": 0,
                    }

                dept = data["departments"][dept_name]
                dept["total"] += 1
                rows_processed += 1

                if status_col and pd.notna(row[status_col]):
                    status = self.detect_status(row[status_col])
                    dept[status] = dept.get(status, 0) + 1
                    data["status_distribution"][status] = data["status_distribution"].get(status, 0) + 1

                if type_col and pd.notna(row[type_col]):
                    t = str(row[type_col]).lower()
                    if "cost" in t or "coût" in t:
                        dept["cost_saving"] += 1
                        data["type_distribution"]["Cost Saving"] = data["type_distribution"].get("Cost Saving", 0) + 1
                    elif "productivity" in t or "productivité" in t:
                        dept["productivity"] += 1
                        data["type_distribution"]["Productivity"] = data["type_distribution"].get("Productivity", 0) + 1
                    elif "quality" in t or "qualité" in t:
                        dept["quality"] += 1
                        data["type_distribution"]["Quality"] = data["type_distribution"].get("Quality", 0) + 1
                    elif "safety" in t or "sécurité" in t:
                        dept["safety"] += 1
                        data["type_distribution"]["Safety"] = data["type_distribution"].get("Safety", 0) + 1
                    else:
                        dept["other"] += 1
                        data["type_distribution"]["Other"] = data["type_distribution"].get("Other", 0) + 1

                if date_col and pd.notna(row[date_col]):
                    all_dates.append(row[date_col])
                    try:
                        dt = pd.to_datetime(row[date_col])
                        month_key = dt.strftime("%Y-%m")
                        dept["by_month"][month_key] = dept["by_month"].get(month_key, 0) + 1
                    except Exception:
                        pass

                if employee_col and pd.notna(row[employee_col]):
                    emp = str(row[employee_col]).strip()
                    if emp:
                        dept["contributors"].add(emp)
                        dept["top_submitters"][emp] = dept["top_submitters"].get(emp, 0) + 1
                        data["top_submitters"][emp] = data["top_submitters"].get(emp, 0) + 1

                if date_col and close_col and pd.notna(row.get(date_col)) and pd.notna(row.get(close_col)):
                    duration = self.calculate_duration(row[date_col], row[close_col])
                    if duration and duration > 0:
                        dept["durations"].append(duration)
                        data["durations"].append(duration)

            except Exception:
                rows_skipped += 1
                continue

        data["time_series"] = self.extract_time_series(all_dates)

        if data["durations"]:
            data["global_kpis"]["avg_duration_days"] = round(float(np.mean(data["durations"])), 1)

        total = sum(data["status_distribution"].values())
        approved = data["status_distribution"].get("approved", 0)
        data["global_kpis"]["approval_rate"] = round((approved / total * 100) if total > 0 else 0, 1)

        for dept in data["departments"].values():
            dept["contributors_count"] = len(dept["contributors"])
            dept["contributors"] = list(dept["contributors"])
            if dept["durations"]:
                dept["avg_duration"] = round(float(np.mean(dept["durations"])), 1)

        data["validation_report"]["valid_rows"] = rows_processed
        data["validation_report"]["skipped_rows"] = rows_skipped

        return data

    def process_bp_file(self, file_path: str) -> Dict[str, Any]:
        df = self._read_excel_first_sheet(file_path)
        df = df.dropna(how="all")
        df.columns = df.columns.str.strip()

        dept_col = self.find_best_department_column(df, self.config.BP_COLUMNS["dept"])
        if not dept_col:
            raise ValueError("Department column not found in BP file")

        data: Dict[str, Any] = {
            "total_rows": len(df),
            "columns_detected": list(df.columns),
            "departments": {},
            "raw_data": [],
            "global_kpis": {},
            "time_series": {},
            "status_distribution": {},
        }

        for _, row in df.iterrows():
            dept_raw = row[dept_col] if pd.notna(row[dept_col]) else ""
            dept_name = self.normalize_department_name(dept_raw)
            if not dept_name:
                fallback = getattr(self.config, "UNKNOWN_DEPT_FALLBACK", None)
                if fallback in self.dept_targets:
                    dept_name = fallback
            if dept_name not in self.dept_targets:
                continue
            if dept_name not in data["departments"]:
                data["departments"][dept_name] = {"total": 0, "items": []}
            data["departments"][dept_name]["total"] += 1

        return data

    def process_kaizen_file(self, file_path: str) -> Dict[str, Any]:
        df = self._read_excel_first_sheet(file_path)
        df = df.dropna(how="all")
        df.columns = df.columns.str.strip()

        dept_col = self.find_best_department_column(df, self.config.KAIZEN_COLUMNS["dept"])
        progress_col = self.find_column(df, self.config.KAIZEN_COLUMNS["progress"])
        if not dept_col:
            raise ValueError("Department column not found in Kaizen file")

        data: Dict[str, Any] = {
            "total_rows": len(df),
            "columns_detected": list(df.columns),
            "departments": {},
            "raw_data": [],
            "global_kpis": {},
        }

        for _, row in df.iterrows():
            dept_raw = row[dept_col] if pd.notna(row[dept_col]) else ""
            dept_name = self.normalize_department_name(dept_raw)
            if not dept_name:
                fallback = getattr(self.config, "UNKNOWN_DEPT_FALLBACK", None)
                if fallback in self.dept_targets:
                    dept_name = fallback
            if dept_name not in self.dept_targets:
                continue

            if dept_name not in data["departments"]:
                data["departments"][dept_name] = {
                    "total_progress": 0.0,
                    "count": 0,
                    "avg_progress": 0.0,
                    "items": [],
                }

            progress = 0.0
            if progress_col and pd.notna(row[progress_col]):
                progress = self.safe_float(row[progress_col], 0.0)
                progress = max(0.0, min(100.0, progress))

            data["departments"][dept_name]["total_progress"] += progress
            data["departments"][dept_name]["count"] += 1

        for dept in data["departments"].values():
            if dept["count"] > 0:
                dept["avg_progress"] = round(dept["total_progress"] / dept["count"], 2)

        return data
