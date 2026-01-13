# user_service.py

import json
import re
from typing import Dict, Any
from database import (
    get_user,
    update_user,
    save_message,
    get_chat_history,
    create_user
)

# =====================
# 대화 저장 & 조회
# =====================

def save_chat(user_id: str, role: str, content: str, extracted_info: Dict = None):
    create_user(user_id)
    save_message(user_id, role, content, extracted_info)

def get_recent_chats(user_id: str, limit: int = 5) -> list:
    return get_chat_history(user_id, limit)

def format_history(chats: list) -> str:
    if not chats:
        return "이전 대화 없음"

    lines = []
    for chat in chats:
        role = "사용자" if chat["role"] == "user" else "상담사"
        lines.append(f"{role}: {chat['content']}")
    return "\n".join(lines)

# =====================
# 사용자 정보 추출
# =====================

def extract_user_info(message: str, llm) -> Dict[str, Any]:
    prompt = f"""
사용자 메시지에서 개인 정보만 추출하세요.
반드시 JSON 형식으로만 답변하세요.

추출 항목:
- age (숫자)
- region ("서울", "경기" 등)
- job_status ("구직중", "재직중", "학생", "무직")
- income_level ("저소득", "중위소득", "일반")
- housing_type ("자가", "전세", "월세", "기숙사")
- interests (["취업", "주거", "금융", "창업", "교육", "복지"])

메시지: "{message}"
JSON:
"""
    try:
        res = llm.invoke(prompt)
        content = res.content if hasattr(res, "content") else str(res)
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if match:
            data = json.loads(match.group())
            return {k: v for k, v in data.items() if v not in [None, "", []]}
    except Exception as e:
        print("❌ 정보 추출 실패:", e)

    return {}

def process_and_save(user_id: str, message: str, llm) -> Dict[str, Any]:
    extracted = extract_user_info(message, llm)

    if extracted:
        update_user(user_id, extracted)

    save_chat(user_id, "user", message, extracted if extracted else None)
    return extracted
