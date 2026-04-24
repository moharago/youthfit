# user_service.py

import json
import re
from typing import Dict, Any
from database import (
    get_user,
    update_user,
    save_message,
    get_chat_history,
    create_user,
)
from profile_schema import ROUTER_MISSING_FIELDS

# =====================
# 대화 저장 & 조회
# =====================

def save_chat(user_id: str, role: str, content: str,
              conversation_id: str = None, extracted_info: Dict = None):
    create_user(user_id)
    save_message(user_id, role, content, conversation_id, extracted_info)

def get_recent_chats(user_id: str, limit: int = 5,
                     conversation_id: str = None) -> list:
    return get_chat_history(user_id, limit, conversation_id)

def format_history(chats: list) -> str:
    if not chats:
        return "이전 대화 없음"

    lines = []
    for chat in chats:
        role = "사용자" if chat["role"] == "user" else "상담사"
        content = chat["content"]
        # 어시스턴트 답변이 너무 길면 앞부분만 전달 (LLM이 그대로 반복하는 것 방지)
        if chat["role"] == "assistant" and len(content) > 200:
            content = content[:200] + "... [이하 생략]"
        lines.append(f"{role}: {content}")
    return "\n".join(lines)

# =====================
# 사용자 정보 추출
# =====================

def _has_explicit_housing_statement(message: str) -> bool:
    """정책명 속 '전세/월세'를 사용자의 주거형태로 오인하지 않기 위한 필터"""
    housing_words = r"(자가|전세|월세|기숙사)"
    explicit_patterns = [
        rf"{housing_words}\s*(살아|살고|거주|지내|사는|입니다|예요|이야)",
        rf"(주거형태|거주형태|사는\s*곳|집)\s*(은|는|이|가)?\s*{housing_words}",
        rf"{housing_words}\s*(계약했|계약했고|계약할|계약\s*예정|집|방)",
    ]
    return any(re.search(pattern, message) for pattern in explicit_patterns)


def _sanitize_extracted_info(message: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """LLM 추출 결과에서 정책명/질문을 개인 정보로 착각한 값을 제거"""
    cleaned = {k: v for k, v in data.items() if v not in [None, "", []]}

    if cleaned.get("housing_type") and not _has_explicit_housing_statement(message):
        cleaned.pop("housing_type", None)

    return cleaned


def extract_user_info(message: str, llm) -> Dict[str, Any]:
    prompt = f"""
사용자 메시지에서 개인 정보만 추출하세요.
반드시 JSON 형식으로만 답변하세요.

중요 규칙:
- 정책명/질문에 들어간 단어를 사용자 상태로 추정하지 마세요.
- 예: "청년 전세자금 대출 조건이 뭐야?" → housing_type을 추출하지 마세요.
- 예: "청년월세 지원 신청 방법은?" → housing_type을 추출하지 마세요.
- 사용자가 "전세 살아요", "월세로 살고 있어요", "주거형태는 기숙사예요"처럼 본인 상황을 직접 말한 경우에만 housing_type을 추출하세요.

추출 항목:
- age (숫자)
- region ("서울", "경기" 등)
- job_status ("구직중", "재직중", "학생", "무직")
- income_level ("저소득", "중위소득", "일반", "모름") — "잘 모르겠어요", "모른다", "모름" 등은 "모름"으로 저장
- housing_type ("자가", "전세", "월세", "기숙사")
- household_size (숫자. "1인" → 1, "2인" → 2, "3인" → 3, "4인 이상" → 4)
- unemployment_benefit ("수급중", "미수급", "모름") — "받고 있어요" → "수급중", "안 받아요" → "미수급", "잘 모르겠어요" → "모름"
- recent_work_history ("있음", "없음", "모름") — "있어요" → "있음", "없어요" → "없음", "잘 모르겠어요" → "모름"

메시지: "{message}"
JSON:
"""
    try:
        res = llm.invoke(prompt)
        content = res.content if hasattr(res, "content") else str(res)
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return _sanitize_extracted_info(message, data)
    except Exception as e:
        print("❌ 정보 추출 실패:", e)

    return {}

def process_and_save(user_id: str, message: str, llm,
                     conversation_id: str = None) -> Dict[str, Any]:
    extracted = extract_user_info(message, llm)

    if extracted:
        # 라우터/DB와 공통으로 관리하는 필드만 저장한다.
        extracted = {k: v for k, v in extracted.items() if k in ROUTER_MISSING_FIELDS or k == "housing_type"}
        update_user(user_id, extracted)

    save_chat(user_id, "user", message, conversation_id, extracted if extracted else None)
    return extracted
