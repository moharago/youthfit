# backend/router.py

import json
import re
from typing import Dict, Any, List, Optional


ALLOWED_FIELDS = [
    "region",
    "household_size",
    "income_level",
    "unemployment_benefit",
    "job_seeking",
    "recent_work_history",
    "student",
]

# ASK_CLARIFY에서 재질문 우선순위(UX 기준)
PRIORITY = [
    "unemployment_benefit",
    "income_level",
    "household_size",
    "region",
    "job_seeking",
    "recent_work_history",
    "student",
]

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
        cleaned = text.strip()

        # 코드블록 제거
        cleaned = re.sub(r"```json", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```", "", cleaned).strip()

        # JSON 객체 범위 추출
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("No JSON object boundaries found")

        json_text = cleaned[start : end + 1]
        return json.loads(json_text)

    except Exception as e:
        # 디버깅용: 필요하면 로그 남겨
        # print("❌ Router JSON parse error:", e, "\nRAW:", text)
        return {
            "route": "RAG_DIRECT",
            "reason": "Router JSON parse failed",
            "missing_fields": [],
            "rewrite_question": None,
        }


def _filter_missing_fields(fields: Any) -> List[str]:
    """missing_fields를 허용 목록으로만 필터링 + 중복 제거(순서 유지)"""
    if not isinstance(fields, list):
        return []

    filtered: List[str] = []
    for f in fields:
        if isinstance(f, str):
            f2 = f.strip()
            if f2 in ALLOWED_FIELDS:
                filtered.append(f2)

    seen = set()
    uniq: List[str] = []
    for f in filtered:
        if f not in seen:
            uniq.append(f)
            seen.add(f)
    return uniq

def _prioritize_missing_fields(missing_fields: List[str], top_k: int = 3) -> List[str]:
    """ASK_CLARIFY에서 missing_fields를 우선순위대로 정렬하고 최대 top_k개만 반환"""
    if not missing_fields:
        return []

    # 혹시 PRIORITY에 없는 값이 들어오면 뒤로 밀리도록 처리
    def key_fn(x: str) -> int:
        return PRIORITY.index(x) if x in PRIORITY else 999

    ordered = sorted(set(missing_fields), key=key_fn)
    return ordered[:top_k]

def route_question(question: str, user_profile: Dict[str, Any], llm) -> Dict[str, Any]:
    """
    Supervisor Router (판단만)
    - RAG_DIRECT: 문서 기반 정보 제공 질문
    - RAG_REWRITE: 검색용으로 재정의가 필요한 질문
    - ASK_CLARIFY: 개인 판정 질문 + 정보 부족(필요 필드만 반환)
    """

    prompt = f"""
너는 청년정책 상담 챗봇의 '분기 판단 엔진'이다.
아래 3가지 중 하나로만 분기하고, 반드시 JSON만 출력한다.

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

[missing_fields 후보 목록(이 목록에서만 선택)]
{ALLOWED_FIELDS}

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

    # 기본 보정
    route = str(result.get("route", "RAG_DIRECT")).strip().upper()
    reason = result.get("reason", None)
    missing_fields = _filter_missing_fields(result.get("missing_fields", []))
    rewrite_question = result.get("rewrite_question", None)

    # RAG_REWRITE가 아니면 rewrite_question 무조건 None 처리
    if route != "RAG_REWRITE":
        rewrite_question = None
        
    # ASK_CLARIFY인데 missing_fields가 비어있으면 최소 안전장치
    if route == "ASK_CLARIFY" and not missing_fields:
        missing_fields = ["region", "income_level", "household_size"]

    # reason이 이상하게(템플릿 문구 복붙 등) 들어오면 코드에서 자동 생성
    if (not isinstance(reason, str)) or ("짧게" in reason) or (len(reason.strip()) < 2):
        reason = _auto_reason(route, missing_fields)
        
    # ASK_CLARIFY인데 missing_fields가 비어있으면 최소 안전장치
    # (판정형인데도 필드 못 뽑았을 때)
    if route == "ASK_CLARIFY" and not missing_fields:
        # 가장 흔한 필드 2~3개 기본값
        missing_fields = ["region", "income_level", "household_size"]

    return {
        "route": route,
        "reason": reason,
        "missing_fields": missing_fields,
        "rewrite_question": rewrite_question,
    }
