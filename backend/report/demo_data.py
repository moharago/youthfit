# backend/report/demo_data.py
# 개발용 데모 데이터(파이썬 dict) - UI에서 바로 주입 가능

from __future__ import annotations

DEMO_SESSION_001 = {
    "session_id": "demo-session-001",
    "chat_log": [
        {"role": "user", "content": "서울 거주. 구직 중이고 이번 달 생활비가 급해요. 당장 받을 수 있는 지원이 있나요?", "ts": "2026-01-13T10:02:00+09:00"},
        {"role": "assistant", "content": "지금은 ‘즉시 신청 가능’ 후보부터 줄이고, 중복 리스크 낮은 선택부터 진행하세요.", "ts": "2026-01-13T10:02:20+09:00"},
        {"role": "user", "content": "29세고 최근 6개월 근로 이력 거의 없어요. 소득은 낮은 편인데 중위소득 기준은 몰라요.", "ts": "2026-01-13T10:03:00+09:00"},
        {"role": "assistant", "content": "근로 이력 제한이 있는 정책/없는 정책을 먼저 나누고, 지금은 단기 숨통부터 확보하는 게 안전합니다.", "ts": "2026-01-13T10:03:20+09:00"},
        {"role": "user", "content": "지금 신청했다가 나중에 더 좋은 정책을 못 받는 경우가 있나요?", "ts": "2026-01-13T10:04:00+09:00"},
        {"role": "assistant", "content": "중복 제한/대체 관계 때문에 순서가 손해로 이어질 수 있어요. 먼저 안전한 선택부터.", "ts": "2026-01-13T10:04:15+09:00"},
    ],
    "extracted_facts": {
        "region": "서울",
        "employment": "구직",
        "age": "29세",
        "income_hint": "소득 낮은 편",
        "urgency": "HIGH",
        "topic_hint": "JOB",
    },
}

DEMO_SESSION_002 = {
    "session_id": "demo-session-002",
    "chat_log": [
        {"role": "user", "content": "서울 재직 중 31세예요. 3~6개월 내 전세/월세 이사를 계획 중인데 순서를 어떻게 잡아야 해요?", "ts": "2026-01-13T11:10:00+09:00"},
        {"role": "assistant", "content": "주거 정책은 계약 시점이 손익을 결정합니다. 지금은 일정/조건을 먼저 확정해 선택지를 열어두세요.", "ts": "2026-01-13T11:10:25+09:00"},
        {"role": "user", "content": "지금 당장 돈은 급하지 않지만 순서 꼬여서 손해 보는 건 싫어요.", "ts": "2026-01-13T11:11:05+09:00"},
        {"role": "assistant", "content": "‘이사 예정일→지원 유형→필수 조건’ 순서로 역산하면 안전합니다.", "ts": "2026-01-13T11:11:20+09:00"},
    ],
    "extracted_facts": {
        "region": "서울",
        "employment": "재직",
        "age": "31세",
        "topic_hint": "HOUSING",
        "urgency": "NORMAL",
        "time_horizon": "3~6개월",
    },
}
