# backend/router.py

import json
import re
from typing import Dict, Any, List, Optional


MISSING_CANDIDATES = {
    "age", "region", "job_status", "household_size", "income_level",
    "unemployment_benefit", "recent_work_history", "student"
}

def _auto_reason(route: str, missing_fields: List[str]) -> str:
    """reason은 디버깅/로깅용이므로 코드에서 안정적으로 생성"""
    if route == "ASK_CLARIFY":
        return f"판정형 질문 + 추가정보 필요({len(missing_fields)}개 후보)"
    if route == "RAG_REWRITE":
        return "모호/포괄 질문 → 재정의 후 RAG 필요"
    return "문서 기반 정보형 질문"


def _safe_json_parse(text: str) -> Dict[str, Any]:
    """
    LLM 출력에서 JSON만 안전하게 추출/파싱
    - ```json ... ``` 코드블록 제거
    - 첫 { 부터 마지막 } 까지만 잘라서 json.loads
    """
    try:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON found")
        return json.loads(match.group())
    except Exception:
        return {
            "route": "RAG_DIRECT",
            "reason": "fallback_router_parse_failed",
            "missing_fields": [],
            "clarifying_questions": [],
            "rewrite_question": None,
        }


def route_question(question: str, user_profile: Dict[str, Any], extracted: Optional[Dict[str, Any]], llm) -> Dict[str, Any]:
    extracted = extracted or {}
    """
    Supervisor Router (판단만)
    - OFF_TOPIC: 청년정책 무관
    - PROFILE_RECOMMEND: 정보만 제공(프로필 업데이트) → 추천/탐색
    - RAG_DIRECT: 문서 기반 정보 제공 질문
    - RAG_REWRITE: 검색용으로 재정의가 필요한 질문
    - ASK_CLARIFY: 개인 판정 질문 + 정보 부족(필요 필드만 반환)
    """

    prompt = f"""
너는 청년정책 상담 챗봇의 '분기 판단 엔진'이다.
아래 3가지 중 하나로만 분기하고, 반드시 JSON만 출력한다.

[입력]
- user_profile: DB에 저장된 사용자 정보
- extracted: 이번 사용자 메시지에서 새로 추출된 사용자 정보(없으면 빈 dict)
- question: 사용자 질문

[우선 규칙]
- 사용자가 "가능/자격/대상/선발/몇유형/1유형/2유형/될까/신청해도" 같은 표현으로
  개인 판정(eligibility) 여부를 묻는 경우는 ASK_CLARIFY를 우선 고려한다.

[missing_fields 후보(이 목록에서만 선택)]
- age
- region
- job_status
- household_size
- income_level
- unemployment_benefit
- recent_work_history
- student

[분기 정의]
1) RAG_DIRECT
- 정책 설명/지원금/조건/신청방법 등 문서 기반 "정보 제공" 질문
- 문서 검색(RAG)로 충분히 답변 가능

2) RAG_REWRITE
- 질문이 모호/포괄적/여러 정책이 섞여 검색에 부적합
- "검색에 적합한 형태로 질문을 재정의"해야 답변 품질이 올라감
- rewrite_question에 "검색에 적합한 정제 질문"을 반드시 생성

3) ASK_CLARIFY
- 사용자가 "가능/자격/대상/선발/몇유형" 등 개인 판정 질문을 함
- user_profile만으로 판단에 필요한 정보가 부족하면 missing_fields에 부족한 필드를 넣는다
- 단, 질문 문장(재질문 문장)은 절대 생성하지 말고 missing_fields만 채운다


[출력 JSON 스키마]
{{
  "route": "RAG_DIRECT|RAG_REWRITE|ASK_CLARIFY",
  "reason": "분기이유(짧게)",
  "missing_fields": [],
  "rewrite_question": null
}}

[현재 user_profile]
{user_profile}

[사용자 질문]
"{question}"

JSON:
""".strip()

    response = llm.invoke(prompt)
    content = response.content if hasattr(response, "content") else str(response)

    # 디버깅 원하면 잠깐 켜두기
    # print("=== ROUTER RAW ===\n", content, "\n=================")

    result = _safe_json_parse(content)

    # result는 dict여야 함
    if not isinstance(result, dict):
        result = {
            "route": "RAG_DIRECT",
            "reason": "fallback_result_not_dict",
            "missing_fields": [],
            "rewrite_question": None,
        }

    # 기본 보정
    route = str(result.get("route", "RAG_DIRECT")).strip().upper()
    reason = result.get("reason", None)
    missing_fields = result.get("missing_fields", [])
    rewrite_question = result.get("rewrite_question", None)

    # missing_fields 정리
    if not isinstance(missing_fields, list):
        missing_fields = []

    # RAG_REWRITE가 아니면 rewrite_question 무조건 None 처리
    if route != "RAG_REWRITE":
        rewrite_question = None
    elif not isinstance(rewrite_question, str) or not rewrite_question.strip():
        # RAG_REWRITE인데 rewrite_question이 없으면 최소 보정
        rewrite_question = question
        
    # ASK_CLARIFY인데 missing_fields가 비어있으면 최소 안전장치
    if route == "ASK_CLARIFY" and not missing_fields:
        missing_fields = ["region", "income_level", "household_size"]

    # reason이 이상하게(템플릿 문구 복붙 등) 들어오면 코드에서 자동 생성
    if (not isinstance(reason, str)) or ("짧게" in reason) or (len(reason.strip()) < 2):
        reason = _auto_reason(route, missing_fields)

    # 최대 3개로 제한
    missing_fields = missing_fields[:3]

    return {
        "route": route,
        "reason": reason,
        "missing_fields": missing_fields,
        "rewrite_question": rewrite_question
    } 