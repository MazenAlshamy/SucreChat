import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchHealth, listRooms } from "../api/client";
import ActionButton from "../components/ActionButton";
import StatusBanner from "../components/StatusBanner";
import { useSession } from "../context/SessionContext";

export default function HomePage() {
  const { user, summary } = useSession();
  const [health, setHealth] = useState(null);
  const [rooms, setRooms] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then((data) => {
        if (!cancelled) {
          setHealth(data);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
        }
      });
    listRooms()
      .then((data) => {
        if (!cancelled) {
          setRooms(data);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRooms([]);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [user]);

  return (
    <div className="stack">
      <section className="hero">
        <div>
          <p className="kicker">لوحة التحكم</p>
          <h1>SecureChat</h1>
          <p>
            أنشئ غرفة خاصة، أرسل رابط دعوة فريداً، ووافق على طلبات الانضمام قبل دخول أي مشارك.
            الأعضاء المعتمدون يتصلون بالصوت والصورة داخل المنصة.
          </p>
          {user ? <p className="welcome-line">مرحباً {user.display_name}</p> : null}
          <div className="hero-actions">
            <Link to="/create">
              <ActionButton>إنشاء غرفة</ActionButton>
            </Link>
            <Link to="/rooms">
              <ActionButton variant="secondary">غرفي</ActionButton>
            </Link>
            <Link to="/join">
              <ActionButton variant="ghost">الانضمام</ActionButton>
            </Link>
            <Link to="/">
              <ActionButton variant="ghost">الصفحة الرئيسية</ActionButton>
            </Link>
          </div>
        </div>
        <div className="card">
          <h2>حالة المنصة</h2>
          {health ? (
            <span className="status-chip">الخادم متصل — {health.database}</span>
          ) : error ? (
            <span className="status-chip danger">تعذر الاتصال بالخادم</span>
          ) : (
            <span className="status-chip warn">جارٍ التحقق من الخادم</span>
          )}
          <p className="small">{health?.message || error || "يتم فحص نقطة /api/health."}</p>
          {health?.media_available ? (
            <p className="small">
              الوسائط جاهزة عبر {health.media_provider === "livekit" ? "LiveKit" : "WebRTC"}.
            </p>
          ) : null}
          {summary.notifications || summary.join_requests || summary.messages ? (
            <p className="small">
              إشعارات: {summary.notifications} — طلبات: {summary.join_requests} — رسائل: {summary.messages}
            </p>
          ) : null}
        </div>
      </section>

      {rooms.length ? (
        <div className="card">
          <h2>غرفك</h2>
          {rooms.map((room) => (
            <p key={room.id}>
              <Link to={room.is_owner ? `/rooms/${room.id}` : `/rooms/${room.id}/meeting`}>
                {room.name} — {room.status}
                {room.is_owner ? ` — ${room.pending_requests} طلب معلق` : ""}
              </Link>
            </p>
          ))}
          <div className="form-actions">
            <Link to="/rooms">
              <ActionButton variant="ghost">كل الغرف</ActionButton>
            </Link>
          </div>
        </div>
      ) : null}

      <div className="page-grid">
        <article className="grid-card">
          <h2>غرف خاصة بدعوة</h2>
          <p>تُنشأ الغرف والدعوات في قاعدة البيانات، ولا يمنح الرابط دخولاً مباشراً.</p>
        </article>
        <article className="grid-card">
          <h2>موافقة قبل الدخول</h2>
          <p>يبقى الطلب معلقاً حتى يقبله المالك. العضوية المعتمدة وحدها تفتح واجهة الغرفة.</p>
        </article>
      </div>

      <StatusBanner title="الصوت والصورة">
        الأعضاء المعتمدون يتصلون بالصوت والصورة عبر WebRTC داخل المنصة. LiveKit اختياري عند توفر بياناته على الخادم.
      </StatusBanner>
    </div>
  );
}
