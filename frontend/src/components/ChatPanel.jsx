import { useEffect, useRef, useState } from "react";
import ActionButton from "./ActionButton";
import { canSendChat } from "../utils/chat";
import { formatClock } from "../utils/time";

export default function ChatPanel({
  title,
  messages,
  currentUserId,
  onSend,
  error,
  onRead,
  loading = false,
  unreadCount = 0,
}) {
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [failedBody, setFailedBody] = useState("");
  const listRef = useRef(null);

  useEffect(() => {
    onRead?.();
  }, [onRead]);

  useEffect(() => {
    const node = listRef.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [messages]);

  async function submit(body) {
    const check = canSendChat(body);
    if (!check.ok || sending) {
      return;
    }
    setSending(true);
    setFailedBody("");
    try {
      await onSend(check.body);
      setDraft("");
    } catch {
      setFailedBody(check.body);
    } finally {
      setSending(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    await submit(draft);
  }

  return (
    <aside className="chat-panel">
      <div className="chat-head">
        <h2>{title || "محادثة الغرفة"}</h2>
        {unreadCount ? <span className="status-chip warn">جديد: {unreadCount}</span> : null}
      </div>
      <div className="chat-list" ref={listRef}>
        {loading && !messages.length ? <p className="small">جارٍ تحميل المحادثة.</p> : null}
        {!loading && !messages.length ? (
          <p className="small">لا رسائل بعد. اكتب لأعضاء الغرفة المعتمدين فقط.</p>
        ) : null}
        {messages.map((item) => {
          const mine = item.mine || item.user_id === currentUserId;
          return (
            <article key={item.id} className={`chat-bubble ${mine ? "mine" : ""}`}>
              <div className="chat-meta">
                <strong>{mine ? "أنت" : item.display_name}</strong>
                <span>{formatClock(item.created_at)}</span>
              </div>
              <p>{item.body}</p>
            </article>
          );
        })}
      </div>
      {sending ? <p className="small">جارٍ إرسال الرسالة.</p> : null}
      {error ? <p className="small chat-error">{error}</p> : null}
      {failedBody ? (
        <div className="form-actions">
          <ActionButton variant="secondary" onClick={() => submit(failedBody)} disabled={sending}>
            إعادة المحاولة
          </ActionButton>
        </div>
      ) : null}
      <form className="chat-form" onSubmit={handleSubmit}>
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          maxLength={1000}
          placeholder="اكتب رسالة"
          aria-label="نص الرسالة"
          disabled={sending}
        />
        <ActionButton type="submit" disabled={sending || !draft.trim()}>
          إرسال
        </ActionButton>
      </form>
    </aside>
  );
}
