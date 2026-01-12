# engine.py - 수정 버전

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

# ⭐ 앱 시작할 때 한 번만 로드
print("⏳ 벡터 DB 로딩 중...")

# ingest.py에서 사용한 것과 동일한 임베딩 모델
hf_embeddings = HuggingFaceEmbeddings(
    model_name="jhgan/ko-sroberta-multitask",
    model_kwargs={'device': 'cpu'},
    encode_kwargs={'normalize_embeddings': True}
)

# 이미 만들어진 벡터 DB 로드
vectorstore = Chroma(
    persist_directory="./data/chroma_db",
    embedding_function=hf_embeddings
)

print("✅ 벡터 DB 로딩 완료!")

# LLM 설정
llm = ChatOpenAI(model_name="gpt-4o", temperature=0)

# 프롬프트
prompt = ChatPromptTemplate.from_template("""
아래 문맥(Context)을 사용하여 질문에 답하세요. 
문맥에 답이 없으면 모른다고 하세요.

<context>
{context}
</context>

질문: {input}
""")

# 체인 생성 (한 번만)
combine_docs_chain = create_stuff_documents_chain(llm, prompt)
retrieval_chain = create_retrieval_chain(vectorstore.as_retriever(), combine_docs_chain)


def get_chat_response(user_message):
    """질문에 대한 답변 생성"""
    response = retrieval_chain.invoke({"input": user_message})
    return response["answer"]