# backend/app.py
import streamlit as st
import requests
import uuid  # ⭐ 추가

# 페이지 설정
st.set_page_config(
    page_title="청년정책 AI 챗봇",
    page_icon="💬",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ⭐ 추가: 사용자 고유 ID 생성
if "user_id" not in st.session_state:
    st.session_state.user_id = str(uuid.uuid4())

user_id = st.session_state.user_id

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
                "name": "청년미래적금",
                "desc": "5년 만기 시 최대 5,000만원 수령",
                "question": "청년미래적금 알려줘"
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


# =========================
# 업데이트 by Dayforged (보고서 기능) - 추가 시작
# =========================
from urllib.parse import urlencode, quote
import streamlit.components.v1 as components

if "chat_ended" not in st.session_state:
    st.session_state.chat_ended = False
if "report_payload" not in st.session_state:
    st.session_state.report_payload = None

# - LOG 기반 파일 report_id 저장(추가)
if "report_id" not in st.session_state:
    st.session_state.report_id = None
# =========================
# 업데이트 by Dayforged (보고서 기능) - 추가 끝
# =========================

def _get_query_params() -> dict:
    try:
        qp = dict(st.query_params)
        return qp
    except Exception:
        try:
            qp = st.experimental_get_query_params()
            return dict(qp) if isinstance(qp, dict) else {}
        except Exception:
            return {}

def _clear_query_params() -> None:
    try:
        st.query_params.clear()
        return
    except Exception:
        try:
            st.experimental_set_query_params()
        except Exception:
            pass

# ✅ 업데이트 by Dayforged (보고서 기능) - 추가 시작
def _build_chat_log_for_report() -> list:
    """
    Streamlit 세션 messages를 ReportFromLogRequest.chat_log 형태로 변환
    """
    out = []
    for m in st.session_state.messages:
        role = m.get("role")
        if role not in ("user", "assistant", "system"):
            role = "system"
        out.append({
            "role": role,
            "content": m.get("content", ""),
            "ts": None
        })
    return out
# ✅ 업데이트 by Dayforged (보고서 기능) - 추가 끝

# (A-1) ?end=1로 들어오면 상담 종료 + report_payload 저장
qp = _get_query_params()
end_flag = qp.get("end")
if isinstance(end_flag, list):
    end_flag = end_flag[0] if end_flag else None

if str(end_flag) == "1" and not st.session_state.chat_ended:
    st.session_state.chat_ended = True

    try:
        resp = requests.post(
            "http://127.0.0.1:8000/report/from_log",
            json={
                "session_id": user_id,
                "chat_log": _build_chat_log_for_report(),
                "extracted_facts": None
            },
            timeout=180
        )
        data = resp.json()
        st.session_state.report_id = data.get("report_id")
        st.session_state.report_payload = data.get("payload")
    except Exception:
        st.session_state.report_id = None
        st.session_state.report_payload = None

    _clear_query_params()
    st.rerun()

end_url = "?" + urlencode({"end": 1})

st.markdown(
    f"""
    <style>
      .report-fixed-footer {{
        position: fixed;
        left: 50%;
        transform: translateX(-50%);
        bottom: 8.5px;
        z-index: 9999;
      }}

      .report-fixed-footer a {{
        display: inline-block;
        background: white;
        color: #1e90ff;
        border: 1px solid #1e90ff;
        border-radius: 999px;

        padding: 10px 13px;
        font-size: 0.95rem;
        font-weight: 520;
        line-height: 1.0;

        box-shadow: 0 6px 14px rgba(0,0,0,0.16);
        text-decoration: none;
        white-space: nowrap;
      }}

      .report-fixed-footer a:hover {{
        background: #1e90ff;
        color: white;
      }}

      .stApp {{
        padding-bottom: 0px;
      }}
    </style>

    <div class="report-fixed-footer">
      <a href="{end_url}" target="_self" rel="noopener noreferrer">🧾 상담 종료</a>
    </div>
    """,
    unsafe_allow_html=True
)

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
    
    st.markdown("### 💡 이런 질문을 해보세요")
    
    for policy in cat_data["policies"]:

        # =========================
        # ✅ 업데이트 by Dayforged (보고서 기능) - 추가 시작
        if st.session_state.chat_ended:
            st.info("상담이 종료되었습니다. 하단의 보고서 섹션을 확인해 주세요.")
            break
        # ✅ 업데이트 by Dayforged (보고서 기능) - 추가 끝
        # =========================

        if st.button(f"👉 {policy['question']}", key=f"q_{policy['name']}"):
            with st.chat_message("user"):
                st.markdown(policy['question'])
            st.session_state.messages.append({"role": "user", "content": policy['question']})
            
            with st.chat_message("assistant"):
                with st.spinner("🤔 답변 생성 중..."):
                    try:
                        response = requests.post(
                            "http://127.0.0.1:8000/chat",
                            json={
                                "message": policy['question'],
                                "user_id": user_id
                            },
                            timeout=180
                        )
                        answer = response.json().get("answer", "오류가 발생했습니다.")
                    except:
                        answer = "❌ 서버 연결에 실패했습니다."
                    st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
    
    st.markdown("---")
    
    if st.button("⬅️ 카테고리 다시 선택"):
        st.session_state.category = None
        st.rerun()

st.divider()

# 이전 채팅 표시
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 사용자 직접 입력
if prompt := st.chat_input("💬 질문을 입력하세요..."):

    # =========================
    # ✅ 업데이트 by Dayforged (보고서 기능) - 추가 시작
    if st.session_state.chat_ended:
        st.warning("상담이 종료되었습니다. 보고서를 확인해 주세요.")
        st.stop()
    # ✅ 업데이트 by Dayforged (보고서 기능) - 추가 끝
    # =========================

    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("assistant"):
        with st.spinner("🤔 답변 생성 중..."):
            try:
                response = requests.post(
                    "http://127.0.0.1:8000/chat",
                    json={
                        "message": prompt,
                        "user_id": user_id
                    },
                    timeout=180
                )
                answer = response.json().get("answer", "오류가 발생했습니다.")
            except:
                answer = "❌ 서버 연결에 실패했습니다."
            st.markdown(answer)
    st.session_state.messages.append({"role": "assistant", "content": answer})


# =========================
# ✅ 업데이트 by Dayforged (보고서 기능) - 추가 시작
# - 상담 종료 후: 페이지 하단에 iframe으로 보고서 화면 표시 (FastAPI /report/view_by_id)
# =========================
if st.session_state.chat_ended:
    st.markdown("---")
    st.subheader("상담 결과 기반 정책 전략 가이드")

    if st.session_state.report_id:
        # ✅ 보고서 관련 코드 (업데이트 by dayforged) - 추가 시작
        # report_id를 URL-safe하게 인코딩 (공백/특수문자 대비)
        safe_report_id = quote(str(st.session_state.report_id), safe="")
        view_url = f"http://127.0.0.1:8000/report/view_by_id?report_id={safe_report_id}"
        # ✅ 보고서 관련 코드 (업데이트 by dayforged) - 추가 끝

        components.iframe(view_url, height=920, scrolling=True)
    else:
        st.error("보고서 생성에 실패했습니다. 백엔드 서버(8000) 상태를 확인해 주세요.")

    with st.expander("디버그(report_payload) 보기", expanded=False):
        st.json(st.session_state.report_payload or {})
# =========================
# ✅ 업데이트 by Dayforged (보고서 기능) - 추가 끝
# =========================


# 사이드바
with st.sidebar:
    st.markdown("## 🎯 사용 방법")
    st.markdown("""
    1. 카테고리 선택
    2. 원하는 정책 클릭
    3. 또는 직접 질문 입력
    """)
    
    st.markdown("---")
    st.markdown(f"🆔 `{user_id[:8]}...`")
    
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.category = None

        # =========================
        # ✅ 업데이트 by Dayforged (보고서 기능) - 추가 시작
        st.session_state.chat_ended = False
        st.session_state.report_payload = None
        st.session_state.report_id = None
        # ✅ 업데이트 by Dayforged (보고서 기능) - 추가 끝
        # =========================

        st.rerun()
