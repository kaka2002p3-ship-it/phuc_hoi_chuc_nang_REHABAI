import { useEffect, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { Bot, History, Info, MessageCircle, Play, Plus, Send, Trash2, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';
import { authHeaders } from '../api';

type ExerciseAction = { type: 'start_exercise' | 'choose_exercise'; exercise_id?: number; label?: string; options?: { exercise_id: number; label: string }[] };
type Message = { role: 'user' | 'assistant'; content: string; action?: ExerciseAction };
type ConversationSummary = { id: string; title: string };

/**
 * Chat data is persisted and can outlive a frontend/backend deployment.
 * Never pass an arbitrary API value directly to JSX: React throws when an
 * object is rendered as a child, which used to make the whole app appear as
 * a blank white page after sending a message.
 */
function safeText(value: unknown, fallback = ''): string {
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean' || typeof value === 'bigint') return String(value);
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    for (const key of ['message', 'content', 'text', 'detail']) {
      if (key in record) {
        const nested = safeText(record[key]);
        if (nested) return nested;
      }
    }
    try {
      const serialized = JSON.stringify(value);
      if (serialized && serialized !== '{}') return serialized.slice(0, 4000);
    } catch {
      // Fall through to the user-friendly fallback for circular values.
    }
  }
  return fallback;
}

function normalizeMessage(value: unknown): Message | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  const role = item.role === 'user' ? 'user' : item.role === 'assistant' ? 'assistant' : null;
  if (!role) return null;
  const content = safeText(item.content, role === 'assistant' ? 'Mình chưa có nội dung trả lời.' : '');
  if (!content && role === 'user') return null;
  return { role, content };
}

function normalizeConversation(value: unknown): ConversationSummary | null {
  if (!value || typeof value !== 'object') return null;
  const item = value as Record<string, unknown>;
  if (typeof item.id !== 'string' || !item.id) return null;
  return { id: item.id, title: safeText(item.title, 'Hội thoại') };
}

const welcome: Message = {
  role: 'assistant',
  content: 'Chào bạn, mình là RehabAI Đồng hành 😊 Hôm nay bạn muốn tập một bài nhẹ, hỏi điều gì đó, hay chỉ trò chuyện một chút?'
};

export default function PatientChat() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([welcome]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [language, setLanguage] = useState<'auto'|'vi'|'en'>('vi');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const target = bottomRef.current;
    if (!target || typeof target.scrollIntoView !== 'function') return;
    try {
      target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch {
      // Scrolling is cosmetic. Older browsers/WebViews must never be allowed
      // to crash the whole chat widget because this API is missing/broken.
    }
  }, [messages, loading]);
  useEffect(() => {
    fetch('/api/chat/conversations', { headers: authHeaders(token) })
      .then(response => response.ok ? response.json() : [])
      .then(payload => setConversations(Array.isArray(payload)
        ? payload.map((item: unknown) => normalizeConversation(item)).filter((item: ConversationSummary | null): item is ConversationSummary => Boolean(item))
        : []))
      .catch(() => setConversations([]));
  }, [token, conversationId]);
  useEffect(() => {
    const openFromSuggestion = (event: Event) => {
      const prompt = (event as CustomEvent<string>).detail;
      setOpen(true);
      setHistoryOpen(false);
      if (typeof prompt === 'string' && prompt.trim()) setInput(prompt.trim());
    };
    window.addEventListener('rehabai:open-chat', openFromSuggestion);
    return () => window.removeEventListener('rehabai:open-chat', openFromSuggestion);
  }, []);

  const loadConversation = async (id: string) => {
    const response = await fetch(`/api/chat/conversations/${id}`, { headers: authHeaders(token) });
    if (!response.ok) return;
    const data = await response.json();
    setConversationId(id);
    const loaded: Message[] = Array.isArray(data?.messages)
      ? data.messages.map((item: unknown) => normalizeMessage(item)).filter((item: Message | null): item is Message => Boolean(item))
      : [];
    setMessages(loaded.length > 0 ? loaded : [welcome]);
    setHistoryOpen(false);
  };

  const startNewConversation = () => {
    setConversationId(null);
    setMessages([welcome]);
    setErrorMessage(null);
    setHistoryOpen(false);
  };

  const removeConversation = async (id: string) => {
    const response = await fetch(`/api/chat/conversations/${id}`, { method: 'DELETE', headers: authHeaders(token) });
    if (response.ok) {
      setConversations(items => items.filter(item => item.id !== id));
      if (conversationId === id) { setConversationId(null); setMessages([welcome]); }
    }
  };

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const content = input.trim();
    if (!content || loading) return;
    const next: Message[] = [...messages, { role: 'user', content }];
    setMessages(next);
    setInput('');
    setErrorMessage(null);
    setLoading(true);
    try {
      const activeSessionId = sessionStorage.getItem('rehabai_active_session');
      const requestBody = (sessionId: string | null, currentConversationId: string | null) => JSON.stringify({
        message: content,
        messages: next.slice(-12),
        conversation_id: currentConversationId,
        session_id: sessionId,
        language,
      });
      let response = await fetch('/api/chat', { method: 'POST', headers: authHeaders(token, true), body: requestBody(activeSessionId, conversationId) });
      // A browser tab can retain a session after a restart, logout, or user
      // switch. Stale session/conversation ids must not disable general chat.
      if (response.status === 404 && (activeSessionId || conversationId)) {
        sessionStorage.removeItem('rehabai_active_session');
        setConversationId(null);
        response = await fetch('/api/chat', { method: 'POST', headers: authHeaders(token, true), body: requestBody(null, null) });
      }
      if (!response.ok) {
        let detail = `HTTP ${response.status}`;
        try { const payload = await response.json(); if (typeof payload.detail === 'string') detail = payload.detail; } catch { /* keep status */ }
        throw new Error(detail);
      }
      const data = await response.json();
      const reply = safeText(data?.assistant?.message ?? data?.message, 'Mình chưa nhận được nội dung trả lời. Bạn thử lại nhé.');
      setConversationId(typeof data?.conversation_id === 'string' ? data.conversation_id : conversationId);
      setMessages(items => [...items, { role: 'assistant', content: reply }]);
    } catch (reason) {
      const detail = reason instanceof Error ? reason.message : 'Không thể kết nối máy chủ.';
      setErrorMessage(detail);
      setMessages(items => [...items, {
        role: 'assistant',
        content: 'Mình chưa gửi được tin nhắn. Bạn có thể thử lại; nếu đang tập và có triệu chứng bất thường, hãy dừng tập và liên hệ người thân hoặc nhân viên y tế.'
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="patient-chat">
      {open && (
        <section className="chat-panel" aria-label="RehabAI Đồng hành">
          <header className="chat-header">
            <div className="chat-title"><Bot size={21} /><div><strong>RehabAI Đồng hành</strong><small>Hỗ trợ và trò chuyện</small></div></div>
            <div className="chat-header-actions"><select className="chat-language-select" aria-label="Ngôn ngữ chatbot" value={language} onChange={e=>setLanguage(e.target.value as 'auto'|'vi'|'en')}><option value="auto">Auto</option><option value="vi">VI</option><option value="en">EN</option></select><button className={`chat-icon-button ${historyOpen ? 'active' : ''}`} onClick={() => setHistoryOpen(value => !value)} aria-label="Mở lịch sử hội thoại" aria-expanded={historyOpen}><History size={19}/>{conversations.length > 0 && <span className="chat-history-count">{Math.min(conversations.length, 9)}</span>}</button><button className="chat-icon-button" onClick={() => setOpen(false)} aria-label="Đóng trò chuyện"><X size={20} /></button></div>
          </header>
          <div className="chat-notice" role="note"><Info size={15}/><span>AI Coach hiện phân tích câu hỏi và dữ liệu buổi tập. Chưa hỗ trợ nhìn hoặc phân tích ảnh trực tiếp.</span></div>
          {historyOpen && <div className="chat-history-popover" aria-label="Lịch sử hội thoại"><div className="chat-history-heading"><strong>Lịch sử trò chuyện</strong><button type="button" onClick={startNewConversation}><Plus size={15}/> Cuộc trò chuyện mới</button></div>{conversations.length > 0 ? <div className="chat-conversations">{conversations.slice(0, 8).map(item => <div key={item.id} className={conversationId === item.id ? 'active' : ''}><button type="button" onClick={() => loadConversation(item.id)}>{item.title || 'Hội thoại'}</button><button type="button" aria-label="Xóa hội thoại" onClick={() => removeConversation(item.id)}><Trash2 size={14} /></button></div>)}</div> : <p className="chat-history-empty">Chưa có cuộc trò chuyện đã lưu.</p>}</div>}
          <div className="chat-messages" aria-live="polite">
            {messages.map((message, index) => <div key={index} className={`chat-message ${message.role}`}>
              <div className={`chat-bubble ${message.role}`}>{safeText(message.content, 'Mình chưa có nội dung trả lời.')}</div>
              {message.action?.type === 'start_exercise' && message.action.exercise_id && (
                <button className="chat-exercise-action" onClick={() => navigate(`/app/practice/${message.action!.exercise_id}`)}><Play size={15} /> Bắt đầu {safeText(message.action.label, 'bài tập')}</button>
              )}
              {message.action?.type === 'choose_exercise' && message.action.options?.map(option => (
                <button key={option.exercise_id} className="chat-exercise-action" onClick={() => navigate(`/app/practice/${option.exercise_id}`)}><Play size={15} /> {safeText(option.label, 'Bài tập')}</button>
              ))}
            </div>)}
            {loading && <div className="chat-bubble assistant chat-typing">Đang suy nghĩ…</div>}
            <div ref={bottomRef} />
          </div>
          {errorMessage && <div className="chat-error" role="alert">{errorMessage}</div>}
          <div className="chat-suggestions">
            {['Tôi muốn tâm sự', 'Tóm tắt buổi tập', 'Giải thích kết quả', 'Gợi ý ăn uống', 'Hướng dẫn dùng ứng dụng'].map(text => (
              <button key={text} onClick={() => setInput(text)}>{text}</button>
            ))}
          </div>
          <form className="chat-input" onSubmit={send}>
            <input value={input} onChange={event => setInput(event.target.value)} maxLength={2000} placeholder="Nhập điều bạn muốn hỏi…" aria-label="Tin nhắn" />
            <button type="submit" disabled={!input.trim() || loading} aria-label="Gửi"><Send size={18} /></button>
          </form>
          <p className="chat-emergency">Cấp cứu: gọi số cấp cứu tại nơi bạn đang ở.</p>
        </section>
      )}
      <button className="chat-launcher" onClick={() => setOpen(value => !value)} aria-label="Mở RehabAI Đồng hành">
        {open ? <X size={25} /> : <MessageCircle size={25} />}
        {!open && <span>Trò chuyện</span>}
      </button>
    </div>
  );
}
