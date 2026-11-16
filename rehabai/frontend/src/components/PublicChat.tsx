import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Bot, Info, MessageCircle, Send, X } from 'lucide-react';

type Message = { role: 'user' | 'assistant'; content: string };
const welcome: Message = { role: 'assistant', content: 'Chào bạn! Mình có thể giới thiệu về RehabAI, các bài tập, cách sử dụng website và những lưu ý an toàn chung.' };

// Public API responses can be cached by a proxy or come from an older
// backend version. React cannot render an object as a child, so normalize
// every value before it enters chat state or JSX.
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
      // Use the fallback for circular/unserializable payloads.
    }
  }
  return fallback;
}

export default function PublicChat() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([welcome]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [language, setLanguage] = useState<'auto' | 'vi' | 'en'>('vi');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const target = bottomRef.current;
    if (!target || typeof target.scrollIntoView !== 'function') return;
    try {
      target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch {
      // Auto-scroll is optional and must not take down the public website.
    }
  }, [messages, loading]);
  useEffect(() => {
    const handler = (event: Event) => {
      const prompt = (event as CustomEvent<string>).detail;
      setOpen(true);
      if (typeof prompt === 'string') setInput(prompt);
    };
    window.addEventListener('rehabai:open-public-chat', handler);
    return () => window.removeEventListener('rehabai:open-public-chat', handler);
  }, []);

  const send = async (event: FormEvent) => {
    event.preventDefault();
    const content = input.trim();
    if (!content || loading) return;
    const next = [...messages, { role: 'user' as const, content }];
    setMessages(next); setInput(''); setLoading(true);
    try {
      const response = await fetch('/api/public-chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ message: content, messages: next.slice(-8), language }) });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const data: unknown = await response.json();
      const payload = data && typeof data === 'object' ? data as Record<string, unknown> : {};
      const assistant = payload.assistant && typeof payload.assistant === 'object'
        ? payload.assistant as Record<string, unknown>
        : undefined;
      const reply = safeText(assistant?.message ?? payload.message, 'Mình chưa thể trả lời lúc này.');
      setMessages(items => [...items, { role: 'assistant', content: reply }]);
    } catch {
      setMessages(items => [...items, { role: 'assistant', content: 'Chatbot tạm thời chưa khả dụng. Bạn có thể xem các trang Bài tập, Kiến thức hoặc FAQ để tìm thông tin đã được kiểm duyệt.' }]);
    } finally { setLoading(false); }
  };

  return <div className="public-chat">
    {open && <section className="public-chat-panel" aria-label="Chatbot RehabAI công khai">
      <header className="public-chat-header"><div><Bot size={20}/><span><strong>Hỏi RehabAI</strong><small>Trợ lý thông tin công khai</small></span></div><div><select value={language} onChange={event => setLanguage(event.target.value as 'auto' | 'vi' | 'en')} aria-label="Ngôn ngữ"><option value="vi">VI</option><option value="en">EN</option><option value="auto">Auto</option></select><button type="button" onClick={() => setOpen(false)} aria-label="Đóng chatbot"><X size={18}/></button></div></header>
      <div className="public-chat-notice"><Info size={14}/><span>Không truy cập tài khoản, lịch sử tập hoặc dữ liệu cá nhân.</span></div>
      <div className="public-chat-messages" aria-live="polite">{messages.map((message, index) => <div className={`public-chat-message ${message.role}`} key={`${message.role}-${index}`}><div>{safeText(message.content, 'Mình chưa có nội dung trả lời.')}</div></div>)}{loading && <div className="public-chat-message assistant"><div className="public-chat-typing">Đang suy nghĩ…</div></div>}<div ref={bottomRef}/></div>
      <div className="public-chat-suggestions">{['RehabAI là gì?', 'Có những bài tập nào?', 'Dữ liệu của tôi có riêng tư không?'].map(item => <button type="button" key={item} onClick={() => setInput(item)}>{item}</button>)}</div>
      <form className="public-chat-input" onSubmit={send}><input value={input} onChange={event => setInput(event.target.value)} maxLength={2000} placeholder="Đặt câu hỏi…" aria-label="Tin nhắn"/><button type="submit" disabled={!input.trim() || loading} aria-label="Gửi"><Send size={17}/></button></form>
    </section>}
    <button className="public-chat-launcher" type="button" onClick={() => setOpen(value => !value)} aria-label="Mở chatbot RehabAI">{open ? <X size={22}/> : <MessageCircle size={22}/>}<span>Hỏi RehabAI</span></button>
  </div>;
}
