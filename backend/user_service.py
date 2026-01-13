# user_service.py

import json
import re
from typing import Dict, Any, List, Tuple, Optional
from database import get_user, update_user, get_missing_fields, save_message


def extract_user_info(message: str, llm) -> Dict[str, Any]:
    """LLM으로 메시지에서 사용자 정보 추출"""
    
    prompt = f"""
사용자 메시지에서 다음 정보를 추출해주세요.
추출할 수 없는 정보는 null로 표시하세요.
반드시 JSON 형식으로만 답변하세요. 다른 설명 없이 JSON만 출력하세요.

추출할 정보:
- age: 나이 (숫자만)
- region: 거주지역 (서울, 경기, 부산 등 시/도 단위)
- job_status: 취업상태 (구직중, 재직중, 학생, 무직 중 하나)
- income_level: 소득수준 (저소득, 중위소득, 일반 중 하나)
- housing_type: 주거형태 (자가, 전세, 월세, 기숙사 중 하나)
- interests: 관심분야 배열 (취업, 주거, 금융, 창업, 교육, 복지 중 해당하는 것들)

사용자 메시지: "{message}"

JSON:
"""
    
    try:
        response = llm.invoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)
        
        # JSON 추출
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            extracted = json.loads(json_match.group())
            # null 값 필터링
            return {k: v for k, v in extracted.items() if v is not None}
    except Exception as e:
        print(f"❌ 정보 추출 오류: {e}")
    
    return {}


def process_and_save(user_id: str, message: str, llm) -> Dict[str, Any]:
    """
    사용자 메시지 처리 & DB 저장
    1. 정보 추출
    2. DB 업데이트
    3. 대화 저장
    """
    # 1. 정보 추출
    extracted = extract_user_info(message, llm)
    
    if extracted:
        print(f"📝 추출된 정보: {extracted}")
        # 2. 사용자 정보 DB 업데이트
        update_user(user_id, extracted)
    
    # 3. 대화 저장
    save_message(user_id, "user", message, extracted if extracted else None)
    
    return extracted


def save_bot_response(user_id: str, answer: str):
    """챗봇 응답 DB 저장"""
    save_message(user_id, "assistant", answer)