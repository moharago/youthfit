# backend/report/report_view.py
from __future__ import annotations

from typing import Any, Dict, List

from fastapi.responses import HTMLResponse


def _safe_get(d: Dict[str, Any], key: str, default=None):
    return d.get(key, default) if isinstance(d, dict) else default


def render_report_html(report_payload: Dict[str, Any]) -> HTMLResponse:
    meta = _safe_get(report_payload, "meta", {}) or {}
    mode = str(_safe_get(meta, "mode", "REPORT"))

    report = _safe_get(report_payload, "report", {}) or {}
    header = str(_safe_get(report, "header", "상담 결과 기반 정책 전략 가이드"))
    summary = str(_safe_get(report, "strategy_summary", ""))

    subtitle = "상담 기록을 바탕으로 “시간축 전략”을 정리합니다."

    timeline = _safe_get(report, "timeline", []) or []

    def pick(key: str):
        for b in timeline:
            if _safe_get(b, "key", "") == key:
                return b
        return None

    now_b = pick("NOW") or {}
    m3_b = pick("PLUS_3M") or {}
    m6_b = pick("PLUS_6M") or {}

    def policies(block: Dict[str, Any]) -> List[Dict[str, Any]]:
        p = _safe_get(block, "policies", [])
        return p if isinstance(p, list) else []

    # 요구사항: 박스는 1개씩만
    now_p = policies(now_b)[:1]
    m3_p = policies(m3_b)[:1]
    m6_p = policies(m6_b)[:1]

    bullets = _summary_to_3_bullets(summary)

    html = f"""
<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Report</title>

  <style>
    body {{
      margin: 0;
      padding: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial;
      background: transparent;
    }}

    .wrap {{
      padding: 18px 18px 26px 18px;
    }}

    .card {{
      background: rgba(255,255,255,0.92);
      border-radius: 16px;
      padding: 16px 16px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.10);
      margin-bottom: 14px;
    }}

    .title {{
      font-size: 18px;
      font-weight: 800;
      color: #0b1220;
      margin: 0 0 6px 0;
    }}

    .sub {{
      color: rgba(11,18,32,0.65);
      font-size: 13px;
      margin: 0 0 12px 0;
    }}

    /* 타임라인 바 */
    .timeline-wrap {{
      background: white;
      border-radius: 12px;
      padding: 14px 14px;
      border: 1px solid rgba(11,18,32,0.10);
      margin: 10px 0 10px 0;
    }}

    .timeline-bar {{
      position: relative;
      height: 40px;
      margin-top: 6px;
    }}

    .timeline-line {{
      position: absolute;
      top: 17px;
      left: 0;
      right: 0;
      height: 6px;
      border-radius: 999px;
      background: rgba(11,18,32,0.10);
    }}

    .tick {{
      position: absolute;
      top: 7px;
      width: 4px;
      height: 26px;
      background: rgba(11,18,32,0.85);
      border-radius: 999px;
      transform: translateX(-2px);
    }}

    .tick-labels {{
      display: flex;
      justify-content: space-between;
      margin-top: 6px;
      font-size: 12px;
      color: rgba(11,18,32,0.70);
      font-weight: 800;
    }}

    /* ✅ 타임라인 아래 박스 3개를 "한 줄"로 나열 */
    .box-row {{
      display: grid;
      grid-template-columns: 1fr 1fr 1fr;
      gap: 10px;
      margin-top: 10px;
    }}

    .pbox {{
      background: white;
      border-radius: 12px;
      padding: 12px 12px;
      border: 1px solid rgba(11,18,32,0.10);
      min-height: 58px;
      display: flex;
      align-items: center;
      justify-content: center;
      text-align: center;
    }}

    .pname {{
      font-weight: 900;
      color: #1e90ff;
      font-size: 13px;
      line-height: 1.25;
      text-decoration: none;
    }}

    .pname:hover {{
      text-decoration: underline;
    }}

    .muted {{
      color: rgba(11,18,32,0.45);
      font-size: 12px;
      font-weight: 700;
    }}

    .sec-title {{
      font-weight: 900;
      font-size: 14px;
      color: #0b1220;
      margin: 0 0 10px 0;
    }}

    .bullets {{
      margin: 0;
      padding-left: 18px;
      color: rgba(11,18,32,0.84);
      font-size: 13px;
      line-height: 1.45;
      font-weight: 650;
    }}
    .bullets li {{
      margin: 6px 0;
    }}

    .note {{
      color: rgba(11,18,32,0.55);
      font-size: 12px;
      margin-top: 8px;
    }}
  </style>
</head>

<body>
  <div class="wrap">
    <div class="card">
      <div class="title">{_escape(header)}</div>
      <div class="sub">{_escape(subtitle)}</div>

      <div class="timeline-wrap">
        <div class="sec-title">시간축 전략</div>

        <div class="timeline-bar">
          <div class="timeline-line"></div>
          <div class="tick" style="left:0%"></div>
          <div class="tick" style="left:50%"></div>
          <div class="tick" style="left:100%"></div>
        </div>

        <div class="tick-labels">
          <div>지금</div>
          <div>3개월 후</div>
          <div>6개월 후</div>
        </div>

        <div class="box-row">
          {_policy_name_box(now_p[0]) if now_p else _empty_box("추천 없음")}
          {_policy_name_box(m3_p[0]) if m3_p else _empty_box("추천 없음")}
          {_policy_name_box(m6_p[0]) if m6_p else _empty_box("추천 없음")}
        </div>
      </div>

      <div class="card" style="margin-top: 14px;">
        <div class="sec-title">3줄 요약</div>
        <ul class="bullets">
          <li>{_escape(bullets[0])}</li>
          <li>{_escape(bullets[1])}</li>
          <li>{_escape(bullets[2])}</li>
        </ul>
      </div>

      <div class="note">표시 모드: {_escape(mode)}</div>
    </div>
  </div>
</body>
</html>
    """.strip()

    return HTMLResponse(content=html)


def _policy_name_box(p: Dict[str, Any]) -> str:
    """
    박스에는 정책명만.
    - 링크가 있으면 정책명에 a 태그로 연결
    - 없으면 텍스트
    """
    name = _safe_get(p, "policy_name", "(정책명 없음)")
    links = _safe_get(p, "links", []) or []

    url = None
    if isinstance(links, list) and links:
        first = links[0] if isinstance(links[0], dict) else None
        if first:
            url = _safe_get(first, "url", None)

    if url:
        return f"""
        <div class="pbox">
          <a class="pname" href="{_escape_attr(url)}" target="_blank" rel="noopener noreferrer">{_escape(name)}</a>
        </div>
        """.strip()

    # 링크 없으면 그냥 이름만
    return f"""
    <div class="pbox">
      <div class="pname">{_escape(name)}</div>
    </div>
    """.strip()


def _empty_box(text: str) -> str:
    return f"""
    <div class="pbox">
      <div class="muted">{_escape(text)}</div>
    </div>
    """.strip()


def _summary_to_3_bullets(summary: str) -> List[str]:
    """
    report_generator가 '- ...' 형태로 내려주도록 만들었지만,
    혹시 깨져도 화면은 항상 3개가 보이게.
    """
    t = (summary or "").strip()
    if not t:
        return [
            "서울시 청년 대중 교통비 지원",
            "국비지원 훈련 과정 (내일배움카드)",
            "중복/기간 제약 해제",
        ]

    lines = [x.strip() for x in t.splitlines() if x.strip()]
    cleaned: List[str] = []
    for x in lines:
        x2 = x.strip()
        for p in ["- ", "• ", "1) ", "2) ", "3) ", "1. ", "2. ", "3. "]:
            if x2.startswith(p):
                x2 = x2[len(p):].strip()
        if x2:
            cleaned.append(x2)

    while len(cleaned) < 3:
        cleaned.append("추가 질문을 주면 더 정확히 정리할 수 있어요.")
    return cleaned[:3]


def _escape(s: str) -> str:
    s = "" if s is None else str(s)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
         .replace("'", "&#39;")
    )


def _escape_attr(s: str) -> str:
    # HTML attribute용 최소 이스케이프
    s = "" if s is None else str(s)
    return (
        s.replace("&", "&amp;")
         .replace('"', "&quot;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )
