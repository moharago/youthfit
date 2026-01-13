# backend/report/report_generator.py
# 시간 기반 전략(JSON) 생성 핵심 로직
# - 지금은 "Planner(보고서)" 중심으로 완성
# - OPENAI_API_KEY 있으면 JSON-only planner 호출
# - 없거나 실패하면 fallback으로 "전략 형태" 유지

from __future__ import annotations
import os
import json
import re
from typing import List, Dict, Any

import requests

from .report_schema import (
    ReportRequest,
    ReportResponse,
    StrategyReport,
    TimelineBlock,
    PolicyCard,
)


_FACT_PATTERNS = {
    "region": re.compile(r"(서울|경기|인천|부산|대구|대전|광주|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)"),
    "employment": re.compile(r"(재직|구직|실업|취업준비|프리랜서|사업\s?준비|자영업|학생|학업)"),
    "age": re.compile(r"(\d{2})\s?세"),
    "income_hint": re.compile(r"(중위소득|소득|건보료|건강보험료|연봉|월급)"),
    "urgent_cash": re.compile(r"(당장|급해|긴급|이번달|이번\s?주|현금|즉시|바로|생활비)"),
    "housing": re.compile(r"(전세|월세|주거|이사|대출)"),
    "job_support": re.compile(r"(취업|구직|일자리|면접|이력서|고용)"),
}


def extract_facts_from_chat(chat_log: List[Dict[str, Any]]) -> Dict[str, Any]:
    text = "\n".join([m.get("content", "") for m in chat_log if m.get("role") != "system"])
    facts: Dict[str, Any] = {}

    for k, pat in _FACT_PATTERNS.items():
        m = pat.search(text)
        if m:
            facts[k] = m.group(0)

    facts["urgency"] = "HIGH" if _FACT_PATTERNS["urgent_cash"].search(text) else "NORMAL"
    facts["topic_hint"] = "HOUSING" if _FACT_PATTERNS["housing"].search(text) else ("JOB" if _FACT_PATTERNS["job_support"].search(text) else "GENERAL")
    return facts


def _call_openai_json(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY가 없습니다.")

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    url = "https://api.openai.com/v1/chat/completions"

    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }

    r = requests.post(
        url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        data=json.dumps(payload),
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)


def _planner_system_prompt() -> str:
    return """
너는 "대한민국 청년 정책 시간 기반 전략 상담 AI"의 Planner다.
목표는 정보 나열이 아니라, 시간 축(지금/이후/나중) 기반 행동 전략을 만든다.

[출력 규칙 - 절대 위반 금지]
- 반드시 JSON만 출력한다. (설명/문장/마크다운 금지)
- timeline은 NOW, PLUS_1M, PLUS_3M, PLUS_6M 중 필요한 것만, 최대 4개.
- 각 시점의 policies는 0~3개, 가능하면 1~2개로 유지.
- why_now는 1줄(90자 이내).
- strategy_summary는 3~4문장, 반드시 포함:
  1) 지금 해야 할 선택
  2) 기다리면 더 유리한 선택
  3) 순서를 잘못 잡으면 불리한 지점

[Self-check]
- 시간 기준 없이 정책을 나열했는지 검사하고 수정한다.
- 선행 조건/중복 제한이 불명확하면 “보수적으로” 표현한다.
""".strip()


def _planner_user_prompt(chat_log: List[Dict[str, Any]], facts: Dict[str, Any]) -> str:
    return f"""
다음 상담 로그와 추출 사실만 근거로 "시간 기반 정책 전략 가이드"를 구성해라.

[Extracted Facts]
{json.dumps(facts, ensure_ascii=False, indent=2)}

[Chat Log]
{json.dumps(chat_log, ensure_ascii=False, indent=2)}

[JSON Output Shape]
{{
  "header": "상담 결과 기반 정책 전략 가이드",
  "timeline": [
    {{
      "key": "NOW",
      "title": "지금",
      "policies": [
        {{
          "policy_name": "...",
          "why_now": "...",
          "benefit_type": "CASH|VOUCHER|LOAN|EDU|JOB|HOUSING|ETC",
          "links": [{{"label":"공식페이지","url":"https://..."}}]
        }}
      ]
    }}
  ],
  "strategy_summary": "..."
}}
""".strip()


def _fallback_report(facts: Dict[str, Any]) -> StrategyReport:
    urgency = facts.get("urgency", "NORMAL")
    region = facts.get("region", "지역 미확인")
    employment = facts.get("employment", "상태 미확인")
    topic = facts.get("topic_hint", "GENERAL")

    # ✅ UI 요구사항: Now/3개월/6개월에서 "각 1개"만 보여줘도 되게 설계
    # (정책명은 실제 정책이 아니라 "전략 카드"로 표현 — Validator 붙으면 실제 정책명으로 대체)
    if topic == "HOUSING":
        now_cards = [
            PolicyCard(
                policy_name="(전략) 이사/계약 시점 확정 + 신청 가능 시점 체크",
                why_now="주거 정책은 ‘계약 전/후 가능’이 갈리니 지금 일정 확정이 손해를 줄입니다.",
                benefit_type="HOUSING",
                links=[],
            )
        ]
        plus3_cards = [
            PolicyCard(
                policy_name="(전략) 서류/조건(소득·재직·무주택) 충족 상태로 ‘대출/지원’ 비교",
                why_now="+3개월 내 조건을 정리하면, 효율 높은 선택지를 놓치지 않습니다.",
                benefit_type="ETC",
                links=[],
            )
        ]
        plus6_cards = [
            PolicyCard(
                policy_name="(전략) 중복 제한/대체 관계 점검 후 최종 선택 확정",
                why_now="순서를 잘못 잡으면 더 큰 혜택을 막을 수 있어 최종 결정은 마지막에 확정합니다.",
                benefit_type="HOUSING",
                links=[],
            )
        ]
    else:
        now_cards = [
            PolicyCard(
                policy_name="(전략) 즉시 신청 가능한 단기 지원 후보 1개부터 확정",
                why_now=f"{urgency} 우선순위: 지금 신청 가능한 정책부터 먼저 잡아 손실을 줄이세요.",
                benefit_type="CASH",
                links=[],
            )
        ]
        plus3_cards = [
            PolicyCard(
                policy_name=f"(전략) {employment} 상태에서 조건형 정책을 열기 위한 준비(기록/서류)",
                why_now="+3개월 내 준비하면 ‘조건 충족 시점’에 맞춰 더 좋은 선택이 열립니다.",
                benefit_type="JOB",
                links=[],
            )
        ]
        plus6_cards = [
            PolicyCard(
                policy_name=f"(전략) {region} 기준 고효율 정책은 중복/기간 제약 확인 후 진행",
                why_now="지금 섣불리 선택하면 나중에 더 큰 혜택을 막을 수 있어 순서가 핵심입니다.",
                benefit_type="ETC",
                links=[],
            )
        ]

    timeline = [
        TimelineBlock(key="NOW", title="Now", policies=now_cards[:3]),
        TimelineBlock(key="PLUS_3M", title="3개월 후", policies=plus3_cards[:3]),
        TimelineBlock(key="PLUS_6M", title="6개월 후", policies=plus6_cards[:3]),
    ]

    summary = (
        "지금은 ‘바로 실행 가능한 선택’ 1개를 먼저 확정해 불확실성을 줄이세요. "
        "3개월 내에는 조건/서류/기록을 갖춰 더 유리한 선택지를 여는 편이 좋습니다. "
        "6개월 시점에는 중복 제한·기간 제약을 점검하지 않으면 손해로 이어질 수 있습니다."
    )

    return StrategyReport(header="상담 결과 기반 정책 전략 가이드", timeline=timeline, strategy_summary=summary)


def generate_strategy_report(req: ReportRequest) -> ReportResponse:
    chat_log = [m.model_dump() for m in req.chat_log]
    facts = req.extracted_facts or extract_facts_from_chat(chat_log)

    meta: Dict[str, Any] = {"used_llm": False, "provider": None}

    try:
        planner_json = _call_openai_json(
            system_prompt=_planner_system_prompt(),
            user_prompt=_planner_user_prompt(chat_log, facts),
        )
        report = StrategyReport(**planner_json)
        meta.update({"used_llm": True, "provider": "openai"})
    except Exception as e:
        report = _fallback_report(facts)
        meta.update({"used_llm": False, "provider": None, "error": str(e)})

    return ReportResponse(session_id=req.session_id, report=report, meta=meta)
