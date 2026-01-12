import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import CharacterTextSplitter
# 최신 방식의 임포트 경로입니다.
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

def get_chat_response(user_message):
    # 1. 문서 로드 (data 폴더의 txt 읽기)
    loader = DirectoryLoader('./data', glob="*.txt", loader_cls=TextLoader)
    documents = loader.load()

    # 2. 문서 쪼개기
    text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=0)
    texts = text_splitter.split_documents(documents)

    # 3. 벡터 DB 생성
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma.from_documents(texts, embeddings)

    # 4. 최신 RAG 체인 생성
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0)
    
    # AI에게 주는 지침(프롬프트)
    prompt = ChatPromptTemplate.from_template("""
    아래 문맥(Context)을 사용하여 질문에 답하세요. 
    문맥에 답이 없으면 모른다고 하세요.
    
    <context>
    {context}
    </context>
    
    질문: {input}
    """)

    # 문서 결합 체인과 검색 체인 연결
    combine_docs_chain = create_stuff_documents_chain(llm, prompt)
    retrieval_chain = create_retrieval_chain(vectorstore.as_retriever(), combine_docs_chain)

    # 5. 답변 생성
    response = retrieval_chain.invoke({"input": user_message})
    return response["answer"]