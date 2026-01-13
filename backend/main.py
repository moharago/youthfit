# backend/main.py
# FastAPI 실행 및 앤드포인트 설정

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any

from langchain_ollama import ChatOllama
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from user_service import (
    process_and_save,
    save_chat,
    get_recent_chats,
    format_history,
)
from database import get_user
from router import route_question
from clarify_service import format_clarify_message, should_force_clarify_for_eligibility


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
hf_embeddings = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask"
)

vectorstore = Chroma(
    persist_directory="./data/chroma_db",
    embedding_function=hf_embeddings
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# =========================
# LLM
# =========================
llm = ChatOllama(model="gemma3:4b", temperature=0)

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

    ⛔ 절대 규칙:
    1. [정책 정보]에 있는 내용만 답변하세요.
    2. 없는 정책은 절대 언급 금지!
    3. 반드시 한국어로만 답변하세요.

    ⚠️ 추천 관련 규칙 (매우 중요):
    1. 사용자 조건이 정책의 필수 요건을 모두 충족한다고 확인되지 않으면:
    - "추천합니다", "해당됩니다", "지원받을 수 있습니다" 사용 금지!
    - 대신 "적용 가능성이 있습니다", "추가 조건 확인이 필요합니다" 사용
    
    2. 소득, 무주택 여부, 취업 상태 등이 확인 안 됐으면:
    - "해당 정책은 [미확인 조건]을 충족해야 신청 가능합니다" 라고 안내

    3. 답변 형식:
    - 정책 소개
    - 필수 조건 안내
    - 사용자가 확인해야 할 추가 조건 명시
    """
)

# =========================
# FastAPI
# =========================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "guest"


def get_user_info_text(user_id: str) -> str:
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
    if user.get("housing_type"):
        parts.append(f"주거형태: {user['housing_type']}")
    
    return ", ".join(parts) if parts else "사용자 정보 없음"


def run_rag(question: str, user_id: str) -> str:
    history = format_history(get_recent_chats(user_id))
    user_info = get_user_info_text(user_id)

    docs = retriever.invoke(question)
    if not docs:
        return "관련 정책 정보를 찾을 수 없습니다."

    context = "\n\n".join(d.page_content for d in docs)
    chain = prompt | llm | StrOutputParser()

    return chain.invoke({
        "question": question,
        "context": context,
        "history": history,
        "user_info": user_info
    })


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


@app.post("/chat")
async def chat(req: ChatRequest):
    user_id = req.user_id
    message = req.message.strip()

    # 1️⃣ 정보 추출 + 저장
    extracted = process_and_save(user_id, message, llm)
    print(f"📝 추출된 정보: {extracted}")

    # 2) 관련 없는 질문 거절
    if is_unrelated(message):
        answer = "죄송하지만, 저는 청년정책 안내 전문 챗봇이에요. 청년정책에 대해 질문해주세요! 😊"
        save_chat(user_id, "assistant", answer)
        return {"answer": answer}

    # 3) 정보만 제공한 경우 → 조건 기반 추천(기존 기능 유지)
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
            history = format_history(get_recent_chats(user_id))
            user_info = get_user_info_text(user_id)

            chain = prompt | llm | StrOutputParser()
            answer = chain.invoke({
                "question": f"{extracted} 조건에 맞을 수 있는 청년 정책을 안내해줘. 단, 확정 추천은 금지하고 추가 확인사항을 같이 안내해줘.",
                "context": context,
                "history": history,
                "user_info": user_info
            })
        else:
            answer = f"정보 저장했어요! ({extracted}) 관련 정책을 찾아볼게요. 어떤 분야가 궁금하세요? (취업/주거/금융/창업)"

        save_chat(user_id, "assistant", answer)
        return {"answer": answer}

    # 4) Router 판단 (✅ 신규)
    user_profile = get_user(user_id) or {}
    route_result = route_question(message, user_profile, extracted, llm)
    print(f"🧭 ROUTER: {route_result}")

    # Router 흔들릴 때 대비: 판정형 키워드가 강하면 강제 clarify
    if should_force_clarify_for_eligibility(message) and route_result["route"] == "RAG_DIRECT":
        route_result["route"] = "ASK_CLARIFY"
        if not route_result.get("missing_fields"):
            route_result["missing_fields"] = ["region", "income_level", "unemployment_benefit"]
        route_result["reason"] = "판정형 질문(키워드) + 정보 부족 가능성"

    # 4-1) ASK_CLARIFY → clarify_service에서 질문 생성
    if route_result["route"] == "ASK_CLARIFY":
        answer = format_clarify_message(route_result)
        save_chat(user_id, "assistant", answer)
        return {"answer": answer}

    # 4-2) RAG_REWRITE → rewrite_question으로 RAG
    if route_result["route"] == "RAG_REWRITE":
        rq = route_result.get("rewrite_question") or message
        answer = run_rag(rq, user_id)
        save_chat(user_id, "assistant", answer)
        return {"answer": answer}

    # 4-3) RAG_DIRECT → 그대로 RAG
    answer = run_rag(message, user_id)
    save_chat(user_id, "assistant", answer)
    return {"answer": answer}


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
