import React, { useState, useRef, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import "./App.css";

const QUICK_QUESTIONS = {
  취업: [
    "내게 맞는 일자리 지원금을 찾고 싶어",
    "국민취업지원제도에 대해 알고 싶어",
    "면접 컨설팅을 받을 수 있는 곳이 있어?",
    "청년 내일채움공제 자격 요건은?",
    "지역별 일자리 카페는 어디에 있어?",
    "청년일자리도약장려금 신청 방법은?",
  ],
  주거: [
    "청년월세 지원 신청 방법은?",
    "청년 전세자금 대출 조건이 뭐야?",
    "행복주택 입주 자격이 어떻게 돼?",
    "청년 주거급여 분리지급이 뭐야?",
    "전세 사기 예방 방법 알려줘",
    "청년 공공임대 신청 어떻게 해?",
  ],
  금융: [
    "청년도약계좌 가입 조건이 뭐야?",
    "청년미래적금 만기 수령액은?",
    "청년 저금리 신용대출 상품 알려줘",
    "청년 내일저축계좌 신청 방법은?",
    "소득 없어도 청년 금융 지원 받을 수 있어?",
    "청년 금융 상품 비교해줘",
  ],
  창업: [
    "청년창업사관학교 지원 방법은?",
    "청년 창업자금 대출 조건이 뭐야?",
    "예비창업패키지 신청 방법 알려줘",
    "창업 아이디어가 있는데 어디서 도움받아?",
    "창업 공간 무료로 쓸 수 있는 곳 있어?",
    "초기 창업자 지원금 종류 알려줘",
  ],
  교육: [
    "국민내일배움카드 발급 방법은?",
    "청년 해외취업 연수 프로그램 있어?",
    "직업훈련 생계비 대출 알려줘",
    "K-디지털 트레이닝 어떻게 신청해?",
    "무료 직업훈련 과정 추천해줘",
    "취업 준비 비용 지원해주는 정책 있어?",
  ],
  복지: [
    "청년 심리상담 무료로 받을 수 있어?",
    "청년 건강검진 어떻게 신청해?",
    "청년 기초생활수급 조건이 뭐야?",
    "1인 청년 가구 복지 지원 알려줘",
    "청년 자립 지원 프로그램 있어?",
    "청년 마음건강 바우처 신청 방법은?",
  ],
};

const CATEGORY_ICONS = {
  취업: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
      <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
    </svg>
  ),
  주거: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
      <polyline points="9 22 9 12 15 12 15 22" />
    </svg>
  ),
  금융: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <line x1="12" y1="1" x2="12" y2="23" />
      <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  ),
  창업: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z" />
      <path d="M12 15l-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z" />
      <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0" />
      <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5" />
    </svg>
  ),
  교육: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z" />
      <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z" />
    </svg>
  ),
  복지: (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
    </svg>
  ),
};

const CATEGORIES = ["취업", "주거", "금융", "창업", "교육", "복지"];
const USER_ID_STORAGE_KEY = "youthfit_user_id";
const CONV_ID_STORAGE_KEY = "youthfit_conv_id";

const getStoredUserId = () => {
  const existing = localStorage.getItem(USER_ID_STORAGE_KEY);
  if (existing) return existing;
  const created = uuidv4();
  localStorage.setItem(USER_ID_STORAGE_KEY, created);
  return created;
};

// 새로고침마다 새 대화 세션 시작
const initConversationId = () => {
  const created = uuidv4();
  localStorage.setItem(CONV_ID_STORAGE_KEY, created);
  return created;
};

const renderMarkdown = (text) =>
  text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br/>");

const BotIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
  </svg>
);

const UserIcon = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
    <circle cx="12" cy="7" r="4" />
  </svg>
);

function App() {
  const [userId] = useState(getStoredUserId);
  const [conversationId] = useState(initConversationId);
  const [category, setCategory] = useState("취업");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [inlineInputs, setInlineInputs] = useState({});    // { field: string }
  const [inlineActive, setInlineActive] = useState({});    // { field: boolean }
  const [inlinePrefixes, setInlinePrefixes] = useState({}); // { field: prefix }
  const chatEndRef = useRef(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const askQuestion = async (question) => {
    setIsLoading(true);
    setMessages(prev => [
      ...prev,
      { role: "user", content: question },
      { role: "assistant", content: "" },
    ]);

    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, user_id: userId, conversation_id: conversationId }),
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          const data = line.slice(6);
          if (data === "[DONE]") continue;
          try {
            const { chunk, clarify } = JSON.parse(data);
            if (chunk || clarify) {
              setMessages(prev => {
                const updated = [...prev];
                const last = updated[updated.length - 1];
                if (last?.role === "assistant") {
                  updated[updated.length - 1] = {
                    ...last,
                    content: chunk ? last.content + chunk : last.content,
                    clarify: clarify || last.clarify,
                  };
                }
                return updated;
              });
            }
          } catch {}
        }
      }
    } catch {
      setMessages(prev => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last?.role === "assistant" && !last.content) {
          updated[updated.length - 1] = { ...last, content: "❌ 서버 연결에 실패했습니다." };
        }
        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleSend = () => {
    if (input.trim()) {
      askQuestion(input.trim());
      setInput("");
    }
  };

  const isDirect = (option) =>
    option.label?.includes("직접") || option.value.endsWith(" ");

  const handleClarifyOption = (messageIndex, field, option) => {
    if (!option?.value || isLoading) return;
    if (isDirect(option)) {
      setInlineActive(prev => ({ ...prev, [field]: true }));
      setInlinePrefixes(prev => ({ ...prev, [field]: option.value }));
      return;
    }
    setInlineActive(prev => ({ ...prev, [field]: false }));
    setMessages(prev => prev.map((msg, idx) => {
      if (idx !== messageIndex) return msg;
      return {
        ...msg,
        clarifySelections: { ...(msg.clarifySelections || {}), [field]: option },
      };
    }));
  };

  const handleInlineConfirm = (messageIndex, field) => {
    const raw = inlineInputs[field]?.trim();
    if (!raw) return;
    const prefix = inlinePrefixes[field] || "";
    const fullValue = prefix + raw; // "나이는 만 " + "34" → "나이는 만 34"
    setMessages(prev => prev.map((msg, idx) => {
      if (idx !== messageIndex) return msg;
      return {
        ...msg,
        clarifySelections: {
          ...(msg.clarifySelections || {}),
          [field]: { label: raw, value: fullValue }, // 칩엔 "34", 전송엔 "나이는 만 34"
        },
      };
    }));
    setInlineInputs(prev => ({ ...prev, [field]: "" }));
    setInlineActive(prev => ({ ...prev, [field]: false }));
  };

  const handleClarifySubmit = (messageIndex) => {
    const message = messages[messageIndex];
    const selections = message?.clarifySelections || {};
    const selectedValues = message?.clarify?.items
      ?.map(item => selections[item.field]?.value)
      .filter(Boolean);

    if (!selectedValues?.length) return;
    askQuestion(selectedValues.join("\n"));
  };

  const renderMessageContent = (msg, idx) => {
    if (msg.role === "assistant" && msg.content === "") {
      return <span className="typing-indicator"><span /><span /><span /></span>;
    }

    const selections = msg.clarifySelections || {};
    const clarifyItems = msg.clarify?.items || [];
    const selectedCount = clarifyItems.filter(item => selections[item.field]).length;
    const canSubmit = selectedCount === clarifyItems.length && clarifyItems.length > 0 && !isLoading;

    return (
      <>
        <span dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
        {msg.role === "assistant" && clarifyItems.length > 0 && (
          <div className="clarify-panel">
            {clarifyItems.map(item => {
              const selected = selections[item.field];
              const chipOptions = item.options.filter(o => !isDirect(o));
              const directOption = item.options.find(o => isDirect(o));
              const showInline = inlineActive[item.field];

              return (
                <div className="clarify-group" key={item.field}>
                  <p className="clarify-question">{item.question}</p>

                  {/* 선택 완료 상태 */}
                  {selected ? (
                    <div className="clarify-options">
                      <button
                        className="clarify-chip selected"
                        type="button"
                        disabled={isLoading}
                        onClick={() => {
                          setMessages(prev => prev.map((m, i) => {
                            if (i !== idx) return m;
                            const next = { ...(m.clarifySelections || {}) };
                            delete next[item.field];
                            return { ...m, clarifySelections: next };
                          }));
                        }}
                      >
                        {selected.label} ✕
                      </button>
                    </div>
                  ) : (
                    <>
                      <div className="clarify-options">
                        {chipOptions.map(option => (
                          <button
                            key={`${item.field}-${option.label}`}
                            className="clarify-chip"
                            type="button"
                            disabled={isLoading}
                            onClick={() => handleClarifyOption(idx, item.field, option)}
                          >
                            {option.label}
                          </button>
                        ))}
                        {directOption && !showInline && (
                          <button
                            className="clarify-chip"
                            type="button"
                            disabled={isLoading}
                            onClick={() => handleClarifyOption(idx, item.field, directOption)}
                          >
                            {directOption.label}
                          </button>
                        )}
                      </div>

                      {/* 인라인 입력창 */}
                      {showInline && (
                        <div className="clarify-inline-input">
                          <input
                            type="text"
                            placeholder="직접 입력..."
                            value={inlineInputs[item.field] || ""}
                            autoFocus
                            onChange={e => setInlineInputs(prev => ({ ...prev, [item.field]: e.target.value }))}
                            onKeyDown={e => { if (e.key === "Enter") handleInlineConfirm(idx, item.field); }}
                          />
                          <button
                            className="clarify-inline-confirm"
                            type="button"
                            onClick={() => handleInlineConfirm(idx, item.field)}
                          >
                            확인
                          </button>
                        </div>
                      )}
                    </>
                  )}
                </div>
              );
            })}
            <div className="clarify-actions">
              <span className="clarify-progress">
                {selectedCount}/{clarifyItems.length} 선택
              </span>
              <button
                className="clarify-submit"
                type="button"
                disabled={!canSubmit}
                onClick={() => handleClarifySubmit(idx)}
              >
                완료
              </button>
            </div>
          </div>
        )}
      </>
    );
  };

  const questions = QUICK_QUESTIONS[category] || [];

  return (
    <div className="app">
      <div className="container">
        {/* Header */}
        <header className="header">
          <h1 className="main-title">
            <span className="title-bubble">💬</span>
            청년 정책 맞춤형 AI 상담 챗봇
          </h1>
          <p className="sub-title">안녕하세요, 무엇을 도와드릴까요?</p>
        </header>

        {/* Categories */}
        <section className="section">
          <p className="section-label">관심 분야를 선택해주세요</p>
          <div className="category-list">
            {CATEGORIES.map(cat => (
              <button
                key={cat}
                className={`cat-btn${category === cat ? " active" : ""}`}
                onClick={() => setCategory(cat)}
              >
                <span className="cat-icon">{CATEGORY_ICONS[cat]}</span>
                <span className="cat-label">{cat}</span>
              </button>
            ))}
          </div>
        </section>

        {/* Quick questions */}
        <section className="section">
          <p className="section-label">이런 질문은 어떠세요?</p>
          <div className="quick-grid">
            {questions.map((q, i) => (
              <button key={i} className="quick-chip" onClick={() => askQuestion(q)}>
                {q}
              </button>
            ))}
          </div>
        </section>

        {/* Chat card */}
        <div className="chat-card">
          <div className="chat-header">
            {isLoading && <span className="ai-badge">AI 상담 중...</span>}
          </div>

          <div className="chat-messages">
            {messages.length === 0 ? (
              <div className="chat-empty">위의 질문을 선택하거나 직접 입력해 시작해보세요!</div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`msg-row ${msg.role}`}>
                  {msg.role === "assistant" && (
                    <div className="avatar bot-avatar"><BotIcon /></div>
                  )}
                  <div className="msg-bubble">
                    {renderMessageContent(msg, idx)}
                  </div>
                  {msg.role === "user" && (
                    <div className="avatar user-avatar"><UserIcon /></div>
                  )}
                </div>
              ))
            )}
            <div ref={chatEndRef} />
          </div>

          <div className="input-bar">
            <input

              type="text"
              placeholder="무엇이든 물어보세요"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === "Enter") handleSend(); }}
            />
            <button className="send-btn" onClick={handleSend} type="button">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
