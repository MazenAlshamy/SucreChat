import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../api/client";
import ActionButton from "../components/ActionButton";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import { useSession } from "../context/SessionContext";
import { formatClock } from "../utils/time";

export default function NotificationsPage() {
  const { refreshSummary } = useSession();
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function load() {
    const data = await listNotifications();
    setItems(data.items || []);
    setUnread(data.unread_count || 0);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function handleRead(item) {
    if (item.read) {
      return;
    }
    try {
      await markNotificationRead(item.id);
      await load();
      await refreshSummary();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleReadAll() {
    try {
      await markAllNotificationsRead();
      setMessage("عُلّمت كل الإشعارات كمقروءة.");
      await load();
      await refreshSummary();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="stack">
      <div className="card">
        <PageHeader
          kicker="صندوق الوارد"
          title="الإشعارات"
          description="طلبات الانضمام، الرسائل، ودخول أو مغادرة المشاركين."
        />
        <p className="small">غير المقروء: {unread}</p>
        <div className="form-actions">
          <ActionButton variant="secondary" onClick={handleReadAll} disabled={!unread}>
            تعليم الكل كمقروء
          </ActionButton>
          <Link to="/app">
            <ActionButton variant="ghost">لوحة التحكم</ActionButton>
          </Link>
          <Link to="/rooms">
            <ActionButton variant="ghost">غرفي</ActionButton>
          </Link>
        </div>
      </div>
      {error ? <StatusBanner title="تعذر التحميل">{error}</StatusBanner> : null}
      {message ? <StatusBanner title="تم" tone="success">{message}</StatusBanner> : null}
      <div className="card">
        {error ? (
          <p>تعذر عرض الإشعارات بسبب خطأ التحميل.</p>
        ) : items.length ? (
          items.map((item) => (
            <article key={item.id} className={`list-row ${item.read ? "" : "unread"}`}>
              <div>
                <strong>{item.title}</strong>
                <p className="small">
                  {item.body}
                  {item.room_name ? ` — ${item.room_name}` : ""}
                </p>
                <p className="small">{formatClock(item.created_at)}</p>
              </div>
              <div className="form-actions">
                {item.link ? (
                  <Link to={item.link} onClick={() => handleRead(item)}>
                    <ActionButton variant="secondary">فتح</ActionButton>
                  </Link>
                ) : null}
                {item.read ? null : (
                  <ActionButton variant="ghost" onClick={() => handleRead(item)}>
                    مقروء
                  </ActionButton>
                )}
              </div>
            </article>
          ))
        ) : (
          <p>لا إشعارات بعد.</p>
        )}
      </div>
    </div>
  );
}
