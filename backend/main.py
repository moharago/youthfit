# backend/main.py
# FastAPI 실행 및 앤드포인트 설정

import os
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
prompt = ChatPromptTemplate.from_template("""
당신은 청년정책 전문 상담사입니다.

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

📋 답변 형식:
- 정책 소개 (1~2문장)
- 주요 지원 내용
- 신청 조건
- 추가 확인 사항 (사용자 정보가 있을 때만)
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


def _get_rag_context(question: str) -> tuple:
    """문서 검색 및 컨텍스트 반환 (동기)"""
    list_keywords = ["어디", "위치", "목록", "전체", "모든", "다 알려", "뭐뭐 있어", "몇 개", "리스트"]
    is_list_question = any(kw in question for kw in list_keywords)
    k_value = 10 if is_list_question else 3
    docs = vectorstore.similarity_search(question, k=k_value)

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
        return None, None, None

    context = "\n\n".join(d.page_content for d in docs)
    q = f"{question}\n\n※ 검색된 모든 항목의 이름과 위치를 목록으로 정리해서 알려주세요." if is_list_question else question
    return docs, context, q


async def _stream_llm(chain_input: dict, user_id: str, conversation_id: Optional[str] = None):
    """LLM 응답을 SSE 형식으로 스트리밍"""
    chain = prompt | llm | StrOutputParser()
    full = []
    try:
        async for chunk in chain.astream(chain_input):
            full.append(chunk)
            yield f"data: {_json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
    except Exception as e:
        print(f"❌ LLM 스트리밍 오류: {e}")
        yield f"data: {_json.dumps({'chunk': '답변 생성 중 오류가 발생했습니다.'}, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"
        if full:
            save_chat(user_id, "assistant", "".join(full), conversation_id)


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


def _rag_stream_response(question: str, user_id: str, conversation_id: str = None) -> StreamingResponse:
    """RAG 검색 후 스트리밍 응답 생성"""
    docs, context, q = _get_rag_context(question)

    if not docs:
        return StreamingResponse(
            _stream_static("관련 정책 정보를 찾을 수 없습니다.", user_id, conversation_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
        )

    history = format_history(get_recent_chats(user_id, conversation_id=conversation_id))
    user_info = get_user_info_text(user_id, question)
    chain_input = {"question": q, "context": context, "history": history, "user_info": user_info}

    return StreamingResponse(
        _stream_llm(chain_input, user_id, conversation_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
    )


def is_info_only(message: str) -> bool:
    """정보 제공만 하는 메시지인지 확인"""
    info_patterns = ["살아", "살고", "이야", "예요", "입니다", "세야", "살이야"]
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
    conv_id = req.conversation_id

    # 대화 세션 생성 (없으면 자동 생성)
    if conv_id:
        create_conversation(conv_id, user_id)

    # 1️⃣ 정보 추출 + 저장
    extracted = process_and_save(user_id, message, llm, conv_id)
    print(f"📝 추출된 정보: {extracted}")

    # 2) 관련 없는 질문 거절
    if is_unrelated(message):
        answer = "죄송하지만, 저는 청년정책 안내 전문 챗봇이에요. 청년정책에 대해 질문해주세요! 😊"
        return StreamingResponse(_stream_static(answer, user_id, conv_id), media_type="text/event-stream", headers=SSE_HEADERS)

    # 3) 정보만 제공한 경우 → 조건 기반 추천
    if extracted and is_info_only(message):
        search_query = ""
        if extracted.get("region"):
            search_query += f"{extracted['region']} 청년 정책 "
        if extracted.get("job_status"):
            search_query += f"{extracted['job_status']} "
        if extracted.get("age"):
            search_query += f"{extracted['age']}세 "
        search_query += "청년 지원 정책"

        docs = retriever.invoke(search_query)
        if docs:
            context = "\n\n".join(d.page_content for d in docs)
            history = format_history(get_recent_chats(user_id, conversation_id=conv_id))
            user_info = get_user_info_text(user_id, message)
            chain_input = {
                "question": f"{extracted} 조건에 맞을 수 있는 청년 정책을 안내해줘. 단, 확정 추천은 금지하고 추가 확인사항을 같이 안내해줘.",
                "context": context,
                "history": history,
                "user_info": user_info
            }
            return StreamingResponse(_stream_llm(chain_input, user_id, conv_id), media_type="text/event-stream", headers=SSE_HEADERS)
        else:
            answer = f"정보 저장했어요! ({extracted}) 관련 정책을 찾아볼게요. 어떤 분야가 궁금하세요? (취업/주거/금융/창업)"
            return StreamingResponse(_stream_static(answer, user_id, conv_id), media_type="text/event-stream", headers=SSE_HEADERS)

    # 4) Router 판단
    user_profile = get_user(user_id) or {}
    route_result = route_question(message, user_profile, extracted, llm)
    print(f"🧭 ROUTER: {route_result}")

    if should_force_clarify_for_eligibility(message) and route_result["route"] == "RAG_DIRECT":
        route_result["route"] = "ASK_CLARIFY"
        if not route_result.get("missing_fields"):
            route_result["missing_fields"] = ["region", "income_level", "unemployment_benefit"]
        route_result["reason"] = "판정형 질문(키워드) + 정보 부족 가능성"

    if (
        route_result["route"] == "RAG_DIRECT"
        and should_force_clarify_for_personalized_policy(message, user_profile)
    ):
        route_result["route"] = "ASK_CLARIFY"
        route_result["missing_fields"] = get_personalized_policy_missing_fields(user_profile)
        route_result["reason"] = "지역/나이 기반 개인화 정책 질문 + 핵심 정보 부족"

    # 4-1) ASK_CLARIFY
    if route_result["route"] == "ASK_CLARIFY":
        payload = format_clarify_payload(route_result)
        return StreamingResponse(
            _stream_static(payload["text"], user_id, conv_id, {"clarify": payload["clarify"]}),
            media_type="text/event-stream",
            headers=SSE_HEADERS
        )

    # 4-2) RAG_REWRITE
    if route_result["route"] == "RAG_REWRITE":
        rq = route_result.get("rewrite_question") or message
        return _rag_stream_response(rq, user_id, conv_id)

    # 4-3) RAG_DIRECT
    return _rag_stream_response(message, user_id, conv_id)


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
