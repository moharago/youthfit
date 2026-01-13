# backend/report/report_from_db_service.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from database import get_chat_history, get_user
from report.report_schema import (
    ReportFromDBRequest,
    ReportFromLogRequest,
    ReportRequest,
    ChatMessage,
    ReportResponse,
    StrategyReport,
    TimelineBlock,
    PolicyCard,
    PolicyLink,
)
from report.report_generator import generate_strategy_report, extract_facts_from_chat

# =========================
# ✅ 업데이트 by Dayforged (보고서 기능)
# - 기존에는 정책 언급 수로 SUMMARY_ONLY / REPORT 분기
# - 현재는 MVP 안정성 우선: "항상 REPORT"로 강제 (요약/빈칸 방지 포함)
# =========================

_ALLOWED_TIMELINE_KEYS = ["NOW", "PLUS_3M", "PLUS_6M"]

# (참고) 정책/제도 키워드 감지 (사용자+챗봇 발화 전체에서 통합)
# - 현재는 "항상 REPORT"라서 gate로 쓰지 않음(메타/디버그용으로만 사용 가능)
_POLICY_PATTERN = re.compile(r"[가-힣]{2,}(제도|지원금|지원|장려금|카드|통장|대출|수당|장려|희망|일자리|정책|도약|청년)")


def _apply_mvp_constraints(report: StrategyReport) -> StrategyReport:
    """
    MVP 제약:
    - 타임라인은 NOW/PLUS_3M/PLUS_6M만
    - 시점당 카드 1개만 유지
    - 항상 3개 시점이 존재하도록 보정(비어있으면 이후 단계에서 주입)
    """
    if not report.timeline:
        report.timeline = []

    filtered: List[TimelineBlock] = []
    for block in report.timeline:
        if block.key in _ALLOWED_TIMELINE_KEYS:
            block.policies = (block.policies or [])[:1]
            filtered.append(block)

    order = {k: i for i, k in enumerate(_ALLOWED_TIMELINE_KEYS)}
    filtered.sort(key=lambda b: order.get(b.key, 999))

    report.timeline = filtered[:3]
    return report


def _count_policy_mentions(chat_log: List[Dict[str, Any]]) -> int:
    text = "\n".join([m.get("content", "") for m in chat_log if m.get("role") in ("user", "assistant")])
    uniques = set()
    for m in re.finditer(_POLICY_PATTERN, text):
        uniques.add(m.group(0))
    return len(uniques)


# =========================
# 보고서 관련 코드 (업데이트 by dayforged) - 추가 시작
# ✅ MVP 안정성 우선:
# - "내용이 없거나/LLM 실패/DB 불안정"이어도
#   NOW/3M/6M에 각 1개씩 무조건 카드가 보이도록 강제 주입
# - 정책명은 발표용 '그럴듯한 기본값'을 사용
# =========================
def _default_policy_cards(topic_hint: str | None) -> Dict[str, PolicyCard]:
    """
    topic_hint에 따라 기본 카드(시점별 1개)를 준비.
    - topic_hint는 report_generator.extract_facts_from_chat에서 생성되는 값( HOUSING / JOB / GENERAL )
    """
    topic_hint = (topic_hint or "GENERAL").upper()

    if topic_hint == "HOUSING":
        return {
            "NOW": PolicyCard(
                policy_name="청년월세 한시 특별지원",
                why_now="월세 부담 완화 성격은 ‘지금’ 신청 가능 여부부터 확인하는 게 손해를 줄입니다.",
                benefit_type="HOUSING",
                links=[],
            ),
            "PLUS_3M": PolicyCard(
                policy_name="청년 전세자금 대출",
                why_now="3개월 안에 소득/무주택 등 조건을 정리하면 더 유리한 선택지를 비교할 수 있습니다.",
                benefit_type="LOAN",
                links=[],
            ),
            "PLUS_6M": PolicyCard(
                policy_name="(전략) 중복 제한/서류 요건 점검 후 최종 선택",
                why_now="나중에 더 큰 혜택을 막지 않도록, 6개월 시점에 중복/기간 제약을 재점검합니다.",
                benefit_type="ETC",
                links=[],
            ),
        }

    if topic_hint == "JOB":
        return {
            "NOW": PolicyCard(
                policy_name="국민취업지원제도",
                why_now="구직/취업 지원은 절차가 있으니 지금 신청 가능 여부와 필요 서류부터 확인하는 게 유리합니다.",
                benefit_type="JOB",
                links=[],
            ),
            "PLUS_3M": PolicyCard(
                policy_name="청년일자리도약장려금",
                why_now="3개월 내 취업/채용 조건을 맞추면 기업지원 연계 가능성이 열릴 수 있습니다.",
                benefit_type="JOB",
                links=[],
            ),
            "PLUS_6M": PolicyCard(
                policy_name="국민내일배움카드",
                why_now="장기적으로 역량/자격을 쌓아 선택지를 늘리는 전략이 필요합니다.",
                benefit_type="EDU",
                links=[],
            ),
        }

    # GENERAL
    return {
        "NOW": PolicyCard(
            policy_name="(전략) 교통비/생활비 단기 지원 후보 확인",
            why_now="지금은 ‘즉시 가능한 지원’부터 확인해 불확실성을 줄이는 게 우선입니다.",
            benefit_type="CASH",
            links=[],
        ),
        "PLUS_3M": PolicyCard(
            policy_name="청년월세 한시 특별지원",
            why_now="3개월 안에 조건(거주/소득 등)을 정리하면 신청 가능성이 올라갑니다.",
            benefit_type="HOUSING",
            links=[],
        ),
        "PLUS_6M": PolicyCard(
            policy_name="국민내일배움카드",
            why_now="6개월 시점에는 교육/훈련을 통해 장기적으로 선택지를 확대하는 전략이 유리합니다.",
            benefit_type="EDU",
            links=[],
        ),
    }


def _ensure_block(report: StrategyReport, key: str, title: str) -> TimelineBlock:
    for b in report.timeline:
        if b.key == key:
            return b
    b = TimelineBlock(key=key, title=title, policies=[])
    report.timeline.append(b)
    return b


def _force_inject_defaults(report: StrategyReport, facts: Dict[str, Any] | None) -> StrategyReport:
    """
    - NOW/PLUS_3M/PLUS_6M 블록이 없으면 생성
    - 각 블록에 policies가 없으면 기본 카드 1개 주입
    - policies가 1개보다 많으면 이미 MVP 제약에서 1개로 잘림
    """
    facts = facts or {}
    topic_hint = facts.get("topic_hint", "GENERAL")

    defaults = _default_policy_cards(topic_hint)

    now_b = _ensure_block(report, "NOW", "지금")
    m3_b = _ensure_block(report, "PLUS_3M", "3개월 후")
    m6_b = _ensure_block(report, "PLUS_6M", "6개월 후")

    if not now_b.policies:
        now_b.policies = [defaults["NOW"]]
    if not m3_b.policies:
        m3_b.policies = [defaults["PLUS_3M"]]
    if not m6_b.policies:
        m6_b.policies = [defaults["PLUS_6M"]]

    # 순서 고정
    order = {k: i for i, k in enumerate(_ALLOWED_TIMELINE_KEYS)}
    report.timeline.sort(key=lambda b: order.get(b.key, 999))

    # 요약도 빈칸이면 기본 문구로 채움
    if not (report.strategy_summary or "").strip():
        report.strategy_summary = (
            "지금은 ‘바로 실행 가능한 지원’부터 1개 확정해 불확실성을 줄이세요. "
            "3개월 내에는 조건/서류를 정리해 더 유리한 선택지를 열고, "
            "6개월 시점에는 중복 제한·기간 제약을 재점검해 손해를 방지합니다."
        )

    return report
# =========================
# 보고서 관련 코드 (업데이트 by dayforged) - 추가 끝
# =========================


def _profile_keywords(user: Dict[str, Any] | None, facts: Dict[str, Any] | None) -> str:
    if user:
        parts: List[str] = []
        if user.get("age"):
            parts.append(f"{user['age']}세")
        if user.get("region"):
            parts.append(f"{user['region']} 거주")
        if user.get("job_status"):
            parts.append(str(user["job_status"]))
        if user.get("income_level"):
            parts.append(f"소득: {user['income_level']}")
        if user.get("housing_type"):
            parts.append(f"주거: {user['housing_type']}")
        if parts:
            return ", ".join(parts)

    facts = facts or {}
    region = facts.get("region")
    employment = facts.get("employment")
    age = facts.get("age")
    parts2 = []
    if region:
        parts2.append(f"{region} 거주")
    if employment:
        parts2.append(str(employment))
    if age:
        parts2.append(str(age))
    return ", ".join(parts2) if parts2 else "사용자 정보 없음"


def _load_chat_log_from_db(user_id: str, limit: int) -> List[ChatMessage]:
    rows = get_chat_history(user_id, limit=limit)  # [{role, content, timestamp}, ...]
    out: List[ChatMessage] = []
    for r in rows:
        role = r.get("role")
        content = r.get("content", "")
        ts = r.get("timestamp")
        ts_str = str(ts) if ts is not None else None

        if role not in ("user", "assistant", "system"):
            role = "system"

        out.append(ChatMessage(role=role, content=content, ts=ts_str))
    return out


def generate_report_from_db(req: ReportFromDBRequest) -> ReportResponse:
    chat_log_models = _load_chat_log_from_db(user_id=req.user_id, limit=req.limit)
    chat_log = [m.model_dump() for m in chat_log_models]

    facts = req.extracted_facts or extract_facts_from_chat(chat_log)
    policy_mentions = _count_policy_mentions(chat_log)

    meta: Dict[str, Any] = {
        "source": "db",
        "user_id": req.user_id,
        "limit": req.limit,
        # MVP 안정성: 항상 REPORT로 강제
        "sufficiency": {"policy_mentions": policy_mentions, "ok": True, "forced": True},
    }

    base_req = ReportRequest(
        session_id=req.session_id,
        chat_log=chat_log_models,
        extracted_facts=req.extracted_facts,
    )

    try:
        resp = generate_strategy_report(base_req)
        resp.report = _apply_mvp_constraints(resp.report)
        resp.report = _force_inject_defaults(resp.report, facts=facts)
        resp.meta = {**(resp.meta or {}), **meta, "mode": "REPORT"}
        return resp
    except Exception as e:
        # ✅ 어떤 상황에서도 "REPORT 화면"이 나오게 강제
        report = StrategyReport(header="상담 결과 기반 정책 전략 가이드", timeline=[], strategy_summary="")
        report = _apply_mvp_constraints(report)
        report = _force_inject_defaults(report, facts=facts)

        meta.update({"error": str(e), "mode": "REPORT_FALLBACK"})
        return ReportResponse(session_id=req.session_id, report=report, meta=meta)


def generate_report_from_log(req: ReportFromLogRequest) -> ReportResponse:
    chat_log_models = req.chat_log
    chat_log = [m.model_dump() for m in chat_log_models]

    facts = req.extracted_facts or extract_facts_from_chat(chat_log)
    policy_mentions = _count_policy_mentions(chat_log)

    meta: Dict[str, Any] = {
        "source": "log",
        "user_id": None,
        "limit": len(chat_log),
        # MVP 안정성: 항상 REPORT로 강제
        "sufficiency": {"policy_mentions": policy_mentions, "ok": True, "forced": True},
    }

    base_req = ReportRequest(
        session_id=req.session_id,
        chat_log=chat_log_models,
        extracted_facts=req.extracted_facts,
    )

    try:
        resp = generate_strategy_report(base_req)
        resp.report = _apply_mvp_constraints(resp.report)
        resp.report = _force_inject_defaults(resp.report, facts=facts)
        resp.meta = {**(resp.meta or {}), **meta, "mode": "REPORT"}
        return resp
    except Exception as e:
        report = StrategyReport(header="상담 결과 기반 정책 전략 가이드", timeline=[], strategy_summary="")
        report = _apply_mvp_constraints(report)
        report = _force_inject_defaults(report, facts=facts)

        meta.update({"error": str(e), "mode": "REPORT_FALLBACK"})
        return ReportResponse(session_id=req.session_id, report=report, meta=meta)
