# backend/report/report_generator.py
# 보고서 생성 핵심 로직 (팀 코드와 동일: ChatOllama.invoke() 사용 / API 호출 없음)
# - Planner: NOW/3M/6M + 정책명(최소 1개씩) + why_now 생성
# - 3줄 요약: 항상 LLM이 "액션/주의/다음단계" 3줄로 생성(예시 포함)
# - 파싱 실패 시 fallback_report로 절대 죽지 않게

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from langchain_ollama import ChatOllama

from .report_schema import (
    ReportRequest,
    ReportResponse,
    StrategyReport,
    TimelineBlock,
    PolicyCard,
)

_FACT_PATTERNS = {
    "region": re.compile(r"(서울|경기|인천|부산|대구|대전|광주|울산|세종|강원|충북|충남|전북|전남|경북|경남|제주)"),
    "employment": re.compile(r"(재직|구직|실업|취업준비|프리랜서|사업\s?준비|자영업|학생|학업|무직)"),
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



def _get_llm() -> ChatOllama:
    # 팀 main.py와 동일한 기본 모델로 통일
    # (환경변수 OLLAMA_REPORT_MODEL이 있으면 그걸 우선 사용)
    model = os.getenv("OLLAMA_REPORT_MODEL", "gemma3:4b")
    temperature = float(os.getenv("OLLAMA_REPORT_TEMPERATURE", "0"))
    return ChatOllama(model=model, temperature=temperature)



def _safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    """
    LLM 출력에서 JSON object만 안전하게 추출
    - 첫 { 부터 마지막 } 까지 추출 후 json.loads
    """
    if not text:
        return None
    try:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            return None
        return json.loads(m.group(0))
    except Exception:
        return None


def _llm_json(llm: ChatOllama, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """
    ChatOllama.invoke()로 JSON을 받는다.
    - LangChain 메시지 객체를 안 쓰고(팀 코드도 string prompt 사용),
      system/user를 한 번에 문자열로 합쳐 전달
    """
    prompt = f"""
[System]
{system_prompt}

[User]
{user_prompt}
""".strip()

    res = llm.invoke(prompt)
    content = res.content if hasattr(res, "content") else str(res)

    data = _safe_json_parse(content)
    if data is None:
        raise ValueError("LLM JSON parse failed")
    return data


def _fallback_report(facts: Dict[str, Any]) -> StrategyReport:
    urgency = facts.get("urgency", "NORMAL")
    region = facts.get("region", None)
    employment = facts.get("employment", "상태 미확인")
    topic = facts.get("topic_hint", "GENERAL")

    if topic == "HOUSING":
        now = PolicyCard(
            policy_name="청년월세 한시 특별지원",
            why_now="월세/주거는 지금 신청 가능 여부부터 확인하세요.",
            benefit_type="HOUSING",
            links=[],
        )
        m3 = PolicyCard(
            policy_name="청년 전세자금 대출",
            why_now="3개월 내 소득·무주택 등 조건을 정리하세요.",
            benefit_type="LOAN",
            links=[],
        )
        m6 = PolicyCard(
            policy_name="(전략) 중복 제한/기간 제약 점검",
            why_now="6개월 시점에 중복/기간을 재점검하세요.",
            benefit_type="ETC",
            links=[],
        )
    else:
        now = PolicyCard(
            policy_name="국민취업지원제도",
            why_now=f"{urgency} 기준으로 지금 신청 가능 여부부터 확인하세요.",
            benefit_type="JOB",
            links=[],
        )
        m3 = PolicyCard(
            policy_name="청년일자리도약장려금",
            why_now=f"{employment} 상태에서 3개월 내 서류/조건을 정리하세요.",
            benefit_type="JOB",
            links=[],
        )
        region_phrase = f"{region} 기준" if region else "거주지 기준"
        m6 = PolicyCard(
            policy_name=f"(전략) {region_phrase} 추가 지원 탐색",
            why_now="6개월 시점엔 중복/기간 제약을 확인하며 확장하세요.",
            benefit_type="ETC",
            links=[],
        )

    return StrategyReport(
        header="상담 결과 기반 정책 전략 가이드",
        timeline=[
            TimelineBlock(key="NOW", title="지금", policies=[now]),
            TimelineBlock(key="PLUS_3M", title="3개월 후", policies=[m3]),
            TimelineBlock(key="PLUS_6M", title="6개월 후", policies=[m6]),
        ],
        strategy_summary="",
    )


def _planner_system_prompt() -> str:
    return """
너는 '청년정책 상담 보고서 Planner'다.
상담 로그를 바탕으로 '지금/3개월/6개월' 3개 시점에 대해 정책명 1개씩만 추천한다.

[출력 절대 규칙]
- 반드시 JSON만 출력한다. (설명/문장/마크다운 금지)
- timeline은 정확히 3개: NOW, PLUS_3M, PLUS_6M
- 각 시점 policies는 정확히 1개
- why_now는 90자 이내 (짧게)
- policy_name은 가능한 한 실제 정책명 형태로 (없으면 '(전략) ...'로 작성)
- links는 빈 배열 허용 (URL은 지금 단계에서 생략 가능)

[JSON 스키마]
{
  "header": "상담 결과 기반 정책 전략 가이드",
  "timeline": [
    {"key":"NOW","title":"지금","policies":[{"policy_name":"...","why_now":"...","benefit_type":"CASH|VOUCHER|LOAN|EDU|JOB|HOUSING|ETC","links":[]}]},
    {"key":"PLUS_3M","title":"3개월 후","policies":[{"policy_name":"...","why_now":"...","benefit_type":"CASH|VOUCHER|LOAN|EDU|JOB|HOUSING|ETC","links":[]}]},
    {"key":"PLUS_6M","title":"6개월 후","policies":[{"policy_name":"...","why_now":"...","benefit_type":"CASH|VOUCHER|LOAN|EDU|JOB|HOUSING|ETC","links":[]}]}
  ],
  "strategy_summary": ""
}
""".strip()


def _planner_user_prompt(chat_log: List[Dict[str, Any]], facts: Dict[str, Any]) -> str:
    return f"""
상담 로그와 추출 사실을 근거로, 아래 JSON 스키마를 채워라.
- 정책이 확정되지 않으면 '(전략) ...'로 작성하되, 사용자가 이해 가능한 문장으로.

[Extracted Facts]
{json.dumps(facts, ensure_ascii=False, indent=2)}

[Chat Log]
{json.dumps(chat_log, ensure_ascii=False, indent=2)}

JSON:
""".strip()


def _summary_system_prompt() -> str:
    # ✅ “사용자가 꼭 알고 나가야 하는 정보”를 강제하는 역할 프롬프트
    return """
너는 '상담 종료 직전 3줄 요약'을 쓰는 마지막 편집자다.
사용자는 이 3줄만 보고 "지금 뭘 해야 하는지"를 이해하고 나가야 한다.

[절대 규칙]
- 반드시 JSON만 출력한다.
- bullets는 정확히 3개.
- 각 bullet은 "사용자 행동" 중심으로 써라. (상담 메타/분석/감정/긴급도 평가 금지)
- 반드시 아래 3가지 역할을 순서대로 지켜라:
  1) 지금 당장 해야 할 행동(신청/확인/준비)
  2) 놓치면 손해/주의사항(조건 미확인, 중복, 기간 등) — 단정 금지
  3) 다음 단계(추가로 확인해야 할 정보 1~2개만 콕 찍기)
- 상담 로그/추출 사실 범위 밖 내용은 만들지 말 것.
- 추천 정책명이 있으면 1개 이상 bullet에 포함.

[예시(절대 수정 금지, 이 톤/수준을 그대로 따라라)]
- 지금 바로 신청 가능한 지원 제도부터 확인하세요. 예. 서울시 청년 대중교통비 지원, 
- 25년 상반기 무주택 청년 월세 ‘한시 지원’ 있었으니, 26년 1분기에도 재개 여부를 체크해보세요.
- 실업급여 수급 종료 후, 6개월이 지난 시점부터 국민취업지원제도 이용이 가능합니다.

[JSON]
{ "bullets": ["...", "...", "..."] }
""".strip()


def _summary_user_prompt(chat_log: List[Dict[str, Any]], facts: Dict[str, Any], timeline_names: List[str]) -> str:
    # ✅ 실제 화면에 뜨는 추천 정책명을 같이 주면, LLM이 “메타요약”으로 도망갈 확률이 줄어듦
    return f"""
아래 자료만 근거로 3줄 요약 bullets 3개를 작성하라.

[추천 정책명(화면에 표시되는 후보)]
{json.dumps(timeline_names, ensure_ascii=False)}

[Extracted Facts]
{json.dumps(facts, ensure_ascii=False, indent=2)}

[Chat Log]
{json.dumps(chat_log, ensure_ascii=False, indent=2)}

JSON:
""".strip()


def _timeline_policy_names(report: StrategyReport) -> List[str]:
    names: List[str] = []
    for block in (report.timeline or []):
        for p in (block.policies or []):
            n = (p.policy_name or "").strip()
            if n and n not in names:
                names.append(n)
    return names[:5]


def _format_bullets_to_text(bullets: List[str]) -> str:
    b = [(str(x).strip()) for x in bullets[:3]]
    while len(b) < 3:
        b.append("추가 질문을 주면 더 정확히 정리할 수 있어요.")
    return "\n".join([f"- {b[0]}", f"- {b[1]}", f"- {b[2]}"])


def generate_strategy_report(req: ReportRequest) -> ReportResponse:
    llm = _get_llm()

    chat_log = [m.model_dump() for m in req.chat_log]
    facts = req.extracted_facts or extract_facts_from_chat(chat_log)

    meta: Dict[str, Any] = {
        "provider": "ollama_chatollama",
        "model": os.getenv("OLLAMA_REPORT_MODEL", "llama3.2"),
        "planner_used_llm": False,
        "summary_used_llm": False,
    }

    # 1) Planner (타임라인+정책명) 생성 시도
    try:
        planner_json = _llm_json(
            llm=llm,
            system_prompt=_planner_system_prompt(),
            user_prompt=_planner_user_prompt(chat_log, facts),
        )
        report = StrategyReport(**planner_json)
        meta["planner_used_llm"] = True
    except Exception as e:
        report = _fallback_report(facts)
        meta["planner_used_llm"] = False
        meta["planner_error"] = str(e)

    # 2) 3줄 요약은 항상 LLM 시도(실패하면 fallback 문구)
    try:
        names = _timeline_policy_names(report)
        summary_json = _llm_json(
            llm=llm,
            system_prompt=_summary_system_prompt(),
            user_prompt=_summary_user_prompt(chat_log, facts, names),
        )
        bullets = summary_json.get("bullets", [])
        if not (isinstance(bullets, list) and len(bullets) == 3):
            raise ValueError("bullets shape invalid")
        report.strategy_summary = _format_bullets_to_text(bullets)
        meta["summary_used_llm"] = True
    except Exception as e:
        # 네가 준 예시를 “기준 수준”으로 안전문구 제공
        report.strategy_summary = "\n".join([
            "- 지금 바로 신청 가능한 지원 제도부터 확인하세요. (예: 청년 교통비/생활비 계열)",
            "- 월세·주거·소득·중복수급 조건부터 확인하고, 제출 서류를 미리 준비해두세요.",
            "- 26년 1분기 무주택 청년 월세 한시 지원 재개 여부를 기억해두고 체크하세요.",
        ])
        meta["summary_used_llm"] = False
        meta["summary_error"] = str(e)

    return ReportResponse(session_id=req.session_id, report=report, meta=meta)
