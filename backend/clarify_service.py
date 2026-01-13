# backend/clarify_service.py

from typing import List, Dict

# missing_fields -> 사용자에게 던질 질문 템플릿
FIELD_QUESTIONS: Dict[str, str] = {
    "region": "현재 거주 지역(시/도)은 어디인가요? (예: 서울/경기/부산)",
    "household_size": "가구원 수는 몇 명인가요? (본인 포함)",
    "income_level": "가구 소득이 중위소득 기준 어느 정도인지 아시나요? (60% 이하 / 100% 이하 / 잘 모름)",
    "unemployment_benefit": "현재 실업급여를 받고 계신가요? (예/아니오/모름)",
    "job_seeking": "현재 구직등록(워크넷 등)이나 구직활동 의사가 있으신가요? (예/아니오)",
    "recent_work_history": "최근 2년 내 근로 이력이 있나요? (있음/없음/모름)",
    "student": "현재 학생 신분인가요? (예/아니오)",
}

def build_clarifying_questions(missing_fields: List[str], max_q: int = 3) -> List[str]:
    """
    router가 준 missing_fields를 질문 템플릿으로 변환
    - 최대 max_q개만 반환
    """
    questions = []
    for f in missing_fields:
        q = FIELD_QUESTIONS.get(f)
        if q:
            questions.append(q)
    return questions[:max_q]


def format_clarify_message(route_result: Dict) -> str:
    """
    ASK_CLARIFY일 때 사용자에게 보여줄 메시지(텍스트) 생성
    """
    questions = build_clarifying_questions(route_result.get("missing_fields", []), max_q=3)

    if not questions:
        return "정확한 안내를 위해 몇 가지 정보가 더 필요해요. 현재 거주 지역과 소득 수준을 알려주실 수 있을까요?"

    msg = "정확한 자격/유형 판단을 위해 몇 가지만 더 확인할게요 🙂\n\n"
    for i, q in enumerate(questions, start=1):
        msg += f"{i}) {q}\n"
    msg += "\n답변해주시면 해당 제도 기준으로 가능 여부/유형을 더 정확히 안내해드릴게요."
    return msg
