import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRooms } from "../api/client";
import ActionButton from "../components/ActionButton";
import PageHeader from "../components/PageHeader";
import StatusBanner from "../components/StatusBanner";
import { useSession } from "../context/SessionContext";

export default function RoomsPage() {
  const { user, summary } = useSession();
  const [rooms, setRooms] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listRooms()
      .then(setRooms)
      .catch((err) => setError(err.message));
  }, [user]);

  return (
    <div className="stack">
      <div className="card">
        <PageHeader
          kicker="لوحة الغرف"
          title="غرفي"
          description="الغرف التي تملكها أو انضممت إليها بعد الموافقة."
        />
        <div className="form-actions">
          <Link to="/create">
            <ActionButton>إنشاء غرفة</ActionButton>
          </Link>
          <Link to="/join">
            <ActionButton variant="secondary">الانضمام</ActionButton>
          </Link>
          <Link to="/app">
            <ActionButton variant="ghost">لوحة التحكم</ActionButton>
          </Link>
        </div>
      </div>
      {error ? <StatusBanner title="تعذر تحميل الغرف">{error}</StatusBanner> : null}
      <div className="card">
        {rooms.length ? (
          rooms.map((room) => (
            <article key={room.id} className="list-row">
              <div>
                <strong>{room.name}</strong>
                <p className="small">
                  {room.status === "active" ? "نشطة" : "مغلقة"} — الأعضاء: {room.member_count}/{room.max_participants}
                  {room.is_owner && room.pending_requests ? ` — طلبات معلّقة: ${room.pending_requests}` : ""}
                </p>
              </div>
              <div className="form-actions">
                <Link to={room.is_owner ? `/rooms/${room.id}` : `/rooms/${room.id}/meeting`}>
                  <ActionButton variant="secondary">{room.is_owner ? "إدارة" : "دخول"}</ActionButton>
                </Link>
                {room.status === "active" ? (
                  <Link to={`/rooms/${room.id}/meeting`}>
                    <ActionButton>الاجتماع</ActionButton>
                  </Link>
                ) : null}
              </div>
            </article>
          ))
        ) : (
          <p>لا غرف بعد. أنشئ غرفة أو اطلب الانضمام عبر دعوة.</p>
        )}
      </div>
      {summary.join_requests ? (
        <StatusBanner title="طلبات معلّقة">{summary.join_requests} طلب بانتظار قرارك.</StatusBanner>
      ) : null}
    </div>
  );
}
