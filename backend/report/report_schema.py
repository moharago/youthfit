# backend/report/report_schema.py
# 보고서 입출력 스키마 고정 (UI 렌더링 안정성 확보)

from __future__ import annotations
from typing import List, Optional, Literal
from pydantic import BaseModel, Field, HttpUrl, model_validator


TimelineKey = Literal["NOW", "PLUS_1M", "PLUS_3M", "PLUS_6M"]
BenefitType = Literal["CASH", "VOUCHER", "LOAN", "EDU", "JOB", "HOUSING", "ETC"]


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(..., description="채팅 메시지 역할")
    content: str = Field(..., description="메시지 본문")
    ts: Optional[str] = Field(None, description="타임스탬프(옵션)")


class PolicyLink(BaseModel):
    label: str = Field(..., description="링크 라벨(예: 공식페이지)")
    url: HttpUrl = Field(..., description="공식 링크 URL")


class PolicyCard(BaseModel):
    policy_name: str = Field(..., description="정책명")
    why_now: str = Field(..., description="왜 이 시점에 적합한지 1줄 요약")
    benefit_type: BenefitType = Field(..., description="혜택 유형")
    links: List[PolicyLink] = Field(default_factory=list, description="공식 링크(있을 때만)")

    @model_validator(mode="after")
    def _validate_why_now_len(self):
        if len(self.why_now.strip()) > 90:
            raise ValueError("why_now는 90자 이내로 제한하세요.")
        return self


class TimelineBlock(BaseModel):
    key: TimelineKey = Field(..., description="시점 키")
    title: str = Field(..., description="UI 표기용 타이틀(예: 지금, +1개월)")
    policies: List[PolicyCard] = Field(default_factory=list, description="시점별 정책 카드(최대 3개)")

    @model_validator(mode="after")
    def _validate_policy_count(self):
        if len(self.policies) > 3:
            raise ValueError("시점별 정책 카드는 최대 3개까지 허용됩니다.")
        return self


class StrategyReport(BaseModel):
    header: str = Field("상담 결과 기반 정책 전략 가이드", description="보고서 헤더")
    timeline: List[TimelineBlock] = Field(..., description="타임라인(최대 4개)")
    strategy_summary: str = Field(..., description="전체 전략 요약(3~4문장)")

    @model_validator(mode="after")
    def _validate_timeline_count(self):
        if len(self.timeline) > 4:
            raise ValueError("타임라인은 최대 4개까지 허용됩니다.")
        return self


class ReportRequest(BaseModel):
    session_id: str = Field(..., description="세션 식별자(프론트에서 생성 가능)")
    chat_log: List[ChatMessage] = Field(..., description="상담 전체 로그")
    extracted_facts: Optional[dict] = Field(None, description="상담 로그에서 추출된 핵심 사실(옵션)")


# ✅ NEW: DB에서 채팅 기록을 끌어와 보고서 생성할 때 쓰는 요청
class ReportFromDBRequest(BaseModel):
    session_id: str = Field(..., description="세션 식별자(프론트에서 생성 가능)")
    user_id: str = Field(..., description="DB에 저장된 user_id")
    limit: int = Field(30, description="최근 대화 몇 개를 보고서에 쓸지(기본 30)")
    extracted_facts: Optional[dict] = Field(None, description="추출 사실(옵션)")


class ReportResponse(BaseModel):
    session_id: str
    report: StrategyReport
    meta: dict = Field(default_factory=dict, description="생성 메타데이터/디버그")
