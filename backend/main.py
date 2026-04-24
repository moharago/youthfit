# backend/main.py
# FastAPI 실행 및 앤드포인트 설정

import os
import re
import uuid
import json as _json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from user_service import (
    process_and_save,
    save_chat,
    get_recent_chats,
    format_history,
    _has_explicit_housing_statement,
)
from database import get_user, create_conversation
from router import route_question
from clarify_service import (
    format_clarify_payload,
    get_personalized_policy_missing_fields,
    should_force_clarify_for_eligibility,
    should_force_clarify_for_personalized_policy,
)


# =========================
# 업데이트 by Dayforged (보고서 기능) - 추가 시작
# =========================
from report.report_schema import ReportFromDBRequest
from report.report_schema import ReportFromLogRequest
from report.report_exporter import export_report_json, load_report_json
from report.report_from_db_service import generate_report_from_db
from report.report_from_db_service import generate_report_from_log
from report.report_view import render_report_html
# =========================
# 업데이트 by Dayforged (보고서 기능) - 추가 끝
# =========================


# =========================
# 벡터 DB
# =========================
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

vectorstore = Chroma(
    persist_directory="./data/chroma_db",
    embedding_function=embeddings
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# =========================
# LLM
# =========================
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# =========================
# Prompt
# =========================
followup_prompt = ChatPromptTemplate.from_template("""
당신은 청년정책 상담봇입니다. 사용자가 직전에 안내받은 정책에 대해 후속 질문을 하고 있습니다.

[사용자 정보]
{user_info}

[이전 대화]
{history}

[참고 정책 정보]
{context}

[후속 질문]
{question}

규칙:
1. **이전에 안내한 정책 카드(정책명·주요 지원 내용·신청 조건 전체)를 다시 출력하는 것은 절대 금지.**
2. 후속 질문이 묻는 항목 하나만 1~3문장으로 직접 답하세요:
   - "얼마", "금액", "돈", "수당" → 지원금액만
   - "어디", "지역", "기관", "상관없" → 신청 가능 지역/기관만
   - "어떻게 신청", "방법" → 신청방법만
   - "가능한가요", "신청할 수 있나요", "해당되나요", "~은요?", "~도요?" → 사용자 정보 기반으로 가능 여부만
3. 한국어로 답변하세요.
4. 지역을 묻는 질문 처리 규칙:
   - [참고 정책 정보]에서 담당기관이 고용노동부·복지부·국토부·교육부·중소벤처기업부 등 중앙부처이거나, 여러 지역(서울·제주 등) 항목이 동시에 있으면 전국 단위 정책입니다.
   - 전국 단위 정책이면 어느 지역을 물어도 "신청 가능합니다. 가까운 [담당기관(고용센터/주민센터 등)]에서 신청하세요."라고 답하세요.
   - **절대 금지**: 문서에 명시되지 않은 지역 제한을 임의로 추가하는 것. "X 지역에 한정되어 있습니다", "X 지역에서는 신청할 수 없습니다" 같은 표현은 문서에 명확한 지역 제한 근거가 있을 때만 사용하세요.
   - 특정 지자체 사업(예: ○○시 청년 지원)처럼 명백히 지역 한정인 경우에만 "해당 지역 전용 정보는 확인할 수 없습니다"라고 하세요.
""")

prompt = ChatPromptTemplate.from_template("""
당신은 아래 [정책 정보]를 사용자에게 전달하는 안내봇입니다.
[정책 정보]에 있는 내용만 그대로 전달하고, 그 외의 판단이나 평가는 하지 않습니다.

[사용자 정보]
{user_info}

[이전 대화]
{history}

[정책 정보]
{context}

[질문]
{question}

⛔ 절대 규칙 (반드시 지킬 것):
1. [정책 정보]에 있는 내용만 답변하세요. 없는 정책은 절대 언급 금지.
2. 반드시 한국어로만 답변하세요.
3. [사용자 정보]가 "사용자 정보 없음"이면 사용자 상황 언급을 완전히 생략하고 바로 정책 안내만 하세요.
   - "사용자 정보 없음 상황", "정보가 없으시군요" 같은 표현 절대 사용 금지.
4. 사용자 조건이 확인되지 않으면 "추천합니다", "해당됩니다" 사용 금지.
   대신 "신청 조건은 ~입니다", "추가 확인이 필요합니다" 사용.
   - [정책 정보]에 "나이 제한없음", "제한없음"이라고 명시된 경우, 특정 연령대를 "신청 불가"라고 단정 금지.
   - 문서에 없는 제한을 임의로 추가하지 마세요. "신청할 수 없습니다"는 문서에 명확한 근거가 있을 때만 사용하세요.
5. [정책 정보]에 문서가 있으면 그 문서 내용을 그대로 안내하세요.
   ❌ 절대 금지 표현 (문서가 있을 때):
   - "~에 대한 정보는 제공되지 않습니다"
   - "~관련 정책 정보는 제공되지 않습니다"
   - "제공되지 않습니다" / "찾을 수 없습니다" / "없습니다"
   - "대신 ~에 대해 안내드리겠습니다" (다른 정책으로 전환 금지)
   - "~은/는 제공되지 않지만" (조건절로 우회하는 것도 금지)
   ✅ 올바른 방법: 문서에 있는 정책을 그대로 소개하면 됩니다.
   - 정책명이 질문과 정확히 일치하지 않아도 됩니다. 관련 내용이면 안내하세요.
   - 예: "국민취업지원제도" 질문 + 국민취업지원제도 문서 → 바로 그 내용을 안내
   - 예: "면접 컨설팅" 질문 → 면접 준비, 취업 컨설팅, 모의면접 문서가 있으면 안내
   - 조건 충족 여부를 판단하지 말고 정책 내용과 신청 조건을 제시하세요.

📋 답변 방식:
- [이전 대화]에 특정 정책 Q&A가 있고 현재 질문이 그 정책에 대한 후속 질문이면:
  ① 이전에 논의한 정책을 기준으로 현재 질문에만 직접 답하세요.
  ② 이전 답변 내용을 처음부터 다시 나열하는 것은 절대 금지입니다.
  ③ 후속 질문이 특정 항목을 물어보면 [정책 정보]에서 그 항목만 찾아서 답하세요:
     - "어디", "위치", "지역", "기관", "~은요?", "~도요?" → '지역' 필드와 '담당기관' 필드 값만 답하세요. 담당기관이 중앙부처(고용노동부·복지부 등)이면 "전국에서 신청 가능"임을 안내하세요
     - "얼마", "금액", "돈", "수당" → '지원내용'에서 금액 정보만 답하세요
     - "어떻게 신청", "신청 방법" → '신청방법' 정보만 답하세요
     - "가능한가요?", "신청할 수 있나요?" → 문서와 확인된 사용자 정보만 근거로 답하고, 미확인 조건은 "추가 확인이 필요합니다"로 표현하세요
  ④ 절대로 이전 답변 전체를 다시 쓰지 마세요. 질문에 해당하는 항목만 답하면 됩니다.
  ⑤ 사용자가 이전 답변의 모순을 지적하면 ("~라고 했는데 왜 ~는 안 된다고 하나요?") 이전 답변을 반복하지 말고, [정책 정보]를 다시 확인해서 정확한 내용으로 정정하세요.
  ⑥ "알려준 거 다 신청 가능한가요?", "방금 말한 정책들 저한테 해당되나요?" 같은 질문은 [이전 대화]에 나온 정책들의 신청 조건을 [사용자 정보]와 비교해서 각 정책별로 간결하게 답하세요. 새로운 정책을 검색하지 마세요.
  예) 이전에 국민취업지원제도 안내 → "돈은 얼마 받는 건데요?"
  → "구직촉진수당은 월 50만 원씩 최대 6개월 지급됩니다."
  예) 이전에 진로취업 상담 안내 → "그게 어디 있는 건데요?"
  → "담당기관은 [기관명]이며, [지역] 지역에서 운영됩니다."
  예) 이전에 일자리도약장려금(남구 대상) 안내 → "경주 삽니다. 신청 가능한가요?"
  → "일자리도약장려금은 남구 거주자 대상 지역 사업이라, 경주에서는 신청이 어렵습니다."
- 질문에 직접 답하는 자연스러운 문장으로 작성하세요.
- 문서의 "정책명: ...", "지역: ...", "소득기준: ..." 같은 key:value 형식을 그대로 복사하지 마세요. 문장으로 변환하세요.
- "대상 나이: 0~0세" 또는 "0~0세"는 "제한없음"으로 표시하세요.
- 정책 정보 질문이면 아래 형식으로 작성:
  **[정책명]**
  한 줄 소개
  **주요 지원 내용**
  - 항목1
  - 항목2
  **신청 조건**
  - 조건1
  - 조건2
- 자격/가능 여부 질문이면: 문서와 [사용자 정보]만으로 판단 가능한 경우에만 첫 문장에서 가능/불가능 여부를 밝히고, 그 외에는 "추가 확인이 필요합니다"를 먼저 말한 뒤 조건을 bullet로 나열하세요.
- [정책 정보]에 여러 정책이 있고 질문이 "프로그램", "종류", "뭐가 있나요" 같이 목록을 묻는 경우:
  각 정책을 **[정책명]** + 한 줄 소개 형식으로 나열하세요. 하나만 골라서 상세 설명하지 마세요.
- 줄글로 길게 쓰지 마세요. 핵심만 bullet point로 간결하게 작성하세요.
- 답변 마지막에 "추가 확인 사항", 번호 매긴 질문 목록 등을 붙이지 마세요.
- [이전 대화]는 어떤 정책이 논의됐는지 파악하는 용도로만 사용하세요.
- [이전 대화]의 '상담사' 응답을 현재 답변에 절대 그대로 복사하지 마세요.
- 현재 [질문]에만 집중해서 새로운 답변을 작성하세요.
"""
)

# =========================
# FastAPI
# =========================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: str
    conversation_id: Optional[str] = None


def _is_housing_policy_question(message: str) -> bool:
    patterns = [
        "전세자금", "전세 자금", "전세대출", "전세 대출", "전세지원", "전세 지원",
        "월세지원", "월세 지원", "월세대출", "월세 대출", "전세 사기",
    ]
    return any(pattern in message for pattern in patterns)


def get_user_info_text(user_id: str, current_message: str = "") -> str:
    """사용자 정보를 텍스트로 변환"""
    user = get_user(user_id)
    if not user:
        return "사용자 정보 없음"
    
    parts = []
    if user.get("age"):
        parts.append(f"나이: {user['age']}세")
    if user.get("region"):
        parts.append(f"지역: {user['region']}")
    if user.get("job_status"):
        parts.append(f"취업상태: {user['job_status']}")
    if user.get("income_level"):
        parts.append(f"소득수준: {user['income_level']}")
    should_include_housing = not (
        current_message
        and _is_housing_policy_question(current_message)
        and not _has_explicit_housing_statement(current_message)
    )
    if user.get("housing_type") and should_include_housing:
        parts.append(f"주거형태: {user['housing_type']}")
    
    return ", ".join(parts) if parts else "사용자 정보 없음"


_QUERY_EXPANSIONS = [
    (["면접 컨설팅", "면접컨설팅", "면접 코칭", "면접코칭", "모의면접"], "면접 컨설팅 취업 코칭 모의면접 자기소개서 첨삭 상담"),
    (["취업 컨설팅", "취업컨설팅"], "취업 컨설팅 코칭 멘토링 상담 취업 지원"),
    (["자기소개서", "자소서"], "자기소개서 자소서 첨삭 컨설팅 취업"),
    (["창업 컨설팅", "창업컨설팅"], "창업 컨설팅 스타트업 사업화 멘토링"),
    (["해외 연수", "해외연수", "해외취업 연수", "해외 취업 연수"], "해외연수 해외취업 K-Move 글로벌 해외진출 해외일경험"),
]

def _expand_query(question: str) -> str:
    for triggers, expansion in _QUERY_EXPANSIONS:
        if any(t in question for t in triggers):
            return expansion
    return question


def _filter_mismatched_docs(docs: list, question: str) -> list:
    """쿼리 의도와 명백히 맞지 않는 문서 제거"""
    if "컨설팅" in question or "코칭" in question or "모의면접" in question:
        if "정장" not in question and "대여" not in question:
            return [d for d in docs if "정장 대여" not in d.page_content and "정장대여" not in d.page_content]
    # 해외연수 질문에서 특정 업종(어업·수산·산림 등) 한정 문서 후순위로 밀기
    if ("해외" in question and ("연수" in question or "취업" in question)):
        sector_specific = ["수산업 연수", "어업인 해외", "산림청년"]
        general = [d for d in docs if not any(s in d.page_content for s in sector_specific)]
        specific = [d for d in docs if any(s in d.page_content for s in sector_specific)]
        return general + specific  # 일반 문서 먼저, 업종 특화 문서 나중
    return docs


def _get_rag_context(question: str, user_profile: Optional[dict] = None) -> tuple:
    """문서 검색 및 컨텍스트 반환 (동기)"""
    list_keywords = ["어디", "위치", "목록", "전체", "모든", "다 알려", "뭐뭐 있어", "몇 개", "리스트", "곳", "기관", "센터", "받을 수", "프로그램", "종류", "뭐가 있", "어떤 게 있", "뭐뭐"]
    is_list_question = any(kw in question for kw in list_keywords)
    k_value = 10 if is_list_question else 5

    search_query = _expand_query(question)
    # 필터링이 필요한 경우 더 많이 가져와서 줄임
    fetch_k = k_value + 5 if search_query != question else k_value
    docs = vectorstore.similarity_search(search_query, k=fetch_k)
    docs = _filter_mismatched_docs(docs, question)
    docs = docs[:k_value]  # 원래 k_value로 자름

    print("\n" + "="*60)
    print(f"🔍 RAG 검색 쿼리: {question}")
    print(f"📄 검색된 문서 수: {len(docs)}")
    for i, doc in enumerate(docs):
        print(f"\n--- Document {i+1} ---")
        print(f"📝 내용:\n{doc.page_content[:500]}...")
        if hasattr(doc, 'metadata') and doc.metadata:
            print(f"🏷️ 메타데이터: {doc.metadata}")
    print("="*60 + "\n")

    if not docs:
        return None, None, None, []

    context = "\n\n".join(d.page_content for d in docs)
    q = f"{question}\n\n※ 검색된 모든 항목의 이름과 위치를 목록으로 정리해서 알려주세요." if is_list_question else question

    # 메타데이터에서 URL 수집 (중복 제거)
    links = []
    seen_urls = set()
    for doc in docs:
        url = doc.metadata.get("apply_url", "")
        name = doc.metadata.get("policy_name", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            links.append({"label": name or "신청 바로가기", "url": url})

    return docs, context, q, links


async def _extract_followup(response: str, user_profile: Optional[dict] = None) -> list:
    """LLM 답변에서 후속 확인 질문 추출"""
    # 이미 알고 있는 정보 정리
    known = []
    if user_profile:
        if user_profile.get("age"):
            known.append(f"나이: {user_profile['age']}세 (이미 알고 있음 → 칩 생성 금지)")
        if user_profile.get("region"):
            known.append(f"지역: {user_profile['region']} (이미 알고 있음 → 칩 생성 금지)")
        if user_profile.get("job_status"):
            known.append(f"취업상태: {user_profile['job_status']} (이미 알고 있음 → 칩 생성 금지)")
        if user_profile.get("income_level"):
            known.append(f"소득수준: {user_profile['income_level']} (이미 알고 있음 → 칩 생성 금지)")
    known_str = "\n".join(known) if known else "없음"

    extract_prompt = f"""다음 청년정책 답변에서, 사용자가 클릭 한 번으로 본인 상황을 전달할 수 있는 짧은 응답 문장을 최대 3개 만드세요.

[이미 파악된 사용자 정보 - 이 항목은 칩으로 만들지 말 것]
{known_str}

규칙:
- 반드시 사용자가 말하는 1인칭 존댓말로 작성 (예: "구직 중이에요", "미취업자예요", "학생이에요")
- 질문 형태 절대 금지
- 나이·지역처럼 값이 다양한 항목은 칩으로 만들지 말 것
- 취업상태·소득·결혼여부·재학여부·직종 같이 선택지가 명확한 항목만 추출
- 이미 파악된 정보와 같은 항목은 절대 칩으로 만들지 말 것
- "~지원받고 싶어요", "~신청하고 싶어요" 같이 정책 관심·의향 표현은 칩으로 만들지 말 것. 사용자의 현재 상태·조건만 해당됨
- label과 value는 반드시 같은 내용이어야 함. label에 없는 단어를 value에 추가하지 말 것
- 같은 의미 중복 금지
- 추출할 내용이 없으면 반드시 [] 반환
- 반드시 JSON 배열로만 응답

형식: [{{"label": "버튼 표시 텍스트", "value": "챗봇에 전송할 텍스트"}}]

좋은 예시:
- {{"label": "중위소득 이하예요", "value": "소득이 중위소득 이하예요"}}
- {{"label": "1인 가구예요", "value": "1인 가구예요"}}
- {{"label": "학생이에요", "value": "학생이에요"}}

나쁜 예시 (금지):
- {{"label": "나이가 어떻게 되세요?", ...}}
- {{"label": "현재 취업 중인가요?", ...}}
- 이미 파악된 정보와 동일한 내용

답변:
{response}

JSON:"""
    # 필드별 필터링 키워드
    FIELD_BLOCK_KEYWORDS = {}
    if user_profile:
        if user_profile.get("job_status"):
            FIELD_BLOCK_KEYWORDS["job_status"] = ["취업", "구직", "재직", "미취업", "무직", "일자리", "프리랜서", "자영업", "창업"]
        if user_profile.get("income_level"):
            FIELD_BLOCK_KEYWORDS["income_level"] = ["소득", "중위", "저소득", "수급"]
        if user_profile.get("age"):
            FIELD_BLOCK_KEYWORDS["age"] = ["세", "나이"]
        if user_profile.get("region"):
            FIELD_BLOCK_KEYWORDS["region"] = ["거주", "지역", "살고", "살아"]

    try:
        res = await llm.ainvoke(extract_prompt)
        content = res.content if hasattr(res, "content") else str(res)
        match = re.search(r'\[.*\]', content, re.DOTALL)
        if match:
            chips = _json.loads(match.group())
            # 이미 알고 있는 필드와 관련된 칩 제거
            filtered = []
            for chip in chips:
                label = chip.get("label", "") + chip.get("value", "")
                blocked = any(
                    any(kw in label for kw in keywords)
                    for keywords in FIELD_BLOCK_KEYWORDS.values()
                )
                if not blocked:
                    filtered.append(chip)
            return filtered
    except Exception as e:
        print(f"⚠️ followup 추출 실패: {e}")
    return []


async def _stream_llm(chain_input: dict, user_id: str, conversation_id: Optional[str] = None,
                     user_profile: Optional[dict] = None, links: Optional[list] = None,
                     is_followup: bool = False):
    """LLM 응답을 SSE 형식으로 스트리밍"""
    chain = (followup_prompt if is_followup else prompt) | llm | StrOutputParser()
    full = []
    try:
        async for chunk in chain.astream(chain_input):
            full.append(chunk)
            yield f"data: {_json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
    except Exception as e:
        print(f"❌ LLM 스트리밍 오류: {e}")
        yield f"data: {_json.dumps({'chunk': '답변 생성 중 오류가 발생했습니다.'}, ensure_ascii=False)}\n\n"
    finally:
        full_text = "".join(full)
        if full_text:
            followup = await _extract_followup(full_text, user_profile)
            if followup:
                yield f"data: {_json.dumps({'followup': followup}, ensure_ascii=False)}\n\n"
        if links and full_text:
            relevant_links = [l for l in links if l["label"] and l["label"] in full_text]
            if relevant_links:
                yield f"data: {_json.dumps({'links': relevant_links}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
        if full_text:
            save_chat(user_id, "assistant", full_text, conversation_id)


async def _stream_static(text: str, user_id: str, conversation_id: Optional[str] = None,
                         extra: Optional[Dict[str, Any]] = None):
    """고정 텍스트를 SSE 형식으로 반환"""
    payload = {"chunk": text}
    if extra:
        payload.update(extra)
    try:
        yield f"data: {_json.dumps(payload, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"
        save_chat(user_id, "assistant", text, conversation_id)


def _rag_stream_response(question: str, user_id: str, conversation_id: Optional[str] = None,
                         headers: Optional[Dict[str, Any]] = None,
                         user_profile: Optional[dict] = None,
                         search_query: Optional[str] = None,
                         is_followup: bool = False) -> StreamingResponse:
    """RAG 검색 후 스트리밍 응답 생성
    search_query: RAG 검색에만 쓸 쿼리 (None이면 question 그대로 사용)
    question: LLM에 전달할 실제 질문
    is_followup: True면 후속 질문 전용 프롬프트 사용
    """
    h = headers or SSE_HEADERS
    docs, context, _, links = _get_rag_context(search_query or question, user_profile)

    if not docs:
        return StreamingResponse(
            _stream_static("관련 정책 정보를 찾을 수 없습니다.", user_id, conversation_id),
            media_type="text/event-stream",
            headers=h
        )

    history = format_history(get_recent_chats(user_id, conversation_id=conversation_id))
    user_info = get_user_info_text(user_id, question)
    chain_input = {"question": question, "context": context, "history": history, "user_info": user_info}

    return StreamingResponse(
        _stream_llm(chain_input, user_id, conversation_id, user_profile, links=links, is_followup=is_followup),
        media_type="text/event-stream",
        headers=h
    )


_SECTION_HEADERS = {"신청 조건", "주요 지원 내용", "신청 방법", "지원 내용", "신청방법", "주요내용", "대상", "지원내용"}

def _extract_policy_topic(text: str) -> str:
    """이전 어시스턴트 답변에서 정책명 추출 (섹션 헤더 제외)"""
    # 1순위: **[정책명]** 패턴 (대괄호 있는 것)
    match = re.search(r'\*\*\[([^\]\n*]{2,30})\]\*\*', text)
    if match:
        return match.group(1).strip()
    # 2순위: 일반 **굵은글씨** — 섹션 헤더는 제외
    for m in re.finditer(r'\*\*([^\]\n*]{2,30})\*\*', text):
        candidate = m.group(1).strip()
        if candidate not in _SECTION_HEADERS:
            return candidate
    # 3순위: 첫 문장에서 "X은/는 신청 가능합니다" 패턴으로 정책명 추출
    first_line = text.split('\n')[0].strip()
    m = re.match(r'^(.+?)(?:은|는)\s+신청', first_line)
    if m and 2 <= len(m.group(1)) <= 30:
        return m.group(1).strip()
    # 4순위: 첫 줄이 명사형(문장이 아님)일 때만
    _sentence_markers = ["입니다", "합니다", "됩니다", "있습니다", "없습니다", "경우", "이면", "이므로", "가능합니다", "신청하세요", "하세요"]
    if 4 <= len(first_line) <= 40 and not any(s in first_line for s in _sentence_markers):
        return first_line
    return ""


# 메시지에 포함된 정책 약어 → 정식 명칭 매핑
_POLICY_ABBR: Dict[str, str] = {
    "국취제": "국민취업지원제도",
    "국민취업": "국민취업지원제도",
    "내일채움": "청년내일채움공제",
    "내일채움공제": "청년내일채움공제",
    "청년도약": "청년도약계좌",
    "청년희망": "청년희망적금",
    "취성패": "취업성공패키지",
    "취업성공패키지": "취업성공패키지",
    "일자리도약": "일자리도약장려금",
    "청년내일저축": "청년내일저축계좌",
}


def _build_followup_search_query(message: str, recent: list) -> str:
    """짧은 후속 질문의 RAG 검색용 쿼리 — topic + 질문 측면(aspect)으로 적합한 청크 검색"""
    # 후속 질문의 측면을 파악해서 검색에 추가 → 전체 개요 청크보다 관련 청크 우선 검색
    aspect = ""
    if any(k in message for k in ["얼마", "금액", "돈", "수당", "지원금", "얼마나"]):
        aspect = "지원금액 지원내용"
    elif any(k in message for k in ["어디서", "어디에서", "어느 기관", "어느 센터", "기관이", "센터가", "위치가"]):
        aspect = "담당기관 지역"
    elif any(k in message for k in ["어떻게", "신청방법", "신청 방법"]):
        aspect = "신청방법"

    # 1순위: 현재 메시지에 정책명/약어가 있으면 history 무시하고 그걸로 검색
    for abbr, full_name in _POLICY_ABBR.items():
        if abbr in message:
            return f"{full_name} {aspect}".strip()

    # 2순위: 최근 봇 메시지들을 역순으로 탐색해서 명확한 정책명 추출
    topic = ""
    for chat in reversed(recent):
        if chat["role"] == "assistant":
            _t = _extract_policy_topic(chat["content"])
            if _t and len(_t) > 2:
                topic = _t
                break

    prev_user = next(
        (chat["content"] for chat in reversed(recent) if chat["role"] == "user" and chat["content"] != message),
        "",
    )

    base = topic or prev_user or message
    return f"{base} {aspect}".strip()


def is_info_only(message: str) -> bool:
    """정보 제공만 하는 메시지인지 확인"""
    info_patterns = ["살아", "살고", "삽니다", "사는데", "이야", "예요", "입니다", "세야", "살이야", "이라고요", "이에요", "이고요", "인데요", "인걸요", "거든요"]
    question_patterns = ["알려줘", "뭐야", "추천", "어때", "있어", "?"]
    
    has_info = any(p in message for p in info_patterns)
    has_question = any(p in message for p in question_patterns)
    
    return has_info and not has_question


def is_unrelated(message: str) -> bool:
    """청년정책과 전혀 관련 없는 질문인지 확인"""
    unrelated = ["맛집", "날씨", "연예인", "게임", "영화", "노래"]
    return any(u in message for u in unrelated)


SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}


@app.post("/chat")
async def chat(req: ChatRequest):
    user_id = req.user_id
    message = req.message.strip()
    conv_id = req.conversation_id or str(uuid.uuid4())
    sse_headers = {**SSE_HEADERS, "X-Conversation-Id": conv_id}

    # 대화 세션 생성
    create_conversation(conv_id, user_id)

    # 1️⃣ 정보 추출 + 저장
    extracted = process_and_save(user_id, message, llm, conv_id)
    print(f"📝 추출된 정보: {extracted}")

    # 2) 관련 없는 질문 거절
    if is_unrelated(message):
        answer = "죄송하지만, 저는 청년정책 안내 전문 챗봇이에요. 청년정책에 대해 질문해주세요! 😊"
        return StreamingResponse(_stream_static(answer, user_id, conv_id), media_type="text/event-stream", headers=sse_headers)

    # 3) 정보만 제공한 경우 → 조건 기반 추천
    if extracted and is_info_only(message):
        # 이전 대화에서 마지막 사용자 질문을 검색 쿼리에 포함
        recent = get_recent_chats(user_id, conversation_id=conv_id)
        prev_question = next(
            (c["content"] for c in reversed(recent) if c["role"] == "user" and c["content"] != message),
            ""
        )

        search_query = ""
        if extracted.get("region"):
            search_query += f"{extracted['region']} "
        if extracted.get("job_status"):
            search_query += f"{extracted['job_status']} "
        if extracted.get("age"):
            search_query += f"{extracted['age']}세 "
        if prev_question:
            search_query += f"{prev_question} "
        else:
            search_query += "청년 지원 정책"

        docs = vectorstore.similarity_search(search_query.strip(), k=5)
        if docs:
            context = "\n\n".join(d.page_content for d in docs)
            history = format_history(recent)
            user_info = get_user_info_text(user_id, message)
            question_for_llm = f"{prev_question} ({message})" if prev_question else f"{extracted} 조건에 맞는 청년 정책"
            chain_input = {
                "question": f"{question_for_llm} — 확정 추천 금지, 신청 조건과 함께 안내해줘.",
                "context": context,
                "history": history,
                "user_info": user_info
            }
            info_profile = get_user(user_id) or {}
            # 링크 수집
            info_links = []
            seen = set()
            for doc in docs:
                url = doc.metadata.get("apply_url", "")
                name = doc.metadata.get("policy_name", "")
                if url and url not in seen:
                    seen.add(url)
                    info_links.append({"label": name or "신청 바로가기", "url": url})
            return StreamingResponse(_stream_llm(chain_input, user_id, conv_id, info_profile, links=info_links), media_type="text/event-stream", headers=sse_headers)
        else:
            answer = f"정보 저장했어요! ({extracted}) 관련 정책을 찾아볼게요. 어떤 분야가 궁금하세요? (취업/주거/금융/창업)"
            return StreamingResponse(_stream_static(answer, user_id, conv_id), media_type="text/event-stream", headers=sse_headers)

    # 4) 후속 질문 여부 먼저 판단 (라우팅 오버라이드에 영향)
    _BACK_REF = [
        "알려준", "방금", "위에서", "위의", "그 정책", "그거", "그것", "그걸",
        "거기", "그런 거", "그런거", "말한 거", "말씀하신", "저도", "나도",
        "그럼", "그러면", "그렇다면", "그니까", "그러니까", "아까",
    ]
    is_back_ref = any(p in message for p in _BACK_REF) or len(message.strip()) <= 15

    # 직전 대화에 특정 정책이 있고 자격 관련 질문이면 → 그 정책에 대한 후속 질문으로 처리
    # (예: "제주도 사는데 신청 가능한 건가요?", "제주도에 사는 사람도 신청 가능한가요?")
    if not is_back_ref and should_force_clarify_for_eligibility(message):
        _recent_check = get_recent_chats(user_id, conversation_id=conv_id)
        # 최근 봇 메시지들을 순서대로 탐색해서 명확한 정책명 추출
        for _chat in reversed(_recent_check):
            if _chat["role"] == "assistant":
                _topic = _extract_policy_topic(_chat["content"])
                if _topic and len(_topic) > 2:
                    is_back_ref = True
                    break

    # 4) Router 판단
    user_profile = get_user(user_id) or {}
    route_result = route_question(message, user_profile, extracted, llm)
    print(f"🧭 ROUTER: {route_result}")

    # back_ref 질문은 이전 맥락으로 답할 수 있으므로 라우터 결과와 무관하게 RAG_DIRECT 강제
    if is_back_ref and route_result["route"] == "ASK_CLARIFY":
        route_result["route"] = "RAG_DIRECT"
        route_result["missing_fields"] = []

    if not is_back_ref and should_force_clarify_for_eligibility(message) and route_result["route"] == "RAG_DIRECT":
        route_result["route"] = "ASK_CLARIFY"
        if not route_result.get("missing_fields"):
            route_result["missing_fields"] = ["region", "income_level", "unemployment_benefit"]
        route_result["reason"] = "판정형 질문(키워드) + 정보 부족 가능성"

    if (
        not is_back_ref
        and route_result["route"] == "RAG_DIRECT"
        and should_force_clarify_for_personalized_policy(message, user_profile)
    ):
        route_result["route"] = "ASK_CLARIFY"
        route_result["missing_fields"] = get_personalized_policy_missing_fields(user_profile)
        route_result["reason"] = "지역/나이 기반 개인화 정책 질문 + 핵심 정보 부족"

    # DB에 이미 값이 있는 필드는 missing에서 제거 (값이 "모름"이어도 이미 답변한 것)
    if route_result["route"] == "ASK_CLARIFY":
        route_result["missing_fields"] = [
            f for f in route_result.get("missing_fields", [])
            if not user_profile.get(f) and user_profile.get(f) != "모름"
        ]
        if not route_result["missing_fields"]:
            route_result["route"] = "RAG_DIRECT"

    # 4-1) ASK_CLARIFY
    if route_result["route"] == "ASK_CLARIFY":
        payload = format_clarify_payload(route_result)
        return StreamingResponse(
            _stream_static(payload["text"], user_id, conv_id, {"clarify": payload["clarify"]}),
            media_type="text/event-stream",
            headers=sse_headers
        )

    # 4-2) RAG_REWRITE
    if route_result["route"] == "RAG_REWRITE":
        rq = route_result.get("rewrite_question") or message
        return _rag_stream_response(rq, user_id, conv_id, headers=sse_headers, user_profile=user_profile)

    # 4-3) RAG_DIRECT
    # 후속 질문: RAG 검색은 topic만 사용, LLM 질문은 원본 메시지 + 반복 금지 힌트
    rag_search_query = None
    if is_back_ref:
        recent = get_recent_chats(user_id, conversation_id=conv_id)
        rag_search_query = _build_followup_search_query(message, recent)

    return _rag_stream_response(
        message, user_id, conv_id,
        headers=sse_headers, user_profile=user_profile,
        search_query=rag_search_query,
        is_followup=is_back_ref
    )


# =========================
# 업데이트 by Dayforged (보고서 기능) - 추가 시작
# =========================

# 1) JSON API: Streamlit/기타가 호출
@app.post("/report/from_db")
async def report_from_db(req: ReportFromDBRequest):
    resp = generate_report_from_db(req)
    return resp.model_dump()


# 2) HTML View: Streamlit iframe이 표시할 "보고서 화면"
@app.get("/report/view")
async def report_view(user_id: str, limit: int = 30):
    req = ReportFromDBRequest(
        session_id=user_id,  # MVP: session_id는 user_id로 대체
        user_id=user_id,
        limit=limit,
        extracted_facts=None,
    )
    resp = generate_report_from_db(req).model_dump()
    return render_report_html(resp)


# 3) LOG 기반: Streamlit 세션 로그로 보고서 생성 + report_id 반환(파일 저장)
@app.post("/report/from_log")
async def report_from_log(req: ReportFromLogRequest):
    resp = generate_report_from_log(req).model_dump()

    # ✅ 보고서 관련 코드 (업데이트 by dayforged) - 추가 시작
    # Windows 경로/URL 깨짐 방지:
    # - export_report_json은 "전체 경로"를 반환하므로
    # - 클라이언트(Streamlit)에 반환하는 report_id는 "파일명만" 전달
    saved_path = export_report_json(session_id=req.session_id, payload=resp)
    report_id = os.path.basename(saved_path)
    # ✅ 보고서 관련 코드 (업데이트 by dayforged) - 추가 끝

    return {"report_id": report_id, "payload": resp}


# 4) LOG HTML View: report_id로 파일 로드 후 HTML 렌더
@app.get("/report/view_by_id")
async def report_view_by_id(report_id: str):
    payload = load_report_json(report_id)
    return render_report_html(payload)

# =========================
# 업데이트 by Dayforged (보고서 기능) - 추가 끝
# =========================


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
