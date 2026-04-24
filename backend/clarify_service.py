# backend/clarify_service.py

from typing import List, Dict, Any

# missing_fields -> 사용자에게 던질 질문 템플릿
FIELD_QUESTIONS: Dict[str, str] = {
    "age": "나이가 어떻게 되시나요? (만 나이 기준)",
    "region": "현재 거주 지역은 어디인가요? (시/도 기준 예: 서울, 경기, 부산)",
    "job_status": "현재 취업 상태가 어떻게 되시나요? (구직중/재직중/학생/무직)",
    "household_size": "가구원 수는 몇 명인가요?",
    "income_level": "가구 소득이 중위소득 기준 어느 정도인지 아시나요? (60% 이하 / 100% 이하 / 잘 모르겠어요)",
    "unemployment_benefit": "현재 실업급여를 받고 계신가요? (예/아니오/모름)",
    "recent_work_history": "최근 1~2년 내 근로 이력이 있나요? (있음/없음/모름)",
}

FIELD_OPTIONS: Dict[str, List[Dict[str, str]]] = {
    "age": [
        {"label": "나이 입력", "value": "나이는 만 "},
    ],
    "region": [
        {"label": "서울", "value": "현재 거주 지역은 서울이에요."},
        {"label": "경기", "value": "현재 거주 지역은 경기예요."},
        {"label": "인천", "value": "현재 거주 지역은 인천이에요."},
        {"label": "부산", "value": "현재 거주 지역은 부산이에요."},
        {"label": "대전", "value": "현재 거주 지역은 대전이에요."},
        {"label": "직접 입력", "value": "현재 거주 지역은 "},
    ],
    "job_status": [
        {"label": "구직중", "value": "현재 취업 상태는 구직중이에요."},
        {"label": "재직중", "value": "현재 취업 상태는 재직중이에요."},
        {"label": "학생", "value": "현재 취업 상태는 학생이에요."},
        {"label": "무직", "value": "현재 취업 상태는 무직이에요."},
    ],
    "income_level": [
        {"label": "60% 이하", "value": "가구 소득은 중위소득 60% 이하예요."},
        {"label": "100% 이하", "value": "가구 소득은 중위소득 100% 이하예요."},
        {"label": "잘 모르겠어요", "value": "가구 소득 수준은 잘 모르겠어요."},
    ],
    "unemployment_benefit": [
        {"label": "받고 있어요", "value": "현재 실업급여를 받고 있어요."},
        {"label": "안 받아요", "value": "현재 실업급여를 받고 있지 않아요."},
        {"label": "잘 모르겠어요", "value": "실업급여 수급 여부는 잘 모르겠어요."},
    ],
    "recent_work_history": [
        {"label": "있어요", "value": "최근 1~2년 내 근로 이력이 있어요."},
        {"label": "없어요", "value": "최근 1~2년 내 근로 이력이 없어요."},
        {"label": "잘 모르겠어요", "value": "최근 근로 이력은 잘 모르겠어요."},
    ],
    "household_size": [
        {"label": "1인", "value": "가구원 수는 1명이에요."},
        {"label": "2인", "value": "가구원 수는 2명이에요."},
        {"label": "3인", "value": "가구원 수는 3명이에요."},
        {"label": "4인 이상", "value": "가구원 수는 4명 이상이에요."},
    ],
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


def build_clarify_items(missing_fields: List[str], max_q: int = 3) -> List[Dict[str, Any]]:
    """프론트에서 클릭형 UI로 렌더링할 질문/선택지 목록 생성"""
    items = []
    for field in missing_fields:
        question = FIELD_QUESTIONS.get(field)
        if not question:
            continue
        items.append({
            "field": field,
            "question": question,
            "options": FIELD_OPTIONS.get(field, []),
        })
    return items[:max_q]


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


def format_clarify_payload(route_result: Dict) -> Dict[str, Any]:
    """ASK_CLARIFY 응답을 텍스트와 클릭형 UI 메타데이터로 구성"""
    missing_fields = route_result.get("missing_fields", [])
    items = build_clarify_items(missing_fields, max_q=3)
    return {
        "text": format_clarify_message(route_result),
        "clarify": {
            "reason": route_result.get("reason", ""),
            "missing_fields": [item["field"] for item in items],
            "items": items,
        },
    }

def should_force_clarify_for_eligibility(question: str) -> bool:
    """간단 키워드 기반 보조 체크 (LLM router가 흔들릴 때 백업)"""
    keywords = ["가능", "자격", "대상", "선발", "몇유형", "1유형", "2유형", "될까", "신청해도"]
    return any(k in question for k in keywords)


def should_force_clarify_for_personalized_policy(question: str, user_profile: Dict[str, Any]) -> bool:
    """
    지역/나이/소득에 따라 달라지는 생활밀착형 정책은 사용자 정보가 없으면
    특정 지역 정책을 임의 추천하기 전에 확인 질문을 우선한다.
    """
    action_keywords = ["신청", "받을 수", "조건", "지원", "대상", "알려줘", "있어?", "있나요", "있을까요"]
    policy_keywords = [
        "건강검진", "심리상담", "마음건강", "기초생활수급", "자립 지원",
        "복지", "월세", "주거급여", "공공임대", "일자리 카페",
    ]
    missing_core = not user_profile.get("region") or not user_profile.get("age")

    return (
        missing_core
        and any(keyword in question for keyword in action_keywords)
        and any(keyword in question for keyword in policy_keywords)
    )


def get_personalized_policy_missing_fields(user_profile: Dict[str, Any]) -> List[str]:
    """개인화 정책 안내 전에 최소로 확인할 필드 목록"""
    fields = []
    if not user_profile.get("region"):
        fields.append("region")
    if not user_profile.get("age"):
        fields.append("age")
    if not user_profile.get("income_level"):
        fields.append("income_level")
    return fields[:3]
