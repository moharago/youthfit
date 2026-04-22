# ingest.py (pdfplumber 버전)

import os
import glob
import json
import shutil
import pandas as pd
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings

load_dotenv()
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def run_free_ingestion():
    data_folder = 'data/files'
    persist_directory = "./data/chroma_db"
    
    # 1. OpenAI 임베딩 모델 로드
    print("⏳ OpenAI 임베딩 모델 로딩 중...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    all_documents = []
    
    # =====================
    # 2-1. CSV 파일 처리
    # =====================
    csv_files = [f for f in glob.glob(os.path.join(data_folder, '*.csv')) 
                 if not os.path.basename(f).startswith('~$')]
    
    for file_path in csv_files:
        print(f"📄 CSV 처리 중: {os.path.basename(file_path)}")
        try:
            df = pd.read_csv(file_path, encoding='utf-8-sig')
        except:
            df = pd.read_csv(file_path, encoding='cp949')

        for i, row in df.iterrows():
            content_parts = []
            for col in df.columns:
                if pd.notna(row[col]):
                    content_parts.append(f"{col}: {row[col]}")
            content = "\n".join(content_parts)
            
            metadata = {"source": os.path.basename(file_path), "type": "csv"}
            all_documents.append(Document(page_content=content, metadata=metadata))
    
    # =====================
    # 2-2. JSON 파일 처리
    # =====================
    json_files = glob.glob(os.path.join(data_folder, '*.json'))

    for file_path in json_files:
        print(f"📄 JSON 처리 중: {os.path.basename(file_path)}")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        policies = data.get("policies", [])
        for policy in policies:
            content = "\n".join([
                f"정책명: {policy.get('policy_name', '')}",
                f"분야: {policy.get('policy_category_large', '')} > {policy.get('policy_category_mid', '')}",
                f"지역: {policy.get('region_name', '')}",
                f"대상 나이: {policy.get('target_age_min', '')}~{policy.get('target_age_max', '')}세",
                f"취업상태: {policy.get('target_employment_status', '')}",
                f"소득기준: {policy.get('target_income_level', '')}",
                f"요약: {policy.get('summary', '')}",
                f"지원내용: {policy.get('support_content', '')}",
                f"신청방법: {policy.get('application_method', '')}",
                f"담당기관: {policy.get('agency_name', '')}",
                f"키워드: {', '.join(policy.get('keywords', []))}",
            ])
            metadata = {
                "source": os.path.basename(file_path),
                "type": "json",
                "policy_id": policy.get("policy_id", ""),
                "region": policy.get("region_name", ""),
                "category": policy.get("policy_category_large", ""),
            }
            all_documents.append(Document(page_content=content, metadata=metadata))

    # =====================
    # 2-3. TXT 파일 처리
    # =====================
    txt_files = [f for f in glob.glob(os.path.join(data_folder, '*.txt'))
                 if not os.path.basename(f).startswith('~$')]
    
    for file_path in txt_files:
        print(f"📄 TXT 처리 중: {os.path.basename(file_path)}")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except:
            with open(file_path, 'r', encoding='cp949') as f:
                content = f.read()
        
        metadata = {"source": os.path.basename(file_path), "type": "txt"}
        all_documents.append(Document(page_content=content, metadata=metadata))
    
    # =====================
    # 2-3. PDF 파일 처리 (pdfplumber)
    # =====================
    pdf_files = glob.glob(os.path.join(data_folder, '*.pdf'))
    
    if pdf_files:
        import pdfplumber
        
        for file_path in pdf_files:
            print(f"📄 PDF 처리 중: {os.path.basename(file_path)}")
            
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    text = ""
                    
                    # 텍스트 추출
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text
                    
                    # 표(테이블) 추출
                    tables = page.extract_tables()
                    for table in tables:
                        for row in table:
                            if row:
                                row_text = " | ".join([str(cell) if cell else "" for cell in row])
                                text += "\n" + row_text
                    
                    if text and text.strip():
                        metadata = {
                            "source": os.path.basename(file_path),
                            "type": "pdf",
                            "page": page_num + 1
                        }
                        all_documents.append(Document(page_content=text, metadata=metadata))
            
            print(f"   → {len(pdf.pages)}페이지 처리 완료")

    # =====================
    # 3. 결과 확인
    # =====================
    if not all_documents:
        print("❌ 저장할 데이터가 없습니다.")
        return
    
    print(f"\n📊 처리 결과:")
    print(f"   - JSON 파일: {len(json_files)}개")
    print(f"   - CSV 파일: {len(csv_files)}개")
    print(f"   - TXT 파일: {len(txt_files)}개")
    print(f"   - PDF 파일: {len(pdf_files)}개")
    print(f"   - 총 문서: {len(all_documents)}개")

    # =====================
    # 4. 텍스트 분할
    # =====================
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300, 
        chunk_overlap=50
    )
    texts = text_splitter.split_documents(all_documents)
    print(f"   - 분할 후 청크: {len(texts)}개")

    # =====================
    # 5. 기존 DB 삭제 후 새로 생성
    # =====================
    if os.path.exists(persist_directory):
        shutil.rmtree(persist_directory)
        print("\n🗑️ 기존 벡터 DB 삭제")

    print(f"🚀 {len(texts)}개의 청크를 벡터 DB에 저장 중...")
    vectorstore = Chroma.from_documents(
        documents=texts,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    print("✅ 벡터 DB 구축 완료!")

if __name__ == "__main__":
    run_free_ingestion()

    
# import os
# import glob
# import pandas as pd
# from langchain_community.embeddings import HuggingFaceEmbeddings
# from langchain_community.vectorstores import Chroma
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_core.documents import Document  # 에러 해결을 위해 필수 추가

# def run_free_ingestion():
#     data_folder = 'data'
#     persist_directory = "./chroma_db"
    
#     # 1. 한국어 전용 무료 임베딩 모델 로드
#     print("⏳ 한국어 임베딩 모델 로딩 중...")
#     model_name = "jhgan/ko-sroberta-multitask"
#     hf_embeddings = HuggingFaceEmbeddings(
#         model_name=model_name,
#         model_kwargs={'device': 'cpu'},
#         encode_kwargs={'normalize_embeddings': True}
#     )

#     # 2. 파일 읽기 및 문서화
#     csv_files = [f for f in glob.glob(os.path.join(data_folder, '*.csv')) if not os.path.basename(f).startswith('~$')]
#     all_documents = []
    
#     for file_path in csv_files:
#         print(f"📄 읽는 중: {file_path}")
#         try:
#             df = pd.read_csv(file_path, encoding='utf-8-sig')
#         except:
#             df = pd.read_csv(file_path, encoding='cp949')

#         for i, row in df.iterrows():
#             # 실제 CSV의 컬럼명과 일치하는지 꼭 확인하세요!
#             content = f"카페명: {row.get('카페명', '')}\n주소: {row.get('주소', '')}\n소개: {row.get('간략소개', '')}"
#             metadata = {"source": os.path.basename(file_path), "location": row.get('구군', '')}
#             all_documents.append(Document(page_content=content, metadata=metadata))

#     if not all_documents:
#         print("❌ 저장할 데이터가 없습니다. data 폴더를 확인하세요.")
#         return

#     # 3. 텍스트 분할 및 저장
#     text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
#     texts = text_splitter.split_documents(all_documents)

#     print(f"🚀 {len(texts)}개의 지식 조각을 무료 DB에 저장합니다...")
#     vectorstore = Chroma.from_documents(
#         documents=texts,
#         embedding=hf_embeddings,
#         persist_directory=persist_directory
#     )
#     print("✅ 무료 임베딩 기반 DB 구축 완료!")

# if __name__ == "__main__":
#     run_free_ingestion()


# import os
# import glob
# import pandas as pd
# from dotenv import load_dotenv
# from langchain_openai import OpenAIEmbeddings
# from langchain_text_splitters import RecursiveCharacterTextSplitter
# from langchain_community.vectorstores import Chroma
# from langchain.docstore.document import Document

# load_dotenv()

# def run_optimized_ingestion():
#     # 1. 설정 및 경로 준비
#     data_folder = 'data'
#     persist_directory = "./chroma_db"
    
#     # .csv 파일만 필터링 (임시파일 제외)
#     csv_files = [f for f in glob.glob(os.path.join(data_folder, '*.csv')) 
#                  if not os.path.basename(f).startswith('~$')]
    
#     if not csv_files:
#         print("📍 처리할 새로운 CSV 파일이 없습니다.")
#         return

#     all_documents = []

#     # 2. 모든 파일 순회하며 읽기
#     for file_path in csv_files:
#         print(f"📄 파일 분석 중: {file_path}")
#         try:
#             # utf-8-sig는 한글 엑셀 저장 시 생기는 유령 문자를 방지합니다.
#             df = pd.read_csv(file_path, encoding='utf-8-sig')
#         except:
#             df = pd.read_csv(file_path, encoding='cp949')

#         # 3. 데이터 정제 및 메타데이터 추가
#         for i, row in df.iterrows():
#             # 사용자가 궁금해할 정보 위주로 구성
#             content = f"""카페명: {row.get('카페명')}
# 설명: {row.get('간략소개')}
# 운영: {row.get('이용시간')} (휴무: {row.get('휴무일')})
# 주소: {row.get('주소')}
# 유형: {row.get('카페유형')}"""

#             # 메타데이터를 넣어야 나중에 '용산구'만 검색하는 등의 필터링이 가능해집니다.
#             metadata = {
#                 "source": os.path.basename(file_path),
#                 "row": i,
#                 "location": row.get('구군', '미분류'),
#                 "name": row.get('카페명', '알수없음')
#             }
            
#             all_documents.append(Document(page_content=content, metadata=metadata))

#     # 4. 최적화된 텍스트 분할 (RecursiveCharacterTextSplitter)
#     # 단순히 글자수로 자르는 게 아니라 의미 단위(줄바꿈, 마침표 등)로 자릅니다.
#     text_splitter = RecursiveCharacterTextSplitter(
#         chunk_size=800,
#         chunk_overlap=100,
#         separators=["\n\n", "\n", " ", ""]
#     )
#     texts = text_splitter.split_documents(all_documents)

#     # 5. 벡터 DB 저장 (중복 방지를 위해 초기화 후 저장하거나 업데이트)
#     print(f"🚀 총 {len(texts)}개의 지식 조각을 DB에 주입합니다...")
    
#     vectorstore = Chroma.from_documents(
#         documents=texts,
#         embedding=OpenAIEmbeddings(),
#         persist_directory=persist_directory
#     )
    
#     print(f"✅ 최적화 주입 완료! '{persist_directory}'에 저장되었습니다.")

# if __name__ == "__main__":
#     run_optimized_ingestion()