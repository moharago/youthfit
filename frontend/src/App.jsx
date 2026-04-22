import React, { useState } from "react";
import { v4 as uuidv4 } from "uuid";
import "./App.css";

const CATEGORY_POLICIES = {
  "취업": {
    icon: "💼",
    policies: [
      { name: "국민취업지원제도", desc: "구직촉진수당 월 50~60만원 + 취업지원서비스", question: "국민취업지원제도에 대해 자세히 알려줘" },
      { name: "청년일자리도약장려금", desc: "청년 채용 기업에 최대 1,200만원 지원", question: "청년일자리도약장려금 알려줘" },
      { name: "일자리카페", desc: "취업 준비 공간 및 상담 서비스 제공", question: "일자리카페 어디있어?" }
    ]
  },
  "주거": {
    icon: "🏠",
    policies: [
      { name: "청년월세 한시 특별지원", desc: "월 최대 20만원, 12개월 지원", question: "청년월세 지원 알려줘" },
      { name: "청년 전세자금 대출", desc: "저금리 전세자금 대출 지원", question: "청년전세자금 대출 조건 알려줘" }
    ]
  },
  "금융": {
    icon: "💰",
    policies: [
      { name: "청년미래적금", desc: "5년 만기 시 최대 5,000만원 수령", question: "청년미래적금 알려줘" }
    ]
  },
  "창업": {
    icon: "🚀",
    policies: [
      { name: "청년창업사관학교", desc: "창업 교육 및 최대 1억원 사업화 지원", question: "청년창업사관학교 알려줘" },
      { name: "청년전용 창업자금", desc: "저금리 창업자금 대출 지원", question: "청년 창업자금 대출 알려줘" }
    ]
  },
  "교육": {
    icon: "📚",
    policies: [
      { name: "국민내일배움카드", desc: "직업훈련비 최대 500만원 지원", question: "국민내일배움카드 알려줘" },
      { name: "청년 해외취업 지원", desc: "해외취업 연수 및 알선 지원", question: "해외취업 지원 프로그램 알려줘" }
    ]
  },
  "복지": {
    icon: "🏥",
    policies: [
      { name: "청년 마음건강 지원", desc: "심리상담 비용 지원", question: "청년 심리상담 지원 알려줘" },
      { name: "청년 건강검진", desc: "무료 건강검진 지원", question: "청년 건강검진 알려줘" }
    ]
  }
};

function App() {
  const [userId] = useState(uuidv4());
  const [category, setCategory] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");

  const askQuestion = async (question) => {
    setMessages(prev => [...prev, { role: "user", content: question }]);
    try {
      const res = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, user_id: userId })
      });
      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.answer || "오류 발생" }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "❌ 서버 연결에 실패했습니다." }]);
    }
  };

  return (
    <div className="app">
      <h1 className="main-title">💬 청년정책 AI 챗봇</h1>
      <p className="sub-title">청년지원정책에 대해 무엇이든 물어보세요!</p>

      {!category && (
        <>
          <p className="category-title">📂 어떤 분야가 궁금하세요?</p>
          <div className="category-grid">
            {Object.keys(CATEGORY_POLICIES).map(cat => (
              <button key={cat} onClick={() => setCategory(cat)}>
                {CATEGORY_POLICIES[cat].icon} {cat}
              </button>
            ))}
          </div>
        </>
      )}

      {category && (
        <>
          <h3>{CATEGORY_POLICIES[category].icon} {category} 지원 정책</h3>
          {CATEGORY_POLICIES[category].policies.map(policy => (
            <div key={policy.name} className="policy-card">
              <div className="policy-title">{policy.name}</div>
              <div className="policy-desc">{policy.desc}</div>
              <button onClick={() => askQuestion(policy.question)}>👉 {policy.question}</button>
            </div>
          ))}
          <button className="back-btn" onClick={() => setCategory(null)}>⬅️ 카테고리 다시 선택</button>
        </>
      )}

      <hr />

      <div className="chat-container">
        {messages.map((msg, idx) => (
          <div key={idx} className={msg.role === "user" ? "chat-user" : "chat-assistant"}>
            {msg.content}
          </div>
        ))}
      </div>

      <div className="chat-input">
        <input
          type="text"
          placeholder="💬 질문을 입력하세요..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if(e.key==="Enter" && input.trim()){askQuestion(input.trim()); setInput("");} }}
        />
        <button onClick={() => { if(input.trim()){askQuestion(input.trim()); setInput("");} }}>전송</button>
      </div>
    </div>
  );
}

export default App;
