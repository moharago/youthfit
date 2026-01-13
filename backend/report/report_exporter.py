# backend/report/report_exporter.py
# 상담 기록/보고서 export (DB 없이 세션 단위 JSON 저장)

from __future__ import annotations
import os
import json
from datetime import datetime
from typing import Dict, Any

EXPORT_DIR = os.getenv("REPORT_EXPORT_DIR", "report_exports")


def export_report_json(session_id: str, payload: Dict[str, Any]) -> str:
    os.makedirs(EXPORT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(EXPORT_DIR, f"report_{session_id}_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
