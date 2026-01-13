# backend/suggestion_service.py
from __future__ import annotations

from typing import Optional, Tuple, List


# 업데이트 by Dayforged (연관질문 기능)
# - LLM 사용하지 않음 (키워드 룰 기반: 안정/비용 0)
# - 현재 MVP 목적: "답변 아래에 다음 질문 1개"만 추가해서 사용자가 추가 정보/연관 정책을 떠올리게 만들기

CATEGORY_RULES: List[Tuple[str, List[str], str]] = [
    (
        "MONEY",
        ["지원금", "수당", "현금", "돈", "계좌", "적금", "저축", "대출", "이자", "금리", "자산", "통장", "장려금"],
        "혹시 재정적인 지원(현금/수당/대출/저축지원) 중에서 어떤 쪽이 가장 급하신가요? (현금성/대출/저축·자산형성)",
    ),
    (
        "HOUSING",
        ["주거", "월세", "전세", "임대", "보증금", "이사", "자취", "청약", "주택", "집"],
        "혹시 주거 관련해서 월세/전세/이사(보증금) 중 어떤 고민이 가장 크신가요? (월세/전세/이사·보증금)",
    ),
    (
        "JOB",
        ["취업", "구직", "일자리", "면접", "이력서", "직업훈련", "실업", "실업급여", "고용", "근로", "재직", "무직"],
        "혹시 취업 관련해서 지금 단계가 어디쯤이신가요? (구직 시작/훈련·자격증/면접·입사/재직 중 고용유지)",
    ),
    (
        "WELFARE",
        ["복지", "건강", "병원", "상담", "마음건강", "심리", "의료", "돌봄", "가족", "수급", "차상위"],
        "혹시 복지/건강 쪽 지원도 같이 찾고 계신가요? (마음건강/의료비/돌봄·가구지원)",
    ),
]


def _pick_category(message: str) -> Optional[str]:
    """키워드 매칭으로 가장 먼저 걸리는 카테고리 반환 (MVP 단순화)"""
    text = (message or "").strip()
    if not text:
        return None

    for cat, keywords, _ in CATEGORY_RULES:
        for k in keywords:
            if k in text:
                return cat
    return None


def build_followup_question(message: str) -> Optional[str]:
    """
    사용자 질문(원문) 기반으로 연관 질문 1개 생성.
    - 반환값이 None이면 추가 질문을 붙이지 않는다.
    """
    cat = _pick_category(message)
    if not cat:
        return "추가로 어느 분야가 궁금하세요? (취업/주거/금융/복지)"

    for c, _, q in CATEGORY_RULES:
        if c == cat:
            return q
    return None


def append_followup_to_answer(answer: str, user_message: str) -> str:
    """기존 답변 문자열 끝에 '연관 질문'을 붙여 반환"""
    base = (answer or "").strip()
    followup = build_followup_question(user_message)

    if not followup:
        return base

    # MVP: 텍스트만 추가 (프론트 수정 없이 바로 노출 가능)
    return f"{base}\n\n---\n\n💡 추가 질문\n{followup}"
