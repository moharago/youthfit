# backend/clarify_service.py

from typing import List, Dict

# missing_fields -> 사용자에게 던질 질문 템플릿
FIELD_QUESTIONS: Dict[str, str] = {
    "age": "나이가 어떻게 되시나요? (만 나이 기준)",
    "region": "현재 거주 지역은 어디인가요? (시/도 기준 예: 서울, 경기, 부산)",
    "job_status": "현재 취업 상태가 어떻게 되시나요? (구직중/재직중/학생/무직)",
    "household_size": "가구원 수는 몇 명인가요?",
    "income_level": "가구 소득이 중위소득 기준 어느 정도인지 아시나요? (60% 이하 / 100% 이하 / 잘 모르겠어요)",
    "unemployment_benefit": "현재 실업급여를 받고 계신가요? (예/아니오/모름)",
    "recent_work_history": "최근 1~2년 내 근로 이력이 있나요? (있음/없음/모름)",
    "student": "현재 학생이신가요? (예/아니오)",
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

def should_force_clarify_for_eligibility(question: str) -> bool:
    """간단 키워드 기반 보조 체크 (LLM router가 흔들릴 때 백업)"""
    keywords = ["가능", "자격", "대상", "선발", "몇유형", "1유형", "2유형", "될까", "신청해도"]
    return any(k in question for k in keywords)
