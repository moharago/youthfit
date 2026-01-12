# backend/app.py

import streamlit as st
import requests

# 페이지 설정
st.set_page_config(
    page_title="청년정책 AI 챗봇",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 커스텀 CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1e90ff 0%, #00bfff 100%);
        background-attachment: fixed;
    }
    
    .main-title {
        text-align: center;
        color: white;
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
    }
    
    .sub-title {
        text-align: center;
        color: rgba(255,255,255,0.9);
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    
    .stButton > button {
        background: white;
        color: #1e90ff;
        border: 2px solid #1e90ff;
        border-radius: 25px;
        padding: 10px 30px;
        font-weight: 600;
        box-shadow: 0 4px 15px rgba(30, 144, 255, 0.2);
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        background: #1e90ff;
        color: white;
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(30, 144, 255, 0.4);
    }
    
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1e90ff 0%, #00bfff 100%);
    }
    
    section[data-testid="stSidebar"] .stMarkdown {
        color: white;
    }
    
    .policy-card {
        background: white;
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .policy-title {
        color: #1e90ff;
        font-size: 1.2rem;
        font-weight: 700;
        margin-bottom: 10px;
    }
    
    .policy-desc {
        color: #333;
        font-size: 0.95rem;
    }
    
    .category-title {
        color: white;
        font-size: 1.2rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# 카테고리별 정책 데이터
CATEGORY_POLICIES = {
    "취업": {
        "icon": "💼",
        "policies": [
            {
                "name": "국민취업지원제도",
                "desc": "구직촉진수당 월 50~60만원 + 취업지원서비스",
                "question": "국민취업지원제도에 대해 자세히 알려줘"
            },
            {
                "name": "청년일자리도약장려금",
                "desc": "청년 채용 기업에 최대 1,200만원 지원",
                "question": "청년일자리도약장려금 알려줘"
            },
            {
                "name": "일자리카페",
                "desc": "취업 준비 공간 및 상담 서비스 제공",
                "question": "일자리카페 어디있어?"
            }
        ]
    },
    "주거": {
        "icon": "🏠",
        "policies": [
            {
                "name": "청년월세 한시 특별지원",
                "desc": "월 최대 20만원, 12개월 지원",
                "question": "청년월세 지원 알려줘"
            },
            {
                "name": "청년 전세자금 대출",
                "desc": "저금리 전세자금 대출 지원",
                "question": "청년 전세자금 대출 조건 알려줘"
            }
        ]
    },
    "금융": {
        "icon": "💰",
        "policies": [
            {
                "name": "청년도약계좌",
                "desc": "5년 만기 시 최대 5,000만원 수령",
                "question": "청년도약계좌 알려줘"
            },
            {
                "name": "청년내일저축계좌",
                "desc": "3년 만기 시 최대 1,440만원 수령",
                "question": "청년내일저축계좌 알려줘"
            }
        ]
    },
    "창업": {
        "icon": "🚀",
        "policies": [
            {
                "name": "청년창업사관학교",
                "desc": "창업 교육 및 최대 1억원 사업화 지원",
                "question": "청년창업사관학교 알려줘"
            },
            {
                "name": "청년전용 창업자금",
                "desc": "저금리 창업자금 대출 지원",
                "question": "청년 창업자금 대출 알려줘"
            }
        ]
    },
    "교육": {
        "icon": "📚",
        "policies": [
            {
                "name": "국민내일배움카드",
                "desc": "직업훈련비 최대 500만원 지원",
                "question": "국민내일배움카드 알려줘"
            },
            {
                "name": "청년 해외취업 지원",
                "desc": "해외취업 연수 및 알선 지원",
                "question": "해외취업 지원 프로그램 알려줘"
            }
        ]
    },
    "복지": {
        "icon": "🏥",
        "policies": [
            {
                "name": "청년 마음건강 지원",
                "desc": "심리상담 비용 지원",
                "question": "청년 심리상담 지원 알려줘"
            },
            {
                "name": "청년 건강검진",
                "desc": "무료 건강검진 지원",
                "question": "청년 건강검진 알려줘"
            }
        ]
    }
}

# 헤더
st.markdown('<h1 class="main-title">💬 청년정책 AI 챗봇</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">청년지원정책에 대해 무엇이든 물어보세요!</p>', unsafe_allow_html=True)

# 세션 초기화
if "category" not in st.session_state:
    st.session_state.category = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "selected_question" not in st.session_state:
    st.session_state.selected_question = None

# 카테고리 버튼
st.markdown('<p class="category-title">📂 어떤 분야가 궁금하세요?</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("💼 취업", use_container_width=True):
        st.session_state.category = "취업"
with col2:
    if st.button("🏠 주거", use_container_width=True):
        st.session_state.category = "주거"
with col3:
    if st.button("💰 금융", use_container_width=True):
        st.session_state.category = "금융"

col4, col5, col6 = st.columns(3)
with col4:
    if st.button("🚀 창업", use_container_width=True):
        st.session_state.category = "창업"
with col5:
    if st.button("📚 교육", use_container_width=True):
        st.session_state.category = "교육"
with col6:
    if st.button("🏥 복지", use_container_width=True):
        st.session_state.category = "복지"

# 카테고리 선택 시 정책 목록 표시
# 카테고리 선택 시 정책 목록 표시
if st.session_state.category:
    cat = st.session_state.category
    cat_data = CATEGORY_POLICIES[cat]
    
    st.markdown(f"### {cat_data['icon']} {cat} 지원 정책")
    
    for policy in cat_data["policies"]:
        st.markdown(f"""
        <div class="policy-card">
            <div class="policy-title">{policy['name']}</div>
            <div class="policy-desc">{policy['desc']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    # 예상 질문 섹션
    st.markdown("### 💡 이런 질문을 해보세요")
    
    for policy in cat_data["policies"]:
        if st.button(f"👉 {policy['question']}", key=f"q_{policy['name']}"):
            # 클릭하면 질문 + 답변 바로 실행
            with st.chat_message("user"):
                st.markdown(policy['question'])
            st.session_state.messages.append({"role": "user", "content": policy['question']})
            
            with st.chat_message("assistant"):
                with st.spinner("🤔 답변 생성 중..."):
                    try:
                        response = requests.post(
                            "http://127.0.0.1:8000/chat",
                            json={"message": policy['question']},
                            timeout=60
                        )
                        answer = response.json().get("answer", "오류가 발생했습니다.")
                    except:
                        answer = "❌ 서버 연결에 실패했습니다."
                    st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
    
    st.markdown("---")
    
    # 뒤로가기 버튼
    if st.button("⬅️ 카테고리 다시 선택"):
        st.session_state.category = None
        st.rerun()

st.divider()

# 이전 채팅 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# 자동 질문 처리 (정책 클릭 시)
if st.session_state.selected_question:
    prompt = st.session_state.selected_question
    st.session_state.selected_question = None
    
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("🤔 답변 생성 중..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/chat",
                    json={"message": prompt},
                    timeout=60
                )
                answer = response.json().get("answer", "오류가 발생했습니다.")
            except:
                answer = "❌ 서버 연결에 실패했습니다."
            st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

# 사용자 직접 입력
if prompt := st.chat_input("💬 질문을 입력하세요..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("🤔 답변 생성 중..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/chat",
                    json={"message": prompt},
                    timeout=60
                )
                answer = response.json().get("answer", "오류가 발생했습니다.")
            except:
                answer = "❌ 서버 연결에 실패했습니다."
            st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})

# 사이드바
with st.sidebar:
    st.markdown("## 🎯 사용 방법")
    st.markdown("""
    1. 카테고리 선택
    2. 원하는 정책 클릭
    3. 또는 직접 질문 입력
    """)
    
    st.markdown("---")
    
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.category = None
        st.rerun()