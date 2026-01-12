# FastAPI 실행 및 앤드포인트 설정

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from langchain_ollama import ChatOllama 
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 1. 임베딩 모델 로드 (ingest.py와 동일해야 함)
model_name = "jhgan/ko-sroberta-multitask"
hf_embeddings = HuggingFaceEmbeddings(model_name=model_name)

# 2. 벡터 DB 연결
persist_directory = "./data/chroma_db"
if os.path.exists(persist_directory):
    vectorstore = Chroma(persist_directory=persist_directory, embedding_function=hf_embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    print("✅ 벡터 DB 연결 성공!")
else:
    print("❌ DB가 없습니다. ingest.py를 먼저 실행하세요.")
    retriever = None

# 3. Ollama Llama 3.2 모델 설정
llm = ChatOllama(model="llama3.2", temperature=0)

# 4. 프롬프트 및 체인 구성 (LCEL 방식)
template = """당신은 청년정책 전문 상담사입니다.

⚠️ 가장 중요한 규칙:
- 청년정책과 관련 없는 질문(맛집, 연예인, 날씨, 코딩, 일반 상식 등)에는
  "죄송하지만, 저는 청년정책 안내 전문 챗봇이에요. 청년정책에 대해 질문해주세요! 😊"
  라고만 답변하고 다른 말은 하지 마세요.

청년정책 관련 질문일 경우에만 아래 규칙을 따르세요:
1. 아래 정보(context)에 있는 내용만 답변하세요.
2. 정보에 없는 내용은 "제공된 정책 자료에서 해당 정보를 찾을 수 없습니다."라고 답하세요.
3. 지원금액, 대상, 조건 등 구체적인 숫자를 포함해서 답변하세요.
4. 친근하고 이해하기 쉬운 말투를 사용하세요.
5. 사용자가 특정 지역을 물어보면 해당 지역 정보만 답변하세요.
6. 관련 없는 정보는 언급하지 마세요.

정보: {context}
질문: {question}
"""
prompt = ChatPromptTemplate.from_template(template)

def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# 최종 챗봇 체인
if retriever:
    qa_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )
else:
    qa_chain = None

# --- FastAPI 설정 ---
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat(request: ChatRequest):
    try:
        if not qa_chain:
            return {"answer": "서버 설정 오류: DB가 연결되지 않았습니다."}
        
        answer = qa_chain.invoke(request.message)
        return {"answer": answer}
    except Exception as e:
        return {"answer": f"에러 발생: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# from fastapi import FastAPI
# from fastapi.middleware.cors import CORSMiddleware
# from pydantic import BaseModel
# from engine import get_chat_response

# # 1. FastAPI 앱 생성
# app = FastAPI()

# # 2. CORS 설정 (이 부분이 있어야 React와 연결됩니다!)
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],      # 모든 곳에서 오는 요청 허용 (개발 단계에서 편리)
#     allow_credentials=True,
#     allow_methods=["*"],      # GET, POST 등 모든 방식 허용
#     allow_headers=["*"],      # 모든 헤더 허용
# )

# # 3. 데이터 모델 정의 (schema.py로 분리 가능)
# class ChatRequest(BaseModel):
#     message: str

# # 4. 테스트용 엔드포인트
# @app.get("/")
# def read_root():
#     return {"status": "FastAPI Server is Running!"}

# # 5. 실제 채팅 엔드포인트
# @app.post("/chat")
# async def chat(request: ChatRequest):
#     # 나중에 여기에 engine.py의 로직을 연결할 거예요.
#     user_message = request.message
#     # engine.py의 함수를 실행하여 진짜 답변을 가져옵니다.
#     answer = get_chat_response(user_message)
#     print(f"사용자 질문: {user_message}")
    
#     return {"answer": answer}