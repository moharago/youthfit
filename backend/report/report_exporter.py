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


def load_report_json(path_or_report_id: str) -> Dict[str, Any]:
    """
    - path_or_report_id:
      1) export_report_json이 반환한 "전체 경로"를 그대로 받을 수 있음
      2) 또는 report_exports 아래 파일명(report_...json)만 받을 수 있음

    안전장치:
    - 파일명만 받은 경우: basename으로 경로 주입 방지
    """
    # 1) 전체 경로로 온 경우 우선 처리
    if os.path.isabs(path_or_report_id) or os.path.sep in str(path_or_report_id):
        path = path_or_report_id
    else:
        safe_name = os.path.basename(path_or_report_id)
        path = os.path.join(EXPORT_DIR, safe_name)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Report file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
